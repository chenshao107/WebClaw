#!/bin/bash

# ============================================
# WebClaw 一键安装脚本 (Linux/macOS)
# 自动创建虚拟环境、安装依赖、配置环境
# ============================================

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║           🔧 WebClaw 一键安装                            ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python
echo "[1/5] 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python3！请先安装 Python 3.10+"
    echo "       macOS: brew install python3"
    echo "       Ubuntu: sudo apt install python3 python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "[信息] Python 版本: $PYTHON_VERSION"

# 创建虚拟环境
echo ""
echo "[2/5] 创建虚拟环境..."
if [ -f "venv/bin/python" ]; then
    echo "[信息] 虚拟环境已存在，跳过创建"
else
    python3 -m venv venv
    echo "[成功] 虚拟环境创建完成"
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo ""
echo "[3/5] 安装项目依赖..."
pip install --upgrade pip -q
pip install -r requirements.txt
echo "[成功] 依赖安装完成"

# 安装 Playwright 浏览器
echo ""
echo "[4/5] 安装 Playwright 浏览器..."
playwright install chromium || {
    echo "[警告] Playwright 浏览器安装失败，可能需要手动安装"
    echo "       运行: playwright install chromium"
}
echo "[成功] Playwright 浏览器安装完成"

# 配置环境
echo ""
echo "[5/5] 配置环境..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "[成功] 已创建 .env 配置文件"
    echo "[提示] 请编辑 .env 文件，填入你的 LLM API Key"
else
    echo "[信息] .env 文件已存在，跳过创建"
fi

# 完成
echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✅ 安装完成！"
echo ""
echo "  📝 下一步操作："
echo ""
echo "  1. 配置 LLM API Key："
echo "     编辑 .env 文件，填入你的 API Key"
echo ""
echo "  2. 启动 MCP 服务："
echo "     python server/mcp_server.py --transport sse"
echo "     服务将在 http://127.0.0.1:8765/sse 运行"
echo ""
echo "  3. 配置 MCP（在 Cursor/VSCode 中）："
echo "     复制 mcp_config.json 的内容到 IDE 的 MCP 配置"
echo ""
echo "  4. 启动 Chrome 调试模式："
echo "     macOS: 使用 Chrome --remote-debugging-port=9222"
echo "     Linux: google-chrome --remote-debugging-port=9222"
echo ""
echo "  5. 开始使用！"
echo "     在 IDE 中调用 MCP 工具即可"
echo ""
echo "════════════════════════════════════════════════════════════"
