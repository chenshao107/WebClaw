@echo off
chcp 65001 >nul
title WebClaw - Chrome 启动器

:: ============================================
:: WebClaw Chrome 启动脚本
:: 启动带远程调试端口的 Chrome，供 Playwright 连接
:: ============================================

echo.
echo  ╔══════════════════════════════════════════════════════════╗
echo  ║                                                          ║
echo  ║           🚀 WebClaw Chrome 启动器                       ║
echo  ║                                                          ║
echo  ║   正在启动支持 AI 控制的浏览器...                         ║
echo  ║                                                          ║
echo  ╚══════════════════════════════════════════════════════════╝
echo.

:: 配置参数
set "DEBUG_PORT=9222"

:: 用户数据目录设置
:: 使用独立配置（推荐）：干净环境，不与普通 Chrome 冲突
set "USER_DATA_DIR=%LOCALAPPDATA%\WebClaw\ChromeProfile"

:: 如需使用默认 Chrome 配置（保留书签、插件、登录状态），取消下面这行的注释：
:: set "USER_DATA_DIR=%LOCALAPPDATA%\Google\Chrome\User Data"

:: 查找 Chrome 路径（支持 Chrome / Edge / Chromium）
set CHROME_PATH=

:: 尝试查找 Chrome
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
) else if exist "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
) else if exist "C:\Program Files\Microsoft\Edge\Application\msedge.exe" (
    set "CHROME_PATH=C:\Program Files\Microsoft\Edge\Application\msedge.exe"
)

if not defined CHROME_PATH (
    echo [错误] 未找到 Chrome 或 Edge 浏览器！
    echo 请确保已安装 Google Chrome 或 Microsoft Edge。
    pause
    exit /b 1
)

echo [信息] 找到浏览器: "%CHROME_PATH%"
echo [信息] 调试端口: %DEBUG_PORT%
echo [信息] 用户数据目录: "%USER_DATA_DIR%"
echo.

echo [提示] 正在使用独立配置（干净环境，不与普通 Chrome 冲突）

:: 创建用户数据目录
if not exist "%USER_DATA_DIR%" (
    mkdir "%USER_DATA_DIR%"
    echo [信息] 已创建新的用户配置文件
)

:: 检查端口是否被占用
netstat -ano | findstr ":%DEBUG_PORT%" >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo [警告] 端口 %DEBUG_PORT% 已被占用！
    echo.
    echo 可能的原因：
    echo   1. Chrome 已经以调试模式运行
    echo   2. 其他程序占用了该端口
    echo.
    echo 如果 Chrome 已经在调试模式下运行，可以直接使用。
    echo.
    choice /C YN /N /M "是否继续? (Y=继续, N=退出) "
    if errorlevel 2 exit /b 1
)

echo [信息] 正在启动 Chrome...
echo.

:: 启动 Chrome（带调试端口）
:: 注意：start 命令会立即返回，所以不能用 ERRORLEVEL 判断
start "WebClaw Chrome" "%CHROME_PATH%" ^
    --remote-debugging-port=%DEBUG_PORT% ^
    --user-data-dir="%USER_DATA_DIR%" ^
    --no-first-run ^
    --no-default-browser-check ^
    --disable-default-apps ^
    --disable-background-timer-throttling ^
    --disable-backgrounding-occluded-windows ^
    --disable-renderer-backgrounding ^
    --disable-features=TranslateUI ^
    --disable-component-extensions-with-background-pages ^
    --window-size=1920,1080 ^
    --window-position=100,100 ^
    "about:blank"

:: 等待 Chrome 进程启动
timeout /t 3 /nobreak >nul

:: 检查 Chrome 进程是否存在
tasklist /FI "IMAGENAME eq chrome.exe" 2>nul | find /I "chrome.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] Chrome 进程未能启动！
    pause
    exit /b 1
)

:: 验证调试端口（带重试）
echo [信息] 验证调试端口...
set RETRY_COUNT=0
set MAX_RETRIES=5

:verify_loop
set /a RETRY_COUNT+=1
echo [信息] 尝试连接 (%RETRY_COUNT%/%MAX_RETRIES%)...

powershell -Command "try { $resp = Invoke-WebRequest -Uri 'http://localhost:%DEBUG_PORT%/json/version' -TimeoutSec 3 -UseBasicParsing; Write-Host '[成功] Chrome 调试服务已启动'; Write-Host ('[信息] 浏览器版本: ' + ($resp.Content | ConvertFrom-Json).Browser); exit 0; } catch { exit 1; }"

if %ERRORLEVEL% == 0 goto :verify_success

if %RETRY_COUNT% LSS %MAX_RETRIES% (
    echo [信息] 等待 Chrome 启动调试服务...
    timeout /t 2 /nobreak >nul
    goto :verify_loop
)

echo.
echo [错误] Chrome 调试端口未响应，请检查：
echo   1. 防火墙是否阻止了端口 %DEBUG_PORT%
echo   2. Chrome 是否以调试模式启动
echo   3. 尝试重新运行脚本
pause
exit /b 1

:verify_success

echo.
echo ════════════════════════════════════════════════════════════
echo   ✅ Chrome 已成功启动并开启调试模式！
echo.
echo   📍 调试端口: %DEBUG_PORT%
echo   📂 用户数据: "%USER_DATA_DIR%"
echo.
echo   💡 现在你可以：
echo      1. 正常使用浏览器浏览网页
echo      2. 在 Cursor 中调用 MCP 工具控制浏览器
echo      3. Playwright 可以通过端口 %DEBUG_PORT% 连接此浏览器
echo.
echo   ⚠️  注意：关闭此窗口不会关闭 Chrome
echo       如需完全退出，请手动关闭浏览器窗口
echo ════════════════════════════════════════════════════════════
echo.

:: 保持窗口打开，显示状态
:loop
timeout /t 5 /nobreak >nul
:: 检查 Chrome 是否仍在运行
tasklist /FI "IMAGENAME eq chrome.exe" 2>nul | find /I "chrome.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [信息] Chrome 已关闭
    goto :end
)
goto :loop

:end
echo.
echo 按任意键退出...
pause >nul
