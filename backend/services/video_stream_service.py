"""
视频流数据库服务（纯异步版本）
负责视频流的数据库CRUD操作和状态管理
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from utils.timezone_utils import now_isoformat
from sqlalchemy import select, update, delete, func, or_, text

from database.connection import DatabaseManager
from models.video_stream import (
    VideoStreamDB,
    VideoStreamCreate,
    VideoStreamUpdate,
    VideoStreamResponse,
    StreamStatusEnum
)
from models.video_stream_algorithm_config import (
    VideoStreamAlgorithmConfigDB,
    VideoStreamAlgorithmConfigHistoryDB,
    LegacyConfigResponse,
    LegacyTemplateResponse
)

logger = logging.getLogger(__name__)


def _stream_to_response(stream: VideoStreamDB) -> VideoStreamResponse:
    """将数据库模型转换为响应模型"""
    return VideoStreamResponse(
        id=str(stream.id),
        name=stream.name,
        stream_url=stream.stream_url,
        stream_type=stream.stream_type,
        location=stream.location,
        group_name=stream.group_name,
        description=stream.description,
        tags=stream.tags or [],
        status=stream.status,
        created_at=stream.created_at,
        updated_at=stream.updated_at
    )


class VideoStreamService:
    """视频流服务（纯异步版本）"""

    @staticmethod
    async def create_stream(stream_data: VideoStreamCreate) -> VideoStreamResponse:
        """创建视频流记录"""
        async with DatabaseManager.get_session() as session:
            # 检查流地址是否重复
            result = await session.execute(
                select(VideoStreamDB).where(VideoStreamDB.stream_url == stream_data.stream_url)
            )
            existing_stream = result.scalar_one_or_none()
            if existing_stream:
                raise ValueError("视频流地址已存在")

            # 创建数据库记录
            db_stream = VideoStreamDB(
                name=stream_data.name,
                stream_url=stream_data.stream_url,
                stream_type=stream_data.stream_type,
                location=stream_data.location,
                group_name=stream_data.group_name,
                description=stream_data.description,
                tags=stream_data.tags
            )

            session.add(db_stream)
            await session.flush()
            await session.refresh(db_stream)

            return _stream_to_response(db_stream)

    @staticmethod
    async def get_streams(
        page: int = 1,
        page_size: int = 20,
        group_name: Optional[str] = None,
        status: Optional[StreamStatusEnum] = None,
        search: Optional[str] = None
    ) -> List[VideoStreamResponse]:
        """获取视频流列表"""
        async with DatabaseManager.get_session() as session:
            query = select(VideoStreamDB)

            # 添加过滤条件
            conditions = []
            if group_name:
                conditions.append(VideoStreamDB.group_name == group_name)
            if status:
                conditions.append(VideoStreamDB.status == status)
            if search:
                conditions.append(or_(
                    VideoStreamDB.name.ilike(f"%{search}%"),
                    VideoStreamDB.description.ilike(f"%{search}%"),
                    VideoStreamDB.location.ilike(f"%{search}%")
                ))

            if conditions:
                query = query.where(*conditions)

            # 分页和排序
            query = query.order_by(VideoStreamDB.created_at.desc())
            query = query.limit(page_size).offset((page - 1) * page_size)

            result = await session.execute(query)
            streams = result.scalars().all()

            return [_stream_to_response(stream) for stream in streams]

    @staticmethod
    async def get_stream_by_id(stream_id: UUID) -> Optional[VideoStreamResponse]:
        """根据ID获取视频流"""
        async with DatabaseManager.get_session() as session:
            stream = await session.get(VideoStreamDB, stream_id)
            return _stream_to_response(stream) if stream else None

    @staticmethod
    async def update_stream(stream_id: UUID, stream_data: VideoStreamUpdate) -> Optional[VideoStreamResponse]:
        """更新视频流信息"""
        async with DatabaseManager.get_session() as session:
            stream = await session.get(VideoStreamDB, stream_id)
            if not stream:
                return None

            # 更新字段
            update_data = stream_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                setattr(stream, field, value)

            await session.flush()
            await session.refresh(stream)

            return _stream_to_response(stream)

    @staticmethod
    async def delete_stream(stream_id: UUID) -> bool:
        """删除视频流"""
        async with DatabaseManager.get_session() as session:
            result = await session.execute(
                delete(VideoStreamDB).where(VideoStreamDB.id == stream_id)
            )
            return result.rowcount > 0

    @staticmethod
    async def get_streams_count(
        group_name: Optional[str] = None,
        status: Optional[StreamStatusEnum] = None,
        search: Optional[str] = None
    ) -> int:
        """获取视频流总数"""
        async with DatabaseManager.get_session() as session:
            query = select(func.count(VideoStreamDB.id))

            # 添加过滤条件
            conditions = []
            if group_name:
                conditions.append(VideoStreamDB.group_name == group_name)
            if status:
                conditions.append(VideoStreamDB.status == status)
            if search:
                conditions.append(or_(
                    VideoStreamDB.name.ilike(f"%{search}%"),
                    VideoStreamDB.description.ilike(f"%{search}%"),
                    VideoStreamDB.location.ilike(f"%{search}%")
                ))

            if conditions:
                query = query.where(*conditions)

            result = await session.execute(query)
            return result.scalar()

    @staticmethod
    async def update_stream_status(stream_id: UUID, status: StreamStatusEnum) -> bool:
        """更新流状态"""
        async with DatabaseManager.get_session() as session:
            result = await session.execute(
                update(VideoStreamDB)
                .where(VideoStreamDB.id == stream_id)
                .values(status=status)
            )
            return result.rowcount > 0

    @staticmethod
    async def get_streams_by_group(group_name: str) -> List[VideoStreamResponse]:
        """根据分组获取视频流"""
        async with DatabaseManager.get_session() as session:
            result = await session.execute(
                select(VideoStreamDB)
                .where(VideoStreamDB.group_name == group_name)
                .order_by(VideoStreamDB.name)
            )
            streams = result.scalars().all()
            return [_stream_to_response(stream) for stream in streams]

    @staticmethod
    async def configure_analysis_templates(stream_id: str, template_ids: List[str], priority: int = 1, confidence_threshold: float = 0.7) -> bool:
        """配置视频流分析模板"""
        async with DatabaseManager.get_session() as session:
            try:
                # 首先验证视频流是否存在
                stream = await VideoStreamService.get_stream_by_id(UUID(stream_id))
                if not stream:
                    logger.error(f"视频流不存在: {stream_id}")
                    return False

                stream_uuid = UUID(stream_id)

                # 删除该流的所有现有配置（重新配置）
                await session.execute(
                    delete(VideoStreamAlgorithmConfigDB)
                    .where(VideoStreamAlgorithmConfigDB.stream_id == stream_uuid)
                )

                # 批量插入新配置
                new_configs = []
                for template_id in template_ids:
                    # 查询模板的实际名称
                    template_name = await VideoStreamService._get_template_name_by_id(template_id)

                    config = VideoStreamAlgorithmConfigDB(
                        stream_id=stream_uuid,
                        template_id=template_id,
                        template_name=template_name,
                        priority=priority,
                        confidence_threshold=confidence_threshold,
                        is_active=True,
                        created_by="system"
                    )
                    new_configs.append(config)

                session.add_all(new_configs)
                await session.flush()

                logger.info(f"为视频流 {stream_id} ({stream.name}) 配置分析模板:")
                logger.info(f"  - 模板ID列表: {template_ids}")
                logger.info(f"  - 优先级: {priority}")
                logger.info(f"  - 置信度阈值: {confidence_threshold}")
                logger.info(f"  - 已保存到数据库: {len(new_configs)} 个配置")

                return True

            except Exception as e:
                logger.error(f"配置视频流分析模板失败: {str(e)}")
                raise

    @staticmethod
    async def _get_template_name_by_id(template_id: str) -> str:
        """根据模板ID获取模板名称"""
        try:
            async with DatabaseManager.get_session() as session:
                # 查询模板名称
                query = text("""
                SELECT name
                FROM ai_model_configs
                WHERE id = :template_id
                """)
                result = await session.execute(query, {'template_id': template_id})
                row = result.fetchone()

                if row:
                    return row[0]
                else:
                    logger.warning(f"未找到模板ID {template_id} 的名称")
                    return f'未知算法({template_id[:8]})'

        except Exception as e:
            logger.warning(f"获取模板名称失败: {e}")
            return f'未知算法({template_id[:8]})'

    @staticmethod
    async def get_stream_analysis_templates(stream_id: str):
        """获取视频流的分析模板配置"""
        async with DatabaseManager.get_session() as session:
            try:
                # 首先验证视频流是否存在
                stream = await VideoStreamService.get_stream_by_id(UUID(stream_id))
                if not stream:
                    return None

                stream_uuid = UUID(stream_id)

                # 从数据库查询配置信息
                result = await session.execute(
                    select(VideoStreamAlgorithmConfigDB)
                    .where(
                        VideoStreamAlgorithmConfigDB.stream_id == stream_uuid,
                        VideoStreamAlgorithmConfigDB.is_active == True
                    )
                    .order_by(VideoStreamAlgorithmConfigDB.priority.desc(), VideoStreamAlgorithmConfigDB.created_at)
                )
                configs = result.scalars().all()

                if configs:
                    # 构造兼容旧版API的响应格式
                    templates = []
                    for config in configs:
                        templates.append({
                            'id': config.template_id,
                            'template_id': config.template_id,
                            'name': config.template_name,
                            'template_name': config.template_name,
                            'priority': config.priority,
                            'confidence_threshold': config.confidence_threshold,
                            'configured_at': config.created_at.isoformat() if config.created_at else now_isoformat()
                        })

                    return {
                        'success': True,
                        'templates': templates,
                        'stream_id': stream_id,
                        'total': len(templates)
                    }
                else:
                    return {
                        'success': True,
                        'templates': [],
                        'stream_id': stream_id,
                        'total': 0,
                        'message': '暂无配置的分析模板'
                    }

            except Exception as e:
                logger.error(f"获取视频流分析模板失败: {str(e)}")
                return None

    @staticmethod
    async def get_stream_configuration(stream_id: str):
        """获取视频流配置信息"""
        try:
            # 获取流基本信息
            stream = await VideoStreamService.get_stream_by_id(UUID(stream_id))
            if not stream:
                return None

            return {
                'id': str(stream.id),
                'name': stream.name,
                'rtsp_url': stream.stream_url,
                'stream_type': stream.stream_type,
                'status': stream.status.value,
                'location': stream.location,
                'description': stream.description,
                'group_name': stream.group_name
            }

        except Exception as e:
            logger.error(f"获取视频流配置失败: {str(e)}")
            return None

    @staticmethod
    async def get_analysis_templates(stream_id: str):
        """获取分析模板配置 - 兼容方法"""
        return await VideoStreamService.get_stream_analysis_templates(stream_id)
