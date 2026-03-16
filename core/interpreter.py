"""
代码解释器：负责 exec() 和 Playwright 持久化

核心职责：
1. 保持 Playwright 的 browser 和 page 对象在多个代码块执行间不销毁
2. 限制执行环境，捕获所有 stdout 和 stderr
3. 将执行过程中的观察结果返回给执行层 Agent
"""

import io
import sys
import traceback
from typing import Dict, Any, Optional, Tuple
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field


@dataclass
class ExecutionResult:
    """代码执行结果"""
    success: bool
    stdout: str = ""
    stderr: str = ""
    output: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    page_state: Optional[Dict[str, Any]] = field(default_factory=dict)


class CodeInterpreter:
    """
    代码解释器类
    
    提供安全的代码执行环境，保持 Playwright 浏览器状态
    """
    
    def __init__(self):
        # 持久化的执行环境
        self._globals: Dict[str, Any] = {}
        self._locals: Dict[str, Any] = {}
        self._initialized: bool = False
        
        # 浏览器相关对象引用
        self._browser: Optional[Any] = None
        self._page: Optional[Any] = None
        self._context: Optional[Any] = None
        
        # 执行历史
        self._execution_history: list = []
    
    def initialize(self, headless: bool = False, debug_port: Optional[int] = None) -> ExecutionResult:
        """
        初始化 Playwright 环境
        
        Args:
            headless: 是否无头模式
            debug_port: Chrome 远程调试端口
            
        Returns:
            ExecutionResult: 初始化结果
        """
        import time
        start_time = time.time()
        
        init_code = '''
from playwright.sync_api import sync_playwright

# 启动 Playwright
p = sync_playwright().start()

# 浏览器启动参数
launch_args = {
    "headless": headless,
}

# 如果提供了调试端口，连接到现有 Chrome
if debug_port:
    browser = p.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
    context = browser.contexts[0] if browser.contexts else browser.new_context()
else:
    browser = p.chromium.launch(**launch_args)
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )

page = context.new_page()

print(f"[初始化成功] Browser: {browser}, Page: {page}")
'''
        
        result = self.execute(init_code, {
            'headless': headless,
            'debug_port': debug_port
        })
        
        if result.success:
            self._initialized = True
            # 保存关键对象引用
            self._browser = self._globals.get('browser')
            self._page = self._globals.get('page')
            self._context = self._globals.get('context')
        
        result.execution_time = time.time() - start_time
        return result
    
    def execute(self, code: str, extra_globals: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        执行 Python 代码
        
        Args:
            code: 要执行的代码字符串
            extra_globals: 额外的全局变量
            
        Returns:
            ExecutionResult: 执行结果
        """
        import time
        start_time = time.time()
        
        # 准备执行环境
        exec_globals = self._globals.copy()
        if extra_globals:
            exec_globals.update(extra_globals)
        
        # 捕获输出
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                # 使用 exec 执行代码
                exec(code, exec_globals, self._locals)
            
            # 更新持久化环境
            self._globals.update({k: v for k, v in exec_globals.items() 
                                 if not k.startswith('_') and k not in ['exec', 'eval']})
            
            # 获取最后一行表达式的值（如果有）
            output = None
            if code.strip() and not code.strip().endswith(')'):
                try:
                    last_line = code.strip().split('\n')[-1]
                    if not last_line.startswith(('def ', 'class ', 'import ', 'from ', 'if ', 'for ', 'while ', 'with ', 'try:', '@')):
                        output = eval(last_line, self._globals, self._locals)
                except:
                    pass
            
            # 获取页面状态
            page_state = self._capture_page_state()
            
            return ExecutionResult(
                success=True,
                stdout=stdout_buffer.getvalue(),
                stderr=stderr_buffer.getvalue(),
                output=output,
                execution_time=time.time() - start_time,
                page_state=page_state
            )
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            return ExecutionResult(
                success=False,
                stdout=stdout_buffer.getvalue(),
                stderr=stderr_buffer.getvalue(),
                error=error_msg,
                execution_time=time.time() - start_time
            )
    
    def _capture_page_state(self) -> Optional[Dict[str, Any]]:
        """捕获当前页面状态"""
        try:
            page = self._globals.get('page')
            if page and hasattr(page, 'url'):
                return {
                    'url': page.url,
                    'title': page.title() if hasattr(page, 'title') else None,
                }
        except:
            pass
        return None
    
    def get_page(self) -> Optional[Any]:
        """获取当前 page 对象"""
        return self._globals.get('page')
    
    def get_browser(self) -> Optional[Any]:
        """获取当前 browser 对象"""
        return self._globals.get('browser')
    
    def close(self) -> None:
        """关闭浏览器，清理资源"""
        try:
            browser = self._globals.get('browser')
            p = self._globals.get('p')
            
            if browser:
                browser.close()
            if p:
                p.stop()
                
            self._globals.clear()
            self._locals.clear()
            self._initialized = False
            
        except Exception as e:
            print(f"[关闭错误] {e}")
    
    @property
    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
