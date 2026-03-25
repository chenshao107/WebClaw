from tools.base import BaseTool
from core.interpreter import CodeInterpreter  # 修改这里

class PythonExecutorTool(BaseTool):
    def __init__(self, interpreter: CodeInterpreter):  # 修改这里
        self.interpreter = interpreter

    @property
    def name(self) -> str:
        return "execute_python"

    def _get_tool_descriptions(self) -> str:
        """动态获取已注册工具的说明"""
        tools = CodeInterpreter.get_tool_descriptions()
        if not tools:
            return ""
        
        lines = ["【预置函数】"]
        for tool in tools:
            lines.append(f"- {tool['name']}{tool['signature']}: {tool['description']}")
        return "\n".join(lines)

    @property
    def description(self) -> str:
        tool_section = self._get_tool_descriptions()
        
        return (
            "在持久化的 Playwright 环境中执行 Python 代码。环境已预置以下对象和函数：\n"
            "【预置对象】\n"
            "- page: 当前页面，可使用 page.goto(), page.locator(), page.evaluate() 等 Playwright API\n"
            "- context: 浏览器上下文，可使用 context.new_page() 创建新标签页\n"
            "- browser: 浏览器实例\n"
            f"{tool_section}\n"
            "【使用建议】\n"
            "1. 操作前先调用 list_tabs() 查看可用标签页\n"
            "2. 获取页面内容时优先使用 capture_snapshot() 而非 page.content()\n"
            "3. 若需返回数据给大模型观察，请使用 print()\n"
            "【添加新工具】\n"
            "如需添加新工具函数，在 tools/ 目录下创建新文件，"
            "然后在 CodeInterpreter._register_builtin_tools() 中注册即可，无需修改此描述。"
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