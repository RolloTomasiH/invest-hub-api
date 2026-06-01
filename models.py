import sqlite3
import os

# 数据库路径：本地用 backend/data/，云端用当前目录
LOCAL_DB = os.path.join(os.path.dirname(__file__), '..', 'backend', 'data', 'invest.db')
CLOUD_DB = os.path.join(os.path.dirname(__file__), 'data', 'invest.db')

if os.path.exists(LOCAL_DB):
    DB_PATH = LOCAL_DB
else:
    DB_PATH = CLOUD_DB
    # 确保目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_db():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            cost_price REAL DEFAULT 0,
            current_price REAL DEFAULT 0,
            market_value REAL DEFAULT 0,
            profit_loss REAL DEFAULT 0,
            profit_rate REAL DEFAULT 0,
            industry TEXT DEFAULT '',
            position_ratio REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS industry_allocation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            value REAL DEFAULT 0,
            amount REAL DEFAULT 0,
            stocks TEXT DEFAULT ''
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT DEFAULT '',
            tags TEXT DEFAULT '',
            date TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            status TEXT DEFAULT '已发布'
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            total_value REAL DEFAULT 0,
            daily_return REAL DEFAULT 0,
            cumulative_return REAL DEFAULT 0
        )
    """)
    
    conn.commit()
    conn.close()


# 初始化数据库
init_db()
