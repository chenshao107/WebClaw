"""
MCP 服务入口：渐进式披露的 MCP 工具集

核心职责：
1. 实现 MCP 协议接口
2. 提供渐进式工具披露（初始最小化，help 返回完整信息）
3. 支持工具灵活配置（可开关特定工具）
"""

import json
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

# MCP 协议相关导入
try:
    # 尝试使用 FastMCP（更简单的 API）
    from mcp.server.fastmcp import FastMCP
    MCP_AVAILABLE = True
    USE_FASTMCP = True
except ImportError:
    try:
        # 回退到标准 Server
        from mcp.server import Server
        from mcp.types import Tool, TextContent
        MCP_AVAILABLE = True
        USE_FASTMCP = False
    except ImportError:
        MCP_AVAILABLE = False
        USE_FASTMCP = False
        print("[警告] MCP 库未安装，MCP 服务不可用")

from core.agent import ExecutorAgent
from core.llm_provider import LLMProvider
from core.interpreter import ExecutionResult
from tools.experience_tools import EXPERIENCE_TOOLS
from tools.mcp_tools import MCPToolSet, MCPToolConfig


@dataclass
class MCPToolDefinition:
    """MCP Tool 定义"""
    name: str
    description: str
    parameters: Dict[str, Any]


class MCPServer:
    """
    MCP 服务类 - 渐进式披露设计
    
    初始只暴露最小化工具描述，
    调用 browser_help 后返回完整工具文档和浏览器状态。
    """
    
    def __init__(
        self,
        agent: Optional[ExecutorAgent] = None,
        name: str = "webclaw-mcp-server",
        tool_config: Optional[MCPToolConfig] = None,
        llm_provider: Optional[LLMProvider] = None
    ):
        """
        初始化 MCP 服务
        
        Args:
            agent: ExecutorAgent 实例（可选，延迟创建）
            name: 服务名称
            tool_config: 工具配置（控制启用哪些工具）
            llm_provider: LLM 提供商（用于创建 Agent）
        """
        self.agent = agent
        self.name = name
        self.server = None
        self.tool_config = tool_config or MCPToolConfig()
        self.llm_provider = llm_provider
        self._agent_factory = None
        self._interpreter = None
        self._registered_tools = []  # 保存工具引用
        
        if MCP_AVAILABLE:
            if USE_FASTMCP:
                self.server = FastMCP(name)
            else:
                self.server = Server(name)
            self._register_tools()
    
    def _ensure_components(self):
        """确保 interpreter 和 agent 已创建"""
        if self._interpreter is None:
            from core.interpreter import PlaywrightInterpreter
            self._interpreter = PlaywrightInterpreter()
            self._interpreter.start()
        
        if self.agent is None and self.tool_config.enable_agent_task:
            # 延迟创建 Agent
            llm = self.llm_provider or LLMProvider()
            from tools.python_executor import PythonExecutorTool
            tools = [PythonExecutorTool(self._interpreter)]
            self.agent = ExecutorAgent(llm=llm, tools=tools)
    
    def _get_browser_state(self) -> Dict:
        """获取浏览器当前状态"""
        try:
            self._ensure_components()
            if self._interpreter and self._interpreter.page:
                return {
                    "url": self._interpreter.page.url,
                    "title": self._interpreter.page.title(),
                    "ready": True
                }
        except Exception as e:
            return {"error": str(e), "ready": False}
        return {"ready": False, "message": "浏览器未连接"}
    
    def _register_tools(self):
        """注册渐进式 MCP Tools"""
        if not self.server:
            return
        
        # 使用新的工具集工厂
        toolset = MCPToolSet(self.tool_config)
        
        # 创建工具实例
        def agent_factory():
            self._ensure_components()
            return self.agent
        
        tools = toolset.create_tools(
            interpreter=self._interpreter,
            agent_factory=agent_factory,
            get_browser_state=self._get_browser_state
        )
        
        # 注册到 MCP server
        for tool in tools:
            self._register_tool(tool)
        
        # 同时注册经验管理工具（如果启用）
        for tool in EXPERIENCE_TOOLS:
            self._register_tool(tool)
    
    def _register_tool(self, tool):
        """注册单个工具到 MCP server"""
        self._registered_tools.append(tool)
        
        if USE_FASTMCP:
            # FastMCP 使用装饰器方式
            import functools
            
            @self.server.tool(name=tool.name)
            @functools.wraps(tool.execute)
            async def wrapper(**kwargs):
                if tool.name in ["execute_python", "agent_task", "browser_help"]:
                    self._ensure_components()
                return tool.execute(**kwargs)
            
            wrapper.__doc__ = tool.description
        else:
            # 标准 Server 需要手动注册 handler
            # 保存工具供后续手动处理
            pass
    
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
        
        # 确保组件已初始化
        self._ensure_components()
        
        try:
            if USE_FASTMCP:
                # FastMCP 使用 run 方法
                await self.server.run(transport=transport)
            else:
                # 标准 Server
                if transport == "stdio":
                    await self.server.run_stdio_async()
                elif transport == "sse":
                    await self.server.run_sse_async()
                else:
                    raise ValueError(f"不支持的传输方式: {transport}")
        finally:
            if self._interpreter:
                self._interpreter.stop()
    
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
            ),
            # 经验管理工具
            MCPToolDefinition(
                name="record_experience",
                description="记录一条新的操作经验到知识库中，供未来类似任务参考",
                parameters={
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "经验主题，如 'GitHub 登录流程'"
                        },
                        "content": {
                            "type": "string",
                            "description": "经验具体内容"
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "关键词标签"
                        },
                        "domains": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "适用网站域名"
                        }
                    },
                    "required": ["topic", "content"]
                }
            ),
            MCPToolDefinition(
                name="mark_experience_outdated",
                description="将一条经验标记为过时或失效",
                parameters={
                    "type": "object",
                    "properties": {
                        "exp_id": {
                            "type": "integer",
                            "description": "经验 ID"
                        },
                        "reason": {
                            "type": "string",
                            "description": "过时原因"
                        }
                    },
                    "required": ["exp_id", "reason"]
                }
            ),
            MCPToolDefinition(
                name="search_experiences",
                description="搜索知识库中的历史经验",
                parameters={
                    "type": "object",
                    "properties": {
                        "keywords": {
                            "type": "string",
                            "description": "搜索关键词"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "返回条数限制",
                            "default": 5
                        }
                    },
                    "required": ["keywords"]
                }
            ),
            MCPToolDefinition(
                name="get_experience_stats",
                description="获取经验知识库的统计信息",
                parameters={
                    "type": "object",
                    "properties": {}
                }
            )
        ]


def create_server(
    headless: bool = False,
    debug_port: Optional[int] = None,
    llm_provider: str = "anthropic",
    llm_model: Optional[str] = None,
    # 工具配置参数
    enable_help: bool = True,
    enable_execute_python: bool = True,
    enable_agent_task: bool = True,
    enable_experience_tools: bool = True
) -> MCPServer:
    """
    创建 MCP 服务器实例（渐进式披露 + 可配置工具）
    
    Args:
        headless: 是否无头模式
        debug_port: Chrome 调试端口
        llm_provider: LLM 提供商
        llm_model: LLM 模型名称
        enable_help: 是否启用 browser_help 工具
        enable_execute_python: 是否启用 execute_python 工具
        enable_agent_task: 是否启用 agent_task 工具
        enable_experience_tools: 是否启用经验管理工具
        
    Returns:
        MCPServer 实例
    """
    # 创建工具配置
    tool_config = MCPToolConfig(
        enable_help=enable_help,
        enable_execute_python=enable_execute_python,
        enable_agent_task=enable_agent_task
    )
    
    # 如果不启用经验工具，清空经验工具列表
    if not enable_experience_tools:
        global EXPERIENCE_TOOLS
        EXPERIENCE_TOOLS = []
    
    # 延迟创建 Agent，传入配置
    return MCPServer(
        agent=None,  # 延迟创建
        tool_config=tool_config,
        llm_provider=None  # 内部会根据需要创建
    )


def _get_env_bool(key: str, default: bool = True) -> bool:
    """从环境变量读取布尔值"""
    import os
    value = os.getenv(key, str(default).lower())
    return value.lower() in ('true', '1', 'yes', 'on')


# 命令行入口
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="WebClaw MCP 服务器 - 渐进式披露设计")
    parser.add_argument("--headless", action="store_true", help="无头模式")
    parser.add_argument("--debug-port", type=int, help="Chrome 调试端口")
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"], help="传输方式")
    parser.add_argument("--llm", default="anthropic", choices=["anthropic", "openai", "deepseek"], help="LLM 提供商")
    parser.add_argument("--llm-model", help="LLM 模型名称（如 deepseek-chat）")
    
    # 工具开关参数（命令行参数优先级高于环境变量）
    parser.add_argument("--no-help", action="store_true", help="禁用 browser_help 工具")
    parser.add_argument("--no-python", action="store_true", help="禁用 execute_python 工具")
    parser.add_argument("--no-agent", action="store_true", help="禁用 agent_task 工具")
    parser.add_argument("--no-experience", action="store_true", help="禁用经验管理工具")
    
    args = parser.parse_args()
    
    # 从环境变量读取配置（命令行参数可覆盖）
    enable_help = not args.no_help and _get_env_bool("MCP_ENABLE_HELP", True)
    enable_python = not args.no_python and _get_env_bool("MCP_ENABLE_PYTHON", True)
    enable_agent = not args.no_agent and _get_env_bool("MCP_ENABLE_AGENT", True)
    enable_experience = not args.no_experience and _get_env_bool("MCP_ENABLE_EXPERIENCE", True)
    
    server = create_server(
        headless=args.headless,
        debug_port=args.debug_port,
        llm_provider=args.llm,
        llm_model=args.llm_model,
        enable_help=enable_help,
        enable_execute_python=enable_python,
        enable_agent_task=enable_agent,
        enable_experience_tools=enable_experience
    )
    
    print(f"[WebClaw] 启动服务器...")
    print(f"  - 传输方式: {args.transport}")
    print(f"  - 无头模式: {args.headless}")
    print(f"  - 调试端口: {args.debug_port or '未启用'}")
    print(f"  - LLM 提供商: {args.llm}")
    print(f"  - 工具配置: help={enable_help}, python={enable_python}, agent={enable_agent}, exp={enable_experience}")
    
    asyncio.run(server.run(transport=args.transport))
