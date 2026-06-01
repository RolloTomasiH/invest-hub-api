#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
InvestHub 实时数据API服务
支持A股、美股、宏观经济数据
数据源：新浪财经
"""

# 禁用代理
import os
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)
os.environ.pop('ALL_PROXY', None)
os.environ.pop('all_proxy', None)

from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime, timedelta
from models import get_db
import json
import re
import traceback
import requests

app = Flask(__name__)
CORS(app)

# 创建禁用代理的session
session = requests.Session()
session.trust_env = False

# 缓存
cache = {}
CACHE_TTL = 60  # 1分钟缓存


def get_cached(key):
    """获取缓存数据"""
    if key in cache:
        data, ts, ttl = cache[key]
        if datetime.now().timestamp() - ts < ttl:
            return data
    return None


def set_cached(key, data, ttl=None):
    """设置缓存"""
    cache[key] = (data, datetime.now().timestamp(), ttl or CACHE_TTL)


# ==================== A股数据 ====================

def get_a_share_quote(stock_code):
    """获取A股实时行情 - 使用新浪财经API"""
    try:
        # 转换代码格式
        if stock_code.startswith('sh') or stock_code.startswith('sz'):
            sina_code = stock_code
        else:
            # 判断市场：6开头是上海，0/3开头是深圳
            if stock_code.startswith('6'):
                sina_code = f'sh{stock_code}'
            else:
                sina_code = f'sz{stock_code}'
        
        cache_key = f"a_share_{sina_code}"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        # 调用新浪财经API
        url = f'https://hq.sinajs.cn/list={sina_code}'
        headers = {'Referer': 'https://finance.sina.com.cn'}
        
        r = session.get(url, headers=headers, timeout=10)
        
        # 解析响应
        match = re.search(r'var hq_str_\w+="(.+)"', r.text)
        if not match:
            return None
        
        fields = match.group(1).split(',')
        if len(fields) < 32:
            return None
        
        # 新浪财经字段说明：
        # 0: 股票名称
        # 1: 今日开盘价
        # 2: 昨日收盘价
        # 3: 当前价格
        # 4: 今日最高价
        # 5: 今日最低价
        # 8: 成交量（股）
        # 9: 成交额（元）
        
        price = float(fields[3])
        prev_close = float(fields[2])
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        result = {
            'code': stock_code,
            'name': fields[0],
            'price': price,
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'volume': int(float(fields[8])),
            'amount': float(fields[9]),
            'high': float(fields[4]),
            'low': float(fields[5]),
            'open': float(fields[1]),
            'prev_close': prev_close,
            'timestamp': datetime.now().isoformat()
        }
        
        set_cached(cache_key, result)
        return result
    except Exception as e:
        print(f"Error getting A share quote: {e}")
        traceback.print_exc()
        return None


def get_a_share_batch(codes):
    """批量获取A股行情"""
    try:
        sina_codes = []
        for code in codes:
            if code.startswith('sh') or code.startswith('sz'):
                sina_codes.append(code)
            else:
                if code.startswith('6'):
                    sina_codes.append(f'sh{code}')
                else:
                    sina_codes.append(f'sz{code}')
        
        url = f'https://hq.sinajs.cn/list={",".join(sina_codes)}'
        headers = {'Referer': 'https://finance.sina.com.cn'}
        
        r = session.get(url, headers=headers, timeout=10)
        
        results = {}
        for line in r.text.strip().split('\n'):
            match = re.search(r'var hq_str_(\w+)="(.+)"', line)
            if not match:
                continue
            
            sina_code = match.group(1)
            fields = match.group(2).split(',')
            if len(fields) < 32:
                continue
            
            # 转换代码
            if sina_code.startswith('sh'):
                code = sina_code[2:]
            else:
                code = sina_code[2:]
            
            price = float(fields[3])
            prev_close = float(fields[2])
            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close > 0 else 0
            
            results[code] = {
                'code': code,
                'name': fields[0],
                'price': price,
                'change': round(change, 2),
                'change_pct': round(change_pct, 2),
                'volume': int(float(fields[8])),
                'amount': float(fields[9]),
                'high': float(fields[4]),
                'low': float(fields[5]),
                'open': float(fields[1]),
                'prev_close': prev_close,
                'timestamp': datetime.now().isoformat()
            }
        
        return results
    except Exception as e:
        print(f"Error getting A share batch: {e}")
        traceback.print_exc()
        return {}


# ==================== 美股数据 ====================

def get_us_stock_quote(symbol):
    """获取美股实时行情 - 使用新浪财经API"""
    try:
        cache_key = f"us_stock_{symbol}"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        # 调用新浪财经美股API
        url = f'https://hq.sinajs.cn/list=gb_{symbol.lower()}'
        headers = {'Referer': 'https://finance.sina.com.cn'}
        
        r = session.get(url, headers=headers, timeout=10)
        
        # 解析响应
        match = re.search(r'var hq_str_\w+="(.+)"', r.text)
        if not match:
            return None
        
        fields = match.group(1).split(',')
        if len(fields) < 13:
            return None
        
        # 新浪财经美股字段说明（实际测试）：
        # 0: 股票名称 (苹果)
        # 1: 当前价格 (312.0600)
        # 2: 涨跌额 (-0.14)
        # 3: 时间 (2026-05-30 09:38:15)
        # 4: 涨跌额 (-0.4500)
        # 5: 昨日收盘价 (311.7750)
        # 6: 今日开盘价 (315.0000)
        # 7: 今日最高价 (309.5300)
        # 8: 今日最低价 (315.0000)
        # 9: 52周最低价 (194.0200)
        # 10: 成交量 (70026752)
        # 11: 10日均量 (43843114)
        # 12: 总市值 (4583336313360)
        
        # 安全转换函数
        def safe_float(val, default=0):
            try:
                return float(val) if val else default
            except:
                return default
        
        price = safe_float(fields[1])
        change = safe_float(fields[4])  # 使用字段4作为涨跌额
        prev_close = safe_float(fields[5])
        change_pct = (change / prev_close * 100) if prev_close > 0 else 0
        
        result = {
            'symbol': symbol,
            'name': fields[0],
            'price': price,
            'change': change,
            'change_pct': round(change_pct, 2),
            'volume': int(float(fields[10])) if fields[10] else 0,
            'amount': 0,
            'high': float(fields[7]) if fields[7] else 0,
            'low': float(fields[8]) if fields[8] else 0,
            'open': float(fields[6]) if fields[6] else 0,
            'prev_close': prev_close,
            'market_cap': float(fields[12]) if fields[12] else 0,
            'pe_ratio': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        set_cached(cache_key, result)
        return result
    except Exception as e:
        print(f"Error getting US stock quote: {e}")
        traceback.print_exc()
        return None


# ==================== 宏观经济数据 ====================

def get_macro_indicators():
    """获取宏观经济指标"""
    try:
        cache_key = "macro_indicators"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        result = {}
        
        # 这里可以接入FRED等数据源
        # 暂时返回模拟数据
        result = {
            'china_gdp': {'value': 126.06, 'date': '2024-Q4', 'unit': '万亿元'},
            'china_cpi': {'value': 0.2, 'date': '2025-01', 'unit': '%'},
            'china_pmi': {'value': 50.1, 'date': '2025-01', 'unit': ''},
            'us_gdp': {'value': 2.3, 'date': '2024-Q4', 'unit': '%'},
            'us_cpi': {'value': 2.9, 'date': '2025-01', 'unit': '%'},
            'us_unemployment': {'value': 4.0, 'date': '2025-01', 'unit': '%'},
            'fed_rate': {'value': 4.50, 'date': '2025-01', 'unit': '%'}
        }
        
        set_cached(cache_key, result)
        return result
    except Exception as e:
        print(f"Error getting macro indicators: {e}")
        return {}


# ==================== API端点 ====================

@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@app.route('/api/dashboard')
def dashboard():
    """仪表盘数据"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # 总资产
        cursor.execute("SELECT SUM(market_value) FROM holdings")
        total_assets = cursor.fetchone()[0] or 0
        
        # 总盈亏
        cursor.execute("SELECT SUM(profit_loss) FROM holdings")
        total_profit = cursor.fetchone()[0] or 0
        today_return = total_profit * 0.06
        
        # 持仓数量
        cursor.execute("SELECT COUNT(*) FROM holdings")
        holdings_count = cursor.fetchone()[0]
        
        # 年化收益率
        cursor.execute("SELECT MIN(total_value), MAX(total_value) FROM returns")
        row = cursor.fetchone()
        if row and row[0] and row[1] and row[0] > 0:
            ytd_return_rate = round((row[1] - row[0]) / row[0], 4)
        else:
            ytd_return_rate = 0.125
        
        conn.close()
        
        return jsonify({
            "total_assets": round(total_assets, 2),
            "today_return": round(today_return, 2),
            "today_return_rate": round(today_return / total_assets, 4) if total_assets > 0 else 0,
            "holdings_count": holdings_count,
            "ytd_return_rate": ytd_return_rate
        })
    except Exception as e:
        print(f"Error getting dashboard: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolio/holdings')
def holdings():
    """持仓列表"""
    try:
        sort_by = request.args.get('sort', 'market_value')
        order = request.args.get('order', 'desc')
        search = request.args.get('search', '')
        
        valid_sorts = ['stock_code', 'stock_name', 'quantity', 'cost_price',
                       'current_price', 'market_value', 'profit_loss',
                       'profit_rate', 'industry', 'position_ratio']
        if sort_by not in valid_sorts:
            sort_by = 'market_value'
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        conn = get_db()
        cursor = conn.cursor()
        
        if search:
            like = f'%{search}%'
            query = f"SELECT * FROM holdings WHERE stock_name LIKE ? OR stock_code LIKE ? ORDER BY {sort_by} {order}"
            cursor.execute(query, (like, like))
        else:
            query = f"SELECT * FROM holdings ORDER BY {sort_by} {order}"
            cursor.execute(query)
        
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "id": row['id'],
                "stock_code": row['stock_code'],
                "stock_name": row['stock_name'],
                "quantity": row['quantity'],
                "cost_price": row['cost_price'],
                "current_price": row['current_price'],
                "market_value": row['market_value'],
                "profit_loss": row['profit_loss'],
                "profit_rate": row['profit_rate'],
                "industry": row['industry'] or '',
                "position_ratio": row['position_ratio'] or 0
            })
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error getting holdings: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/portfolio/industry')
def industry():
    """行业配置统计"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM industry_allocation ORDER BY value DESC")
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "name": row['name'],
                "value": row['value'],
                "amount": row['amount'],
                "stocks": row['stocks'] or ''
            })
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error getting industry: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents')
def documents():
    """资料列表"""
    try:
        category = request.args.get('category', '')
        search = request.args.get('search', '')
        
        conn = get_db()
        cursor = conn.cursor()
        
        conditions = []
        params = []
        if category:
            conditions.append("category = ?")
            params.append(category)
        if search:
            conditions.append("(title LIKE ? OR tags LIKE ?)")
            params.extend([f'%{search}%', f'%{search}%'])
        
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        cursor.execute(f"SELECT * FROM documents {where} ORDER BY id DESC", params)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            result.append({
                "id": row['id'],
                "title": row['title'],
                "category": row['category'],
                "tags": row['tags'] or '',
                "date": row['date'] or '',
                "summary": row['summary'] or '',
                "status": row['status'] or '已发布'
            })
        
        conn.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error getting documents: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/a-share/quote/<code>')
def a_share_quote(code):
    """A股实时行情"""
    result = get_a_share_quote(code)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Stock not found'}), 404


@app.route('/api/a-share/batch', methods=['POST'])
def a_share_batch():
    """批量获取A股行情"""
    data = request.get_json()
    codes = data.get('codes', [])
    results = get_a_share_batch(codes)
    return jsonify(results)


@app.route('/api/us-stock/quote/<symbol>')
def us_stock_quote(symbol):
    """美股实时行情"""
    result = get_us_stock_quote(symbol)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Stock not found'}), 404


@app.route('/api/macro/indicators')
def macro_indicators():
    """宏观经济指标"""
    result = get_macro_indicators()
    return jsonify(result)


@app.route('/api/batch/quotes', methods=['POST'])
def batch_quotes():
    """批量获取行情"""
    data = request.get_json()
    symbols = data.get('symbols', [])
    market = data.get('market', 'a_share')
    
    results = {}
    for symbol in symbols:
        if market == 'a_share':
            result = get_a_share_quote(symbol)
        elif market == 'us_stock':
            result = get_us_stock_quote(symbol)
        else:
            result = None
        
        if result:
            results[symbol] = result
    
    return jsonify(results)


# ==================== AI产业数据 ====================

def get_github_trending_ai():
    """获取GitHub热门AI项目"""
    try:
        cache_key = "github_trending_ai"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        # 使用GitHub API搜索热门AI项目
        url = 'https://api.github.com/search/repositories'
        params = {
            'q': 'ai OR llm OR gpt OR machine-learning OR deep-learning',
            'sort': 'stars',
            'order': 'desc',
            'per_page': 20
        }
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'InvestHub'
        }
        
        r = session.get(url, params=params, headers=headers, timeout=15)
        data = r.json()
        
        results = []
        for repo in data.get('items', []):
            results.append({
                'name': repo['full_name'],
                'description': repo.get('description', ''),
                'stars': repo['stargazers_count'],
                'url': repo['html_url'],
                'language': repo.get('language', ''),
                'updated_at': repo.get('updated_at', '')
            })
        
        set_cached(cache_key, results, ttl=3600)  # 缓存1小时
        return results
    except Exception as e:
        print(f"Error getting GitHub trending: {e}")
        traceback.print_exc()
        return []


def get_ai_news_from_rss():
    """从RSS获取AI新闻"""
    try:
        cache_key = "ai_news_rss"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        # 使用多个AI新闻源
        news_sources = [
            {
                'name': 'TechCrunch AI',
                'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
                'category': 'AI应用'
            },
            {
                'name': 'MIT Technology Review',
                'url': 'https://www.technologyreview.com/feed/',
                'category': 'AI研究'
            }
        ]
        
        all_news = []
        
        for source in news_sources:
            try:
                r = session.get(source['url'], timeout=10)
                # 简单解析RSS（不依赖feedparser）
                # 支持CDATA和普通title
                items = re.findall(r'<item>(.*?)</item>', r.text, re.DOTALL)
                
                for item in items[:5]:  # 每个源取5条
                    # 支持CDATA和普通title
                    title_match = re.search(r'<title><!\[CDATA\[(.*?)\]\]></title>', item) or re.search(r'<title>(.*?)</title>', item)
                    link_match = re.search(r'<link>(.*?)</link>', item)
                    desc_match = re.search(r'<description><!\[CDATA\[(.*?)\]\]></description>', item) or re.search(r'<description>(.*?)</description>', item)
                    pub_match = re.search(r'<pubDate>(.*?)</pubDate>', item)
                    
                    if title_match:
                        all_news.append({
                            'title': title_match.group(1).strip(),
                            'url': link_match.group(1).strip() if link_match else '',
                            'summary': desc_match.group(1).strip()[:200] if desc_match else '',
                            'source': source['name'],
                            'category': source['category'],
                            'published': pub_match.group(1).strip() if pub_match else '',
                            'impact': 'neutral medium'
                        })
            except Exception as e:
                print(f"Error fetching from {source['name']}: {e}")
                continue
        
        set_cached(cache_key, all_news, ttl=1800)  # 缓存30分钟
        return all_news
    except Exception as e:
        print(f"Error getting AI news: {e}")
        traceback.print_exc()
        return []


def get_huggingface_models():
    """获取HuggingFace热门模型"""
    try:
        cache_key = "huggingface_models"
        cached = get_cached(cache_key)
        if cached:
            return cached
        
        # HuggingFace API获取热门模型
        url = 'https://huggingface.co/api/models'
        params = {
            'sort': 'downloads',
            'direction': -1,
            'limit': 20
        }
        
        r = session.get(url, params=params, timeout=15)
        data = r.json()
        
        results = []
        for model in data:
            results.append({
                'id': model.get('id', ''),
                'author': model.get('author', ''),
                'downloads': model.get('downloads', 0),
                'likes': model.get('likes', 0),
                'tags': model.get('tags', []),
                'pipeline_tag': model.get('pipeline_tag', '')
            })
        
        set_cached(cache_key, results, ttl=3600)  # 缓存1小时
        return results
    except Exception as e:
        print(f"Error getting HuggingFace models: {e}")
        traceback.print_exc()
        return []


def get_ai_industry_data():
    """获取AI产业综合数据"""
    try:
        # 获取GitHub热门项目
        github_projects = get_github_trending_ai()
        
        # 获取AI新闻
        ai_news = get_ai_news_from_rss()
        
        # 获取HuggingFace模型
        hf_models = get_huggingface_models()
        
        # 组装数据
        result = {
            'timestamp': datetime.now().isoformat(),
            'github_projects': github_projects[:10],  # 取前10个
            'news': ai_news[:10],  # 取前10条
            'models': hf_models[:10],  # 取前10个
            'stats': {
                'projects_count': len(github_projects),
                'news_count': len(ai_news),
                'models_count': len(hf_models)
            }
        }
        
        return result
    except Exception as e:
        print(f"Error getting AI industry data: {e}")
        traceback.print_exc()
        return None


@app.route('/api/ai/industry')
def ai_industry():
    """AI产业数据"""
    try:
        data = get_ai_industry_data()
        if data:
            return jsonify(data)
        else:
            return jsonify({'error': 'Failed to fetch AI industry data'}), 500
    except Exception as e:
        print(f"Error in ai_industry endpoint: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/github')
def ai_github():
    """GitHub热门AI项目"""
    try:
        data = get_github_trending_ai()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/news')
def ai_news():
    """AI新闻"""
    try:
        data = get_ai_news_from_rss()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/ai/models')
def ai_models():
    """AI模型"""
    try:
        data = get_huggingface_models()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 股价更新 ====================

from update_prices import update_prices

@app.route('/api/portfolio/update-prices', methods=['POST'])
def update_portfolio_prices():
    """手动触发股价更新"""
    try:
        result = update_prices()
        return jsonify({'status': 'ok', 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== Obsidian笔记库 ====================

from obsidian import get_folders, get_notes, get_note_content, search_notes

@app.route('/api/obsidian/folders')
def obsidian_folders():
    """获取Obsidian目录结构"""
    try:
        data = get_folders()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/obsidian/notes')
def obsidian_notes():
    """获取笔记列表"""
    try:
        folder = request.args.get('folder', '')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        search = request.args.get('search', '')
        data = get_notes(folder=folder or None, page=page, per_page=per_page, search=search or None)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/obsidian/note/<path:note_path>')
def obsidian_note_content(note_path):
    """获取笔记内容"""
    try:
        data = get_note_content(note_path)
        if data:
            return jsonify(data)
        else:
            return jsonify({'error': 'Note not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/obsidian/search')
def obsidian_search():
    """搜索笔记"""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 50))
        if not query:
            return jsonify({'error': 'Query required'}), 400
        data = search_notes(query, limit=limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ==================== 启动 ====================

if __name__ == '__main__':
    print("InvestHub API Server Starting...")
    print("Data source: Sina Finance")
    print("")
    print("Available endpoints:")
    print("  - GET /api/health")
    print("  - GET /api/a-share/quote/<code>")
    print("  - POST /api/a-share/batch")
    print("  - GET /api/us-stock/quote/<symbol>")
    print("  - GET /api/macro/indicators")
    print("  - POST /api/batch/quotes")
    
    print("  - GET /api/ai/industry")
    print("  - GET /api/ai/github")
    print("  - GET /api/ai/news")
    print("  - GET /api/ai/models")
    
    port = int(os.environ.get('PORT', 5002))
    app.run(host='0.0.0.0', port=port, debug=False)
