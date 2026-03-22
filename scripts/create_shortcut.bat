@echo off
chcp 65001 >nul
title WebClaw - 创建桌面快捷方式

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║                                                          ║
echo ║        🔗 创建 WebClaw 桌面快捷方式                      ║
echo ║                                                          ║
echo ╚══════════════════════════════════════════════════════════╝
echo.

:: 获取当前目录
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set TARGET_BAT=%SCRIPT_DIR%start_chrome.bat

:: 检查目标脚本是否存在
if not exist "%TARGET_BAT%" (
    echo [错误] 找不到启动脚本: %TARGET_BAT%
    pause
    exit /b 1
)

:: 设置快捷方式路径
set DESKTOP_DIR=%USERPROFILE%\Desktop
set SHORTCUT_NAME=WebClaw Chrome.lnk
set SHORTCUT_PATH=%DESKTOP_DIR%\%SHORTCUT_NAME%

echo [信息] 正在创建快捷方式...
echo [信息] 目标: %TARGET_BAT%
echo [信息] 快捷方式位置: %SHORTCUT_PATH%
echo.

:: 使用 PowerShell 创建快捷方式
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT_PATH%'); $Shortcut.TargetPath = '%TARGET_BAT%'; $Shortcut.WorkingDirectory = '%SCRIPT_DIR%'; $Shortcut.IconLocation = '%SystemRoot%\System32\SHELL32.dll,14'; $Shortcut.Description = '启动支持 AI 控制的 Chrome 浏览器'; $Shortcut.Save();"

if %ERRORLEVEL% NEQ 0 (
    echo [错误] 创建快捷方式失败！
    pause
    exit /b 1
)

echo [成功] ✅ 快捷方式已创建！
echo.
echo ════════════════════════════════════════════════════════════
echo   📌 快捷方式位置:
echo      %SHORTCUT_PATH%
echo.
echo   💡 使用方法:
echo      1. 双击桌面上的 "WebClaw Chrome" 图标
echo      2. 等待 Chrome 启动完成
echo      3. 正常使用浏览器
echo      4. 在 Cursor 中调用 MCP 工具控制浏览器
echo ════════════════════════════════════════════════════════════
echo.

choice /C YN /N /M "是否立即启动 Chrome? (Y=是, N=否) "
if errorlevel 2 goto :end
if errorlevel 1 goto :launch

:launch
echo.
echo [信息] 正在启动 Chrome...
call "%TARGET_BAT%"

:end
echo.
echo 按任意键退出...
pause >nul
