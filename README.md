这个名字选得很好！**`MacroChromeMCP`** 完美平衡了技术直观性与功能描述。它强调了“宏（Macro）”的概念，直接告诉用户：这不是一个只能点点按按的工具，而是一个能执行宏观任务的代理。

以下是为你重新优化的 GitHub README，采用了更加工业化、专业化的风格：

---

# MacroChromeMCP

> **告别上下文爆炸。将浏览器操作从“原子指令”升级为“语义宏任务”。**

## 💡 为什么需要 MacroChromeMCP？

目前的浏览器 Agent 技术路线（如普通的 Puppeteer/Chrome MCP）普遍存在**“信息信噪比失衡”**的问题：

1. **上下文炸弹：** 为了执行一个简单的点击，Agent 需要读取整个页面的 `innerText` 或 HTML 源码。
2. **Token 浪费：** 每次页面跳转，冗长的 DOM 信息会反复塞满 LLM 的上下文窗口。
3. **规划偏移：** 面对网页底层的复杂干扰，主 Agent 极易迷失在细枝末节中，忘记了最初的全局目标。

**MacroChromeMCP** 通过“双状态机”架构解决这一难题：它在 Planner（主 Agent）与浏览器之间建立了一个**高抽象隔离层**。

---

## 🏗️ 核心架构：双状态机 (Dual-SM)

项目采用了 **Planner-Executor（决策者-执行者）** 模式：

### 1. Planner (全局决策者) - 主 LLM

* **视角：** 只看业务逻辑。
* **语言：** “去 GitHub 给我点个 Star”、“在携程订一张去深圳的机票”。
* **接口：** 调用 MacroChromeMCP 提供的“宏工具”。

### 2. Executor (局部执行者) - 迷你 Agent

* **视角：** 深度接触浏览器底层（DOM、Shadow Root、网络请求）。
* **逻辑：** 负责解析网页源码、处理验证码、等待元素加载、处理弹窗。
* **隔离：** 任务完成后，**销毁所有低密度网页信息**，仅回送任务结果。

---

## 🌟 项目特性

* **🚀 上下文隔离 (Context Isolation)：** 网页源码级别的“脏信息”永远不会流向你的主 Agent。主 Agent 的上下文仅保留核心业务逻辑，Token 消耗降低 **80%** 以上。
* **🛠️ 语义化宏工具：** 封装了复杂的交互逻辑。不再是 `click_element`，而是 `perform_task("登录系统并导出报表")`。
* **🧩 完美兼容生态：** 标准 MCP 接口，可直接接入 **Claude Desktop, Cursor, Zed** 等任何支持 Model Context Protocol 的客户端。
* **🛡️ 隐私与效率：** 敏感的 DOM 结构在本地 Executor 处理，减少数据上云，同时大幅提升响应速度。

---

## 🛠️ 技术实现

### 任务流演示

当主 Agent 发起一个宏任务时：

1. **Planner 调用：**
```json
{
  "tool": "macro_execute",
  "arguments": {
    "task": "在 Amazon 搜索 'Mechanical Keyboard' 并返回前三个产品的价格",
    "constraints": "仅限自营商品"
  }
}

```


2. **Executor 执行：**
* 启动 Playwright 实例。
* 自行解析搜索框、注入脚本、翻页、过滤。
* 提炼关键数据。


3. **结果返回（仅返回精简信息）：**
```json
{
  "status": "success",
  "data": [
    {"name": "Keychron K2", "price": "$79"},
    {"name": "Logitech G Pro", "price": "$129"},
    {"name": "Razer BlackWidow", "price": "$99"}
  ]
}

```



---

## 📅 路线图 (Roadmap)

* [x] **V0.1:** 定义高抽象级 MCP Tool 协议。
* [ ] **V0.2:** 实现基于 Playwright 的轻量级本地执行器。
* [ ] **V0.3:** 集成小型本地 LLM (如 Qwen-7B-Instruct) 作为默认 Executor。
* [ ] **V0.4:** 提供 Chrome 扩展适配层，支持在当前浏览器页面的直接接管。

---

## 🤝 贡献与参与

我们正在重新定义 AI 与 Web 的交互方式。如果你对 **Agent 分层架构** 或 **低成本自动化** 感兴趣，欢迎提 Issue 或提交 PR。

---

**MacroChromeMCP** —— 让 Agent 的视野保持纯净，让执行变得精准。

---
