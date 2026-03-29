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

:: 将路径中的反斜杠转换为双反斜杠（JSON需要转义）
set "JSON_PATH=%PROJECT_DIR:\=\\%"

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
echo       "command": "%JSON_PATH%\\venv\\Scripts\\python.exe",
echo       "args": [
echo         "%JSON_PATH%\\server\\mcp_server.py",
echo         "--transport", "stdio"
echo       ],
echo       "env": {
echo         "PYTHONPATH": "%JSON_PATH%"
echo       }
echo     }
echo   }
echo }
echo.
echo ════════════════════════════════════════════════════════════
echo.

:: 同时生成到文件
set "OUTPUT_FILE=%PROJECT_DIR%\my_mcp_config.json"
(
echo {
echo   "mcpServers": {
echo     "webclaw": {
echo       "command": "%JSON_PATH%\\venv\\Scripts\\python.exe",
echo       "args": [
echo         "%JSON_PATH%\\server\\mcp_server.py",
echo         "--transport", "stdio"
echo       ],
echo       "env": {
echo         "PYTHONPATH": "%JSON_PATH%"
echo       }
echo     }
echo   }
echo }
) > "%OUTPUT_FILE%"

echo 配置已保存到: %OUTPUT_FILE%
echo.
echo 提示：
echo   - Cursor 用户: 按 Ctrl+Shift+, 打开设置，点击 MCP，粘贴配置
echo   - 或者复制 my_mcp_config.json 内容到 mcp.json
echo.
pause
