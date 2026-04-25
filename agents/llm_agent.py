#!/usr/bin/env python3
"""
LLM Agent 模块
统一的大模型调用接口，支持多服务商和流式输出
"""

import json
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Generator, AsyncGenerator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """聊天消息"""
    role: str
    content: str


@dataclass
class ChatResult:
    """聊天结果"""
    success: bool
    content: str
    model: str
    usage: Dict[str, int]
    error_message: Optional[str] = None


@dataclass
class StreamChunk:
    """流式输出块"""
    type: str
    content: str
    done: bool = False
    usage: Optional[Dict[str, int]] = None


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
            **kwargs: 其他参数
            
        Returns:
            非流式返回 ChatResult，流式返回 Generator[StreamChunk, None, None]
        """
        client = self._get_client()
        
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
            response = client.Generation.call(
                model=model,
                messages=messages,
                result_format="message"
            )
            
            if response.status_code == 200:
                content = response.output.choices[0]["message"]["content"]
                usage = {
                    "input_tokens": getattr(response.usage, 'input_tokens', 0),
                    "output_tokens": getattr(response.usage, 'output_tokens', 0),
                    "total_tokens": getattr(response.usage, 'total_tokens', 0)
                }
                
                return ChatResult(
                    success=True,
                    content=content,
                    model=model,
                    usage=usage
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
