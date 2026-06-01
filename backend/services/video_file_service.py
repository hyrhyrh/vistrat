"""
视频文件数据库服务
负责视频文件的数据库CRUD操作


"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, update, delete, func, or_

from database.connection import DatabaseManager
from models.video_file import (
    VideoFileDB, VideoFileCreate, VideoFileUpdate, VideoFileResponse,
    VideoAnalysisTemplateCreate, VideoStatusEnum
)
from models.video_analysis_template import VideoAnalysisTemplateDB

logger = logging.getLogger(__name__)


class VideoFileService:
    """视频文件服务（纯异步版本）"""

    @staticmethod
    def _db_to_response(db_video: VideoFileDB) -> VideoFileResponse:
        """将数据库对象转换为响应模型"""
        video_dict = {
            "id": str(db_video.id),
            "name": db_video.name,
            "original_filename": db_video.original_filename,
            "file_path": db_video.file_path,
            "thumbnail_path": db_video.thumbnail_path,
            "file_size": db_video.file_size,
            "duration": db_video.duration,
            "fps": db_video.fps,
            "width": db_video.width,
            "height": db_video.height,
            "format": db_video.format,
            "status": db_video.status.value if hasattr(db_video.status, 'value') else str(db_video.status),
            "tags": db_video.tags or [],
            "description": db_video.description,
            "analysis_progress": db_video.analysis_progress,
            "analyzed_at": db_video.analyzed_at,
            "total_alerts": db_video.total_alerts,
            "last_alert_at": db_video.last_alert_at,
            "created_at": db_video.created_at,
            "updated_at": db_video.updated_at
        }
        return VideoFileResponse(**video_dict)

    @staticmethod
    async def create_video(video_data: VideoFileCreate) -> VideoFileResponse:
        """创建视频记录"""
        async with DatabaseManager.get_session() as session:
            db_video = VideoFileDB(
                name=video_data.name,
                original_filename=video_data.original_filename,
                file_path=video_data.file_path,
                thumbnail_path=video_data.thumbnail_path,
                description=video_data.description,
                tags=video_data.tags,
                file_size=video_data.file_size,
                duration=video_data.duration,
                fps=video_data.fps,
                width=video_data.width,
                height=video_data.height,
                format=video_data.format,
                status=video_data.status if video_data.status else VideoStatusEnum.PENDING
            )

            session.add(db_video)
            await session.flush()
            await session.refresh(db_video)

            return VideoFileService._db_to_response(db_video)

    @staticmethod
    async def get_video_by_id(video_id: str) -> Optional[VideoFileResponse]:
        """根据ID获取视频信息"""
        async with DatabaseManager.get_session() as session:
            stmt = select(VideoFileDB).where(VideoFileDB.id == UUID(video_id))
            result = await session.execute(stmt)
            db_video = result.scalar_one_or_none()

            if db_video:
                return VideoFileService._db_to_response(db_video)
            return None

    @staticmethod
    async def get_video_by_original_filename(filename: str) -> Optional[VideoFileResponse]:
        """根据原始文件名获取视频信息"""
        async with DatabaseManager.get_session() as session:
            stmt = (select(VideoFileDB)
                   .where(VideoFileDB.original_filename == filename)
                   .order_by(VideoFileDB.created_at.desc())
                   .limit(1))
            result = await session.execute(stmt)
            db_video = result.scalar_one_or_none()

            if db_video:
                return VideoFileService._db_to_response(db_video)
            return None

    @staticmethod
    async def get_videos_with_search(
        search_name: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[VideoFileResponse]:
        """搜索视频列表"""
        async with DatabaseManager.get_session() as session:
            stmt = select(VideoFileDB).where(VideoFileDB.status != VideoStatusEnum.DELETED)

            # 添加搜索条件
            if search_name:
                stmt = stmt.where(
                    or_(
                        VideoFileDB.name.ilike(f"%{search_name}%"),
                        VideoFileDB.original_filename.ilike(f"%{search_name}%")
                    )
                )

            if status:
                # 验证status是否为有效的枚举值
                try:
                    status_enum = VideoStatusEnum(status)
                    stmt = stmt.where(VideoFileDB.status == status_enum)
                except ValueError:
                    # 如果status无效，记录警告但继续查询（忽略无效的status过滤）
                    logger.warning(f"无效的视频状态值: {status}，已忽略此过滤条件")
                    pass

            if tags:
                # PostgreSQL数组包含查询
                stmt = stmt.where(VideoFileDB.tags.op("@>")(tags))

            # 排序和分页
            stmt = stmt.order_by(VideoFileDB.created_at.desc()).limit(limit).offset(offset)

            result = await session.execute(stmt)
            db_videos = result.scalars().all()

            return [VideoFileService._db_to_response(video) for video in db_videos]

    @staticmethod
    async def update_video(video_id: str, update_data) -> Optional[VideoFileResponse]:
        """更新视频信息"""
        async with DatabaseManager.get_session() as session:
            # 构建更新数据
            update_values = {}

            # 支持字典和Pydantic模型
            if isinstance(update_data, dict):
                items = update_data.items()
            else:
                items = update_data.dict(exclude_unset=True).items()

            for field, value in items:
                if value is not None:
                    update_values[field] = value

            if not update_values:
                # 没有更新内容，直接返回当前数据
                stmt = select(VideoFileDB).where(VideoFileDB.id == UUID(video_id))
                result = await session.execute(stmt)
                db_video = result.scalar_one_or_none()
                if db_video:
                    return VideoFileService._db_to_response(db_video)
                return None

            # 执行更新
            stmt = (
                update(VideoFileDB)
                .where(VideoFileDB.id == UUID(video_id))
                .values(**update_values)
                .returning(VideoFileDB)
            )

            result = await session.execute(stmt)
            updated_video = result.scalar_one_or_none()

            if updated_video:
                return VideoFileService._db_to_response(updated_video)
            return None

    @staticmethod
    async def update_video_status(video_id: str, status: VideoStatusEnum) -> bool:
        """更新视频状态"""
        from models.video_file import VideoFileUpdate
        update_data = VideoFileUpdate(status=status)
        result = await VideoFileService.update_video(video_id, update_data)
        return result is not None

    @staticmethod
    async def delete_video(video_id: str) -> bool:
        """删除视频记录（软删除）"""
        async with DatabaseManager.get_session() as session:
            # 软删除：更新状态为DELETED
            stmt = (
                update(VideoFileDB)
                .where(VideoFileDB.id == UUID(video_id))
                .values(status=VideoStatusEnum.DELETED)
            )

            result = await session.execute(stmt)
            return result.rowcount > 0

    @staticmethod
    async def get_video_statistics() -> Dict[str, Any]:
        """获取视频统计信息"""
        async with DatabaseManager.get_session() as session:
            # 总数统计
            total_count = await session.scalar(
                select(func.count()).select_from(VideoFileDB)
                .where(VideoFileDB.status != VideoStatusEnum.DELETED)
            )

            # 按状态统计
            status_stats = await session.execute(
                select(VideoFileDB.status, func.count())
                .where(VideoFileDB.status != VideoStatusEnum.DELETED)
                .group_by(VideoFileDB.status)
            )

            status_counts = {status.value: 0 for status in VideoStatusEnum if status != VideoStatusEnum.DELETED}
            for status, count in status_stats:
                status_counts[status.value] = count

            # 存储使用统计
            storage_usage = await session.scalar(
                select(func.sum(VideoFileDB.file_size))
                .where(VideoFileDB.status != VideoStatusEnum.DELETED)
            ) or 0

            return {
                'total': total_count,
                'by_status': status_counts,
                'storage_usage_bytes': storage_usage,
                'storage_usage_gb': round(storage_usage / (1024**3), 2)
            }

    @staticmethod
    async def configure_analysis_templates(
        video_id: str,
        ai_model_config_ids: List[str],
        detection_type_codes: List[str] = []
    ) -> bool:
        """
        配置视频分析模板（支持复合检测）

        Args:
            video_id: 视频ID
            ai_model_config_ids: AI模型配置ID列表
            detection_type_codes: 检测类型编码列表（复合检测），默认为空

        Returns:
            是否配置成功

        行为：
            - 如果detection_type_codes为空：为每个AI模型创建一个template（向后兼容）
            - 如果detection_type_codes不为空：使用第一个AI模型，为每个detection_type创建一个template
        """
        from services.ai_model_service import AIModelService

        async with DatabaseManager.get_session() as session:
            # 删除现有的视频分析模板配置
            await session.execute(
                delete(VideoAnalysisTemplateDB)
                .where(VideoAnalysisTemplateDB.video_id == UUID(video_id))
            )

            # 获取第一个AI模型配置（用于复合检测）
            if not ai_model_config_ids:
                logger.warning(f"未提供AI模型配置，无法配置分析模板")
                return False

            ai_config = await AIModelService.get_config_by_id(ai_model_config_ids[0])
            if not ai_config:
                logger.warning(f"找不到AI模型配置: {ai_model_config_ids[0]}")
                return False

            # 合并系统提示词和用户提示词作为基础prompt_content
            base_prompt_content = ""
            if ai_config.system_prompt:
                base_prompt_content += ai_config.system_prompt
            if ai_config.user_prompt:
                if base_prompt_content:
                    base_prompt_content += "\n\n"
                base_prompt_content += ai_config.user_prompt
            if not base_prompt_content:
                base_prompt_content = "请分析这张图片的内容。"

            # 分支处理：复合检测 vs 传统模式
            if detection_type_codes:
                # 复合检测模式：为每个detection_type创建一个template
                from services.video_analysis_template_service import video_analysis_template_service

                for i, type_code in enumerate(detection_type_codes):
                    # 获取detection_type信息
                    detection_type = await video_analysis_template_service.get_detection_type_by_code(type_code)

                    if not detection_type:
                        logger.warning(f"未找到检测类型: {type_code}")
                        continue

                    template = VideoAnalysisTemplateDB(
                        video_id=UUID(video_id),
                        template_id=UUID(ai_model_config_ids[0]),  # 使用AI配置ID作为模板引用
                        template_name=ai_config.name,
                        name=detection_type['name'],  # 使用检测类型名称
                        category=detection_type['category'],
                        description=detection_type['description'],
                        prompt_content=base_prompt_content,  # 使用AI模型的prompt
                        priority=i + 1,
                        enabled=True,
                        analysis_status='ready',
                        detection_type_code=type_code  # 关键：关联检测类型
                    )
                    session.add(template)

                logger.info(
                    f"为视频 {video_id} 配置了复合检测: "
                    f"1个AI模型({ai_config.name}), {len(detection_type_codes)}个检测类型"
                )

            else:
                # 传统模式：为每个AI模型创建一个template（向后兼容）
                for i, config_id in enumerate(ai_model_config_ids):
                    ai_cfg = await AIModelService.get_config_by_id(config_id)
                    if not ai_cfg:
                        logger.warning(f"找不到AI模型配置: {config_id}")
                        continue

                    # 重新构建prompt
                    prompt_content = ""
                    if ai_cfg.system_prompt:
                        prompt_content += ai_cfg.system_prompt
                    if ai_cfg.user_prompt:
                        if prompt_content:
                            prompt_content += "\n\n"
                        prompt_content += ai_cfg.user_prompt
                    if not prompt_content:
                        prompt_content = "请分析这张图片的内容。"

                    template = VideoAnalysisTemplateDB(
                        video_id=UUID(video_id),
                        template_id=UUID(config_id),
                        template_name=ai_cfg.name,
                        name=ai_cfg.name,
                        category=ai_cfg.tags[0] if ai_cfg.tags else 'general',
                        description=ai_cfg.description or f"使用{ai_cfg.provider}的{ai_cfg.model_name}模型进行分析",
                        prompt_content=prompt_content,
                        priority=i + 1,
                        enabled=True,
                        analysis_status='ready'
                    )
                    session.add(template)

                logger.info(f"为视频 {video_id} 配置了 {len(ai_model_config_ids)} 个分析模板（传统模式）")

            return True

    @staticmethod
    async def get_analysis_templates(video_id: str) -> List[Dict[str, Any]]:
        """获取视频的分析模板配置（关联ai_model_configs获取算法名称）"""
        async with DatabaseManager.get_session() as session:
            stmt = (
                select(VideoAnalysisTemplateDB)
                .where(VideoAnalysisTemplateDB.video_id == UUID(video_id))
                .order_by(VideoAnalysisTemplateDB.priority.desc())
            )

            result = await session.execute(stmt)
            templates = result.scalars().all()

            # 关联查询ai_model_configs获取算法真实名称
            from sqlalchemy import text
            enriched_templates = []

            for template in templates:
                template_dict = {
                    'id': str(template.id),
                    'template_id': str(template.template_id) if template.template_id else None,
                    'template_name': template.template_name,
                    'analysis_status': template.analysis_status.value if hasattr(template.analysis_status, 'value') else str(template.analysis_status),
                    'progress': template.progress,
                    'priority': template.priority,
                    'enabled': template.enabled
                }

                # 如果有template_id，从ai_model_configs查询算法名称
                if template.template_id:
                    query = text("""
                        SELECT name, description, detection_capabilities
                        FROM ai_model_configs
                        WHERE id = :template_id
                    """)
                    ai_result = await session.execute(query, {'template_id': str(template.template_id)})
                    ai_row = ai_result.fetchone()

                    if ai_row:
                        template_dict['algorithm_name'] = ai_row[0]  # 算法真实名称
                        template_dict['algorithm_description'] = ai_row[1]
                        template_dict['detection_capabilities'] = ai_row[2]
                    else:
                        logger.warning(f"⚠️  未找到算法配置: template_id={template.template_id}")
                        template_dict['algorithm_name'] = template.template_name  # 降级使用保存的名称
                else:
                    template_dict['algorithm_name'] = template.template_name

                enriched_templates.append(template_dict)

            return enriched_templates

    @staticmethod
    async def update_analysis_progress(video_id: str, progress: int) -> bool:
        """更新视频分析进度"""
        async with DatabaseManager.get_session() as session:
            stmt = update(VideoFileDB).where(
                VideoFileDB.id == UUID(video_id)
            ).values(
                analysis_progress=progress
            )

            await session.execute(stmt)

            logger.debug(f"更新视频分析进度: {video_id} -> {progress}%")
            return True
