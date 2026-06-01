#!/bin/bash

echo "=========================================="
echo "InvestHub 实时数据API服务"
echo "=========================================="

# 获取脚本所在目录
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 检查依赖
echo "检查依赖..."
cd "$DIR"
pip3 install -r requirements.txt -q

# 启动API服务
echo "启动API服务 (端口 5002)..."
python3 app.py &
API_PID=$!

# 等待服务启动
sleep 3

echo ""
echo "API服务已启动："
echo "  - 本地访问: http://localhost:5002"
echo "  - API端点: http://localhost:5002/api/"
echo ""
echo "可用端点："
echo "  - GET /api/health - 健康检查"
echo "  - GET /api/a-share/quote/<code> - A股行情"
echo "  - GET /api/a-share/list - A股列表"
echo "  - GET /api/us-stock/quote/<symbol> - 美股行情"
echo "  - GET /api/us-stock/history/<symbol> - 美股历史"
echo "  - GET /api/macro/indicators - 宏观指标"
echo "  - GET /api/macro/fred/<series_id> - FRED数据"
echo ""
echo "按 Ctrl+C 停止服务"

# 等待用户中断
wait $API_PID
