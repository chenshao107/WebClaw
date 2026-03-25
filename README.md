
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

WebClaw 同时提供 **MCP (Model Context Protocol)** 服务接口，方便集成到 Cursor、Claude Desktop 等支持 MCP 的客户端：

```json
{
  "mcpServers": {
    "webclaw": {
      "command": "python",
      "args": ["-m", "server.mcp_server"]
    }
  }
}
```

> **注意：** MCP 是连接层，核心能力始终是 Executor Agent。

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
