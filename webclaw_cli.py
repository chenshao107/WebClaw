import os
from dotenv import load_dotenv

from core.interpreter import CodeInterpreter
from core.llm_provider import LLMProvider
from core.agent import ExecutorAgent
from tools.python_executor import PythonExecutorTool

def main():
    # 1. 加载环境变量 (.env 文件里放 OPENAI_API_KEY 和 OPENAI_BASE_URL)
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("LLM_MODEL", "gpt-4o") # 也可以配 deepseek-chat 等

    if not api_key:
        print("错误：请在 .env 文件中设置 OPENAI_API_KEY")
        return

    print("🔌 正在连接/启动本地浏览器 (Playwright)...")
    interpreter = CodeInterpreter()  # 修改这里
    # 默认连接到 start_chrome.bat 启动的 Chrome (端口 9222)
    init_result = interpreter.initialize(debug_port=9222)
    if not init_result.success:
        print(f"错误：浏览器初始化失败 - {init_result.stderr}")
        return
    print("✅ 浏览器初始化成功！")
        
    # 2. 组装你的"瑞士军刀"
    tools = [
        PythonExecutorTool(interpreter=interpreter),
        # 以后你可以新建文件，如 tools/element_highlighter.py，直接在这里 append 进去即可
    ]

    # 3. 初始化神经中枢
    llm = LLMProvider(api_key=api_key, base_url=base_url, model=model)
    agent = ExecutorAgent(llm=llm, tools=tools)

    print("\n╔══════════════════════════════════════════════════════════════╗")
    print("║             🚀 WebClaw AI Agent 引擎已启动                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    try:
        while True:
            user_task = input("\n📝 请输入自然语言任务 (输入 'q' 退出): \n> ").strip()
            if user_task.lower() in ['q', 'quit', 'exit']:
                break
            if not user_task:
                continue
            
            # 将任务丢给 Agent 引擎
            agent.run_task(user_task)

    except KeyboardInterrupt:
        print("\n检测到中断，正在退出...")
    finally:
        interpreter.close()
        print("🛑 浏览器已断开，资源释放完毕。")

if __name__ == "__main__":
    main()
