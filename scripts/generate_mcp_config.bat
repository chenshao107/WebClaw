@echo off
chcp 65001 >nul
title WebClaw - 生成 MCP 配置

:: ============================================
:: 自动生成 MCP 配置
:: 生成可以直接复制到 IDE 的配置内容
:: ============================================

:: 获取项目根目录（脚本在 scripts 目录下，需要上一级）
set "SCRIPT_DIR=%~dp0"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_DIR=%%~fi"

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                                                          ║
echo ║           📋 WebClaw MCP 配置生成器                      ║
echo ║                                                          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo 检测到项目路径: %PROJECT_DIR%
echo.
echo ════════════════════════════════════════════════════════════
echo.
echo 复制以下内容到你的 IDE MCP 配置中 (Cursor: mcp.json)
echo.
echo ════════════════════════════════════════════════════════════
echo.
echo {
echo   "mcpServers": {
echo     "webclaw": {
echo       "url": "http://127.0.0.1:8765/sse"
echo     }
echo   }
echo }
echo.
echo ════════════════════════════════════════════════════════════
echo.
echo ⚠️  重要提示：
echo    使用 SSE 模式前，请先运行 start_mcp_server.bat 启动服务
echo.
echo ════════════════════════════════════════════════════════════
echo.

:: 同时生成到文件
set "OUTPUT_FILE=%PROJECT_DIR%\my_mcp_config.json"
(
echo {
echo   "mcpServers": {
echo     "webclaw": {
echo       "url": "http://127.0.0.1:8765/sse"
echo     }
echo   }
echo }
) > "%OUTPUT_FILE%"

echo 配置已保存到: %OUTPUT_FILE%
echo.
echo 使用步骤：
echo   1. 先运行 start_mcp_server.bat 启动 MCP 服务
echo   2. Cursor 用户: 按 Ctrl+Shift+, 打开设置，点击 MCP，粘贴配置
echo   3. 或者复制 my_mcp_config.json 内容到 mcp.json
echo.
pause
