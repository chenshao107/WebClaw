"""
统一调试入口 (手动模拟 LLM)

用于本地开发和调试，无需连接外部 LLM 即可测试核心功能
"""

import sys
import json
from typing import Optional

from core.interpreter import CodeInterpreter
from core.agent import ExecutorAgent
from tools.utils import ColoredOutput, print_result


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           🚀 MacroChromeMCP 调试控制台                       ║
║                                                              ║
║   浏览器自动化执行 Agent - 本地调试版本                       ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_help():
    """打印帮助信息"""
    help_text = """
可用命令:
  init              - 初始化浏览器环境
  goto <url>        - 导航到指定 URL
  exec <code>       - 执行 Python 代码
  task <desc>       - 执行宏任务（本地模拟）
  screenshot        - 截取当前页面
  info              - 显示当前页面信息
  help              - 显示此帮助
  quit/exit         - 退出程序

示例:
  init
  goto https://www.baidu.com
  exec page.title()
  task 搜索"Python教程"
  screenshot
    """
    print(help_text)


class DebugConsole:
    """调试控制台"""
    
    def __init__(self):
        self.interpreter: Optional[CodeInterpreter] = None
        self.agent: Optional[ExecutorAgent] = None
        self.initialized = False
    
    def init(self, headless: bool = False, debug_port: Optional[int] = None):
        """初始化环境"""
        ColoredOutput.info("正在初始化浏览器环境...")
        
        try:
            self.interpreter = CodeInterpreter()
            result = self.interpreter.initialize(headless=headless, debug_port=debug_port)
            
            if result.success:
                self.initialized = True
                ColoredOutput.success("浏览器环境初始化成功！")
                if result.page_state:
                    print(f"  URL: {result.page_state.get('url', 'N/A')}")
            else:
                ColoredOutput.error(f"初始化失败: {result.error}")
                
        except Exception as e:
            ColoredOutput.error(f"初始化异常: {e}")
    
    def goto(self, url: str):
        """导航到 URL"""
        if not self._check_initialized():
            return
        
        code = f'''
page.goto("{url}")
page.wait_for_load_state("networkidle")
print(f"已导航到: {{page.url}}")
print(f"页面标题: {{page.title()}}")
'''
        result = self.interpreter.execute(code)
        self._print_result(result)
    
    def execute(self, code: str):
        """执行 Python 代码"""
        if not self._check_initialized():
            return
        
        ColoredOutput.info("执行代码...")
        print(f"```python\n{code}\n```")
        
        result = self.interpreter.execute(code)
        self._print_result(result)
    
    def task(self, description: str):
        """执行宏任务（本地模拟）"""
        if not self._check_initialized():
            return
        
        ColoredOutput.info(f"执行任务: {description}")
        
        # 本地模拟任务执行（不调用 LLM）
        # 根据任务关键词生成对应的代码
        code = self._generate_task_code(description)
        
        print("\n[生成的代码]")
        print(f"```python\n{code}\n```")
        
        result = self.interpreter.execute(code)
        self._print_result(result)
    
    def screenshot(self, path: str = "debug_screenshot.png"):
        """截取页面"""
        if not self._check_initialized():
            return
        
        code = f'''
page.screenshot(path="{path}", full_page=True)
print(f"截图已保存: {path}")
'''
        result = self.interpreter.execute(code)
        self._print_result(result)
    
    def info(self):
        """显示页面信息"""
        if not self._check_initialized():
            return
        
        code = '''
print(f"URL: {page.url}")
print(f"标题: {page.title()}")
'''
        result = self.interpreter.execute(code)
        self._print_result(result)
    
    def _generate_task_code(self, description: str) -> str:
        """根据任务描述生成代码（本地模拟）"""
        desc = description.lower()
        
        if "搜索" in description or "search" in desc:
            # 提取搜索关键词
            import re
            keywords = re.findall(r'["\'](.+?)["\']|搜索(.+?)(?:$|\\s)', description)
            keyword = ""
            for k in keywords:
                keyword = k[0] or k[1]
                if keyword:
                    break
            keyword = keyword or "搜索内容"
            
            return f'''
# 执行搜索任务
page.goto("https://www.baidu.com")
page.wait_for_load_state("networkidle")

# 输入搜索词
search_box = page.locator("#kw").first
search_box.fill("{keyword}")

# 点击搜索
page.locator("#su").click()
page.wait_for_load_state("networkidle")

# 等待结果
page.wait_for_selector(".result", timeout=10000)

# 提取前5个结果标题
titles = page.locator(".result .t").all_inner_texts()[:5]

print(json.dumps({{
    "status": "success",
    "keyword": "{keyword}",
    "results": titles,
    "count": len(titles)
}}, ensure_ascii=False))
'''
        
        elif "点击" in description or "click" in desc:
            return '''
# 执行点击任务
# 尝试点击页面上的第一个可见按钮或链接
selectors = ["button", "a", "[role='button']", ".btn", "input[type='submit']"]

clicked = False
clicked_element = None

for selector in selectors:
    try:
        elements = page.locator(selector).all()
        for elem in elements:
            if elem.is_visible():
                elem.click()
                clicked = True
                clicked_element = selector
                break
        if clicked:
            break
    except:
        continue

if clicked:
    page.wait_for_load_state("networkidle")
    print(json.dumps({
        "status": "success",
        "clicked": True,
        "element": clicked_element,
        "current_url": page.url
    }, ensure_ascii=False))
else:
    print(json.dumps({
        "status": "error",
        "message": "未找到可点击元素"
    }, ensure_ascii=False))
'''
        
        elif "截图" in description or "screenshot" in desc:
            return '''
# 执行截图任务
import datetime
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
screenshot_path = f"screenshot_{timestamp}.png"

page.screenshot(path=screenshot_path, full_page=True)

print(json.dumps({
    "status": "success",
    "screenshot_path": screenshot_path,
    "message": f"截图已保存到 {screenshot_path}"
}, ensure_ascii=False))
'''
        
        else:
            # 默认代码
            return f'''
# 执行任务: {description}
print(json.dumps({{
    "status": "success",
    "task": "{description}",
    "message": "任务执行完成（本地模拟）",
    "current_url": page.url
}}, ensure_ascii=False))
'''
    
    def _check_initialized(self) -> bool:
        """检查是否已初始化"""
        if not self.initialized or not self.interpreter:
            ColoredOutput.error("请先执行 init 命令初始化浏览器环境")
            return False
        return True
    
    def _print_result(self, result):
        """打印执行结果"""
        if result.success:
            ColoredOutput.success("执行成功")
            if result.stdout:
                print("[输出]")
                print(result.stdout)
        else:
            ColoredOutput.error("执行失败")
            if result.error:
                print(f"[错误] {result.error}")
            if result.stderr:
                print(f"[stderr] {result.stderr}")
    
    def close(self):
        """关闭资源"""
        if self.interpreter:
            self.interpreter.close()
            ColoredOutput.info("浏览器已关闭")


def main():
    """主函数"""
    print_banner()
    print_help()
    
    console = DebugConsole()
    
    try:
        while True:
            try:
                # 读取用户输入
                user_input = input("\n> ").strip()
                
                if not user_input:
                    continue
                
                # 解析命令
                parts = user_input.split(maxsplit=1)
                command = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # 执行命令
                if command in ["quit", "exit", "q"]:
                    break
                
                elif command == "help":
                    print_help()
                
                elif command == "init":
                    # 解析参数
                    headless = "--headless" in args
                    debug_port = None
                    if "--port" in args:
                        import re
                        match = re.search(r'--port\s+(\d+)', args)
                        if match:
                            debug_port = int(match.group(1))
                    
                    console.init(headless=headless, debug_port=debug_port)
                
                elif command == "goto":
                    if args:
                        console.goto(args)
                    else:
                        ColoredOutput.error("请提供 URL，例如: goto https://www.baidu.com")
                
                elif command == "exec":
                    if args:
                        console.execute(args)
                    else:
                        ColoredOutput.error("请提供代码，例如: exec page.title()")
                
                elif command == "task":
                    if args:
                        console.task(args)
                    else:
                        ColoredOutput.error("请提供任务描述，例如: task 搜索Python教程")
                
                elif command == "screenshot":
                    path = args if args else "debug_screenshot.png"
                    console.screenshot(path)
                
                elif command == "info":
                    console.info()
                
                else:
                    ColoredOutput.warning(f"未知命令: {command}")
                    print_help()
            
            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                ColoredOutput.error(f"错误: {e}")
    
    finally:
        console.close()
        ColoredOutput.info("再见！")


if __name__ == "__main__":
    main()
