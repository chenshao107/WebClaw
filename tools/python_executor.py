from tools.base import BaseTool
from core.interpreter import CodeInterpreter  # 修改这里

class PythonExecutorTool(BaseTool):
    def __init__(self, interpreter: CodeInterpreter):  # 修改这里
        self.interpreter = interpreter

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return (
            "在持久化的 Playwright 环境中执行 Python 代码。环境已预置 'page', 'browser', 'context' 对象。\n"
            "你可以使用 page.locator(), page.evaluate() 等完整 Playwright API。\n"
            "注意：\n"
            "1. 若需返回数据给大模型观察，请使用 print()。\n"
            "2. 为避免上下文爆炸，若获取网页源码或大段文本，请在代码中先用 BeautifulSoup 等工具做截断或摘要！"
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码片段"
                }
            },
            "required": ["code"]
        }

    def execute(self, code: str) -> str:
        result = self.interpreter.execute(code)
        
        # 将 result["success"] 改为 result.success，注意其他属性也全改为点号
        if result.success:
            # 如果没有输出，给一个默认成功的提示，否则 LLM 会困惑
            return result.stdout if result.stdout and result.stdout.strip() else "代码执行成功，无控制台输出。"
        else:
            # 兼容一下，你之前的对象里可能有 stderr 或者 error 属性
            error_msg = getattr(result, 'stderr', '') or getattr(result, 'error', '未知错误')
            return f"代码执行失败:\n{error_msg}"