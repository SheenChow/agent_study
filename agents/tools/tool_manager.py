#!/usr/bin/env python3
"""
工具管理器模块
管理所有注册的工具，提供工具查询和执行功能
"""

import json
from typing import Any, Dict, List, Optional, Type

from agents.tools.base_tool import BaseTool, ToolResult, ToolCall, ToolResponse


class ToolManager:
    """
    工具管理器
    负责注册、管理和执行各种工具
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """
        注册工具
        
        Args:
            tool: 工具实例
        """
        if tool.name in self._tools:
            print(f"⚠️  工具 {tool.name} 已存在，将被覆盖")
        self._tools[tool.name] = tool
        print(f"✅ 已注册工具: {tool.name}")
    
    def register_class(self, tool_class: Type[BaseTool]) -> None:
        """
        注册工具类（自动实例化）
        
        Args:
            tool_class: 工具类
        """
        tool = tool_class()
        self.register(tool)
    
    def unregister(self, tool_name: str) -> bool:
        """
        注销工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否成功注销
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            print(f"✅ 已注销工具: {tool_name}")
            return True
        return False
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        Args:
            tool_name: 工具名称
            
        Returns:
            工具实例，如果不存在则返回None
        """
        return self._tools.get(tool_name)
    
    def has_tool(self, tool_name: str) -> bool:
        """
        检查是否有指定工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否存在
        """
        return tool_name in self._tools
    
    def list_tools(self) -> List[str]:
        """
        获取所有已注册的工具名称
        
        Returns:
            工具名称列表
        """
        return list(self._tools.keys())
    
    def get_tools_definition(self) -> List[Dict[str, Any]]:
        """
        获取所有工具的Function Calling定义
        
        Returns:
            工具定义列表，可直接传递给LLM
        """
        return [tool.to_function_def() for tool in self._tools.values()]
    
    def get_tools_description(self) -> str:
        """
        获取所有工具的文本描述（用于系统提示词）
        
        Returns:
            工具描述文本
        """
        descriptions = []
        for name, tool in self._tools.items():
            params = tool.parameters.get("properties", {})
            param_desc = []
            for param_name, param_info in params.items():
                param_desc.append(f"  - {param_name}: {param_info.get('description', '')}")
            
            descriptions.append(
                f"工具名称: {name}\n"
                f"描述: {tool.description}\n"
                f"参数:\n" + "\n".join(param_desc)
            )
        
        return "\n\n".join(descriptions)
    
    def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        执行工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        tool = self._tools.get(tool_name)
        if tool is None:
            return ToolResult(
                success=False,
                content="",
                error=f"未找到工具: {tool_name}"
            )
        
        errors = tool.validate_parameters(kwargs)
        if errors:
            return ToolResult(
                success=False,
                content="",
                error=f"参数验证失败: {'; '.join(errors)}"
            )
        
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"工具执行异常: {str(e)}"
            )
    
    def execute_tool_call(self, tool_call: ToolCall) -> ToolResult:
        """
        执行工具调用
        
        Args:
            tool_call: 工具调用对象
            
        Returns:
            工具执行结果
        """
        return self.execute_tool(tool_call.name, **tool_call.arguments)
    
    def execute_tool_calls(self, tool_calls: List[ToolCall]) -> List[ToolResponse]:
        """
        批量执行工具调用
        
        Args:
            tool_calls: 工具调用列表
            
        Returns:
            工具响应列表，可直接添加到消息历史
        """
        responses = []
        for tool_call in tool_calls:
            result = self.execute_tool_call(tool_call)
            
            response = ToolResponse(
                tool_call_id=tool_call.id,
                name=tool_call.name,
                content=json.dumps(result.to_dict(), ensure_ascii=False) if result.success 
                        else json.dumps({"error": result.error}, ensure_ascii=False)
            )
            responses.append(response)
        
        return responses


_default_tool_manager: Optional[ToolManager] = None


def get_tool_manager() -> ToolManager:
    """
    获取全局工具管理器实例
    
    Returns:
        ToolManager 实例
    """
    global _default_tool_manager
    if _default_tool_manager is None:
        _default_tool_manager = ToolManager()
    return _default_tool_manager


def register_default_tools() -> ToolManager:
    """
    注册默认工具
    
    Returns:
        工具管理器实例
    """
    manager = get_tool_manager()
    
    from agents.tools.web_search_tool import WebSearchTool
    manager.register(WebSearchTool())
    
    return manager
