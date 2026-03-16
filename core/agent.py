"""
Agent 编排：负责 LLM 交互逻辑、Prompt 管理

核心职责：
1. 接收宏观任务，编排执行流程
2. 与 LLM 交互，生成 Playwright 代码
3. 处理执行结果，进行自修复
4. 收敛最终结果返回给上层
"""

import json
import re
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field

from .interpreter import CodeInterpreter, ExecutionResult
from .prompts import SYSTEM_PROMPT, format_task_prompt, format_repair_prompt


@dataclass
class TaskResult:
    """任务执行结果"""
    success: bool
    task: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    final_data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    total_time: float = 0.0


class ExecutorAgent:
    """
    执行 Agent 类
    
    负责将宏观任务转化为可执行的 Playwright 代码，
    并在失败时进行自修复。
    """
    
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        llm_provider: str = "anthropic",
        llm_model: Optional[str] = None,
        max_retries: int = 3,
        headless: bool = False,
        debug_port: Optional[int] = None
    ):
        """
        初始化 Executor Agent
        
        Args:
            llm_client: LLM 客户端实例
            llm_provider: LLM 提供商 (anthropic/openai/deepseek)
            llm_model: LLM 模型名称（如 deepseek-chat）
            max_retries: 最大重试次数
            headless: 是否无头模式
            debug_port: Chrome 调试端口
        """
        self.llm_client = llm_client
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.max_retries = max_retries
        self.headless = headless
        self.debug_port = debug_port
        
        # 初始化代码解释器
        self.interpreter = CodeInterpreter()
        
        # 执行历史
        self.execution_history: List[Dict[str, Any]] = []
        
        # 初始化标志
        self._initialized = False
    
    def initialize(self) -> bool:
        """初始化浏览器环境"""
        if not self._initialized:
            result = self.interpreter.initialize(
                headless=self.headless,
                debug_port=self.debug_port
            )
            self._initialized = result.success
            if not result.success:
                print(f"[初始化失败] {result.error}")
            return result.success
        return True
    
    def execute_task(self, task_description: str) -> TaskResult:
        """
        执行宏观任务
        
        Args:
            task_description: 任务描述
            
        Returns:
            TaskResult: 任务执行结果
        """
        import time
        start_time = time.time()
        
        # 确保已初始化
        if not self.initialize():
            return TaskResult(
                success=False,
                task=task_description,
                error="浏览器初始化失败"
            )
        
        self.execution_history = []
        
        # 获取当前页面状态
        page_state = self.interpreter._capture_page_state()
        
        # 第一步：生成初始代码
        prompt = format_task_prompt(task_description, page_state, self.execution_history)
        code = self._generate_code(prompt)
        
        if not code:
            return TaskResult(
                success=False,
                task=task_description,
                error="无法生成执行代码"
            )
        
        # 执行循环（支持自修复）
        for attempt in range(self.max_retries):
            print(f"[执行尝试 {attempt + 1}/{self.max_retries}]")
            
            # 执行代码
            result = self.interpreter.execute(code)
            
            # 记录执行历史
            step_record = {
                "attempt": attempt + 1,
                "code": code,
                "success": result.success,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            self.execution_history.append(step_record)
            
            if result.success:
                # 解析结果
                final_data = self._parse_result(result.stdout)
                
                return TaskResult(
                    success=True,
                    task=task_description,
                    steps=self.execution_history,
                    final_data=final_data,
                    total_time=time.time() - start_time
                )
            
            # 执行失败，尝试修复
            print(f"[执行失败] {result.error}")
            
            if attempt < self.max_retries - 1:
                # 生成修复提示
                page_state = self.interpreter._capture_page_state()
                repair_prompt = format_repair_prompt(
                    task_description, code, result.error, page_state
                )
                code = self._generate_code(repair_prompt)
                
                if not code:
                    break
        
        # 所有重试都失败
        return TaskResult(
            success=False,
            task=task_description,
            steps=self.execution_history,
            error=f"执行失败，已重试 {self.max_retries} 次",
            total_time=time.time() - start_time
        )
    
    def _generate_code(self, prompt: str) -> Optional[str]:
        """
        调用 LLM 生成代码
        
        Args:
            prompt: 提示词
            
        Returns:
            生成的代码或 None
        """
        # 如果有外部 LLM 客户端，使用它
        if self.llm_client:
            return self._call_external_llm(prompt)
        
        # 否则使用简单的本地实现（用于测试）
        return self._generate_code_local(prompt)
    
    def _call_external_llm(self, prompt: str) -> Optional[str]:
        """调用外部 LLM"""
        try:
            if self.llm_provider == "anthropic":
                return self._call_anthropic(prompt)
            elif self.llm_provider == "openai":
                return self._call_openai(prompt)
            elif self.llm_provider == "deepseek":
                return self._call_deepseek(prompt)
        except Exception as e:
            print(f"[LLM 调用失败] {e}")
        return None
    
    def _call_anthropic(self, prompt: str) -> Optional[str]:
        """调用 Claude API"""
        # 这里需要实际的 API 调用
        # 示例实现，需要配置 API key
        response = self.llm_client.messages.create(
            model="claude-3-sonnet-20240229",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._extract_code(response.content[0].text)
    
    def _call_openai(self, prompt: str) -> Optional[str]:
        """调用 OpenAI API（兼容 DeepSeek 等 OpenAI 格式 API）"""
        response = self.llm_client.chat.completions.create(
            model=getattr(self, 'llm_model', 'gpt-4-turbo-preview'),
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096
        )
        return self._extract_code(response.choices[0].message.content)
    
    def _generate_code_local(self, prompt: str) -> Optional[str]:
        """
        本地代码生成（用于测试，实际应使用 LLM）
        
        这是一个简化实现，实际使用时应该调用 LLM
        """
        # 从提示词中提取任务
        task_match = re.search(r'## 任务指令\s*\n(.+?)(?=\n##|$)', prompt, re.DOTALL)
        if task_match:
            task = task_match.group(1).strip()
        else:
            task = prompt
        
        # 简单的任务映射（仅用于演示）
        if "搜索" in task or "search" in task.lower():
            return self._generate_search_code(task)
        elif "截图" in task or "screenshot" in task.lower():
            return self._generate_screenshot_code(task)
        elif "点击" in task or "click" in task.lower():
            return self._generate_click_code(task)
        
        # 默认代码模板
        return '''
# 默认执行代码
print('{"status": "success", "message": "任务执行完成", "data": {}}')
'''
    
    def _generate_search_code(self, task: str) -> str:
        """生成搜索代码"""
        return '''
# 执行搜索任务
page.goto("https://www.baidu.com")
page.wait_for_load_state("networkidle")

# 查找搜索框并输入
search_box = page.locator("#kw").first
search_box.fill("搜索内容")

# 点击搜索按钮
page.locator("#su").click()
page.wait_for_load_state("networkidle")

# 等待结果加载
page.wait_for_selector(".result", timeout=10000)

# 提取结果
titles = page.locator(".result .t").all_inner_texts()[:5]

print(f'{"status": "success", "data": {"titles": {titles}}, "summary": "搜索完成"}')
'''
    
    def _generate_screenshot_code(self, task: str) -> str:
        """生成截图代码"""
        return '''
# 执行截图任务
screenshot_path = "screenshot.png"
page.screenshot(path=screenshot_path, full_page=True)

print(f'{"status": "success", "data": {"screenshot_path": "' + screenshot_path + '"}, "summary": "截图已保存"}')
'''
    
    def _generate_click_code(self, task: str) -> str:
        """生成点击代码"""
        return '''
# 执行点击任务
# 尝试多种选择器策略
selectors = ["button", "a", "[role='button']", ".btn", "input[type='submit']"]

clicked = False
for selector in selectors:
    try:
        element = page.locator(selector).first
        if element.is_visible():
            element.click()
            clicked = True
            break
    except:
        continue

if clicked:
    page.wait_for_load_state("networkidle")
    print('{"status": "success", "data": {"clicked": true}, "summary": "点击成功"}')
else:
    print('{"status": "error", "message": "未找到可点击元素"}')
'''
    
    def _extract_code(self, text: str) -> Optional[str]:
        """从 LLM 响应中提取代码块"""
        # 匹配 ```python ... ``` 代码块
        pattern = r'```python\s*\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # 如果没有 python 标记，尝试匹配任意代码块
        pattern = r'```\s*\n(.*?)\n```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # 如果没有代码块标记，返回整个文本
        return text.strip()
    
    def _parse_result(self, stdout: str) -> Dict[str, Any]:
        """解析执行结果"""
        try:
            # 尝试从 stdout 中提取 JSON
            lines = stdout.strip().split('\n')
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    return json.loads(line)
        except:
            pass
        
        # 返回原始输出
        return {"raw_output": stdout}
    
    def close(self):
        """关闭 Agent，释放资源"""
        self.interpreter.close()
        self._initialized = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
