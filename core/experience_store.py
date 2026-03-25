"""
ExperienceStore - Agent 经验记忆存储系统

基于 SQLite + FTS5 实现，支持：
- 全文检索（关键词匹配）
- LRU 权重排序（时间衰减 + 热度 + 成功率）
- 自动容量管理（超出上限删除最旧记录）
- 自我迭代（Agent 可标记过时经验、更新成功率）
"""

import sqlite3
import json
import time
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class Experience:
    """经验记录数据类"""
    id: Optional[int]
    topic: str
    content: str
    tags: List[str]
    domains: List[str]  # 适用网站域名
    last_used: int
    hit_count: int
    created_at: int
    success_rate: float  # 0.0 ~ 1.0
    
    def to_prompt_text(self) -> str:
        """转换为 Prompt 中使用的文本格式"""
        return f"""
[历史经验 - {self.topic}]
适用场景: {', '.join(self.domains) if self.domains else '通用'}
成功率: {self.success_rate*100:.0f}%
内容:
{self.content}
"""


class ExperienceStore:
    """
    Agent 经验存储管理器
    
    使用示例:
        store = ExperienceStore()
        
        # 记录新经验
        store.add_experience(
            topic="GitHub 登录流程",
            content="先点击右上角 Sign in 按钮，然后...",
            tags=["github", "login", "auth"],
            domains=["github.com"]
        )
        
        # 检索相关经验
        experiences = store.retrieve(["github", "登录"], limit=3)
    """
    
    DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "experiences.db"
    DEFAULT_MAX_SIZE = 500  # 默认最大经验条数
    TIME_DECAY_DAYS = 7     # 时间衰减半衰期（天）
    
    def __init__(self, db_path: Optional[Path] = None, max_size: int = DEFAULT_MAX_SIZE):
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.max_size = max_size
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """确保数据库和表结构存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 主表：存储经验数据
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS experiences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tags TEXT,           -- JSON 数组
                    domains TEXT,        -- JSON 数组，适用域名
                    last_used INTEGER,   -- 最后使用时间戳
                    hit_count INTEGER DEFAULT 0,
                    created_at INTEGER,
                    success_rate REAL DEFAULT 1.0,
                    is_outdated INTEGER DEFAULT 0  -- 0=有效, 1=已标记过时
                )
            """)
            
            # FTS5 全文搜索虚拟表
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS experiences_fts USING fts5(
                    topic, 
                    content,
                    tags,
                    content='experiences',
                    content_rowid='id'
                )
            """)
            
            # 触发器：自动同步 FTS5 索引
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS experiences_ai AFTER INSERT ON experiences BEGIN
                    INSERT INTO experiences_fts(rowid, topic, content, tags)
                    VALUES (new.id, new.topic, new.content, new.tags);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS experiences_ad AFTER DELETE ON experiences BEGIN
                    INSERT INTO experiences_fts(experiences_fts, rowid, topic, content, tags)
                    VALUES ('delete', old.id, old.topic, old.content, old.tags);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS experiences_au AFTER UPDATE ON experiences BEGIN
                    INSERT INTO experiences_fts(experiences_fts, rowid, topic, content, tags)
                    VALUES ('delete', old.id, old.topic, old.content, old.tags);
                    INSERT INTO experiences_fts(rowid, topic, content, tags)
                    VALUES (new.id, new.topic, new.content, new.tags);
                END
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _calculate_score(self, hit_count: int, last_used: int, success_rate: float) -> float:
        """
        计算经验综合评分（热度 × 时间衰减 × 成功率）
        
        评分越高，越优先返回
        """
        now = int(time.time())
        days_since_used = (now - last_used) / 86400
        time_decay = 1 / (1 + days_since_used / self.TIME_DECAY_DAYS)
        
        # 基础热度分（对数压缩，避免少数经验垄断）
        heat_score = (hit_count + 1) ** 0.5
        
        return heat_score * time_decay * success_rate
    
    def _extract_keywords(self, text: str) -> List[str]:
        """从文本中提取关键词（简单实现，可扩展）"""
        # 保留中文和英文单词
        words = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text.lower())
        return words
    
    def _build_fts_query(self, keywords: List[str]) -> str:
        """构建 FTS5 查询语句"""
        # 支持 OR 语义：匹配任意一个关键词
        cleaned = [kw.replace('"', ' ') for kw in keywords if kw.strip()]
        if not cleaned:
            return "*"
        return " OR ".join(f'"{kw}"' for kw in cleaned)
    
    def retrieve(
        self, 
        context: str, 
        limit: int = 3,
        domain_filter: Optional[str] = None
    ) -> List[Experience]:
        """
        检索相关经验
        
        Args:
            context: 任务描述或关键词（自然语言）
            limit: 返回条数上限
            domain_filter: 可选，按域名过滤（如 "github.com"）
        
        Returns:
            按综合评分排序的经验列表
        """
        keywords = self._extract_keywords(context)
        fts_query = self._build_fts_query(keywords)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 基础查询：FTS 匹配 + 未过时
            sql = """
                SELECT e.* FROM experiences e
                JOIN experiences_fts fts ON e.id = fts.rowid
                WHERE experiences_fts MATCH ? AND e.is_outdated = 0
            """
            params = [fts_query]
            
            # 可选：域名过滤
            if domain_filter:
                sql += " AND e.domains LIKE ?"
                params.append(f'%"{domain_filter}"%')
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            if not rows:
                return []
            
            # 计算评分并排序
            scored = []
            for row in rows:
                exp = self._row_to_experience(row)
                score = self._calculate_score(
                    exp.hit_count, 
                    exp.last_used, 
                    exp.success_rate
                )
                scored.append((score, exp))
            
            scored.sort(key=lambda x: x[0], reverse=True)
            results = [exp for _, exp in scored[:limit]]
            
            # 更新命中信息（LRU 刷新）
            if results:
                now = int(time.time())
                ids = [exp.id for exp in results]
                placeholders = ','.join('?' * len(ids))
                cursor.execute(f"""
                    UPDATE experiences 
                    SET last_used = ?, hit_count = hit_count + 1 
                    WHERE id IN ({placeholders})
                """, [now] + ids)
                conn.commit()
                
                # 更新内存对象的 last_used
                for exp in results:
                    exp.last_used = now
                    exp.hit_count += 1
            
            return results
    
    def add_experience(
        self,
        topic: str,
        content: str,
        tags: List[str] = None,
        domains: List[str] = None,
        success_rate: float = 1.0
    ) -> int:
        """
        添加新经验
        
        Returns:
            新经验的 ID
        """
        # LRU 清理：超出上限时删除最旧记录
        self._enforce_capacity()
        
        now = int(time.time())
        tags_json = json.dumps(tags or [], ensure_ascii=False)
        domains_json = json.dumps(domains or [], ensure_ascii=False)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO experiences 
                (topic, content, tags, domains, last_used, hit_count, created_at, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (topic, content, tags_json, domains_json, now, 0, now, success_rate))
            
            conn.commit()
            return cursor.lastrowid
    
    def _enforce_capacity(self):
        """强制执行容量限制，删除最久未使用的记录"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取当前数量
            cursor.execute("SELECT COUNT(*) FROM experiences")
            count = cursor.fetchone()[0]
            
            if count >= self.max_size:
                # 删除最久未使用的记录（保留 90% 容量，批量删除避免频繁触发）
                to_delete = int(self.max_size * 0.1) + 1
                cursor.execute("""
                    DELETE FROM experiences 
                    WHERE id IN (
                        SELECT id FROM experiences 
                        ORDER BY last_used ASC, hit_count ASC 
                        LIMIT ?
                    )
                """, (to_delete,))
                conn.commit()
    
    def update_success(self, exp_id: int, success: bool):
        """
        更新经验的成功率（用于自我迭代）
        
        Args:
            exp_id: 经验 ID
            success: 本次使用是否成功
        """
        # 使用指数移动平均更新成功率
        alpha = 0.3  # 新样本权重
        new_rate = 1.0 if success else 0.0
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE experiences 
                SET success_rate = (success_rate * ? + ? * ?)
                WHERE id = ?
            """, (1 - alpha, alpha, new_rate, exp_id))
            conn.commit()
    
    def mark_outdated(self, exp_id: int, reason: str = ""):
        """
        标记经验为过时（Agent 自我修正）
        
        Args:
            exp_id: 经验 ID
            reason: 可选，过时原因
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE experiences 
                SET is_outdated = 1, content = content || ?
                WHERE id = ?
            """, (f"\n\n[已过时: {reason}]", exp_id))
            conn.commit()
    
    def delete_experience(self, exp_id: int):
        """删除指定经验"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM experiences WHERE id = ?", (exp_id,))
            conn.commit()
    
    def get_stats(self) -> Dict:
        """获取存储统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_outdated = 1 THEN 1 ELSE 0 END) as outdated,
                    AVG(success_rate) as avg_success,
                    AVG(hit_count) as avg_hits
                FROM experiences
            """)
            row = cursor.fetchone()
            
            return {
                "total": row["total"],
                "outdated": row["outdated"],
                "avg_success_rate": round(row["avg_success"] or 0, 2),
                "avg_hits": round(row["avg_hits"] or 0, 2),
                "max_capacity": self.max_size
            }
    
    def _row_to_experience(self, row: sqlite3.Row) -> Experience:
        """将数据库行转换为 Experience 对象"""
        return Experience(
            id=row["id"],
            topic=row["topic"],
            content=row["content"],
            tags=json.loads(row["tags"] or "[]"),
            domains=json.loads(row["domains"] or "[]"),
            last_used=row["last_used"],
            hit_count=row["hit_count"],
            created_at=row["created_at"],
            success_rate=row["success_rate"]
        )
    
    def search_by_topic(self, topic_pattern: str) -> List[Experience]:
        """按主题模糊搜索（管理用途）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM experiences WHERE topic LIKE ?",
                (f"%{topic_pattern}%",)
            )
            return [self._row_to_experience(row) for row in cursor.fetchall()]


# 全局单例（可选，根据你的架构选择是否使用）
_experience_store: Optional[ExperienceStore] = None


def get_experience_store() -> ExperienceStore:
    """获取全局 ExperienceStore 实例"""
    global _experience_store
    if _experience_store is None:
        _experience_store = ExperienceStore()
    return _experience_store
