"""
MCP 服务分发层

将 Agent 封装为 MCP Tool 的入口
"""

from .mcp_server import MCPServer, create_server

__all__ = ["MCPServer", "create_server"]
