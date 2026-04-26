"""
记忆存储层
封装 SQLite 数据库操作，提供会话、消息、记忆摘要的持久化存储
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from agents.memory.models import Message, MemorySummary, Session


class MemoryStore:
    """
    记忆存储层
    封装 SQLite 数据库操作
    """
    
    _instance = None
    _lock = None
    
    def __new__(cls, db_path: str = None):
        """单例模式，确保全局只有一个数据库连接"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径，如果不指定则使用默认路径
        """
        if self._initialized:
            return
        
        self.db_path = db_path or self._get_default_path()
        self._ensure_data_directory()
        self._init_db()
        self._initialized = True
    
    def _get_default_path(self) -> str:
        """
        获取默认数据库路径
        
        Returns:
            默认数据库文件路径
        """
        base_dir = Path(__file__).resolve().parent.parent.parent
        data_dir = base_dir / "data"
        return str(data_dir / "agent_memory.db")
    
    def _ensure_data_directory(self):
        """确保数据目录存在"""
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接
        
        Returns:
            SQLite 连接对象
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                is_active INTEGER DEFAULT 1,
                metadata TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                tool_calls TEXT,
                tool_call_id TEXT,
                tool_name TEXT,
                created_at TIMESTAMP NOT NULL,
                metadata TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memory_summaries (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                summary_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 5,
                created_at TIMESTAMP NOT NULL,
                source_message_ids TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_summaries_session_id ON memory_summaries(session_id)")
        
        conn.commit()
        conn.close()
    
    def create_session(self, title: str = "新对话") -> Session:
        """
        创建新会话
        
        Args:
            title: 会话标题
        
        Returns:
            新创建的 Session 对象
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        now = datetime.now()
        
        session = Session(
            id=session_id,
            title=title,
            created_at=now,
            updated_at=now,
            is_active=True,
            metadata={}
        )
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO sessions (id, title, created_at, updated_at, is_active, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session.id,
            session.title,
            session.created_at.isoformat(),
            session.updated_at.isoformat(),
            1 if session.is_active else 0,
            json.dumps(session.metadata) if session.metadata else None
        ))
        
        conn.commit()
        conn.close()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            Session 对象，如果不存在返回 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, created_at, updated_at, is_active, metadata
            FROM sessions
            WHERE id = ?
        """, (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return None
        
        return Session.from_row(tuple(row), row.keys())
    
    def update_session(self, session_id: str, **kwargs) -> bool:
        """
        更新会话
        
        Args:
            session_id: 会话ID
            **kwargs: 要更新的字段 (title, is_active, metadata)
        
        Returns:
            是否更新成功
        """
        valid_fields = {"title", "is_active", "metadata"}
        update_fields = {k: v for k, v in kwargs.items() if k in valid_fields}
        
        if not update_fields:
            return False
        
        update_fields["updated_at"] = datetime.now().isoformat()
        
        set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
        values = list(update_fields.values())
        values.append(session_id)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(f"""
            UPDATE sessions
            SET {set_clause}
            WHERE id = ?
        """, values)
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话（级联删除消息和摘要）
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否删除成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM memory_summaries WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    def list_sessions(self, limit: int = 50, offset: int = 0) -> List[Session]:
        """
        获取会话列表（按更新时间倒序）
        
        Args:
            limit: 返回数量限制
            offset: 偏移量，用于分页
        
        Returns:
            Session 对象列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, created_at, updated_at, is_active, metadata
            FROM sessions
            WHERE is_active = 1
            ORDER BY updated_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        sessions = []
        for row in rows:
            sessions.append(Session.from_row(tuple(row), row.keys()))
        
        return sessions
    
    def get_session_message_count(self, session_id: str) -> int:
        """
        获取会话的消息数量
        
        Args:
            session_id: 会话ID
        
        Returns:
            消息数量
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) FROM messages WHERE session_id = ?
        """, (session_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def add_message(self, message: Message) -> bool:
        """
        添加消息
        
        Args:
            message: Message 对象
        
        Returns:
            是否添加成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        tool_calls_json = None
        if message.tool_calls:
            tool_calls_json = json.dumps(message.tool_calls, ensure_ascii=False)
        
        metadata_json = None
        if message.metadata:
            metadata_json = json.dumps(message.metadata, ensure_ascii=False)
        
        try:
            cursor.execute("""
                INSERT INTO messages (
                    id, session_id, role, content, tool_calls,
                    tool_call_id, tool_name, created_at, metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.id,
                message.session_id,
                message.role,
                message.content,
                tool_calls_json,
                message.tool_call_id,
                message.tool_name,
                message.created_at.isoformat(),
                metadata_json
            ))
            
            cursor.execute("""
                UPDATE sessions
                SET updated_at = ?
                WHERE id = ?
            """, (datetime.now().isoformat(), message.session_id))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def add_messages(self, messages: List[Message]) -> bool:
        """
        批量添加消息
        
        Args:
            messages: Message 对象列表
        
        Returns:
            是否全部添加成功
        """
        if not messages:
            return True
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            for message in messages:
                tool_calls_json = None
                if message.tool_calls:
                    tool_calls_json = json.dumps(message.tool_calls, ensure_ascii=False)
                
                metadata_json = None
                if message.metadata:
                    metadata_json = json.dumps(message.metadata, ensure_ascii=False)
                
                cursor.execute("""
                    INSERT INTO messages (
                        id, session_id, role, content, tool_calls,
                        tool_call_id, tool_name, created_at, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    message.id,
                    message.session_id,
                    message.role,
                    message.content,
                    tool_calls_json,
                    message.tool_call_id,
                    message.tool_name,
                    message.created_at.isoformat(),
                    metadata_json
                ))
            
            session_ids = {m.session_id for m in messages}
            for session_id in session_ids:
                cursor.execute("""
                    UPDATE sessions
                    SET updated_at = ?
                    WHERE id = ?
                """, (datetime.now().isoformat(), session_id))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_messages(self, session_id: str, limit: int = 100, offset: int = 0) -> List[Message]:
        """
        获取会话消息
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
            offset: 偏移量
        
        Returns:
            Message 对象列表（按创建时间正序）
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, session_id, role, content, tool_calls,
                   tool_call_id, tool_name, created_at, metadata
            FROM messages
            WHERE session_id = ?
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
        """, (session_id, limit, offset))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        for row in rows:
            messages.append(Message.from_row(tuple(row), row.keys()))
        
        return messages
    
    def delete_message(self, message_id: str) -> bool:
        """
        删除消息
        
        Args:
            message_id: 消息ID
        
        Returns:
            是否删除成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT session_id FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        
        if row is None:
            conn.close()
            return False
        
        session_id = row[0]
        
        cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        
        cursor.execute("""
            UPDATE sessions
            SET updated_at = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()
        
        return True
    
    def add_summary(self, summary: MemorySummary) -> bool:
        """
        添加记忆摘要
        
        Args:
            summary: MemorySummary 对象
        
        Returns:
            是否添加成功
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        source_message_ids_json = None
        if summary.source_message_ids:
            source_message_ids_json = json.dumps(summary.source_message_ids)
        
        try:
            cursor.execute("""
                INSERT INTO memory_summaries (
                    id, session_id, summary_type, content,
                    importance, created_at, source_message_ids
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                summary.id,
                summary.session_id,
                summary.summary_type,
                summary.content,
                summary.importance,
                summary.created_at.isoformat(),
                source_message_ids_json
            ))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def search_summaries(self, query: str, session_id: str = None, limit: int = 10) -> List[MemorySummary]:
        """
        搜索相关摘要（简单的关键词匹配）
        
        Args:
            query: 搜索关键词
            session_id: 可选，限定在某个会话中搜索
            limit: 返回数量限制
        
        Returns:
            MemorySummary 对象列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        if session_id:
            cursor.execute("""
                SELECT id, session_id, summary_type, content,
                       importance, created_at, source_message_ids
                FROM memory_summaries
                WHERE session_id = ? AND content LIKE ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (session_id, f"%{query}%", limit))
        else:
            cursor.execute("""
                SELECT id, session_id, summary_type, content,
                       importance, created_at, source_message_ids
                FROM memory_summaries
                WHERE content LIKE ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
            """, (f"%{query}%", limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        summaries = []
        for row in rows:
            summaries.append(MemorySummary.from_row(tuple(row), row.keys()))
        
        return summaries
    
    def get_summaries(self, session_id: str, limit: int = 20) -> List[MemorySummary]:
        """
        获取会话的所有摘要
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
        
        Returns:
            MemorySummary 对象列表
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, session_id, summary_type, content,
                   importance, created_at, source_message_ids
            FROM memory_summaries
            WHERE session_id = ?
            ORDER BY importance DESC, created_at DESC
            LIMIT ?
        """, (session_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        summaries = []
        for row in rows:
            summaries.append(MemorySummary.from_row(tuple(row), row.keys()))
        
        return summaries
    
    def close(self):
        """关闭数据库（单例模式下通常不需要手动调用）"""
        pass
