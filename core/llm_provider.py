from openai import OpenAI
from typing import List, Dict, Any, Optional
from core.task_logger import TaskLogger, NoOpTaskLogger

class LLMProvider:
    def __init__(self, 
                 api_key: str, 
                 base_url: str = "https://api.openai.com/v1", 
                 model: str = "gpt-4o",
                 task_logger: Optional[TaskLogger] = None):
        """
        Args:
            api_key: OpenAI API 密钥
            base_url: API 基础 URL
            model: 模型名称
            task_logger: 任务日志记录器，如果为 None 则使用 NoOpTaskLogger（不记录）
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.task_logger = task_logger or NoOpTaskLogger()

    def set_task_logger(self, task_logger: Optional[TaskLogger]) -> None:
        """设置/切换当前任务的日志记录器
        
        Args:
            task_logger: 新的 TaskLogger 实例，None 表示禁用日志
        """
        self.task_logger = task_logger or NoOpTaskLogger()

    def chat_with_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None):
        """发送对话并支持工具调用，同时记录到任务日志"""
        kwargs = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        # 发送请求
        response = self.client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        
        # 记录到任务日志
        self._log_call(kwargs, response, message)
        
        return message
    
    def _log_call(self, request_kwargs: Dict[str, Any], 
                  raw_response: Any, 
                  message: Any) -> None:
        """将 LLM 调用记录到任务日志
        
        Args:
            request_kwargs: 请求参数
            raw_response: 原始响应对象
            message: 解析后的消息对象
        """
        # 构建请求记录
        request_record = {
            "messages": request_kwargs.get("messages", []),
            "tools": request_kwargs.get("tools", []),
            "tool_choice": request_kwargs.get("tool_choice")
        }
        
        # 构建响应记录
        response_dict = message.model_dump(exclude_none=True)
        # 添加 usage 信息（从原始响应中获取）
        if hasattr(raw_response, 'usage') and raw_response.usage:
            usage = raw_response.usage
            response_dict["usage"] = {
                "prompt_tokens": getattr(usage, 'prompt_tokens', 0),
                "completion_tokens": getattr(usage, 'completion_tokens', 0),
                "total_tokens": getattr(usage, 'total_tokens', 0)
            }
        
        self.task_logger.log_llm_call(
            request=request_record,
            response=response_dict,
            model=self.model
        )