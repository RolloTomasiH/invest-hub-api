# InvestHub 实时数据API

## 功能

- **A股数据**：实时行情、历史数据
- **美股数据**：实时行情、历史数据
- **宏观经济**：GDP、CPI、PMI、FRED数据

## 数据源

| 数据源 | 覆盖范围 | 优先级 |
|--------|----------|--------|
| AKShare | A股 | 主要 |
| yfinance | 美股 | 主要 |
| FRED | 宏观经济 | 主要 |

## 快速开始

### 1. 安装依赖

```bash
cd /Users/guerriersolitaire/WorkBuddy/2026-05-29-12-39-45/invest-hub/api
pip3 install -r requirements.txt
```

### 2. 启动API服务

```bash
python3 app.py
```

服务将在 http://localhost:5002 启动

### 3. 测试API

```bash
# 健康检查
curl http://localhost:5002/api/health

# A股行情
curl http://localhost:5002/api/a-share/quote/600519

# 美股行情
curl http://localhost:5002/api/us-stock/quote/AAPL

# 宏观指标
curl http://localhost:5002/api/macro/indicators
```

## API端点

### A股数据

- `GET /api/a-share/quote/<code>` - 获取A股实时行情
  - 示例: `/api/a-share/quote/600519` (贵州茅台)
  
- `GET /api/a-share/list` - 获取A股列表（前100只）

### 美股数据

- `GET /api/us-stock/quote/<symbol>` - 获取美股实时行情
  - 示例: `/api/us-stock/quote/AAPL`
  
- `GET /api/us-stock/history/<symbol>` - 获取美股历史数据
  - 参数: `period` - 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max
  - 示例: `/api/us-stock/history/AAPL?period=1mo`

### 宏观经济

- `GET /api/macro/indicators` - 获取宏观经济指标
  - 返回: GDP、CPI、PMI等

- `GET /api/macro/fred/<series_id>` - 获取FRED数据
  - series_id: GDP, CPI, UNEMPLOYMENT, FED_FUNDS
  - 示例: `/api/macro/fred/GDP`

### 批量查询

- `POST /api/batch/quotes` - 批量获取行情
  - Body: `{"symbols": ["600519", "000858"], "market": "a_share"}`

## 暴露到公网

### 方案1：Cloudflare Tunnel（推荐）

```bash
# 安装cloudflared
brew install cloudflare/cloudflare/cloudflare

# 启动tunnel
cloudflared tunnel --url http://localhost:5002
```

### 方案2：ngrok

```bash
# 安装ngrok
brew install ngrok

# 启动tunnel
ngrok http 5002
```

## 部署到生产环境

### 使用Gunicorn

```bash
pip3 install gunicorn
gunicorn -w 4 -b 0.0.0.0:5002 app:app
```

### 使用Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5002", "app:app"]
```

## 注意事项

1. **API限流**：AKShare和yfinance有请求频率限制
2. **缓存**：数据缓存5分钟，避免频繁请求
3. **数据延迟**：A股数据延迟约15分钟，美股数据延迟约15分钟
4. **免费额度**：所有数据源均为免费使用

## 故障排除

### 问题：ImportError: No module named 'akshare'

```bash
pip3 install akshare
```

### 问题：yfinance无法获取数据

```bash
pip3 install yfinance --upgrade
```

### 问题：端口被占用

```bash
lsof -i :5002
kill -9 <PID>
```
