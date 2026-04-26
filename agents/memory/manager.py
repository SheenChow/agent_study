"""
记忆管理器
提供高层记忆操作接口，整合存储和检索
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from agents.llm_agent import ChatMessage
from agents.memory.models import Message, MemorySummary, Session
from agents.memory.store import MemoryStore


class MemoryManager:
    """
    记忆管理器
    提供高层记忆操作接口，整合存储和检索
    """
    
    _instance = None
    
    def __new__(cls, store: MemoryStore = None):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, store: MemoryStore = None):
        """
        初始化记忆管理器
        
        Args:
            store: MemoryStore 实例，如果不提供则使用默认单例
        """
        if self._initialized:
            return
        
        self.store = store or MemoryStore()
        self._initialized = True
    
    def create_session(self, title: str = "新对话") -> Session:
        """
        创建新会话
        
        Args:
            title: 会话标题
        
        Returns:
            新创建的 Session 对象
        """
        return self.store.create_session(title)
    
    def get_or_create_session(self, session_id: str = None, title: str = "新对话") -> Session:
        """
        获取或创建会话
        
        Args:
            session_id: 会话ID，如果为 None 或不存在则创建新会话
            title: 新会话标题
        
        Returns:
            Session 对象
        """
        if session_id:
            session = self.store.get_session(session_id)
            if session:
                return session
        
        return self.store.create_session(title)
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            Session 对象，如果不存在返回 None
        """
        return self.store.get_session(session_id)
    
    def update_session_title(self, session_id: str, title: str) -> bool:
        """
        更新会话标题
        
        Args:
            session_id: 会话ID
            title: 新标题
        
        Returns:
            是否更新成功
        """
        return self.store.update_session(session_id, title=title)
    
    def delete_session(self, session_id: str) -> bool:
        """
        删除会话
        
        Args:
            session_id: 会话ID
        
        Returns:
            是否删除成功
        """
        return self.store.delete_session(session_id)
    
    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取会话列表（带消息数量）
        
        Args:
            limit: 返回数量限制
        
        Returns:
            会话信息列表，包含消息数量
        """
        sessions = self.store.list_sessions(limit=limit)
        
        result = []
        for session in sessions:
            message_count = self.store.get_session_message_count(session.id)
            session_dict = session.to_dict()
            session_dict["message_count"] = message_count
            result.append(session_dict)
        
        return result
    
    def switch_session(self, session_id: str) -> Tuple[Optional[Session], List[Message]]:
        """
        切换会话，返回会话和历史消息
        
        Args:
            session_id: 会话ID
        
        Returns:
            (会话对象, 消息列表)，如果会话不存在返回 (None, [])
        """
        session = self.store.get_session(session_id)
        if session is None:
            return None, []
        
        messages = self.store.get_messages(session_id)
        return session, messages
    
    def _generate_message_id(self) -> str:
        """生成消息ID"""
        return f"msg_{uuid.uuid4().hex[:12]}"
    
    def save_message(self, session_id: str, role: str, content: str = None, **kwargs) -> Message:
        """
        保存单条消息
        
        Args:
            session_id: 会话ID
            role: 消息角色 (user, assistant, tool, system)
            content: 消息内容
            **kwargs: 其他参数
                - tool_calls: 工具调用信息列表
                - tool_call_id: 工具调用ID (tool角色)
                - tool_name: 工具名称 (tool角色)
                - metadata: 元数据
        
        Returns:
            保存的 Message 对象
        """
        message = Message(
            id=self._generate_message_id(),
            session_id=session_id,
            role=role,
            content=content,
            tool_calls=kwargs.get("tool_calls"),
            tool_call_id=kwargs.get("tool_call_id"),
            tool_name=kwargs.get("tool_name"),
            created_at=datetime.now(),
            metadata=kwargs.get("metadata", {})
        )
        
        self.store.add_message(message)
        return message
    
    def save_user_message(self, session_id: str, content: str, metadata: Dict = None) -> Message:
        """
        保存用户消息
        
        Args:
            session_id: 会话ID
            content: 消息内容
            metadata: 元数据
        
        Returns:
            保存的 Message 对象
        """
        return self.save_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata=metadata or {}
        )
    
    def save_assistant_message(self, session_id: str, content: str, 
                                tool_calls: List[Dict] = None, 
                                usage: Dict = None,
                                metadata: Dict = None) -> Message:
        """
        保存助手消息
        
        Args:
            session_id: 会话ID
            content: 消息内容
            tool_calls: 工具调用信息列表
            usage: token 使用信息
            metadata: 其他元数据
        
        Returns:
            保存的 Message 对象
        """
        meta = metadata or {}
        if usage:
            meta["usage"] = usage
        
        return self.save_message(
            session_id=session_id,
            role="assistant",
            content=content,
            tool_calls=tool_calls,
            metadata=meta
        )
    
    def save_tool_message(self, session_id: str, tool_call_id: str,
                          tool_name: str, content: str, metadata: Dict = None) -> Message:
        """
        保存工具消息
        
        Args:
            session_id: 会话ID
            tool_call_id: 工具调用ID
            tool_name: 工具名称
            content: 工具返回内容
            metadata: 元数据
        
        Returns:
            保存的 Message 对象
        """
        return self.save_message(
            session_id=session_id,
            role="tool",
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            metadata=metadata or {}
        )
    
    def save_system_message(self, session_id: str, content: str, metadata: Dict = None) -> Message:
        """
        保存系统消息
        
        Args:
            session_id: 会话ID
            content: 系统消息内容
            metadata: 元数据
        
        Returns:
            保存的 Message 对象
        """
        return self.save_message(
            session_id=session_id,
            role="system",
            content=content,
            metadata=metadata or {}
        )
    
    def get_messages(self, session_id: str, limit: int = 100) -> List[Message]:
        """
        获取会话消息
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
        
        Returns:
            Message 对象列表
        """
        return self.store.get_messages(session_id, limit=limit)
    
    def get_context(self, session_id: str, 
                    max_messages: int = 20,
                    max_tokens: int = 4000,
                    include_system: bool = True) -> List[ChatMessage]:
        """
        获取对话上下文，用于传递给LLM进行推理
        
        Args:
            session_id: 会话ID
            max_messages: 最大消息数量
            max_tokens: 最大token数（预留，暂未实现精确计算）
            include_system: 是否包含system消息
        
        Returns:
            ChatMessage 对象列表
        """
        messages = self.store.get_messages(session_id, limit=max_messages)
        
        if not include_system:
            messages = [m for m in messages if m.role != "system"]
        
        return [m.to_chat_message() for m in messages]
    
    def get_session_with_messages(self, session_id: str, message_limit: int = 100) -> Optional[Dict[str, Any]]:
        """
        获取会话详情和消息
        
        Args:
            session_id: 会话ID
            message_limit: 消息数量限制
        
        Returns:
            包含会话信息和消息列表的字典，如果会话不存在返回 None
        """
        session = self.store.get_session(session_id)
        if session is None:
            return None
        
        messages = self.store.get_messages(session_id, limit=message_limit)
        
        result = session.to_dict()
        result["messages"] = [m.to_dict() for m in messages]
        result["message_count"] = len(messages)
        
        return result
    
    def add_summary(self, session_id: str, summary_type: str, content: str,
                    importance: int = 5, source_message_ids: List[str] = None) -> MemorySummary:
        """
        添加记忆摘要
        
        Args:
            session_id: 会话ID
            summary_type: 摘要类型 (session, key_point, fact)
            content: 摘要内容
            importance: 重要程度 (1-10)
            source_message_ids: 来源消息ID列表
        
        Returns:
            创建的 MemorySummary 对象
        """
        summary = MemorySummary(
            id=f"sum_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            summary_type=summary_type,
            content=content,
            importance=importance,
            created_at=datetime.now(),
            source_message_ids=source_message_ids or []
        )
        
        self.store.add_summary(summary)
        return summary
    
    def search_memory(self, query: str, 
                      session_id: str = None,
                      limit: int = 5) -> List[Dict[str, Any]]:
        """
        检索相关记忆
        
        Args:
            query: 搜索关键词
            session_id: 可选，限定在某个会话中搜索
            limit: 返回数量限制
        
        Returns:
            相关记忆列表
        """
        summaries = self.store.search_summaries(query, session_id, limit)
        return [s.to_dict() for s in summaries]
    
    def get_summaries(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取会话的所有摘要
        
        Args:
            session_id: 会话ID
            limit: 返回数量限制
        
        Returns:
            摘要列表
        """
        summaries = self.store.get_summaries(session_id, limit)
        return [s.to_dict() for s in summaries]
    
    def delete_message(self, message_id: str) -> bool:
        """
        删除消息
        
        Args:
            message_id: 消息ID
        
        Returns:
            是否删除成功
        """
        return self.store.delete_message(message_id)
