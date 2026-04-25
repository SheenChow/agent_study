"""
Agents模块 - 统一的LLM调用接口
"""

from .llm_agent import LLMService, get_llm_service

__all__ = ['LLMService', 'get_llm_service']
