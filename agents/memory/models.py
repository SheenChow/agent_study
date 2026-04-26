"""
数据模型类
定义会话、消息、记忆摘要等数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any

from agents.llm_agent import ChatMessage


@dataclass
class Session:
    """
    会话数据模型
    表示一个完整的对话会话
    """
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_row(cls, row: tuple, column_names: List[str]) -> "Session":
        """
        从数据库行创建Session对象
        
        Args:
            row: 数据库查询结果行
            column_names: 列名列表，用于映射字段
        
        Returns:
            Session 对象
        """
        row_dict = dict(zip(column_names, row))
        
        created_at = row_dict.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        updated_at = row_dict.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
        
        metadata = row_dict.get("metadata")
        if isinstance(metadata, str) and metadata:
            import json
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        elif metadata is None:
            metadata = {}
        
        is_active = row_dict.get("is_active", 1)
        if isinstance(is_active, int):
            is_active = bool(is_active)
        
        return cls(
            id=row_dict.get("id", ""),
            title=row_dict.get("title", "新对话"),
            created_at=created_at or datetime.now(),
            updated_at=updated_at or datetime.now(),
            is_active=is_active,
            metadata=metadata
        )


@dataclass
class Message:
    """
    消息数据模型
    表示单条聊天消息
    """
    id: str
    session_id: str
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_chat_message(self) -> ChatMessage:
        """
        转换为LLM使用的ChatMessage格式
        
        Returns:
            ChatMessage 对象，用于LLM推理
        """
        return ChatMessage(
            role=self.role,
            content=self.content,
            tool_calls=self.tool_calls,
            tool_call_id=self.tool_call_id,
            name=self.tool_name
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_row(cls, row: tuple, column_names: List[str]) -> "Message":
        """
        从数据库行创建Message对象
        
        Args:
            row: 数据库查询结果行
            column_names: 列名列表
        
        Returns:
            Message 对象
        """
        row_dict = dict(zip(column_names, row))
        
        created_at = row_dict.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        tool_calls = row_dict.get("tool_calls")
        if isinstance(tool_calls, str) and tool_calls:
            import json
            try:
                tool_calls = json.loads(tool_calls)
            except json.JSONDecodeError:
                tool_calls = None
        
        metadata = row_dict.get("metadata")
        if isinstance(metadata, str) and metadata:
            import json
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = {}
        elif metadata is None:
            metadata = {}
        
        return cls(
            id=row_dict.get("id", ""),
            session_id=row_dict.get("session_id", ""),
            role=row_dict.get("role", "user"),
            content=row_dict.get("content"),
            tool_calls=tool_calls,
            tool_call_id=row_dict.get("tool_call_id"),
            tool_name=row_dict.get("tool_name"),
            created_at=created_at or datetime.now(),
            metadata=metadata
        )


@dataclass
class MemorySummary:
    """
    记忆摘要数据模型
    用于存储对话摘要、关键事实等长期记忆
    """
    id: str
    session_id: str
    summary_type: str
    content: str
    importance: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    source_message_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "summary_type": self.summary_type,
            "content": self.content,
            "importance": self.importance,
            "created_at": self.created_at.isoformat(),
            "source_message_ids": self.source_message_ids
        }
    
    @classmethod
    def from_row(cls, row: tuple, column_names: List[str]) -> "MemorySummary":
        """
        从数据库行创建MemorySummary对象
        
        Args:
            row: 数据库查询结果行
            column_names: 列名列表
        
        Returns:
            MemorySummary 对象
        """
        row_dict = dict(zip(column_names, row))
        
        created_at = row_dict.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        
        source_message_ids = row_dict.get("source_message_ids")
        if isinstance(source_message_ids, str) and source_message_ids:
            import json
            try:
                source_message_ids = json.loads(source_message_ids)
            except json.JSONDecodeError:
                source_message_ids = []
        elif source_message_ids is None:
            source_message_ids = []
        
        importance = row_dict.get("importance", 5)
        if isinstance(importance, str):
            importance = int(importance)
        
        return cls(
            id=row_dict.get("id", ""),
            session_id=row_dict.get("session_id", ""),
            summary_type=row_dict.get("summary_type", "key_point"),
            content=row_dict.get("content", ""),
            importance=importance,
            created_at=created_at or datetime.now(),
            source_message_ids=source_message_ids
        )
