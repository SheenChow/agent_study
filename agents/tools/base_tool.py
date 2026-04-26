#!/usr/bin/env python3
"""
工具基类模块
定义所有工具的抽象基类和数据结构
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Generator


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "error": self.error,
            "metadata": self.metadata
        }
    
    def __str__(self) -> str:
        if self.success:
            return self.content
        return f"[错误] {self.error or '未知错误'}"


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    name: str
    arguments: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolCall":
        return cls(
            id=data.get("id", ""),
            name=data.get("function", {}).get("name", ""),
            arguments=json.loads(data.get("function", {}).get("arguments", "{}"))
        )


@dataclass
class ToolResponse:
    """工具响应消息（返回给LLM）"""
    tool_call_id: str
    role: str = "tool"
    name: str = ""
    content: str = ""
    
    def to_message_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
            "content": self.content
        }


class BaseTool(ABC):
    """
    工具抽象基类
    所有工具都需要继承此类并实现 execute 方法
    """
    
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise NotImplementedError(f"子类 {cls.__name__} 必须定义 name 属性")
        if not cls.description:
            raise NotImplementedError(f"子类 {cls.__name__} 必须定义 description 属性")
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult: 工具执行结果
        """
        pass
    
    def to_function_def(self) -> Dict[str, Any]:
        """
        转换为LLM Function Calling格式
        
        Returns:
            Dict: 符合OpenAI Function Calling格式的工具定义
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def validate_parameters(self, params: Dict[str, Any]) -> List[str]:
        """
        验证参数是否符合要求
        
        Args:
            params: 待验证的参数字典
            
        Returns:
            List[str]: 错误信息列表，空列表表示验证通过
        """
        errors = []
        
        required = self.parameters.get("required", [])
        properties = self.parameters.get("properties", {})
        
        for req in required:
            if req not in params:
                errors.append(f"缺少必需参数: {req}")
            elif params[req] is None or params[req] == "":
                errors.append(f"参数 {req} 不能为空")
        
        return errors
