@echo off
chcp 65001 >nul
cd /d "D:\Project\WebClaw"

:: 激活虚拟环境
call venv\Scripts\activate.bat

:: 设置 Python 路径
set PYTHONPATH=D:\Project\WebClaw

:: 启动 MCP Server (SSE 模式)
echo [WebClaw] 正在启动 MCP Server (SSE 模式)...
echo [WebClaw] 服务地址: http://127.0.0.1:8765/sse
echo [WebClaw] 按 Ctrl+C 停止服务
echo.

python server\mcp_server.py --transport sse

pause
