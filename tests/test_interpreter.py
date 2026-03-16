"""
测试解释器是否能正常保持状态
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interpreter import CodeInterpreter, ExecutionResult


class TestCodeInterpreter:
    """测试代码解释器"""
    
    def test_basic_execution(self):
        """测试基本代码执行"""
        interpreter = CodeInterpreter()
        
        result = interpreter.execute("""
x = 1 + 1
print(f"结果是: {x}")
""")
        
        assert result.success is True
        assert "结果是: 2" in result.stdout
        assert result.error is None
    
    def test_state_persistence(self):
        """测试状态持久化"""
        interpreter = CodeInterpreter()
        
        # 第一次执行，设置变量
        result1 = interpreter.execute("x = 100")
        assert result1.success is True
        
        # 第二次执行，访问之前设置的变量
        result2 = interpreter.execute("print(x)")
        assert result2.success is True
        assert "100" in result2.stdout
    
    def test_error_handling(self):
        """测试错误处理"""
        interpreter = CodeInterpreter()
        
        result = interpreter.execute("1/0")
        
        assert result.success is False
        assert result.error is not None
        assert "ZeroDivisionError" in result.error
    
    def test_stdout_capture(self):
        """测试 stdout 捕获"""
        interpreter = CodeInterpreter()
        
        result = interpreter.execute("""
print("第一行")
print("第二行")
""")
        
        assert result.success is True
        assert "第一行" in result.stdout
        assert "第二行" in result.stdout
    
    def test_multiple_executions(self):
        """测试多次执行"""
        interpreter = CodeInterpreter()
        
        # 多次执行，验证状态累积
        interpreter.execute("counter = 0")
        interpreter.execute("counter += 1")
        interpreter.execute("counter += 1")
        result = interpreter.execute("print(counter)")
        
        assert result.success is True
        assert "2" in result.stdout


class TestExecutionResult:
    """测试执行结果类"""
    
    def test_result_creation(self):
        """测试结果对象创建"""
        result = ExecutionResult(
            success=True,
            stdout="test output",
            stderr="",
            output="test",
            execution_time=1.5
        )
        
        assert result.success is True
        assert result.stdout == "test output"
        assert result.execution_time == 1.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
