"""
MCP 服务入口：将 Agent 封装为 MCP Tool

核心职责：
1. 实现 MCP 协议接口
2. 将 ExecutorAgent 暴露为 MCP Tool
3. 处理 MCP 客户端的请求
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

# MCP 协议相关导入
# 注意：实际使用时需要根据 mcp 库的实际 API 调整
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("[警告] MCP 库未安装，MCP 服务不可用")

from core.agent import ExecutorAgent
from core.interpreter import ExecutionResult


@dataclass
class MCPToolDefinition:
    """MCP Tool 定义"""
    name: str
    description: str
    parameters: Dict[str, Any]


class MCPServer:
    """
    MCP 服务类
    
    将 ExecutorAgent 封装为 MCP Tool，供 Planner 调用
    """
    
    def __init__(
        self,
        agent: Optional[ExecutorAgent] = None,
        name: str = "macrochrome-mcp-server"
    ):
        """
        初始化 MCP 服务
        
        Args:
            agent: ExecutorAgent 实例
            name: 服务名称
        """
        self.agent = agent or ExecutorAgent()
        self.name = name
        self.server = None
        
        if MCP_AVAILABLE:
            self.server = Server(name)
            self._register_tools()
    
    def _register_tools(self):
        """注册 MCP Tools"""
        if not self.server:
            return
        
        @self.server.tool()
        async def execute_macro(task: str) -> str:
            """
            执行浏览器宏任务
            
            Args:
                task: 任务描述，例如 "去 B 站搜索三体并返回第一个视频的播放量"
                
            Returns:
                JSON 格式的执行结果
            """
            result = self.agent.execute_task(task)
            
            return json.dumps({
                "success": result.success,
                "task": result.task,
                "final_data": result.final_data,
                "error": result.error,
                "total_time": result.total_time,
                "steps_count": len(result.steps)
            }, ensure_ascii=False, indent=2)
        
        @self.server.tool()
        async def get_page_info() -> str:
            """
            获取当前页面信息
            
            Returns:
                当前页面的 URL 和标题
            """
            page_state = self.agent.interpreter._capture_page_state()
            return json.dumps(page_state or {}, ensure_ascii=False)
        
        @self.server.tool()
        async def execute_python(code: str) -> str:
            """
            在浏览器环境中执行 Python 代码
            
            Args:
                code: Python 代码字符串
                
            Returns:
                执行结果
            """
            result = self.agent.interpreter.execute(code)
            
            return json.dumps({
                "success": result.success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.error,
                "execution_time": result.execution_time
            }, ensure_ascii=False, indent=2)
        
        @self.server.tool()
        async def navigate(url: str) -> str:
            """
            导航到指定 URL
            
            Args:
                url: 目标 URL
                
            Returns:
                导航结果
            """
            code = f'''
page.goto("{url}")
page.wait_for_load_state("networkidle")
print(f'{{"status": "success", "url": page.url, "title": page.title()}}')
'''
            result = self.agent.interpreter.execute(code)
            
            return json.dumps({
                "success": result.success,
                "output": result.stdout,
                "error": result.error
            }, ensure_ascii=False)
        
        @self.server.tool()
        async def screenshot(path: Optional[str] = None) -> str:
            """
            截取当前页面截图
            
            Args:
                path: 截图保存路径，默认为 "screenshot.png"
                
            Returns:
                截图结果
            """
            save_path = path or "screenshot.png"
            code = f'''
page.screenshot(path="{save_path}", full_page=True)
print(f'{{"status": "success", "path": "{save_path}"}}')
'''
            result = self.agent.interpreter.execute(code)
            
            return json.dumps({
                "success": result.success,
                "path": save_path if result.success else None,
                "error": result.error
            }, ensure_ascii=False)
    
    async def run(self, transport: str = "stdio"):
        """
        运行 MCP 服务
        
        Args:
            transport: 传输方式 (stdio/sse)
        """
        if not MCP_AVAILABLE:
            raise RuntimeError("MCP 库未安装，无法启动服务")
        
        if not self.server:
            raise RuntimeError("MCP 服务器未初始化")
        
        # 初始化 Agent
        self.agent.initialize()
        
        try:
            if transport == "stdio":
                await self.server.run_stdio_async()
            elif transport == "sse":
                await self.server.run_sse_async()
            else:
                raise ValueError(f"不支持的传输方式: {transport}")
        finally:
            self.agent.close()
    
    def get_tools(self) -> List[MCPToolDefinition]:
        """
        获取可用的 Tool 列表
        
        Returns:
            Tool 定义列表
        """
        return [
            MCPToolDefinition(
                name="execute_macro",
                description="执行浏览器宏任务，如搜索、数据提取、自动化操作等",
                parameters={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "任务描述，例如：去 B 站搜索三体并返回第一个视频的播放量"
                        }
                    },
                    "required": ["task"]
                }
            ),
            MCPToolDefinition(
                name="get_page_info",
                description="获取当前浏览器页面的 URL 和标题信息",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            ),
            MCPToolDefinition(
                name="execute_python",
                description="在浏览器环境中执行 Python 代码",
                parameters={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python 代码字符串"
                        }
                    },
                    "required": ["code"]
                }
            ),
            MCPToolDefinition(
                name="navigate",
                description="导航到指定 URL",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "目标 URL"
                        }
                    },
                    "required": ["url"]
                }
            ),
            MCPToolDefinition(
                name="screenshot",
                description="截取当前页面截图",
                parameters={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "截图保存路径",
                            "default": "screenshot.png"
                        }
                    }
                }
            )
        ]


def create_server(
    headless: bool = False,
    debug_port: Optional[int] = None,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None
) -> MCPServer:
    """
    创建 MCP 服务器实例
    
    Args:
        headless: 是否无头模式
        debug_port: Chrome 调试端口
        llm_provider: LLM 提供商
        llm_model: LLM 模型名称
        
    Returns:
        MCPServer 实例
    """
    agent = ExecutorAgent(
        headless=headless,
        debug_port=debug_port,
        llm_provider=llm_provider,
        llm_model=llm_model
    )
    
    return MCPServer(agent=agent)


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MacroChromeMCP 服务器")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--debug-port", type=int, help="Chrome 调试端口")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="传输方式")
    parser.add_argument("--llm", default="anthropic", choices=["anthropic", "openai", "deepseek"], help="LLM 提供商")
    parser.add_argument("--llm-model", help="LLM 模型名称（如 deepseek-chat）")
    
    args = parser.parse_args()
    
    server = create_server(
        headless=args.headless,
        debug_port=args.debug_port,
        llm_provider=args.llm,
        llm_model=args.llm_model
    )
    
    print(f"[MacroChromeMCP] 启动服务器...")
    print(f"  - 传输方式: {args.transport}")
    print(f"  - 无头模式: {args.headless}")
    print(f"  - 调试端口: {args.debug_port or '未启用'}")
    print(f"  - LLM 提供商: {args.llm}")
    
    asyncio.run(server.run(transport=args.transport))
