
# 🦅 WebClaw - AI 驱动的浏览器自动化智能体

WebClaw 是一个**AI Agent**接管的浏览器自动化操作框架。用自然语言描述任务，AI 自动规划、编写代码、执行操作、自我修复。

---

## 🚀 快速开始

### 方式一：CLI 模式（独立运行）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 安装 Playwright 浏览器（仅需执行一次）
playwright install chromium

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 OPENAI_API_KEY

# 4. 启动浏览器
scripts\start_chrome.bat

# 5. 运行 WebClaw CLI
python webclaw_cli.py
```

### 方式二：MCP 模式（推荐，集成到 Cursor/Claude）

```bash
# 1. 安装（同上步骤 1-3）

# 2. 启动 MCP 服务器（SSE 模式）
start_mcp_server.bat
# 或: python server/mcp_server.py --transport sse

# 3. 配置 MCP 客户端
# 复制 mcp_config.json 的内容到你的 IDE MCP 配置
# Cursor: Settings → Features → MCP → Add New MCP Server
# Type: url, URL: http://127.0.0.1:8765/sse
```

---

## 🏗️ 架构：AI Agent 三层设计

WebClaw 将浏览器自动化抽象为**智能体协作**问题，而非简单的脚本执行：

### 1. 🤖 Executor Agent (核心智能体)

**这是 WebClaw 的灵魂。**

* **自主规划：** 接收自然语言任务，自主拆解为可执行步骤
* **代码生成：** 实时编写 Playwright 脚本，无需人工编写选择器
* **自我修复：** 遇到报错（元素未找到、弹窗拦截）自动分析并重新生成代码
* **信息提炼：** 只返回关键结果，过滤网页噪音

### 2. 🧠 LLM 神经中枢

* **模型兼容：** 支持 OpenAI、DeepSeek、Gemini 等任意 OpenAI 兼容接口
* **上下文优化：** 通过分层架构，**Token 消耗降低 90% 以上**

### 3. 🎮 Playwright 物理层

* **工业级稳定：** 自动等待、无障碍树解析、网络拦截
* **多标签页：** 跨页面、跨会话的复杂工作流

---

## 🔄 工作流示例

```
用户: "新开一个标签页，去github看看当 下最火的AI项目都有哪"

WebClaw Agent:
  ↓ 分析任务意图
  ↓ 生成 Playwright 代码（导航→搜索→提取）
  ↓ 执行
  ↓ 返回
```

---

## 🔌 MCP 支持（可选）

WebClaw 提供 **渐进式 MCP 工具集**，可集成到 Cursor、Claude Desktop 等支持 MCP 的客户端。

### 特性

- **SSE 服务器模式**：支持状态持久化，多次调用共享浏览器会话
- **渐进式披露**：初始只显示极简描述，调用 `browser_help` 获取完整文档
- **灵活配置**：可开关任意工具（help / execute_python / agent_task / experience）
- **预封装函数**：`execute_python` 环境内置常用浏览器操作函数

### 快速配置

**1. 启动 MCP 服务器**

```bash
# 方式一：使用脚本启动（推荐）
python server/mcp_server.py --transport sse --port 8765

# 方式二：后台运行（Linux/Mac）
nohup python server/mcp_server.py --transport sse --port 8765 > mcp.log 2>&1 &
```

**2. 配置 MCP 客户端**

编辑 `mcp_config.json`（项目根目录）：

```json
{
  "mcpServers": {
    "webclaw": {
      "url": "http://127.0.0.1:8765/sse"
    }
  }
}
```

或在 Cursor 中配置：
- 打开 Cursor Settings → Features → MCP
- 点击 "Add New MCP Server"
- **Name**: `webclaw`
- **Type**: `url`
- **URL**: `http://127.0.0.1:8765/sse`

### 工具清单

| 工具 | 描述 | 可禁用 |
|------|------|--------|
| `browser_help` | 获取完整帮助信息和浏览器当前状态 | `--no-help` |
| `execute_python` | 执行 Python 代码操控浏览器 | `--no-python` |
| `agent_task` | 自然语言任务，由 Agent 自动执行 | `--no-agent` |
| `record_experience` | 记录操作经验到知识库 | `--no-experience` |

### 预封装函数（execute_python 环境可用）

```python
# 页面操作
get_page_summary()           # 获取页面摘要（URL、标题、元素统计）
find_elements(selector, n)   # 查找元素并显示信息
click_element(selector, i)   # 点击第 i 个匹配元素
fill_form(selector, value)   # 填充表单
wait_and_capture(ms)         # 等待并捕获页面状态
extract_links(pattern)       # 提取链接（可正则过滤）
smart_scroll(dir, amount)    # 智能滚动（down/up/bottom/top）

# 标签页管理
new_tab(url)                 # 新开标签页
switch_tab(index)            # 切换到指定标签页
list_tabs()                  # 列出所有标签页
close_tab(index)             # 关闭标签页

# 其他
list_prebuilt_funcs()        # 列出所有可用函数
```

### 使用流程

```
1. 启动 MCP 服务器（SSE 模式）
   python server/mcp_server.py --transport sse

2. 配置 MCP 客户端指向 SSE URL
   http://127.0.0.1:8765/sse

3. 开始使用
   - 调用 browser_help() 获取完整信息
   - 使用 execute_python(code="get_page_summary()") 执行操作
   - 多次调用间共享浏览器状态
```

### 服务器参数

```bash
python server/mcp_server.py [选项]

选项:
  --transport {stdio,sse}  传输方式（默认: stdio）
  --host HOST              SSE 模式主机地址（默认: 127.0.0.1）
  --port PORT              SSE 模式端口（默认: 8765）
  --headless               无头模式（不显示浏览器窗口）
  --debug-port PORT        连接现有 Chrome 调试端口
  --no-help                禁用 browser_help 工具
  --no-python              禁用 execute_python 工具
  --no-agent               禁用 agent_task 工具
  --no-experience          禁用经验管理工具
```

### 环境变量配置

在 `.env` 文件中配置：

```bash
# MCP 工具开关
MCP_ENABLE_HELP=true
MCP_ENABLE_PYTHON=true
MCP_ENABLE_AGENT=true
MCP_ENABLE_EXPERIENCE=true

# 浏览器配置
BROWSER_HEADLESS=false
BROWSER_DEBUG_PORT=9222
```

---

## 🛠️ vs 传统方案

| 特性 | 传统 Chrome MCP | **WebClaw** |
| --- | --- | --- |
| **核心定位** | 远程控制浏览器 | **AI Agent 自主决策** |
| **交互频率** | 极高（每步都需 Planner 决策） | **极低（一次任务一次交互）** |
| **容错能力** | 差（容易被网页变化打断） | **极强（Agent 自愈循环）** |
| **使用方式** | 写代码/配选择器 | **自然语言即可** |
| **Token 成本** | 随页面复杂度爆炸 | **常数级（只传摘要）** |

---

## 📁 项目结构

```
webclaw_cli.py      # 🎯 主入口：AI Agent CLI 交互
server/
  └── mcp_server.py # MCP 服务接口（SSE 模式）
core/               # Agent 核心逻辑
  ├── agent.py      # Executor Agent
  ├── interpreter.py # Code Interpreter
  └── llm_provider.py
tools/              # 工具集（可扩展）
scripts/            # Chrome 启动脚本
mcp_config.json     # MCP 客户端配置示例（SSE 模式）
.env.example        # 环境变量配置模板
```

---
