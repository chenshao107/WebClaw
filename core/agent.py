import json
import os
import re
from typing import List, Dict, Any
from datetime import datetime
from core.llm_provider import LLMProvider
from core.task_logger import TaskLogger
from core.experience_store import ExperienceStore, get_experience_store
from tools.base import BaseTool

# 从环境变量读取配置，默认25步
DEFAULT_MAX_STEPS = int(os.getenv('AGENT_MAX_STEPS', '25'))

class ExecutorAgent:
    def __init__(self, llm: LLMProvider, tools: List[BaseTool], enable_experience: bool = True):
        self.llm = llm
        self.tools = {tool.name: tool for tool in tools}
        self.tool_schemas = [tool.to_openai_format() for tool in tools]
        self.enable_experience = enable_experience
        self.experience_store: ExperienceStore = get_experience_store() if enable_experience else None
        
        self.system_prompt = """你是一个顶级的浏览器自动化特种兵。
你被连接到了一个真实的 Windows Chrome 浏览器上。
你可以通过 `execute_python` 工具编写并执行 Playwright 代码来完成任务。
环境已注入 `page` 全局对象。

【你的工作流 (ReAct)】
1. 思考：分析当前需要做什么。
2. 行动：调用 execute_python 执行代码（如 page.goto(), page.click()，或 print(page.title())）。
3. 观察：阅读代码执行返回的 stdout 或 stderr。
4. 修正：如果报错或未找到元素，重新编写代码重试。
5. 完结：当任务彻底完成时，回复一段包含 "TASK_FINISHED" 字样的总结，并结束工作。

【防上下文爆炸警告】
绝不要直接 print(page.content())！
如果你需要分析页面结构，请在 Python 代码中使用 lxml 或 BeautifulSoup 提取核心可见元素的 innerText，或者精简 DOM，只 print 你最关心的那部分。

【经验学习机制】
- 如果历史经验对你有帮助，请在回复中提及
- 如果发现新技巧或旧经验有误，任务结束后可以调用相关工具记录
- 持续优化你的执行策略"""

        self.history = [{"role": "system", "content": self.system_prompt}]
        self.current_task_logger: TaskLogger = None

    def _generate_task_id(self, task_description: str) -> str:
        """根据任务描述生成任务 ID"""
        # 取前 20 个字符，移除非字母数字字符
        short_desc = re.sub(r'[^\w\u4e00-\u9fff]', '_', task_description[:30])
        timestamp = datetime.now().strftime("%H%M%S")
        return f"{short_desc}_{timestamp}"

    def _build_system_prompt_with_experiences(self, task_description: str) -> str:
        """构建包含相关经验的系统提示"""
        base_prompt = self.system_prompt
        
        if not self.enable_experience or not self.experience_store:
            return base_prompt
        
        # 从任务描述中提取域名（简单启发式）
        domain = None
        url_match = re.search(r'https?://([^/\s]+)', task_description)
        if url_match:
            domain = url_match.group(1)
        
        # 检索相关经验
        experiences = self.experience_store.retrieve(
            context=task_description,
            limit=3,
            domain_filter=domain
        )
        
        if not experiences:
            return base_prompt
        
        # 构建经验提示
        exp_text = "\n\n【相关历史经验】\n"
        for i, exp in enumerate(experiences, 1):
            exp_text += f"\n--- 经验 {i} ---"
            exp_text += exp.to_prompt_text()
        
        return base_prompt + exp_text

    def run_task(self, task_description: str, max_steps: int = None):
        # 使用默认值（从环境变量读取）
        if max_steps is None:
            max_steps = DEFAULT_MAX_STEPS
        # 1. 为本次任务创建新的日志记录器
        task_id = self._generate_task_id(task_description)
        self.current_task_logger = TaskLogger(task_id=task_id)
        self.llm.set_task_logger(self.current_task_logger)
        
        # 2. 构建包含经验的系统提示
        system_prompt = self._build_system_prompt_with_experiences(task_description)
        self.history = [{"role": "system", "content": system_prompt}]
        
        self.history.append({"role": "user", "content": task_description})
        print(f"\n🚀 [Agent 接管任务] {task_description}")

        try:
            for step in range(max_steps):
                print(f"\n--- 第 {step + 1} 轮思考 ---")
                
                # 1. 呼叫大模型
                message = self.llm.chat_with_tools(self.history, self.tool_schemas)
                self.history.append(message.model_dump(exclude_none=True))

                # 2. 判断是否触发了工具调用 (Action)
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)
                        
                        print(f"🛠️  [执行工具] {function_name}")
                        if function_name == "execute_python":
                            print(f"```python\n{arguments.get('code', '')}\n```")

                        # 执行工具
                        tool = self.tools.get(function_name)
                        if tool:
                            observation = tool.execute(**arguments)
                        else:
                            observation = f"Error: 找不到工具 {function_name}"
                        
                        print(f"👀 [观察结果]\n{observation.strip()[:500]}..." if len(observation)>500 else f"👀 [观察结果]\n{observation.strip()}")

                        # 3. 将观察结果 (Observation) 塞回历史记录
                        self.history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": str(observation)
                        })
                else:
                    # 如果没有调用工具，说明它在说话，检查是否完成
                    reply = message.content or ""
                    print(f"🤖 [Agent 回复]\n{reply}")
                    
                    if "TASK_FINISHED" in reply:
                        print("\n🎉 任务圆满结束！")
                        return True
                    
                    # 如果既没调用工具也没说完成，强制它继续
                    self.history.append({
                        "role": "user", 
                        "content": "请继续使用工具执行下一步，或回复 TASK_FINISHED 结束任务。"
                    })

            print("\n⚠️ 达到最大步数限制，任务强制终止。")
            return False
            
        finally:
            # 任务结束（无论成功或失败），标记日志完成
            if self.current_task_logger:
                self.current_task_logger.end_task()
                self.current_task_logger = None
            # 重置 LLM 的日志记录器
            self.llm.set_task_logger(None)