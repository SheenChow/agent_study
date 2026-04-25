#!/usr/bin/env python3
"""
配置管理模块
负责配置的加载、保存、验证和管理
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from dotenv import load_dotenv


@dataclass
class ProviderConfig:
    """服务商配置"""
    name: str
    api_key: str
    default_model: str
    available_models: List[str]


@dataclass
class AppConfig:
    """应用配置"""
    version: str
    updated_at: str
    current_provider: str
    providers: Dict[str, ProviderConfig]
    system_prompt: str


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG = {
        "version": "1.0",
        "updated_at": "",
        "current_provider": "qwen",
        "providers": {
            "qwen": {
                "name": "阿里云千问",
                "api_key": "",
                "default_model": "qwen-turbo",
                "available_models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-omni-turbo"]
            },
            "openai": {
                "name": "OpenAI",
                "api_key": "",
                "default_model": "gpt-3.5-turbo",
                "available_models": ["gpt-3.5-turbo", "gpt-4", "gpt-4o"]
            }
        },
        "system_prompt": "你是一个智能推理助手。当用户提出问题时，你需要：\n1. 仔细分析问题\n2. 逐步思考解决方法\n3. 给出最终答案"
    }
    
    MODEL_INFO = {
        "qwen": {
            "qwen-turbo": {"name": "千问Turbo", "description": "快速推理，适合日常使用"},
            "qwen-plus": {"name": "千问Plus", "description": "更强能力，适合复杂任务"},
            "qwen-max": {"name": "千问Max", "description": "最强能力，适合专业场景"},
            "qwen-omni-turbo": {"name": "千问Omni Turbo", "description": "多模态模型，支持图文理解"}
        },
        "openai": {
            "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "description": "快速且经济的选择"},
            "gpt-4": {"name": "GPT-4", "description": "高级推理能力"},
            "gpt-4o": {"name": "GPT-4o", "description": "最新多模态模型"}
        }
    }
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认使用 data/config.json
        """
        if config_path is None:
            base_dir = Path(__file__).parent
            self.config_path = base_dir / "data" / "config.json"
        else:
            self.config_path = Path(config_path)
        
        self._config: Optional[AppConfig] = None
        
        base_dir = Path(__file__).parent
        env_dev_path = base_dir / ".env-dev"
        env_path = base_dir / ".env"
        
        if env_dev_path.exists():
            print(f"✅ 从 .env-dev 加载环境变量")
            load_dotenv(env_dev_path)
        elif env_path.exists():
            print(f"✅ 从 .env 加载环境变量")
            load_dotenv(env_path)
        else:
            print("⚠️ 未找到 .env-dev 或 .env 文件，使用默认配置")
    
    def load(self) -> AppConfig:
        """
        加载配置
        
        Returns:
            AppConfig实例
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._config = self._dict_to_config(data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ 配置文件解析错误: {e}，使用默认配置")
                self._config = self._create_default_config()
        else:
            print(f"⚠️ 配置文件不存在: {self.config_path}，使用默认配置")
            self._config = self._create_default_config()
        
        self._load_api_key_from_env()
        return self._config
    
    def save(self, config: AppConfig = None) -> bool:
        """
        保存配置
        
        Args:
            config: 要保存的配置，如果为None则保存当前配置
            
        Returns:
            是否保存成功
        """
        if config is None:
            config = self._config
        
        if config is None:
            return False
        
        config.updated_at = datetime.now().isoformat()
        
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = self._config_to_dict(config)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self._config = config
            return True
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
            return False
    
    def get(self) -> AppConfig:
        """
        获取当前配置
        
        Returns:
            AppConfig实例
        """
        if self._config is None:
            self.load()
        return self._config
    
    def get_current_provider(self) -> ProviderConfig:
        """
        获取当前服务商配置
        
        Returns:
            ProviderConfig实例
        """
        config = self.get()
        return config.providers[config.current_provider]
    
    def get_available_models(self, provider: str = None) -> List[Dict[str, Any]]:
        """
        获取指定服务商的可用模型列表（带详细信息）
        
        Args:
            provider: 服务商ID，如果为None则使用当前服务商
            
        Returns:
            模型信息列表，每个模型包含 id, name, description
        """
        if provider is None:
            provider = self.get().current_provider
        
        provider_config = self.get().providers.get(provider)
        if not provider_config:
            return []
        
        model_info = self.MODEL_INFO.get(provider, {})
        result = []
        
        for model_id in provider_config.available_models:
            info = model_info.get(model_id, {})
            result.append({
                "id": model_id,
                "name": info.get("name", model_id),
                "description": info.get("description", "")
            })
        
        return result
    
    def update_config(self, 
                       provider: str = None,
                       api_key: str = None,
                       model: str = None,
                       system_prompt: str = None) -> Dict[str, Any]:
        """
        更新配置
        
        Args:
            provider: 服务商ID
            api_key: API密钥
            model: 模型名称
            system_prompt: 系统提示词
            
        Returns:
            更新结果字典
        """
        config = self.get()
        errors = {}
        
        if provider:
            if provider not in config.providers:
                errors["provider"] = f"不支持的服务商: {provider}"
            else:
                config.current_provider = provider
        
        if api_key is not None:
            if not api_key.strip() and config.current_provider in config.providers:
                errors["api_key"] = "API Key不能为空"
            else:
                config.providers[config.current_provider].api_key = api_key
        
        if model:
            provider_config = config.providers[config.current_provider]
            if model not in provider_config.available_models:
                errors["model"] = f"不支持的模型: {model}"
            else:
                provider_config.default_model = model
        
        if system_prompt is not None:
            config.system_prompt = system_prompt
        
        if errors:
            return {
                "success": False,
                "error": "配置验证失败",
                "details": errors
            }
        
        if self.save(config):
            return {
                "success": True,
                "message": "配置保存成功"
            }
        else:
            return {
                "success": False,
                "error": "保存配置失败"
            }
    
    def mask_api_key(self, api_key: str) -> str:
        """
        掩码显示API Key
        
        Args:
            api_key: 原始API Key
            
        Returns:
            掩码后的字符串，如 sk-******abc123
        """
        if not api_key:
            return ""
        
        if len(api_key) <= 8:
            return "*" * len(api_key)
        
        prefix = api_key[:6]
        suffix = api_key[-4:]
        return f"{prefix}******{suffix}"
    
    def to_dict(self, mask_sensitive: bool = True) -> Dict[str, Any]:
        """
        转换为字典格式（用于API响应）
        
        Args:
            mask_sensitive: 是否掩码敏感信息
            
        Returns:
            配置字典
        """
        config = self.get()
        provider_config = config.providers[config.current_provider]
        
        api_key = provider_config.api_key
        if mask_sensitive:
            api_key = self.mask_api_key(api_key)
        
        return {
            "provider": config.current_provider,
            "provider_name": provider_config.name,
            "api_key": api_key,
            "model": provider_config.default_model,
            "system_prompt": config.system_prompt
        }
    
    def _create_default_config(self) -> AppConfig:
        """创建默认配置"""
        return self._dict_to_config(self.DEFAULT_CONFIG.copy())
    
    def _dict_to_config(self, data: Dict[str, Any]) -> AppConfig:
        """将字典转换为AppConfig"""
        providers = {}
        for provider_id, provider_data in data.get("providers", {}).items():
            providers[provider_id] = ProviderConfig(
                name=provider_data.get("name", ""),
                api_key=provider_data.get("api_key", ""),
                default_model=provider_data.get("default_model", ""),
                available_models=provider_data.get("available_models", [])
            )
        
        return AppConfig(
            version=data.get("version", "1.0"),
            updated_at=data.get("updated_at", ""),
            current_provider=data.get("current_provider", "qwen"),
            providers=providers,
            system_prompt=data.get("system_prompt", "")
        )
    
    def _config_to_dict(self, config: AppConfig) -> Dict[str, Any]:
        """将AppConfig转换为字典"""
        providers = {}
        for provider_id, provider_config in config.providers.items():
            providers[provider_id] = {
                "name": provider_config.name,
                "api_key": provider_config.api_key,
                "default_model": provider_config.default_model,
                "available_models": provider_config.available_models
            }
        
        return {
            "version": config.version,
            "updated_at": config.updated_at,
            "current_provider": config.current_provider,
            "providers": providers,
            "system_prompt": config.system_prompt
        }
    
    def _load_api_key_from_env(self):
        """从环境变量加载API Key"""
        if self._config is None:
            return
        
        qwen_config = self._config.providers.get("qwen")
        if qwen_config and not qwen_config.api_key:
            env_key = os.getenv("DASHSCOPE_API_KEY", "")
            if env_key:
                qwen_config.api_key = env_key
                print("✅ 从环境变量加载了千问API Key")
        
        openai_config = self._config.providers.get("openai")
        if openai_config and not openai_config.api_key:
            env_key = os.getenv("OPENAI_API_KEY", "")
            if env_key:
                openai_config.api_key = env_key
                print("✅ 从环境变量加载了OpenAI API Key")


_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """获取全局配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load()
    return _config_manager
