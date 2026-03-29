"""
渐进式 MCP 工具集 - Progressive Disclosure MCP Tools

设计原则：
1. 初始暴露最小化 - 只有 help 和基本描述
2. 按需获取详情 - 调用 help 返回完整工具文档和浏览器状态
3. 可配置开关 - 灵活启用/禁用特定工具

工具清单：
- help: 获取完整帮助信息和浏览器状态
- execute_python: 执行 Python 代码操控浏览器
- agent_task: 自然语言描述任务，由 Agent 执行
"""

import json
import types
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from tools.base import BaseTool


# ============================================================================
# 预封装函数 - 在 execute_python 环境中可用
# ============================================================================

PREBUILT_FUNCTIONS = '''
# ============================================
# 预封装函数 - 浏览器自动化常用操作
# ============================================

import types  # 预导入 types 模块，供 list_prebuilt_funcs 使用

def get_page_summary():
    """获取页面摘要信息（URL、标题、关键元素）"""
    import json
    result = {
        "url": page.url,
        "title": page.title(),
    }
    # 尝试获取页面主要文本内容（前 500 字符）
    try:
        body_text = page.evaluate("() => document.body.innerText.slice(0, 500)")
        result["body_preview"] = body_text
    except:
        result["body_preview"] = "无法获取"
    
    # 统计元素数量
    try:
        stats = page.evaluate("""() => {
            return {
                links: document.querySelectorAll('a').length,
                buttons: document.querySelectorAll('button').length,
                inputs: document.querySelectorAll('input').length,
                images: document.querySelectorAll('img').length
            }
        }""")
        result["element_stats"] = stats
    except:
        result["element_stats"] = {}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def find_elements(selector: str, max_count: int = 10):
    """查找页面元素并打印基本信息"""
    import json
    elements = page.query_selector_all(selector)
    results = []
    for i, el in enumerate(elements[:max_count]):
        info = {
            "index": i,
            "tag": el.evaluate("el => el.tagName.toLowerCase()"),
            "text": el.inner_text()[:50] if el.inner_text() else "",
            "visible": el.is_visible()
        }
        # 尝试获取常见属性
        for attr in ["id", "class", "href", "src", "name"]:
            val = el.get_attribute(attr)
            if val:
                info[attr] = val[:50] if len(val) > 50 else val
        results.append(info)
    
    print(f"找到 {len(elements)} 个元素，显示前 {len(results)} 个:")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return results


def click_element(selector: str, index: int = 0):
    """点击指定选择器的第 index 个元素"""
    elements = page.query_selector_all(selector)
    if not elements:
        print(f"错误: 未找到匹配 '{selector}' 的元素")
        return False
    if index >= len(elements):
        print(f"错误: 索引 {index} 超出范围，只有 {len(elements)} 个元素")
        return False
    
    el = elements[index]
    if not el.is_visible():
        print(f"警告: 元素不可见，尝试滚动到视口")
        el.scroll_into_view_if_needed()
    
    el.click()
    print(f"已点击: {selector}[{index}]")
    return True


def fill_form(selector: str, value: str):
    """填充表单输入框"""
    el = page.query_selector(selector)
    if not el:
        print(f"错误: 未找到输入框 '{selector}'")
        return False
    
    el.fill(value)
    print(f"已填充: {selector} = '{value[:20]}...'" if len(value) > 20 else f"已填充: {selector} = '{value}'")
    return True


def wait_and_capture(timeout: int = 3000):
    """等待页面稳定并捕获状态"""
    page.wait_for_timeout(timeout)
    page.wait_for_load_state("networkidle")
    get_page_summary()


def extract_links(pattern: str = None):
    """提取页面所有链接，可选按正则过滤"""
    import re
    links = page.query_selector_all("a[href]")
    results = []
    for link in links:
        href = link.get_attribute("href")
        text = link.inner_text()[:30].strip()
        if pattern and not re.search(pattern, href or ""):
            continue
        results.append({"text": text, "href": href})
    
    print(f"提取到 {len(results)} 个链接:")
    for i, link in enumerate(results[:20]):  # 只显示前 20 个
        print(f"  {i+1}. {link['text'][:20]:<20} -> {link['href'][:60]}")
    
    return results


def smart_scroll(direction: str = "down", amount: int = 800):
    """智能滚动页面"""
    if direction == "down":
        page.evaluate(f"window.scrollBy(0, {amount})")
    elif direction == "up":
        page.evaluate(f"window.scrollBy(0, -{amount})")
    elif direction == "bottom":
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    elif direction == "top":
        page.evaluate("window.scrollTo(0, 0)")
    
    # 获取当前滚动位置
    scroll_pos = page.evaluate("() => ({top: window.scrollY, height: document.body.scrollHeight})")
    print(f"滚动 {direction}: 当前位置 {scroll_pos['top']}/{scroll_pos['height']}")
    return scroll_pos


def list_prebuilt_funcs():
    """列出所有预封装函数"""
    funcs = [
        name for name, val in globals().items()
        if isinstance(val, types.FunctionType)
        and val.__module__ == '__main__'
        and not name.startswith('_')
    ]
    print("可用的预封装函数:")
    for func in sorted(funcs):
        print(f"  - {func}")
    return funcs


def new_tab(url: str = None):
    """新开一个标签页并返回页面对象"""
    new_page = context.new_page()
    if url:
        new_page.goto(url)
        new_page.wait_for_load_state("domcontentloaded")
    print(f"新开标签页: {new_page.url if url else 'about:blank'}")
    return new_page


def switch_tab(index: int = 0):
    """切换到指定索引的标签页"""
    global page
    pages = context.pages
    if index < 0 or index >= len(pages):
        print(f"错误: 索引 {index} 超出范围，共有 {len(pages)} 个标签页")
        return None
    page = pages[index]
    print(f"切换到标签页 {index}: {page.url}")
    return page


def list_tabs():
    """列出所有标签页"""
    pages = context.pages
    print(f"共有 {len(pages)} 个标签页:")
    for i, p in enumerate(pages):
        marker = "👉 " if p == page else "   "
        try:
            title = p.title()[:30] if p.title() else "无标题"
            url = p.url[:50] if len(p.url) > 50 else p.url
            print(f"{marker}[{i}] {title} - {url}")
        except:
            print(f"{marker}[{i}] 无法获取信息")
    return pages


def close_tab(index: int = None):
    """关闭指定索引的标签页，默认关闭当前页"""
    global page
    pages = context.pages
    if index is None:
        target = page
    else:
        if index < 0 or index >= len(pages):
            print(f"错误: 索引 {index} 超出范围")
            return False
        target = pages[index]
    
    target.close()
    print(f"已关闭标签页")
    
    # 切换到第一个可用标签页
    remaining = context.pages
    if remaining:
        page = remaining[0]
        print(f"自动切换到: {page.url}")
    return True


# 初始化时打印可用函数（使用全局变量确保只打印一次）
if '_webclaw_initialized' not in globals():
    print("=" * 50)
    print("浏览器自动化环境已就绪")
    print("全局变量: page (当前页面), context (浏览器上下文)")
    print("预封装函数:")
    list_prebuilt_funcs()
    print("=" * 50)
    globals()['_webclaw_initialized'] = True
'''


# ============================================================================
# 工具配置类
# ============================================================================

@dataclass
class MCPToolConfig:
    """MCP 工具配置"""
    enable_help: bool = True
    enable_execute_python: bool = True
    enable_agent_task: bool = True
    
    # execute_python 配置
    include_prebuilt_funcs: bool = True
    prebuilt_funcs_code: str = field(default_factory=lambda: PREBUILT_FUNCTIONS)
    
    # agent_task 配置
    agent_max_steps: int = 15
    
    def get_enabled_tools(self) -> List[str]:
        """获取启用的工具列表"""
        tools = []
        if self.enable_help:
            tools.append("help")
        if self.enable_execute_python:
            tools.append("execute_python")
        if self.enable_agent_task:
            tools.append("agent_task")
        return tools


# ============================================================================
# 工具实现
# ============================================================================

class HelpTool(BaseTool):
    """
    Help 工具 - 渐进式披露的核心
    
    初始时 MCP 只暴露极简描述，
    调用此工具后返回完整的工具文档和浏览器当前状态。
    """
    
    def __init__(self, config: MCPToolConfig = None, get_browser_state: Callable = None):
        self.config = config or MCPToolConfig()
        self.get_browser_state = get_browser_state
    
    @property
    def name(self) -> str:
        return "browser_help"
    
    @property
    def description(self) -> str:
        return "获取浏览器控制器的完整帮助信息和当前状态。当你需要了解可用工具或浏览器当前状态时调用此工具。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "description": "无需参数，调用即返回完整帮助信息"
        }
    
    def execute(self) -> str:
        """返回完整帮助文档"""
        sections = []
        
        # 1. 浏览器当前状态
        sections.append("=" * 60)
        sections.append("【浏览器当前状态】")
        sections.append("=" * 60)
        
        if self.get_browser_state:
            try:
                state = self.get_browser_state()
                sections.append(json.dumps(state, ensure_ascii=False, indent=2))
            except Exception as e:
                sections.append(f"获取状态失败: {e}")
        else:
            sections.append("浏览器状态获取器未配置")
        
        # 2. 可用工具清单
        sections.append("\n" + "=" * 60)
        sections.append("【可用工具清单】")
        sections.append("=" * 60)
        
        enabled = self.config.get_enabled_tools()
        sections.append(f"当前启用的工具: {', '.join(enabled)}")
        
        # 3. 详细工具说明
        if self.config.enable_help:
            sections.append("\n--- browser_help ---")
            sections.append("描述: 获取此帮助信息和浏览器状态")
            sections.append("用法: 无需参数，直接调用")
        
        if self.config.enable_execute_python:
            sections.append("\n--- execute_python ---")
            sections.append("描述: 执行 Python 代码直接操控浏览器")
            sections.append("环境:")
            sections.append("  - page: Playwright Page 对象（当前页面）")
            sections.append("  - 预封装函数: 以下函数可直接调用")
            sections.append("")
            sections.append(self._get_prebuilt_funcs_doc())
        
        if self.config.enable_agent_task:
            sections.append("\n--- agent_task ---")
            sections.append("描述: 用自然语言描述任务，由 Agent 自动规划和执行")
            sections.append("适用场景:")
            sections.append("  - 复杂多步骤任务")
            sections.append("  - 需要智能决策的场景")
            sections.append("  - 你不确定如何编写代码时")
            sections.append("参数:")
            sections.append("  - task: 任务描述（自然语言）")
            sections.append("  - max_steps: 最大执行步数（可选，默认15）")
        
        sections.append("\n" + "=" * 60)
        sections.append("【使用建议】")
        sections.append("=" * 60)
        sections.append("1. 简单操作（点击、填写、获取信息）→ 使用 execute_python")
        sections.append("2. 复杂任务（多步骤、需要判断）→ 使用 agent_task")
        sections.append("3. 不确定怎么做 → 先调用 browser_help 查看状态")
        
        return "\n".join(sections)
    
    def _get_prebuilt_funcs_doc(self) -> str:
        """获取预封装函数文档"""
        docs = """
【页面操作】
  get_page_summary()           - 获取页面摘要（URL、标题、元素统计）
  find_elements(selector, n)   - 查找元素并显示信息
  click_element(selector, i)   - 点击第 i 个匹配元素
  fill_form(selector, value)   - 填充表单
  wait_and_capture(ms)         - 等待并捕获页面状态
  extract_links(pattern)       - 提取链接（可正则过滤）
  smart_scroll(dir, amount)    - 智能滚动（down/up/bottom/top）

【标签页管理】
  new_tab(url)                 - 新开标签页（可选打开URL）
  switch_tab(index)            - 切换到指定索引的标签页
  list_tabs()                  - 列出所有标签页
  close_tab(index)             - 关闭标签页（默认当前页）

【其他】
  list_prebuilt_funcs()        - 列出所有可用函数
"""
        return docs


class ExecutePythonTool(BaseTool):
    """
    执行 Python 代码工具
    
    在浏览器环境中执行 Python 代码，预封装常用函数。
    支持通过工厂函数延迟获取 interpreter，解决 SSE 模式下的初始化问题。
    """
    
    # 类级别的执行锁，确保同一时间只有一个代码在执行
    _execution_lock = None
    
    def __init__(self, config: MCPToolConfig = None, interpreter_or_factory=None):
        self.config = config or MCPToolConfig()
        self._interpreter = interpreter_or_factory
        self._interpreter_factory = None
        
        # 如果传入的是 callable，则作为 factory 使用
        if callable(interpreter_or_factory):
            self._interpreter_factory = interpreter_or_factory
            self._interpreter = None
        
        # 初始化锁（类级别，所有实例共享）
        if ExecutePythonTool._execution_lock is None:
            import asyncio
            ExecutePythonTool._execution_lock = asyncio.Lock()
    
    def _get_interpreter(self):
        """获取 interpreter 实例（支持延迟初始化）"""
        if self._interpreter is not None:
            return self._interpreter
        if self._interpreter_factory is not None:
            self._interpreter = self._interpreter_factory()
            return self._interpreter
        return None
    
    @property
    def name(self) -> str:
        return "execute_python"
    
    @property
    def description(self) -> str:
        return """执行 Python 代码操控浏览器。

环境已预配置：
- page: Playwright Page 对象（当前页面）
- context: 浏览器上下文（用于管理标签页）

推荐使用预封装函数（已自动导入）：
- get_page_summary() - 获取页面摘要（URL、标题、关键元素统计）
- find_elements(selector, max_count) - 查找元素
- click_element(selector, index) - 点击元素
- fill_form(selector, value) - 填充表单
- new_tab(url) - 新开标签页
- switch_tab(index) - 切换标签页
- list_tabs() - 列出所有标签页
- smart_scroll(direction, amount) - 智能滚动
- extract_links(pattern) - 提取链接
- wait_and_capture(timeout) - 等待并捕获状态

只有在预封装函数无法满足需求时，才直接使用 page 对象。"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python 代码字符串。建议优先使用预封装函数如 get_page_summary()、find_elements() 等，它们更简洁且已处理常见异常。只有在特殊需求时才直接使用 page 对象。"
                }
            },
            "required": ["code"]
        }
    
    async def execute_async(self, code: str) -> str:
        """异步执行 Python 代码（在单独线程中运行同步代码）"""
        import asyncio
        # 使用锁确保同一时间只有一个代码在执行，避免状态混乱
        async with ExecutePythonTool._execution_lock:
            return await asyncio.to_thread(self.execute, code)
    
    def execute(self, code: str) -> str:
        """执行 Python 代码"""
        interpreter = self._get_interpreter()
        if not interpreter:
            return "错误: Python 执行器未配置"
        
        # 确保浏览器已初始化（在单独线程中）
        if not interpreter._initialized:
            import os
            from dotenv import load_dotenv
            load_dotenv(override=False)
            debug_port_str = os.getenv("BROWSER_DEBUG_PORT", "")
            debug_port = int(debug_port_str) if debug_port_str else None
            headless = os.getenv("BROWSER_HEADLESS", "false").lower() == "true"
            result = interpreter.initialize(headless=headless, debug_port=debug_port)
            if not result.success:
                return f"浏览器初始化失败: {result.stderr}"
        
        # 包装代码，注入预封装函数
        if self.config.include_prebuilt_funcs:
            full_code = self.config.prebuilt_funcs_code + "\n\n# ===== 用户代码 =====\n" + code
        else:
            full_code = code
        
        try:
            result = interpreter.execute(full_code)
            
            output = []
            if result.stdout:
                output.append("[输出]\n" + result.stdout)
            if result.stderr:
                output.append("[错误]\n" + result.stderr)
            if result.error:
                output.append("[异常]\n" + str(result.error))
            
            return "\n".join(output) if output else "执行完成（无输出）"
        except Exception as e:
            return f"执行失败: {str(e)}"


class AgentTaskTool(BaseTool):
    """
    Agent 任务工具
    
    用自然语言描述任务，由 Agent 自动规划和执行。
    """
    
    def __init__(self, config: MCPToolConfig = None, agent_factory=None):
        self.config = config or MCPToolConfig()
        self.agent_factory = agent_factory  # 延迟创建 Agent
    
    @property
    def name(self) -> str:
        return "agent_task"
    
    @property
    def description(self) -> str:
        return "用自然语言描述浏览器任务，由 AI Agent 自动规划和执行。适合复杂多步骤任务。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "任务描述，例如：'去 GitHub 搜索 playwright 项目，返回 star 数最多的那个'"
                },
                "max_steps": {
                    "type": "integer",
                    "description": "最大执行步数，防止无限循环",
                    "default": 15
                }
            },
            "required": ["task"]
        }
    
    def execute(self, task: str, max_steps: int = None) -> str:
        """执行 Agent 任务"""
        if not self.agent_factory:
            return "错误: Agent 工厂未配置"
        
        try:
            # 延迟创建 Agent
            agent = self.agent_factory()
            steps = max_steps or self.config.agent_max_steps
            
            # 运行任务
            success = agent.run_task(task, max_steps=steps)
            
            result = {
                "success": success,
                "task": task,
                "max_steps": steps,
                "message": "任务完成" if success else "任务未完成或达到步数限制"
            }
            
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return f"Agent 执行失败: {str(e)}"


# ============================================================================
# 工具工厂
# ============================================================================

class MCPToolSet:
    """
    MCP 工具集工厂
    
    根据配置创建工具实例，支持灵活启用/禁用。
    
    使用示例:
        config = MCPToolConfig(
            enable_execute_python=True,
            enable_agent_task=False  # 禁用 Agent
        )
        toolset = MCPToolSet(config)
        tools = toolset.create_tools(interpreter=my_interpreter)
    """
    
    def __init__(self, config: MCPToolConfig = None):
        self.config = config or MCPToolConfig()
    
    def create_tools(
        self,
        interpreter=None,
        interpreter_factory=None,
        agent_factory=None,
        get_browser_state=None
    ) -> List[BaseTool]:
        """
        根据配置创建工具列表
        
        Args:
            interpreter: Python 代码执行器（execute_python 需要，已废弃，请使用 interpreter_factory）
            interpreter_factory: 返回 interpreter 的工厂函数（支持延迟初始化）
            agent_factory: Agent 工厂函数（agent_task 需要）
            get_browser_state: 获取浏览器状态的函数（help 需要）
        
        Returns:
            启用的工具列表
        """
        tools = []
        
        if self.config.enable_help:
            tools.append(HelpTool(self.config, get_browser_state))
        
        if self.config.enable_execute_python:
            # 优先使用 factory 模式，支持延迟初始化
            if interpreter_factory:
                tools.append(ExecutePythonTool(self.config, interpreter_factory))
            else:
                tools.append(ExecutePythonTool(self.config, interpreter))
        
        if self.config.enable_agent_task:
            tools.append(AgentTaskTool(self.config, agent_factory))
        
        return tools
    
    def get_minimal_descriptions(self) -> List[Dict[str, str]]:
        """
        获取最小化工具描述（用于初始暴露）
        
        Returns:
            简化的工具描述列表
        """
        descriptions = []
        
        if self.config.enable_help:
            descriptions.append({
                "name": "browser_help",
                "description": "获取完整帮助信息和浏览器当前状态"
            })
        
        if self.config.enable_execute_python:
            descriptions.append({
                "name": "execute_python",
                "description": "执行 Python 代码操控浏览器（调用 help 查看详情）"
            })
        
        if self.config.enable_agent_task:
            descriptions.append({
                "name": "agent_task",
                "description": "自然语言任务，由 Agent 自动执行（调用 help 查看详情）"
            })
        
        return descriptions
