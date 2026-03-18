import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class TaskLogger:
    """任务级 LLM 调用日志记录器
    
    每个任务拥有独立的日志文件夹，记录该任务中的所有 LLM 调用：
    - 请求内容 (messages, tools)
    - 响应内容
    - 时间戳
    - Token 使用情况
    """
    
    def __init__(self, task_id: str, logs_dir: str = "logs"):
        """
        Args:
            task_id: 任务唯一标识
            logs_dir: 日志根目录，默认为项目根目录下的 logs 文件夹
        """
        self.task_id = task_id
        self.start_time = datetime.now()
        
        # 创建任务专属日志目录: logs/YYYYMMDD_HHMMSS_task_id/
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        self.task_dir = Path(logs_dir) / f"{timestamp}_{task_id}"
        self.task_dir.mkdir(parents=True, exist_ok=True)
        
        # 日志文件路径
        self.log_file = self.task_dir / "llm_calls.jsonl"
        self.summary_file = self.task_dir / "summary.json"
        
        # 统计信息
        self.call_count = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        
        # 写入任务开始信息
        self._write_summary()
        print(f"📁 任务日志目录: {self.task_dir.absolute()}")
    
    def log_llm_call(self, 
                     request: Dict[str, Any], 
                     response: Dict[str, Any],
                     model: str) -> None:
        """记录一次 LLM 调用
        
        Args:
            request: 请求参数 (messages, tools 等)
            response: 响应结果
            model: 使用的模型名称
        """
        self.call_count += 1
        
        # 提取 token 使用情况
        usage = response.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        
        # 构建日志记录
        log_entry = {
            "call_index": self.call_count,
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "request": {
                "messages": request.get("messages", []),
                "tools": request.get("tools", []),
                "tool_choice": request.get("tool_choice")
            },
            "response": {
                "content": response.get("content"),
                "tool_calls": response.get("tool_calls"),
                "role": response.get("role"),
                "finish_reason": response.get("finish_reason")
            },
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": usage.get("total_tokens", 0)
            }
        }
        
        # 追加写入 JSONL 文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        # 更新摘要
        self._write_summary()
        
        print(f"📝 已记录第 {self.call_count} 次 LLM 调用 (tokens: {prompt_tokens}+{completion_tokens})")
    
    def _write_summary(self) -> None:
        """写入/更新任务摘要"""
        summary = {
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat(),
            "call_count": self.call_count,
            "total_tokens": {
                "prompt": self.total_prompt_tokens,
                "completion": self.total_completion_tokens,
                "total": self.total_prompt_tokens + self.total_completion_tokens
            },
            "log_file": str(self.log_file),
            "status": "running" if self.call_count == 0 or not hasattr(self, '_ended') else "completed"
        }
        
        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
    
    def end_task(self) -> None:
        """标记任务结束"""
        self._ended = True
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        summary = {
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": duration,
            "call_count": self.call_count,
            "total_tokens": {
                "prompt": self.total_prompt_tokens,
                "completion": self.total_completion_tokens,
                "total": self.total_prompt_tokens + self.total_completion_tokens
            },
            "log_file": str(self.log_file),
            "status": "completed"
        }
        
        with open(self.summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 任务日志已保存: {self.task_dir.absolute()}")
        print(f"   共 {self.call_count} 次调用, {self.total_prompt_tokens + self.total_completion_tokens} tokens, 耗时 {duration:.1f}秒")
    
    def get_log_path(self) -> Path:
        """获取日志目录路径"""
        return self.task_dir


class NoOpTaskLogger:
    """空实现的 TaskLogger，用于禁用日志记录的情况"""
    
    def __init__(self, *args, **kwargs):
        pass
    
    def log_llm_call(self, *args, **kwargs):
        pass
    
    def end_task(self):
        pass
    
    def get_log_path(self):
        return Path(".")
