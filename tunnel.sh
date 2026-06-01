#!/bin/bash

echo "=========================================="
echo "配置Cloudflare Tunnel"
echo "=========================================="

# 检查cloudflared是否安装
if ! command -v cloudflared &> /dev/null; then
    echo "安装cloudflared..."
    brew install cloudflare/cloudflare/cloudflared
fi

echo "启动Tunnel..."
echo "这会将本地API暴露到公网"
echo ""

# 启动tunnel
cloudflared tunnel --url http://localhost:5002

echo ""
echo "Tunnel已停止"
