import abc
from typing import Any, Dict

class BaseTool(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """工具名称，必须是字母、数字、下划线组合"""
        pass

    @property
    @abc.abstractmethod
    def description(self) -> str:
        """工具的详细描述，告诉 LLM 什么时候用它"""
        pass

    @property
    @abc.abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """符合 JSON Schema 规范的参数定义"""
        pass

    @abc.abstractmethod
    def execute(self, **kwargs) -> str:
        """执行逻辑，必须返回字符串结果供 LLM 观察"""
        pass

    def to_openai_format(self) -> Dict[str, Any]:
        """导出为 OpenAI API 支持的格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }