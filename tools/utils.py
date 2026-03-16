"""
辅助工具脚本

包含格式化输出、HTML 清洗、Token 计算等工具函数
"""

import re
import json
from typing import Dict, Any, List, Optional
from html.parser import HTMLParser


class HTMLStripper(HTMLParser):
    """HTML 标签剥离器"""
    
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []
    
    def handle_data(self, d):
        self.text.append(d)
    
    def get_data(self):
        return ''.join(self.text)


def strip_html_tags(html: str) -> str:
    """
    去除 HTML 标签
    
    Args:
        html: HTML 字符串
        
    Returns:
        纯文本字符串
    """
    stripper = HTMLStripper()
    try:
        stripper.feed(html)
        return stripper.get_data()
    except:
        # 如果解析失败，使用正则表达式
        return re.sub(r'<[^>]+>', '', html)


def clean_html(html: str, preserve_tags: Optional[List[str]] = None) -> str:
    """
    清洗 HTML，移除 script/style 等标签
    
    Args:
        html: HTML 字符串
        preserve_tags: 需要保留的标签列表
        
    Returns:
        清洗后的 HTML
    """
    # 移除 script 和 style 标签及其内容
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除注释
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    
    # 移除空白字符
    html = re.sub(r'>\s+<', '><', html)
    html = html.strip()
    
    return html


def truncate_text(text: str, max_length: int = 1000, suffix: str = "...") -> str:
    """
    截断文本到指定长度
    
    Args:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
        
    Returns:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def format_json(data: Any, indent: int = 2) -> str:
    """
    格式化 JSON 输出
    
    Args:
        data: 数据对象
        indent: 缩进空格数
        
    Returns:
        格式化的 JSON 字符串
    """
    return json.dumps(data, ensure_ascii=False, indent=indent)


def estimate_tokens(text: str, model: str = "gpt-4") -> int:
    """
    估算文本的 Token 数量
    
    这是一个简化的估算方法，实际应使用 tiktoken
    
    Args:
        text: 文本内容
        model: 模型名称
        
    Returns:
        估算的 Token 数量
    """
    # 简化估算：英文约 4 字符/token，中文约 1.5 字符/token
    # 更精确的方法需要使用 tiktoken
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except:
        # 简化估算
        char_count = len(text)
        # 假设混合文本，平均 3 字符/token
        return int(char_count / 3)


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    从文本中提取 JSON 对象
    
    Args:
        text: 包含 JSON 的文本
        
    Returns:
        解析后的 JSON 对象或 None
    """
    # 尝试匹配 ```json ... ``` 代码块
    json_match = re.search(r'```json\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # 尝试匹配 ``` ... ``` 代码块
    json_match = re.search(r'```\s*\n(.*?)\n```', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except:
            pass
    
    # 尝试匹配 { ... }
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    return None


def format_table(data: List[Dict[str, Any]], columns: Optional[List[str]] = None) -> str:
    """
    将数据格式化为表格字符串
    
    Args:
        data: 数据列表
        columns: 指定列名
        
    Returns:
        表格字符串
    """
    if not data:
        return "无数据"
    
    # 获取所有列名
    if not columns:
        columns = list(data[0].keys())
    
    # 计算每列的最大宽度
    widths = {}
    for col in columns:
        widths[col] = max(
            len(str(col)),
            max(len(str(row.get(col, ""))) for row in data)
        )
    
    # 构建表格
    lines = []
    
    # 表头
    header = " | ".join(str(col).ljust(widths[col]) for col in columns)
    lines.append(header)
    lines.append("-" * len(header))
    
    # 数据行
    for row in data:
        line = " | ".join(
            str(row.get(col, "")).ljust(widths[col]) for col in columns
        )
        lines.append(line)
    
    return "\n".join(lines)


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        安全的文件名
    """
    # 移除非法字符
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # 移除控制字符
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    # 限制长度
    filename = filename[:200]
    return filename.strip()


def parse_url(url: str) -> Dict[str, str]:
    """
    解析 URL
    
    Args:
        url: URL 字符串
        
    Returns:
        URL 组成部分
    """
    from urllib.parse import urlparse, parse_qs
    
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    return {
        "scheme": parsed.scheme,
        "netloc": parsed.netloc,
        "path": parsed.path,
        "params": parsed.params,
        "query": parsed.query,
        "fragment": parsed.fragment,
        "query_params": {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
    }


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并字典
    
    Args:
        base: 基础字典
        override: 覆盖字典
        
    Returns:
        合并后的字典
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


class ColoredOutput:
    """彩色输出工具"""
    
    COLORS = {
        "reset": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
    }
    
    @classmethod
    def print(cls, text: str, color: str = "reset", bold: bool = False):
        """打印彩色文本"""
        color_code = cls.COLORS.get(color, cls.COLORS["reset"])
        if bold:
            color_code = cls.COLORS["bold"] + color_code
        print(f"{color_code}{text}{cls.COLORS['reset']}")
    
    @classmethod
    def success(cls, text: str):
        """打印成功消息"""
        cls.print(f"[✓] {text}", "green")
    
    @classmethod
    def error(cls, text: str):
        """打印错误消息"""
        cls.print(f"[✗] {text}", "red")
    
    @classmethod
    def warning(cls, text: str):
        """打印警告消息"""
        cls.print(f"[!] {text}", "yellow")
    
    @classmethod
    def info(cls, text: str):
        """打印信息消息"""
        cls.print(f"[i] {text}", "blue")


# 便捷函数
def print_result(result: Any, title: Optional[str] = None):
    """
    打印格式化的执行结果
    
    Args:
        result: 结果数据
        title: 标题
    """
    if title:
        print(f"\n{'='*50}")
        print(f"  {title}")
        print(f"{'='*50}")
    
    if isinstance(result, dict):
        print(format_json(result))
    else:
        print(result)
    
    print(f"{'='*50}\n")
