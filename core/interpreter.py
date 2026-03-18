"""
代码解释器：使用 code.InteractiveInterpreter 实现真正的交互式执行环境

核心职责：
1. 保持 Playwright 的 browser 和 page 对象在多个代码块执行间不销毁
2. 使用 InteractiveInterpreter 自动累积变量状态
3. 将执行过程中的观察结果返回给执行层 Agent
"""

import io
import sys
import traceback
import code
from typing import Dict, Any, Optional
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
    代码解释器类 - 基于 code.InteractiveInterpreter
    
    提供真正的交互式代码执行环境，变量状态自动累积
    """
    
    def __init__(self):
        # 这是一个真正的交互式命名空间，它会保存所有执行过的状态
        self.locals: Dict[str, Any] = {}
        self.interpreter = code.InteractiveInterpreter(self.locals)
        self._initialized: bool = False
        
        # 浏览器相关对象引用（本地保存一份方便访问）
        self._browser: Optional[Any] = None
        self._page: Optional[Any] = None
        self._context: Optional[Any] = None
        self._pw: Optional[Any] = None
    
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
        from playwright.sync_api import sync_playwright
        
        start_time = time.time()
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        
        try:
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                # 启动 Playwright
                self._pw = sync_playwright().start()
                
                # 如果提供了调试端口，连接到现有 Chrome
                if debug_port:
                    self._browser = self._pw.chromium.connect_over_cdp(f"http://localhost:{debug_port}")
                    self._context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
                    # 连接到已有 Chrome 时，使用已有页面而不是新建
                    if self._context.pages:
                        self._page = self._context.pages[0]
                        print(f"[连接成功] 使用已有页面: {self._page.url}")
                    else:
                        self._page = self._context.new_page()
                        print(f"[连接成功] 新建页面: {self._page}")
                else:
                    self._browser = self._pw.chromium.launch(headless=headless)
                    self._context = self._browser.new_context(
                        viewport={"width": 1920, "height": 1080}
                    )
                    self._page = self._context.new_page()
                
                # 【关键】直接把对象塞进 locals 字典，代码就能访问了
                self.locals["page"] = self._page
                self.locals["browser"] = self._browser
                self.locals["context"] = self._context
                self.locals["p"] = self._pw
                
                self._initialized = True
                print(f"[初始化成功] Browser: {self._browser}, Page: {self._page}")
                
            return ExecutionResult(
                success=True,
                stdout=output_buffer.getvalue(),
                stderr=error_buffer.getvalue(),
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            error_msg = traceback.format_exc()
            return ExecutionResult(
                success=False,
                stdout=output_buffer.getvalue(),
                stderr=f"{error_buffer.getvalue()}\n{error_msg}",
                error=str(e),
                execution_time=time.time() - start_time
            )
    
    def execute(self, code: str) -> ExecutionResult:
        """
        使用 exec 在持久化的 locals 命名空间中执行代码
        """
        output_buffer = io.StringIO()
        error_buffer = io.StringIO()
        
        # 确保 code 结尾有换行，防止某些语法解析错误
        if not code.endswith('\n'):
            code += '\n'
        
        # 【注入快捷变量】确保关键对象在 locals 中可用
        # 这样 Agent 可以直接使用 page, context, browser 等变量
        if self._page:
            self.locals["page"] = self._page
        if self._context:
            self.locals["context"] = self._context
        if self._browser:
            self.locals["browser"] = self._browser
        if self._pw:
            self.locals["p"] = self._pw

        try:
            # 捕获所有输出
            with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
                # 【核心修改】
                # 使用 exec 而不是 runsource
                # 第一个参数是代码，第二个是全局变量，第三个是局部变量
                # 在这里我们全部指向 self.locals，实现变量在多次执行间累积
                exec(code, self.locals, self.locals)
                
            return ExecutionResult(
                success=True,
                stdout=output_buffer.getvalue(),
                stderr=error_buffer.getvalue()
            )
            
        except Exception:
            # 捕获执行期的真实异常
            error_msg = traceback.format_exc()
            return ExecutionResult(
                success=False,
                stdout=output_buffer.getvalue(),
                stderr=f"{error_buffer.getvalue()}\n{error_msg}",
                error=error_msg
            )
            
    def _capture_page_state(self) -> Optional[Dict[str, Any]]:
        """捕获当前页面状态"""
        try:
            page = self.locals.get('page')
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
        return self.locals.get('page')
    
    def get_browser(self) -> Optional[Any]:
        """获取当前 browser 对象"""
        return self.locals.get('browser')
    
    def close(self) -> None:
        """关闭浏览器，清理资源"""
        try:
            if self._browser:
                self._browser.close()
            if self._pw:
                self._pw.stop()
                
            self.locals.clear()
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
