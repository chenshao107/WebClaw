
# 🦅 WebClaw - AI 驱动的浏览器自动化智能体

WebClaw 是一个**AI Agent**接管的浏览器自动化操作框架。用自然语言描述任务，AI 自动规划、编写代码、执行操作、自我修复。

---

## 🚀 快速开始

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

- **渐进式披露**：初始只显示极简描述，调用 `browser_help` 获取完整文档
- **灵活配置**：可开关任意工具（help / execute_python / agent_task / experience）
- **预封装函数**：`execute_python` 环境内置常用浏览器操作函数

### Cursor 配置

**方式一：图形界面配置**

1. 打开 Cursor Settings → Features → MCP
2. 点击 "Add New MCP Server"
3. 填写配置：
   - **Name**: `webclaw`
   - **Type**: `command`
   - **Command**: `D:\\你的路径\\WebClaw\\venv\\Scripts\\python.exe`（使用虚拟环境 Python）
   - **Args**: `D:\\你的路径\\WebClaw\\server\\mcp_server.py --transport stdio`

**方式二：手动编辑配置文件**

编辑 `%USERPROFILE%\.cursor\mcp.json`：

```json
{
  "mcpServers": {
    "webclaw": {
      "command": "D:\\Documents\\Project\\WebClaw\\venv\\Scripts\\python.exe",
      "args": [
        "D:\\Documents\\Project\\WebClaw\\server\\mcp_server.py",
        "--transport",
        "stdio"
      ],
      "env": {
        "PYTHONPATH": "D:\\Documents\\Project\\WebClaw"
      }
    }
  }
}
```

> **注意**：必须使用虚拟环境的 `python.exe`，否则找不到依赖包。

### 工具清单

| 工具 | 描述 | 可禁用 |
|------|------|--------|
| `browser_help` | 获取完整帮助信息和浏览器当前状态 | `--no-help` |
| `execute_python` | 执行 Python 代码操控浏览器 | `--no-python` |
| `agent_task` | 自然语言任务，由 Agent 自动执行 | `--no-agent` |
| `record_experience` | 记录操作经验到知识库 | `--no-experience` |

### 预封装函数（execute_python 环境可用）

```python
get_page_summary()           # 获取页面摘要（URL、标题、元素统计）
find_elements(selector, n)   # 查找元素并显示信息
click_element(selector, i)   # 点击第 i 个匹配元素
fill_form(selector, value)   # 填充表单
wait_and_capture(ms)         # 等待并捕获页面状态
extract_links(pattern)       # 提取链接（可正则过滤）
smart_scroll(dir, amount)    # 智能滚动（down/up/bottom/top）
list_prebuilt_funcs()        # 列出所有可用函数
```

### 使用流程

```
Planner (Cursor) 看到极简描述:
  - browser_help: "获取完整帮助信息和浏览器当前状态"
  - execute_python: "执行 Python 代码操控浏览器（调用 help 查看详情）"

  ↓ 调用 browser_help()
  
  返回完整信息:
    - 浏览器当前 URL、标题
    - 完整工具文档
    - 预封装函数列表
    
  ↓ 根据需求选择工具
  
  简单操作 → execute_python(code="get_page_summary()")
  复杂任务 → agent_task(task="去 GitHub 搜索...")
```

### 测试 MCP 连接

```bash
# 查看配置指南
python test_mcp.py --cursor-config

# 运行所有测试
python test_mcp.py --test-all

# 启动 MCP 服务器（独立测试）
python test_mcp.py --server --transport stdio
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
server/             # MCP 服务接口（可选）
core/               # Agent 核心逻辑
  ├── agent.py      # Executor Agent
  ├── interpreter.py # Code Interpreter
  └── llm_provider.py
tools/              # 工具集（可扩展）
scripts/            # Chrome 启动脚本
```

---
