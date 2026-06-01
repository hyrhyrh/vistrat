"""
AI供应商配置服务


"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func
from database.connection import DatabaseManager
from models.ai_provider_config import (
    AIProviderConfigDB, AIProviderConfigCreate, AIProviderConfigUpdate,
    AIProviderConfigResponse, AIProviderSimple
)

logger = logging.getLogger(__name__)


def _db_to_response(db_provider: AIProviderConfigDB) -> AIProviderConfigResponse:
    """将数据库模型转换为响应模型"""
    return AIProviderConfigResponse(
        id=str(db_provider.id),
        provider_name=db_provider.provider_name,
        display_name=db_provider.display_name,
        icon=db_provider.icon,
        description=db_provider.description,
        api_base_url=db_provider.api_base_url,
        api_key=db_provider.api_key,
        api_version=db_provider.api_version,
        available_models=db_provider.available_models,
        default_model=db_provider.default_model,
        max_tokens_limit=db_provider.max_tokens_limit,
        request_headers=db_provider.request_headers,
        request_timeout=db_provider.request_timeout,
        is_active=db_provider.is_active,
        sort_order=db_provider.sort_order,
        extra_config=db_provider.extra_config,
        created_at=db_provider.created_at.isoformat(),
        updated_at=db_provider.updated_at.isoformat()
    )


class AIProviderService:
    """AI供应商配置服务"""

    @staticmethod
    async def create_provider(provider_data: AIProviderConfigCreate) -> AIProviderConfigResponse:
        """创建AI供应商配置"""
        async with DatabaseManager.get_session() as session:
            # 检查供应商名称是否已存在
            stmt = select(AIProviderConfigDB).where(
                AIProviderConfigDB.provider_name == provider_data.provider_name
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                raise ValueError(f"供应商 {provider_data.provider_name} 已存在")

            # 创建新配置
            db_provider = AIProviderConfigDB(**provider_data.model_dump())
            session.add(db_provider)
            await session.flush()
            await session.refresh(db_provider)

            return AIProviderConfigResponse(
                id=str(db_provider.id),
                **provider_data.model_dump(),
                created_at=db_provider.created_at.isoformat(),
                updated_at=db_provider.updated_at.isoformat()
            )

    @staticmethod
    async def get_provider_by_id(provider_id: str) -> Optional[AIProviderConfigResponse]:
        """根据ID获取AI供应商配置"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AIProviderConfigDB).where(AIProviderConfigDB.id == provider_id)
            result = await session.execute(stmt)
            db_provider = result.scalar_one_or_none()

            if not db_provider:
                return None

            return _db_to_response(db_provider)

    @staticmethod
    async def get_provider_by_name(provider_name: str) -> Optional[AIProviderConfigResponse]:
        """根据名称获取AI供应商配置"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AIProviderConfigDB).where(AIProviderConfigDB.provider_name == provider_name)
            result = await session.execute(stmt)
            db_provider = result.scalar_one_or_none()

            if not db_provider:
                return None

            return _db_to_response(db_provider)

    @staticmethod
    async def get_all_providers(
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[AIProviderConfigResponse]:
        """获取所有AI供应商配置"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AIProviderConfigDB)

            if active_only:
                stmt = stmt.where(AIProviderConfigDB.is_active == True)

            stmt = stmt.order_by(AIProviderConfigDB.sort_order, AIProviderConfigDB.created_at)
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            db_providers = result.scalars().all()

            return [_db_to_response(provider) for provider in db_providers]

    @staticmethod
    async def get_simple_providers(active_only: bool = True) -> List[AIProviderSimple]:
        """获取简化的AI供应商信息"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AIProviderConfigDB)

            if active_only:
                stmt = stmt.where(AIProviderConfigDB.is_active == True)

            stmt = stmt.order_by(AIProviderConfigDB.sort_order)

            result = await session.execute(stmt)
            db_providers = result.scalars().all()

            return [
                AIProviderSimple(
                    id=str(provider.id),
                    provider_name=provider.provider_name,
                    display_name=provider.display_name,
                    icon=provider.icon,
                    available_models=provider.available_models,
                    is_active=provider.is_active
                )
                for provider in db_providers
            ]

    @staticmethod
    async def update_provider(provider_id: str, update_data: AIProviderConfigUpdate) -> Optional[AIProviderConfigResponse]:
        """更新AI供应商配置"""
        async with DatabaseManager.get_session() as session:
            # 获取现有配置
            stmt = select(AIProviderConfigDB).where(AIProviderConfigDB.id == provider_id)
            result = await session.execute(stmt)
            db_provider = result.scalar_one_or_none()

            if not db_provider:
                return None

            # 更新字段
            update_dict = update_data.model_dump(exclude_unset=True)
            if update_dict:
                stmt = update(AIProviderConfigDB).where(
                    AIProviderConfigDB.id == provider_id
                ).values(**update_dict)
                await session.execute(stmt)
                await session.flush()
                await session.refresh(db_provider)

            return _db_to_response(db_provider)

    @staticmethod
    async def delete_provider(provider_id: str) -> bool:
        """删除AI供应商配置"""
        async with DatabaseManager.get_session() as session:
            stmt = delete(AIProviderConfigDB).where(AIProviderConfigDB.id == provider_id)
            result = await session.execute(stmt)
            return result.rowcount > 0

    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """获取AI供应商统计信息"""
        async with DatabaseManager.get_session() as session:
            # 总数统计
            total_stmt = select(func.count(AIProviderConfigDB.id))
            total_result = await session.execute(total_stmt)
            total_count = total_result.scalar()

            # 活跃供应商统计
            active_stmt = select(func.count(AIProviderConfigDB.id)).where(
                AIProviderConfigDB.is_active == True
            )
            active_result = await session.execute(active_stmt)
            active_count = active_result.scalar()

            return {
                "total_providers": total_count,
                "active_providers": active_count,
                "inactive_providers": total_count - active_count
            }
