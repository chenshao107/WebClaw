"""
MCP 测试脚本 - 测试渐进式 MCP 工具集

使用方式:
1. 直接运行测试: python test_mcp.py
2. 作为 MCP 服务器运行: python test_mcp.py --server
3. 测试特定工具: python test_mcp.py --test-tool browser_help
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from tools.mcp_tools import MCPToolSet, MCPToolConfig, HelpTool, ExecutePythonTool, AgentTaskTool
from core.experience_store import get_experience_store


def test_tool_config():
    """测试工具配置"""
    print("=" * 60)
    print("测试 1: 工具配置")
    print("=" * 60)
    
    # 默认配置（全部启用）
    config1 = MCPToolConfig()
    print(f"默认配置: {config1.get_enabled_tools()}")
    
    # 禁用 agent_task
    config2 = MCPToolConfig(enable_agent_task=False)
    print(f"禁用 agent: {config2.get_enabled_tools()}")
    
    # 只启用 help
    config3 = MCPToolConfig(
        enable_help=True,
        enable_execute_python=False,
        enable_agent_task=False
    )
    print(f"仅 help: {config3.get_enabled_tools()}")
    
    print("✓ 工具配置测试通过\n")


def test_help_tool():
    """测试 help 工具"""
    print("=" * 60)
    print("测试 2: Help 工具")
    print("=" * 60)
    
    config = MCPToolConfig()
    
    # 模拟浏览器状态获取函数
    def mock_get_state():
        return {
            "url": "https://example.com",
            "title": "测试页面",
            "ready": True
        }
    
    help_tool = HelpTool(config, mock_get_state)
    
    print(f"工具名称: {help_tool.name}")
    print(f"工具描述: {help_tool.description}")
    print("\n执行结果:")
    result = help_tool.execute()
    print(result[:800] + "..." if len(result) > 800 else result)
    
    print("\n✓ Help 工具测试通过\n")


def test_experience_store():
    """测试经验存储"""
    print("=" * 60)
    print("测试 3: 经验存储系统")
    print("=" * 60)
    
    store = get_experience_store()
    
    # 添加测试经验
    exp_id = store.add_experience(
        topic="测试经验",
        content="这是一个测试经验的内容",
        tags=["test", "demo"],
        domains=["example.com"]
    )
    print(f"添加经验 ID: {exp_id}")
    
    # 检索经验
    results = store.retrieve("测试", limit=3)
    print(f"检索结果: {len(results)} 条")
    for exp in results:
        print(f"  - [{exp.id}] {exp.topic}")
    
    # 获取统计
    stats = store.get_stats()
    print(f"统计: {stats}")
    
    print("\n✓ 经验存储测试通过\n")


def test_minimal_descriptions():
    """测试最小化描述（渐进式披露）"""
    print("=" * 60)
    print("测试 4: 渐进式披露 - 最小化描述")
    print("=" * 60)
    
    config = MCPToolConfig()
    toolset = MCPToolSet(config)
    
    minimal = toolset.get_minimal_descriptions()
    print("初始暴露给 Planner 的极简描述:")
    for tool in minimal:
        print(f"  - {tool['name']}: {tool['description']}")
    
    print("\n✓ 渐进式披露测试通过\n")


async def test_mcp_server():
    """测试 MCP 服务器启动"""
    print("=" * 60)
    print("测试 5: MCP 服务器")
    print("=" * 60)
    
    try:
        from server.mcp_server import create_server, MCPServer
        
        # 创建服务器（不启动，仅测试配置）
        server = create_server(
            enable_help=True,
            enable_execute_python=True,
            enable_agent_task=False,  # 测试时禁用 agent
            enable_experience_tools=True
        )
        
        print(f"服务器名称: {server.name}")
        print(f"工具配置: {server.tool_config.get_enabled_tools()}")
        
        # 获取工具定义
        tools = server.get_tools()
        print(f"\n注册的工具:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description[:50]}...")
        
        print("\n✓ MCP 服务器测试通过")
        print("  要启动服务器运行: python -m server.mcp_server --transport stdio")
        
    except Exception as e:
        print(f"✗ MCP 服务器测试失败: {e}")
        import traceback
        traceback.print_exc()


def print_cursor_config():
    """打印 Cursor 配置指南"""
    print("=" * 60)
    print("Cursor MCP 配置指南")
    print("=" * 60)
    
    project_path = Path(__file__).parent.resolve()
    venv_python = project_path / "venv" / "Scripts" / "python.exe"
    
    # 检测虚拟环境
    if venv_python.exists():
        python_cmd = str(venv_python)
        print(f"\n✓ 检测到虚拟环境: {venv_python}")
    else:
        python_cmd = "python"
        print(f"\n⚠ 未检测到虚拟环境，使用系统 python")
    
    sse_config = {
        "mcpServers": {
            "webclaw": {
                "url": "http://127.0.0.1:8765/sse"
            }
        }
    }
    
    print("\n" + "=" * 60)
    print("WebClaw MCP SSE 模式配置")
    print("=" * 60)
    
    print("\n【步骤 1】启动 MCP 服务器:")
    print(f"   cd {project_path}")
    print(f"   python server/mcp_server.py --transport sse --port 8765")
    
    print("\n【步骤 2】配置 Cursor:")
    print("   1. 打开 Cursor Settings → Features → MCP")
    print("   2. 点击 'Add New MCP Server'")
    print("   3. 填写配置:")
    print(f"      - Name: webclaw")
    print(f"      - Type: url")
    print(f"      - URL: http://127.0.0.1:8765/sse")
    
    print("\n   或者手动编辑 ~/.cursor/mcp.json:")
    print(json.dumps(sse_config, indent=2, ensure_ascii=False))
    
    print("\n【可选配置】")
    print("   --host 127.0.0.1 : 绑定主机地址")
    print("   --port 8765      : 绑定端口")
    print("   --headless       : 无头模式")
    print("   --debug-port 9222: 连接现有 Chrome")
    print("   --no-help        : 禁用 browser_help")
    print("   --no-python      : 禁用 execute_python")
    print("   --no-agent       : 禁用 agent_task")
    print("   --no-experience  : 禁用经验管理")


def main():
    parser = argparse.ArgumentParser(description="MCP 测试工具")
    parser.add_argument("--test-all", action="store_true", help="运行所有测试")
    parser.add_argument("--test-tool", choices=["config", "help", "experience", "minimal", "server"],
                       help="测试特定组件")
    parser.add_argument("--server", action="store_true", help="启动 MCP 服务器")
    parser.add_argument("--cursor-config", action="store_true", help="显示 Cursor 配置")
    
    # 服务器参数
    parser.add_argument("--transport", default="stdio", choices=["stdio", "sse"])
    parser.add_argument("--no-help", action="store_true")
    parser.add_argument("--no-python", action="store_true")
    parser.add_argument("--no-agent", action="store_true")
    parser.add_argument("--no-experience", action="store_true")
    
    args = parser.parse_args()
    
    # 显示 Cursor 配置
    if args.cursor_config:
        print_cursor_config()
        return
    
    # 启动服务器
    if args.server:
        from server.mcp_server import create_server
        
        server = create_server(
            enable_help=not args.no_help,
            enable_execute_python=not args.no_python,
            enable_agent_task=not args.no_agent,
            enable_experience_tools=not args.no_experience
        )
        
        print(f"[WebClaw] 启动 MCP 服务器...")
        print(f"  - 传输方式: {args.transport}")
        print(f"  - 工具: help={not args.no_help}, python={not args.no_python}, agent={not args.no_agent}")
        
        asyncio.run(server.run(transport=args.transport))
        return
    
    # 运行测试
    if args.test_all or args.test_tool is None:
        print("\n" + "=" * 60)
        print("WebClaw 渐进式 MCP 工具集测试")
        print("=" * 60 + "\n")
        
        test_tool_config()
        test_help_tool()
        test_experience_store()
        test_minimal_descriptions()
        
        # 异步测试
        asyncio.run(test_mcp_server())
        
        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)
        print("\n要查看 Cursor 配置，运行: python test_mcp.py --cursor-config")
        print("要启动 MCP 服务器，运行: python test_mcp.py --server")
        
    elif args.test_tool == "config":
        test_tool_config()
    elif args.test_tool == "help":
        test_help_tool()
    elif args.test_tool == "experience":
        test_experience_store()
    elif args.test_tool == "minimal":
        test_minimal_descriptions()
    elif args.test_tool == "server":
        asyncio.run(test_mcp_server())


if __name__ == "__main__":
    main()
