#!/usr/bin/env python3
"""
LLM Agent 模块
统一的大模型调用接口，支持多服务商、流式输出和工具调用
"""

import json
import os
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Generator, Callable
from dataclasses import dataclass, field


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None


@dataclass
class ChatResult:
    """聊天结果"""
    success: bool
    content: str
    model: str
    usage: Dict[str, int]
    error_message: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


@dataclass
class StreamChunk:
    """流式输出块"""
    type: str
    content: str
    done: bool = False
    usage: Optional[Dict[str, int]] = None
    tool_call: Optional[Dict[str, Any]] = None


@dataclass
class ToolCallInfo:
    """工具调用信息"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class AgentStep:
    """Agent执行步骤"""
    step_type: str
    content: str
    tool_name: Optional[str] = None
    tool_arguments: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None
    is_final: bool = False


@dataclass
class AgentResult:
    """Agent执行结果"""
    success: bool
    final_answer: str
    steps: List[AgentStep] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0})
    error_message: Optional[str] = None


class BaseLLMService(ABC):
    """LLM服务抽象基类"""
    
    @abstractmethod
    def chat(self, 
             messages: List[ChatMessage],
             model: str = None,
             stream: bool = False,
             **kwargs) -> Any:
        """
        发起聊天请求
        
        Args:
            messages: 消息列表
            model: 模型名称
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Returns:
            非流式返回 ChatResult，流式返回 Generator[StreamChunk, None, None]
        """
        pass
    
    @abstractmethod
    def validate_api_key(self, api_key: str) -> bool:
        """
        验证API Key是否有效
        
        Args:
            api_key: API密钥
            
        Returns:
            是否有效
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            模型ID列表
        """
        pass


class QwenService(BaseLLMService):
    """阿里云千问服务"""
    
    def __init__(self, api_key: str = None):
        """
        初始化千问服务
        
        Args:
            api_key: API密钥，如果不提供则从环境变量读取
        """
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self._client = None
    
    def _get_client(self):
        """获取DashScope客户端"""
        if self._client is None:
            import dashscope
            dashscope.api_key = self.api_key
            self._client = dashscope
        return self._client
    
    def chat(self,
             messages: List[ChatMessage],
             model: str = "qwen-turbo",
             stream: bool = False,
             system_prompt: str = None,
             **kwargs) -> Any:
        """
        发起聊天请求
        
        Args:
            messages: 消息列表
            model: 模型名称，默认 qwen-turbo
            stream: 是否流式输出
            system_prompt: 系统提示词
            **kwargs: 其他参数（如 tools, tool_choice）
            
        Returns:
            非流式返回 ChatResult，流式返回 Generator[StreamChunk, None, None]
        """
        client = self._get_client()
        
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            msg_dict = {"role": msg.role}
            
            if msg.content is not None:
                msg_dict["content"] = msg.content
            
            if msg.tool_calls:
                msg_dict["tool_calls"] = msg.tool_calls
            
            if msg.tool_call_id:
                msg_dict["tool_call_id"] = msg.tool_call_id
            
            if msg.name:
                msg_dict["name"] = msg.name
            
            formatted_messages.append(msg_dict)
        
        if stream:
            return self._chat_stream(formatted_messages, model, **kwargs)
        else:
            return self._chat_non_stream(formatted_messages, model, **kwargs)
    
    def _chat_non_stream(self, 
                          messages: List[Dict[str, Any]],
                          model: str,
                          **kwargs) -> ChatResult:
        """非流式聊天"""
        try:
            client = self._get_client()
            
            call_kwargs = {
                "model": model,
                "messages": messages,
                "result_format": "message"
            }
            
            tools = kwargs.get("tools")
            if tools:
                call_kwargs["tools"] = tools
            
            tool_choice = kwargs.get("tool_choice")
            if tool_choice:
                call_kwargs["tool_choice"] = tool_choice
            
            response = client.Generation.call(**call_kwargs)
            
            if response.status_code == 200:
                message = response.output.choices[0]["message"]
                content = message.get("content", "")
                tool_calls = message.get("tool_calls")
                
                usage = {
                    "input_tokens": getattr(response.usage, 'input_tokens', 0),
                    "output_tokens": getattr(response.usage, 'output_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0)
                }
                
                return ChatResult(
                    success=True,
                    content=content,
                    model=model,
                    usage=usage,
                    tool_calls=tool_calls
                )
            else:
                return ChatResult(
                    success=False,
                    content="",
                    model=model,
                    usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                    error_message=f"API错误: {response.code} - {response.message}"
                )
                
        except Exception as e:
            return ChatResult(
                success=False,
                content="",
                model=model,
                usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                error_message=f"调用失败: {str(e)}"
            )
    
    def _chat_stream(self,
                     messages: List[Dict[str, str]],
                     model: str,
                     **kwargs) -> Generator[StreamChunk, None, None]:
        """流式聊天"""
        try:
            client = self._get_client()
            
            responses = client.Generation.call(
                model=model,
                messages=messages,
                result_format="message",
                stream=True
            )
            
            full_content = ""
            total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            
            for response in responses:
                if response.status_code == 200:
                    if hasattr(response, 'output') and response.output:
                        choices = response.output.choices
                        if choices and len(choices) > 0:
                            message = choices[0].get("message", {})
                            content = message.get("content", "")
                            
                            if content:
                                delta = content[len(full_content):]
                                if delta:
                                    full_content = content
                                    yield StreamChunk(
                                        type="text",
                                        content=delta,
                                        done=False
                                    )
                    
                    if hasattr(response, 'usage') and response.usage:
                        total_usage = {
                            "input_tokens": getattr(response.usage, 'input_tokens', 0),
                            "output_tokens": getattr(response.usage, 'output_tokens', 0),
                            "total_tokens": getattr(response.usage, 'total_tokens', 0)
                        }
                else:
                    yield StreamChunk(
                        type="error",
                        content=f"API错误: {response.code} - {response.message}",
                        done=True
                    )
                    return
            
            yield StreamChunk(
                type="done",
                content="",
                done=True,
                usage=total_usage
            )
            
        except Exception as e:
            yield StreamChunk(
                type="error",
                content=f"调用失败: {str(e)}",
                done=True
            )
    
    def validate_api_key(self, api_key: str) -> bool:
        """验证API Key是否有效"""
        try:
            import dashscope
            dashscope.api_key = api_key
            
            messages = [{"role": "user", "content": "ping"}]
            response = dashscope.Generation.call(
                model="qwen-turbo",
                messages=messages,
                result_format="message",
                max_tokens=10
            )
            
            return response.status_code == 200
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "qwen-turbo",
            "qwen-plus", 
            "qwen-max",
            "qwen-omni-turbo"
        ]


class OpenAIService(BaseLLMService):
    """OpenAI服务（预留实现）"""
    
    def __init__(self, api_key: str = None):
        """
        初始化OpenAI服务
        
        Args:
            api_key: API密钥
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self._client = None
    
    def _get_client(self):
        """获取OpenAI客户端"""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    def chat(self,
             messages: List[ChatMessage],
             model: str = "gpt-3.5-turbo",
             stream: bool = False,
             system_prompt: str = None,
             **kwargs) -> Any:
        """发起聊天请求"""
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        
        for msg in messages:
            formatted_messages.append({"role": msg.role, "content": msg.content})
        
        if stream:
            return self._chat_stream(formatted_messages, model, **kwargs)
        else:
            return self._chat_non_stream(formatted_messages, model, **kwargs)
    
    def _chat_non_stream(self,
                          messages: List[Dict[str, str]],
                          model: str,
                          **kwargs) -> ChatResult:
        """非流式聊天"""
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=model,
                messages=messages
            )
            
            content = response.choices[0].message.content
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            return ChatResult(
                success=True,
                content=content,
                model=model,
                usage=usage
            )
            
        except Exception as e:
            return ChatResult(
                success=False,
                content="",
                model=model,
                usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                error_message=f"调用失败: {str(e)}"
            )
    
    def _chat_stream(self,
                     messages: List[Dict[str, str]],
                     model: str,
                     **kwargs) -> Generator[StreamChunk, None, None]:
        """流式聊天"""
        try:
            client = self._get_client()
            
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True
            )
            
            full_content = ""
            total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_content += delta.content
                        yield StreamChunk(
                            type="text",
                            content=delta.content,
                            done=False
                        )
                
                if hasattr(chunk, 'usage') and chunk.usage:
                    total_usage = {
                        "input_tokens": getattr(chunk.usage, 'prompt_tokens', 0),
                        "output_tokens": getattr(chunk.usage, 'completion_tokens', 0),
                        "total_tokens": getattr(chunk.usage, 'total_tokens', 0)
                    }
            
            yield StreamChunk(
                type="done",
                content="",
                done=True,
                usage=total_usage
            )
            
        except Exception as e:
            yield StreamChunk(
                type="error",
                content=f"调用失败: {str(e)}",
                done=True
            )
    
    def validate_api_key(self, api_key: str) -> bool:
        """验证API Key是否有效"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            client.models.list()
            return True
        except Exception:
            return False
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return [
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4o"
        ]


class LLMService:
    """统一的LLM服务工厂"""
    
    _services: Dict[str, BaseLLMService] = {}
    
    @classmethod
    def get_service(cls, provider: str, api_key: str = None) -> BaseLLMService:
        """
        获取指定服务商的LLM服务实例
        
        Args:
            provider: 服务商ID ('qwen' 或 'openai')
            api_key: API密钥
            
        Returns:
            LLM服务实例
        """
        cache_key = f"{provider}:{api_key[:8] if api_key else 'default'}"
        
        if cache_key not in cls._services:
            if provider == "qwen":
                cls._services[cache_key] = QwenService(api_key)
            elif provider == "openai":
                cls._services[cache_key] = OpenAIService(api_key)
            else:
                raise ValueError(f"不支持的服务商: {provider}")
        
        return cls._services[cache_key]
    
    @classmethod
    def clear_cache(cls):
        """清除服务缓存"""
        cls._services.clear()


def get_llm_service(provider: str = "qwen", api_key: str = None) -> BaseLLMService:
    """
    便捷函数：获取LLM服务
    
    Args:
        provider: 服务商ID
        api_key: API密钥
        
    Returns:
        LLM服务实例
    """
    return LLMService.get_service(provider, api_key)


DEFAULT_SYSTEM_PROMPT_WITH_TOOLS = """你是一个智能推理助手，可以使用工具来获取实时信息。

使用规则：
1. 对于时效性问题（如新闻、天气、实时数据、当前事件等），请先使用 web_search 工具搜索最新信息
2. 对于常识性问题或历史知识，可以直接回答，不需要使用工具
3. 调用工具时，请严格按照工具参数要求传递参数
4. 工具返回结果后，根据结果生成最终回答
5. 如果使用了工具，请在回答开头注明"[已搜索]"

回答风格：
- 简洁明了
- 逻辑清晰
- 引用搜索结果中的信息来回答问题
"""


class AgentWithTools:
    """
    带工具能力的Agent
    实现 ReAct 模式：推理-行动-观察 循环
    """
    
    def __init__(self, 
                 llm_service: BaseLLMService,
                 model: str = "qwen-turbo",
                 system_prompt: str = None,
                 tools: List[Any] = None,
                 tool_manager: Any = None):
        """
        初始化带工具能力的Agent
        
        Args:
            llm_service: LLM服务实例
            model: 模型名称
            system_prompt: 系统提示词
            tools: 工具列表（BaseTool实例）
            tool_manager: 工具管理器实例
        """
        self.llm_service = llm_service
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT_WITH_TOOLS
        
        if tool_manager:
            self.tool_manager = tool_manager
        else:
            from agents.tools.tool_manager import ToolManager
            self.tool_manager = ToolManager()
            if tools:
                for tool in tools:
                    self.tool_manager.register(tool)
        
        self.max_iterations = 5
        self.current_iteration = 0
    
    def chat(self, 
             user_message: str,
             history: List[ChatMessage] = None,
             stream: bool = False,
             step_callback: Callable[[AgentStep], None] = None) -> Any:
        """
        执行对话（带工具调用能力）
        
        Args:
            user_message: 用户消息
            history: 对话历史
            stream: 是否流式输出
            step_callback: 步骤回调函数，用于通知执行进度
            
        Returns:
            非流式返回 AgentResult，流式返回 Generator[StreamChunk, None, None]
        """
        messages = history.copy() if history else []
        messages.append(ChatMessage(role="user", content=user_message))
        
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        steps = []
        
        for iteration in range(self.max_iterations):
            self.current_iteration = iteration + 1
            
            tools_def = self.tool_manager.get_tools_definition()
            
            result = self.llm_service.chat(
                messages=messages,
                model=self.model,
                stream=False,
                system_prompt=self.system_prompt,
                tools=tools_def
            )
            
            total_usage["input_tokens"] += result.usage.get("input_tokens", 0)
            total_usage["output_tokens"] += result.usage.get("output_tokens", 0)
            total_usage["total_tokens"] += result.usage.get("total_tokens", 0)
            
            if result.tool_calls:
                assistant_msg = ChatMessage(
                    role="assistant",
                    content=result.content,
                    tool_calls=result.tool_calls
                )
                messages.append(assistant_msg)
                
                for tool_call_data in result.tool_calls:
                    try:
                        tool_call = ToolCallInfo(
                            id=tool_call_data.get("id", str(uuid.uuid4())),
                            name=tool_call_data.get("function", {}).get("name", ""),
                            arguments=json.loads(tool_call_data.get("function", {}).get("arguments", "{}"))
                        )
                        
                        step = AgentStep(
                            step_type="tool_call",
                            content=f"正在调用工具: {tool_call.name}",
                            tool_name=tool_call.name,
                            tool_arguments=tool_call.arguments
                        )
                        steps.append(step)
                        if step_callback:
                            step_callback(step)
                        
                        tool_result = self.tool_manager.execute_tool(
                            tool_call.name,
                            **tool_call.arguments
                        )
                        
                        step = AgentStep(
                            step_type="tool_result",
                            content=f"工具执行完成: {tool_call.name}",
                            tool_name=tool_call.name,
                            tool_result=tool_result.content if tool_result.success else tool_result.error
                        )
                        steps.append(step)
                        if step_callback:
                            step_callback(step)
                        
                        tool_msg = ChatMessage(
                            role="tool",
                            content=tool_result.content if tool_result.success else json.dumps({"error": tool_result.error}),
                            tool_call_id=tool_call.id,
                            name=tool_call.name
                        )
                        messages.append(tool_msg)
                        
                    except Exception as e:
                        error_msg = f"工具调用处理失败: {str(e)}"
                        step = AgentStep(
                            step_type="error",
                            content=error_msg
                        )
                        steps.append(step)
                        if step_callback:
                            step_callback(step)
                        
                        tool_msg = ChatMessage(
                            role="tool",
                            content=json.dumps({"error": error_msg}),
                            tool_call_id=tool_call_data.get("id", ""),
                            name=tool_call_data.get("function", {}).get("name", "")
                        )
                        messages.append(tool_msg)
                
                continue
            
            if result.content:
                final_step = AgentStep(
                    step_type="final_answer",
                    content=result.content,
                    is_final=True
                )
                steps.append(final_step)
                if step_callback:
                    step_callback(final_step)
                
                return AgentResult(
                    success=True,
                    final_answer=result.content,
                    steps=steps,
                    usage=total_usage
                )
        
        return AgentResult(
            success=False,
            final_answer="",
            steps=steps,
            usage=total_usage,
            error_message=f"达到最大迭代次数 ({self.max_iterations})，无法完成任务"
        )
    
    def chat_stream(self,
                    user_message: str,
                    history: List[ChatMessage] = None,
                    step_callback: Callable[[AgentStep], None] = None) -> Generator[StreamChunk, None, None]:
        """
        流式对话（带工具调用能力）
        
        Args:
            user_message: 用户消息
            history: 对话历史
            step_callback: 步骤回调函数
            
        Yields:
            StreamChunk: 流式输出块
        """
        messages = history.copy() if history else []
        
        result = self.chat(
            user_message=user_message,
            history=history,
            stream=False,
            step_callback=step_callback
        )
        
        if result.success:
            for char in result.final_answer:
                yield StreamChunk(
                    type="text",
                    content=char,
                    done=False
                )
            
            yield StreamChunk(
                type="done",
                content="",
                done=True,
                usage=result.usage
            )
        else:
            yield StreamChunk(
                type="error",
                content=result.error_message or "执行失败",
                done=True
            )
