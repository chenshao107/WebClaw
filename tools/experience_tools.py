"""
经验管理工具 - 让 Agent 能够自我管理记忆

这些工具暴露给 LLM，使其能够：
- 记录新发现的经验
- 标记过时的经验
- 查询现有经验
"""

from typing import Any, Dict, List
from tools.base import BaseTool
from core.experience_store import get_experience_store, ExperienceStore


class RecordExperienceTool(BaseTool):
    """
    记录新经验工具
    
    当 Agent 发现某个操作技巧、网站特殊处理方式、或成功完成某类任务时，
    可以使用此工具记录下来，供未来类似任务参考。
    """
    
    @property
    def name(self) -> str:
        return "record_experience"
    
    @property
    def description(self) -> str:
        return """记录一条新的操作经验到知识库中。

使用时机：
1. 成功完成一个复杂任务后，总结出可复用的方法
2. 发现某个网站的特殊操作方式或 DOM 结构特点
3. 找到解决某类问题的有效策略
4. 绕过某些反爬虫或验证机制的技巧

注意：
- 主题要简洁明确
- 内容要具体可操作
- 标签要包含关键词，方便未来检索"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "经验主题，简洁描述这是什么经验，如 'GitHub 登录流程'、'B站视频下载方法'"
                },
                "content": {
                    "type": "string",
                    "description": "经验具体内容，详细描述操作步骤、注意事项、代码示例等"
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "关键词标签，用于检索，如 ['github', 'login', 'authentication']"
                },
                "domains": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "适用网站域名，如 ['github.com', 'stackoverflow.com']"
                }
            },
            "required": ["topic", "content"]
        }
    
    def execute(self, topic: str, content: str, tags: List[str] = None, domains: List[str] = None) -> str:
        store = get_experience_store()
        
        try:
            exp_id = store.add_experience(
                topic=topic,
                content=content,
                tags=tags or [],
                domains=domains or []
            )
            return f"✅ 经验已记录 (ID: {exp_id}): {topic}"
        except Exception as e:
            return f"❌ 记录失败: {str(e)}"


class MarkExperienceOutdatedTool(BaseTool):
    """
    标记经验过时工具
    
    当 Agent 发现某条历史经验已经失效、错误、或有更好的替代方案时，
    使用此工具将其标记为过时。
    """
    
    @property
    def name(self) -> str:
        return "mark_experience_outdated"
    
    @property
    def description(self) -> str:
        return """将一条经验标记为过时或失效。

使用时机：
1. 按照某条历史经验操作时发现已经失效（网站改版、接口变更等）
2. 发现某条经验的方法不是最优的，有更简单的方式
3. 经验内容有误，可能导致任务失败

注意：
- 尽量提供过时原因，帮助理解
- 标记后该经验不会再被推荐给未来的任务"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "exp_id": {
                    "type": "integer",
                    "description": "经验 ID（从经验内容中可以看到）"
                },
                "reason": {
                    "type": "string",
                    "description": "过时原因，如 '网站改版，按钮位置已变更'、'有更简单的 CSS 选择器'"
                }
            },
            "required": ["exp_id", "reason"]
        }
    
    def execute(self, exp_id: int, reason: str) -> str:
        store = get_experience_store()
        
        try:
            store.mark_outdated(exp_id, reason)
            return f"✅ 经验 {exp_id} 已标记为过时: {reason}"
        except Exception as e:
            return f"❌ 操作失败: {str(e)}"


class SearchExperienceTool(BaseTool):
    """
    搜索经验工具
    
    让 Agent 主动查询知识库中的经验。
    """
    
    @property
    def name(self) -> str:
        return "search_experiences"
    
    @property
    def description(self) -> str:
        return """主动搜索知识库中的历史经验。

使用时机：
1. 任务开始前，想了解是否有相关经验可以参考
2. 遇到困难时，查找是否有类似问题的解决方案
3. 验证某条经验是否存在或是否已被标记过时"""
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "搜索关键词，如 'github login'、'验证码处理'"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数限制，默认 5 条",
                    "default": 5
                }
            },
            "required": ["keywords"]
        }
    
    def execute(self, keywords: str, limit: int = 5) -> str:
        store = get_experience_store()
        
        try:
            experiences = store.retrieve(context=keywords, limit=limit)
            
            if not experiences:
                return f"🔍 未找到与 '{keywords}' 相关的经验"
            
            result = f"🔍 找到 {len(experiences)} 条相关经验:\n"
            for i, exp in enumerate(experiences, 1):
                result += f"\n{i}. [{exp.id}] {exp.topic}"
                result += f" (成功率: {exp.success_rate*100:.0f}%, 使用次数: {exp.hit_count})"
                if exp.domains:
                    result += f"\n   适用: {', '.join(exp.domains)}"
                result += f"\n   {exp.content[:200]}..."
            
            return result
        except Exception as e:
            return f"❌ 搜索失败: {str(e)}"


class GetExperienceStatsTool(BaseTool):
    """
    获取经验库统计信息工具
    """
    
    @property
    def name(self) -> str:
        return "get_experience_stats"
    
    @property
    def description(self) -> str:
        return "获取经验知识库的统计信息，包括总条数、平均成功率等"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }
    
    def execute(self) -> str:
        store = get_experience_store()
        
        try:
            stats = store.get_stats()
            return f"""📊 经验库统计:
- 总经验数: {stats['total']}
- 已过时: {stats['outdated']}
- 平均成功率: {stats['avg_success_rate']*100:.1f}%
- 平均使用次数: {stats['avg_hits']}
- 容量上限: {stats['max_capacity']}"""
        except Exception as e:
            return f"❌ 获取统计失败: {str(e)}"


# 工具导出列表
EXPERIENCE_TOOLS = [
    RecordExperienceTool(),
    MarkExperienceOutdatedTool(),
    SearchExperienceTool(),
    GetExperienceStatsTool()
]
