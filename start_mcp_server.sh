#!/bin/bash

# ============================================
# WebClaw MCP Server 启动脚本 (Linux/macOS)
# SSE 模式 - 支持状态持久化
# ============================================

# 获取脚本所在目录
cd "$(dirname "$0")"

# 激活虚拟环境
source venv/bin/activate

# 设置 Python 路径
export PYTHONPATH="$(pwd)"

echo "[WebClaw] 正在启动 MCP Server (SSE 模式)..."
echo "[WebClaw] 服务地址: http://127.0.0.1:8765/sse"
echo "[WebClaw] 按 Ctrl+C 停止服务"
echo ""

python server/mcp_server.py --transport sse
