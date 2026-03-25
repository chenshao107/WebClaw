"""
WebClaw 脚本工具包

包含：
- start_chrome.bat: 启动带调试端口的 Chrome
- check_chrome.py: 检查 Chrome 调试端口状态
- create_shortcut.bat: 创建桌面快捷方式
"""

from .check_chrome import check_chrome_debug_port, list_open_tabs

__all__ = ["check_chrome_debug_port", "list_open_tabs"]
