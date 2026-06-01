#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日股价更新脚本
从新浪财经获取最新价格，更新数据库中的持仓数据
"""

import os
import re
import sqlite3
import requests
from datetime import datetime

# 禁用代理
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'invest.db')

session = requests.Session()
session.trust_env = False


def get_sina_code(stock_code):
    """转换股票代码为新浪财经格式"""
    if stock_code.startswith('sh') or stock_code.startswith('sz'):
        return stock_code
    
    # 处理港股
    if '.HK' in stock_code:
        code = stock_code.replace('.HK', '')
        return f'hk{code}'
    
    # 处理美股
    if stock_code.startswith('us') or len(stock_code) <= 5:
        return f'gb_{stock_code.lower().replace("us", "")}'
    
    # A股
    code = stock_code.split('.')[0] if '.' in stock_code else stock_code
    if code.startswith('6'):
        return f'sh{code}'
    else:
        return f'sz{code}'


def fetch_a_share_price(sina_code):
    """获取A股实时价格"""
    try:
        url = f'https://hq.sinajs.cn/list={sina_code}'
        headers = {'Referer': 'https://finance.sina.com.cn'}
        r = session.get(url, headers=headers, timeout=10)
        
        match = re.search(r'var hq_str_\w+="(.+)"', r.text)
        if not match:
            return None
        
        fields = match.group(1).split(',')
        if len(fields) < 32:
            return None
        
        price = float(fields[3])
        prev_close = float(fields[2])
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        return {
            'price': price,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2)
        }
    except Exception as e:
        print(f"  Error fetching {sina_code}: {e}")
        return None


def fetch_hk_price(sina_code):
    """获取港股实时价格"""
    try:
        url = f'https://hq.sinajs.cn/list={sina_code}'
        headers = {'Referer': 'https://finance.sina.com.cn'}
        r = session.get(url, headers=headers, timeout=10)
        
        match = re.search(r'var hq_str_\w+="(.+)"', r.text)
        if not match:
            return None
        
        fields = match.group(1).split(',')
        if len(fields) < 10:
            return None
        
        price = float(fields[6]) if fields[6] else 0
        prev_close = float(fields[3]) if fields[3] else 0
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        return {
            'price': price,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2)
        }
    except Exception as e:
        print(f"  Error fetching {sina_code}: {e}")
        return None


def fetch_us_price(sina_code):
    """获取美股实时价格"""
    try:
        url = f'https://hq.sinajs.cn/list={sina_code}'
        headers = {'Referer': 'https://finance.sina.com.cn'}
        r = session.get(url, headers=headers, timeout=10)
        
        match = re.search(r'var hq_str_\w+="(.+)"', r.text)
        if not match:
            return None
        
        fields = match.group(1).split(',')
        if len(fields) < 13:
            return None
        
        price = float(fields[1]) if fields[1] else 0
        change = float(fields[4]) if fields[4] else 0
        prev_close = float(fields[5]) if fields[5] else 0
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        return {
            'price': price,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2)
        }
    except Exception as e:
        print(f"  Error fetching {sina_code}: {e}")
        return None


def update_prices():
    """更新所有持仓的股价"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始更新股价...")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有持仓
    cursor.execute("SELECT id, stock_code, stock_name, quantity, cost_price FROM holdings")
    holdings = cursor.fetchall()
    
    print(f"共 {len(holdings)} 只持仓需要更新")
    
    updated = 0
    failed = 0
    
    for h in holdings:
        stock_code = h['stock_code']
        stock_name = h['stock_name']
        
        # 转换代码
        sina_code = get_sina_code(stock_code)
        
        # 根据市场类型获取价格
        if sina_code.startswith('hk'):
            result = fetch_hk_price(sina_code)
        elif sina_code.startswith('gb_'):
            result = fetch_us_price(sina_code)
        else:
            result = fetch_a_share_price(sina_code)
        
        if result and result['price'] > 0:
            new_price = result['price']
            quantity = h['quantity']
            cost_price = h['cost_price']
            market_value = quantity * new_price
            profit_loss = (new_price - cost_price) * quantity
            profit_rate = (new_price - cost_price) / cost_price if cost_price > 0 else 0
            
            cursor.execute("""
                UPDATE holdings SET 
                    current_price = ?,
                    market_value = ?,
                    profit_loss = ?,
                    profit_rate = ?,
                    updated_at = ?
                WHERE id = ?
            """, (new_price, round(market_value, 2), round(profit_loss, 2), 
                  round(profit_rate, 4), datetime.now().isoformat(), h['id']))
            
            updated += 1
            print(f"  ✓ {stock_code} {stock_name}: ¥{new_price}")
        else:
            failed += 1
            print(f"  ✗ {stock_code} {stock_name}: 获取失败")
    
    conn.commit()
    
    # 更新行业配置的金额
    cursor.execute("""
        SELECT industry, SUM(market_value) as total_value 
        FROM holdings 
        GROUP BY industry
    """)
    industry_data = cursor.fetchall()
    
    # 计算总资产
    cursor.execute("SELECT SUM(market_value) FROM holdings")
    total_assets = cursor.fetchone()[0] or 0
    
    for ind in industry_data:
        if ind['industry']:
            value_pct = round(ind['total_value'] / total_assets * 100, 1) if total_assets > 0 else 0
            cursor.execute("""
                UPDATE industry_allocation SET 
                    value = ?,
                    amount = ?
                WHERE name = ?
            """, (value_pct, round(ind['total_value'], 2), ind['industry']))
    
    conn.commit()
    conn.close()
    
    print(f"\n更新完成: 成功 {updated} 只, 失败 {failed} 只")
    print(f"总资产: ¥{total_assets:,.2f}")
    
    return {'updated': updated, 'failed': failed, 'total_assets': total_assets}


if __name__ == '__main__':
    update_prices()
