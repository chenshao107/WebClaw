@echo off
chcp 65001 >nul
echo ==========================================
echo MacroChromeMCP - Demo 启动脚本
echo ==========================================
echo.

REM 激活虚拟环境
call venv\Scripts\activate.bat

REM 检查参数
if "%1"=="test1" (
    echo 测试 1: 获取 HTML 源码...
    python test_1_get_html.py
) else if "%1"=="test2" (
    echo 测试 2: 元素操作...
    python test_2_element_ops.py
) else if "%1"=="test3" (
    echo 测试 3: Tab 页操作...
    python test_3_tab_ops.py
) else if "%1"=="server" (
    echo 启动 MCP Server...
    python -m server.main
) else if "%1"=="debug" (
    echo 启动调试入口...
    python debug_entry.py
) else if "%1"=="chrome" (
    echo 启动 Chrome (带调试端口)...
    call scripts\start_chrome.bat
) else if "%1"=="check" (
    echo 检查 Chrome 调试端口...
    python scripts\check_chrome.py --list-tabs
) else if "%1"=="shortcut" (
    echo 创建桌面快捷方式...
    call scripts\create_shortcut.bat
) else (
    echo 用法: run_demo.bat [选项]
    echo.
    echo 浏览器控制:
    echo   chrome    - 启动 Chrome (带调试端口，供 Playwright 连接)
    echo   check     - 检查 Chrome 调试端口状态
    echo   shortcut  - 创建桌面快捷方式
    echo.
    echo 测试与调试:
    echo   test1     - 测试 HTML 获取
    echo   test2     - 测试元素操作
    echo   test3     - 测试 Tab 操作
    echo   server    - 启动 MCP Server
    echo   debug     - 启动调试入口
    echo.
    pause
)
