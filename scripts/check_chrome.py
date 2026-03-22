"""
Chrome 调试端口检查工具

用于验证 Chrome 是否已正确启动并开启调试端口
"""

import sys
import json
import urllib.request
from typing import Optional, Dict, Any


def check_chrome_debug_port(port: int = 9222, timeout: int = 5) -> Dict[str, Any]:
    """
    检查 Chrome 调试端口状态
    
    Args:
        port: 调试端口号
        timeout: 超时时间（秒）
        
    Returns:
        检查结果字典
    """
    url = f"http://localhost:{port}/json/version"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode('utf-8'))
            return {
                "success": True,
                "connected": True,
                "browser": data.get("Browser", "Unknown"),
                "protocol_version": data.get("Protocol-Version", "Unknown"),
                "web_socket_url": data.get("webSocketDebuggerUrl", None),
                "port": port
            }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "connected": False,
            "error": f"无法连接到 Chrome 调试端口: {e.reason}",
            "port": port
        }
    except Exception as e:
        return {
            "success": False,
            "connected": False,
            "error": str(e),
            "port": port
        }


def list_open_tabs(port: int = 9222, timeout: int = 5) -> Dict[str, Any]:
    """
    列出 Chrome 中打开的标签页
    
    Args:
        port: 调试端口号
        timeout: 超时时间（秒）
        
    Returns:
        标签页列表
    """
    url = f"http://localhost:{port}/json/list"
    
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            tabs = json.loads(response.read().decode('utf-8'))
            return {
                "success": True,
                "tab_count": len(tabs),
                "tabs": [
                    {
                        "id": tab.get("id"),
                        "title": tab.get("title", "N/A"),
                        "url": tab.get("url", "N/A"),
                        "type": tab.get("type", "page")
                    }
                    for tab in tabs
                ]
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="检查 Chrome 调试端口状态")
    parser.add_argument("--port", type=int, default=9222, help="调试端口号 (默认: 9222)")
    parser.add_argument("--list-tabs", action="store_true", help="列出所有打开的标签页")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  WebClaw - Chrome 调试端口检查工具")
    print("=" * 60)
    print()
    
    # 检查版本信息
    print(f"[检查] 正在连接 localhost:{args.port}...")
    result = check_chrome_debug_port(args.port)
    
    if result["success"]:
        print(f"[成功] ✅ Chrome 调试服务已启动")
        print(f"[信息] 浏览器: {result['browser']}")
        print(f"[信息] 协议版本: {result['protocol_version']}")
        print(f"[信息] WebSocket URL: {result['web_socket_url']}")
        
        # 列出标签页
        if args.list_tabs:
            print()
            print("-" * 60)
            tabs_result = list_open_tabs(args.port)
            if tabs_result["success"]:
                print(f"[信息] 当前打开 {tabs_result['tab_count']} 个标签页:")
                for i, tab in enumerate(tabs_result["tabs"], 1):
                    print(f"  {i}. {tab['title'][:50]}")
                    print(f"     URL: {tab['url'][:60]}...")
            else:
                print(f"[错误] 无法获取标签页列表: {tabs_result.get('error')}")
        
        print()
        print("=" * 60)
        print("  ✅ Playwright 可以通过以下方式连接:")
        print(f"     browser = p.chromium.connect_over_cdp('http://localhost:{args.port}')")
        print("=" * 60)
        return 0
    else:
        print(f"[失败] ❌ {result['error']}")
        print()
        print("=" * 60)
        print("  可能的原因:")
        print("    1. Chrome 未以调试模式启动")
        print("    2. 端口号不正确")
        print("    3. 防火墙阻止了连接")
        print()
        print("  解决方法:")
        print("    运行 scripts/start_chrome.bat 启动 Chrome")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
