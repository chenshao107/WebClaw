@echo off
chcp 65001 >nul
title WebClaw - 一键安装

:: ============================================
:: WebClaw 一键安装脚本
:: 自动创建虚拟环境、安装依赖、配置环境
:: ============================================

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║           🔧 WebClaw 一键安装                            ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: 获取脚本所在目录（项目根目录）
set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
cd /d "%PROJECT_DIR%"

echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Python！请先安装 Python 3.10+
    echo        下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [信息] Python 版本: %PYTHON_VERSION%

:: 检查虚拟环境
echo.
echo [2/5] 创建虚拟环境...
if exist "venv\Scripts\python.exe" (
    echo [信息] 虚拟环境已存在，跳过创建
) else (
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo [错误] 创建虚拟环境失败！
        pause
        exit /b 1
    )
    echo [成功] 虚拟环境创建完成
)

:: 激活虚拟环境并安装依赖
echo.
echo [3/5] 安装项目依赖...
call venv\Scripts\activate.bat

:: 升级 pip
python -m pip install --upgrade pip -q

:: 安装依赖
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 依赖安装失败！请检查网络连接
    pause
    exit /b 1
)
echo [成功] 依赖安装完成

:: 安装 Playwright 浏览器
echo.
echo [4/5] 安装 Playwright 浏览器...
playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo [警告] Playwright 浏览器安装失败，可能需要手动安装
    echo        运行: playwright install chromium
)
echo [成功] Playwright 浏览器安装完成

:: 配置环境变量
echo.
echo [5/5] 配置环境...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo [成功] 已创建 .env 配置文件
    echo [提示] 请编辑 .env 文件，填入你的 LLM API Key
) else (
    echo [信息] .env 文件已存在，跳过创建
)

:: 完成
echo.
echo ════════════════════════════════════════════════════════════
echo   ✅ 安装完成！
echo.
echo   📝 下一步操作：
echo.
echo   1. 配置 LLM API Key：
echo      编辑 .env 文件，填入你的 API Key
echo.
echo   2. 启动 MCP 服务：
echo      运行 start_mcp_server.bat
echo      服务将在 http://127.0.0.1:8765/sse 运行
echo.
echo   3. 配置 MCP（在 Cursor/VSCode 中）：
echo      复制 mcp_config.json 的内容到 IDE 的 MCP 配置
echo.
echo   4. 启动 Chrome 调试模式：
echo      运行 scripts\start_chrome.bat
echo.
echo   5. 开始使用！
echo      在 IDE 中调用 MCP 工具即可
echo.
echo ════════════════════════════════════════════════════════════
echo.
pause
