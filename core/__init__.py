"""
MacroChromeMCP 核心逻辑层

包含代码解释器、Agent 编排和 Prompt 管理
"""

from .interpreter import CodeInterpreter
from .agent import ExecutorAgent
from .prompts import SYSTEM_PROMPT, TASK_TEMPLATE

__all__ = ["CodeInterpreter", "ExecutorAgent", "SYSTEM_PROMPT", "TASK_TEMPLATE"]
