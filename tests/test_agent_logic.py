"""
测试 Agent 的思考链路
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import ExecutorAgent, TaskResult
from core.prompts import format_task_prompt, format_repair_prompt


class TestPromptFormatting:
    """测试提示词格式化"""
    
    def test_format_task_prompt(self):
        """测试任务提示词格式化"""
        task = "搜索 Python 教程"
        page_state = {"url": "https://www.baidu.com", "title": "百度一下"}
        history = ["步骤1: 初始化浏览器"]
        
        prompt = format_task_prompt(task, page_state, history)
        
        assert "搜索 Python 教程" in prompt
        assert "https://www.baidu.com" in prompt
        assert "百度一下" in prompt
        assert "步骤1" in prompt
    
    def test_format_repair_prompt(self):
        """测试修复提示词格式化"""
        task = "点击搜索按钮"
        code = "page.click('#search-btn')"
        error = "TimeoutError: element not found"
        page_state = {"url": "https://example.com", "title": "Example"}
        
        prompt = format_repair_prompt(task, code, error, page_state)
        
        assert "点击搜索按钮" in prompt
        assert "page.click" in prompt
        assert "TimeoutError" in prompt
        assert "example.com" in prompt


class TestExecutorAgent:
    """测试执行 Agent"""
    
    def test_agent_initialization(self):
        """测试 Agent 初始化"""
        agent = ExecutorAgent(headless=True)
        
        assert agent.headless is True
        assert agent.max_retries == 3
        assert agent.interpreter is not None
    
    def test_code_extraction(self):
        """测试代码提取"""
        agent = ExecutorAgent()
        
        # 测试 markdown 代码块
        text1 = """
这是一些说明
```python
print("hello")
x = 1 + 1
```
更多说明
"""
        code1 = agent._extract_code(text1)
        assert 'print("hello")' in code1
        assert "x = 1 + 1" in code1
        
        # 测试普通代码块
        text2 = """
```
console.log("test")
```
"""
        code2 = agent._extract_code(text2)
        assert 'console.log("test")' in code2
    
    def test_result_parsing(self):
        """测试结果解析"""
        agent = ExecutorAgent()
        
        # 测试 JSON 输出
        stdout = """
一些日志
{"status": "success", "data": {"key": "value"}}
"""
        result = agent._parse_result(stdout)
        assert result["status"] == "success"
        assert result["data"]["key"] == "value"
        
        # 测试非 JSON 输出
        stdout2 = "普通输出"
        result2 = agent._parse_result(stdout2)
        assert result2["raw_output"] == "普通输出"


class TestTaskResult:
    """测试任务结果"""
    
    def test_task_result_creation(self):
        """测试任务结果创建"""
        result = TaskResult(
            success=True,
            task="测试任务",
            steps=[{"attempt": 1, "code": "print(1)"}],
            final_data={"key": "value"},
            total_time=2.5
        )
        
        assert result.success is True
        assert result.task == "测试任务"
        assert len(result.steps) == 1
        assert result.final_data["key"] == "value"
        assert result.total_time == 2.5


class TestLocalCodeGeneration:
    """测试本地代码生成（模拟 LLM）"""
    
    def test_search_code_generation(self):
        """测试搜索代码生成"""
        agent = ExecutorAgent()
        
        code = agent._generate_search_code("搜索测试")
        
        assert "goto" in code
        assert "fill" in code
        assert "click" in code
    
    def test_screenshot_code_generation(self):
        """测试截图代码生成"""
        agent = ExecutorAgent()
        
        code = agent._generate_screenshot_code("截图")
        
        assert "screenshot" in code
        assert "path=" in code
    
    def test_click_code_generation(self):
        """测试点击代码生成"""
        agent = ExecutorAgent()
        
        code = agent._generate_click_code("点击按钮")
        
        assert "click" in code
        assert "locator" in code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
