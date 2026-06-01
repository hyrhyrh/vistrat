"""
AI配置管理器
从数据库读取AI模型配置并管理多厂商调用
纯异步版本


"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select

from database.connection import DatabaseManager
from models.ai_model import AIModelConfigDB
from models.ai_provider_config import AIProviderConfigDB

logger = logging.getLogger(__name__)


class AIConfigManager:
    """AI配置管理器（纯异步版本）"""

    def __init__(self):
        self._config_cache = {}
        self._cache_expire_time = 300  # 5分钟缓存
        self._last_cache_time = 0

    async def get_model_config_by_id(self, model_id: str) -> Optional[Dict[str, Any]]:
        """根据模型ID获取配置"""
        async with DatabaseManager.get_session() as session:
            try:
                # 查询指定ID的模型配置
                result = await session.execute(
                    select(AIModelConfigDB).where(
                        AIModelConfigDB.id == model_id,
                        AIModelConfigDB.status == 'active'
                    )
                )
                config = result.scalar_one_or_none()

                if config:
                    return await self._build_provider_config(config)
                else:
                    logger.warning(f"未找到模型配置: {model_id}")
                    return None
            except Exception as e:
                logger.error(f"获取模型配置失败 {model_id}: {e}")
                return None

    async def get_model_config_by_provider(self, provider: str) -> Optional[Dict[str, Any]]:
        """根据提供商获取默认配置"""
        async with DatabaseManager.get_session() as session:
            try:
                # 查询指定提供商的活跃模型配置
                result = await session.execute(
                    select(AIModelConfigDB).where(
                        AIModelConfigDB.provider == provider,
                        AIModelConfigDB.status == 'active'
                    ).order_by(AIModelConfigDB.created_at.desc())
                )
                config = result.scalar_one_or_none()

                if config:
                    return await self._build_provider_config(config)
                else:
                    logger.warning(f"未找到提供商配置: {provider}")
                    return None
            except Exception as e:
                logger.error(f"获取提供商配置失败 {provider}: {e}")
                return None

    async def get_all_active_configs(self) -> Dict[str, Dict[str, Any]]:
        """获取所有活跃的模型配置"""
        async with DatabaseManager.get_session() as session:
            try:
                result = await session.execute(
                    select(AIModelConfigDB).where(
                        AIModelConfigDB.status == 'active'
                    ).order_by(AIModelConfigDB.provider, AIModelConfigDB.created_at.desc())
                )
                configs = result.scalars().all()

                config_dict = {}
                for config in configs:
                    provider_config = await self._build_provider_config(config)
                    config_dict[str(config.id)] = provider_config

                return config_dict
            except Exception as e:
                logger.error(f"获取所有配置失败: {e}")
                return {}

    async def _build_provider_config(self, config: AIModelConfigDB) -> Dict[str, Any]:
        """构建提供商配置字典"""
        try:
            # 解析额外配置
            extra_config = config.extra_config or {}

            # 首先尝试从ai_provider_configs表获取API配置
            provider_api_config = await self._get_provider_api_config(config.provider)

            # 构建基础配置
            provider_config = {
                'id': str(config.id),
                'name': config.name,
                'provider': config.provider,
                'model_name': config.model_name,
                'model_type': config.model_type,
                'api_key': provider_api_config.get('api_key', extra_config.get('api_key', '')),
                'base_url': provider_api_config.get('api_base_url', extra_config.get('base_url', '')),
                'temperature': config.temperature,
                'top_p': config.top_p,
                'max_tokens': config.max_tokens,
                'confidence_threshold': config.confidence_threshold,
                'system_prompt': config.system_prompt,
                'user_prompt': config.user_prompt,
                'status': config.status
            }

            # 添加提供商特定配置（如果没有从数据库获取到，使用默认值）
            if not provider_config['base_url']:
                if config.provider.lower() in ['qwen', 'qwen-vl']:
                    provider_config['base_url'] = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
                elif config.provider.lower() in ['openai', 'gpt']:
                    provider_config['base_url'] = 'https://api.openai.com/v1/chat/completions'
                elif config.provider.lower() == 'moonshot':
                    provider_config['base_url'] = 'https://api.moonshot.cn/v1/chat/completions'
                elif config.provider.lower() == 'claude':
                    provider_config['base_url'] = 'https://api.anthropic.com/v1/messages'

            # 特殊标记
            if config.provider.lower() in ['lanyi', 'blue']:
                provider_config['needs_user_agent'] = True  # 蓝翼模型需要特殊User-Agent

            return provider_config

        except Exception as e:
            logger.error(f"构建提供商配置失败: {e}")
            return {}

    async def _get_provider_api_config(self, provider_name: str) -> Dict[str, Any]:
        """从ai_provider_configs表获取API配置"""
        async with DatabaseManager.get_session() as session:
            try:
                result = await session.execute(
                    select(AIProviderConfigDB).where(
                        AIProviderConfigDB.provider_name == provider_name,
                        AIProviderConfigDB.is_active == True
                    )
                )
                provider_config = result.scalar_one_or_none()

                if provider_config:
                    return {
                        'api_base_url': provider_config.api_base_url,
                        'api_key': provider_config.api_key,
                        'api_version': provider_config.api_version,
                        'request_headers': provider_config.request_headers,
                        'request_timeout': provider_config.request_timeout
                    }
                else:
                    logger.warning(f"未找到提供商配置: {provider_name}")
                    return {}
            except Exception as e:
                logger.error(f"获取提供商API配置失败 {provider_name}: {e}")
                return {}

    async def get_default_fallback_config(self) -> Dict[str, Any]:
        """获取默认后备配置"""
        return {
            'id': 'fallback',
            'name': '默认模型',
            'provider': 'qwen',
            'model_name': 'qwen-vl-plus',
            'model_type': 'vision',
            'api_key': '',
            'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
            'temperature': 0.2,
            'top_p': 0.7,
            'max_tokens': 1000,
            'confidence_threshold': 0.8,
            'system_prompt': '你是一个智能视觉分析AI助手。',
            'user_prompt': '请分析这张图片中是否存在异常情况。',
            'status': 'active'
        }

    async def update_model_test_count(self, model_id: str, success: bool):
        """更新模型测试计数"""
        async with DatabaseManager.get_session() as session:
            try:
                # 获取配置
                result = await session.execute(
                    select(AIModelConfigDB).where(AIModelConfigDB.id == model_id)
                )
                config = result.scalar_one_or_none()

                if config:
                    config.test_count += 1
                    if success:
                        config.success_count += 1

                    await session.commit()
                    logger.debug(f"更新模型 {model_id} 测试计数: {config.test_count}/{config.success_count}")
            except Exception as e:
                logger.error(f"更新模型测试计数失败 {model_id}: {e}")


# 全局实例
ai_config_manager = AIConfigManager()
