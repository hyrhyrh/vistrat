"""
ROI (Region of Interest) 配置API
提供视频流感兴趣区域配置的管理接口
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.exc import IntegrityError

from database.connection import get_async_session
from models.roi_config import (
    ROIConfigDB,
    ROIConfigCreate,
    ROIConfigUpdate,
    ROIConfigResponse,
    ROIConfigBatch
)

router = APIRouter(prefix="/api/roi-configs", tags=["ROI配置"])


@router.post("/", response_model=ROIConfigResponse, summary="创建ROI配置")
async def create_roi_config(
    config: ROIConfigCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    创建新的ROI配置
    
    - **stream_id**: 视频流ID
    - **algorithm_id**: 算法ID  
    - **name**: ROI配置名称
    - **regions**: ROI区域列表，每个区域包含x, y, width, height坐标
    """
    try:
        # 检查是否已存在相同的配置
        existing = await session.execute(
            select(ROIConfigDB).where(
                and_(
                    ROIConfigDB.stream_id == UUID(config.stream_id),
                    ROIConfigDB.algorithm_id == config.algorithm_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail=f"该视频流和算法已存在ROI配置，请使用更新接口"
            )
        
        # 创建新配置
        db_config = ROIConfigDB(
            stream_id=UUID(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            regions=[region.dict() for region in config.regions],
            video_width=config.video_width,
            video_height=config.video_height,
            enabled=config.enabled
        )
        
        session.add(db_config)
        await session.commit()
        await session.refresh(db_config)
        
        return ROIConfigResponse(
            id=str(db_config.id),
            stream_id=str(db_config.stream_id),
            algorithm_id=db_config.algorithm_id,
            name=db_config.name,
            description=db_config.description,
            regions=db_config.regions,
            video_width=db_config.video_width,
            video_height=db_config.video_height,
            enabled=db_config.enabled,
            created_at=db_config.created_at,
            updated_at=db_config.updated_at
        )
        
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"数据完整性错误: {str(e)}")
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"创建ROI配置失败: {str(e)}")


@router.get("/", response_model=List[ROIConfigResponse], summary="获取ROI配置列表")
async def get_roi_configs(
    stream_id: Optional[str] = None,
    algorithm_id: Optional[str] = None,
    enabled: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取ROI配置列表，支持按条件筛选
    
    - **stream_id**: 视频流ID (可选)
    - **algorithm_id**: 算法ID (可选)
    - **enabled**: 是否启用 (可选)
    """
    try:
        query = select(ROIConfigDB)
        
        # 添加筛选条件
        if stream_id:
            query = query.where(ROIConfigDB.stream_id == UUID(stream_id))
        if algorithm_id:
            query = query.where(ROIConfigDB.algorithm_id == algorithm_id)
        if enabled is not None:
            query = query.where(ROIConfigDB.enabled == enabled)
            
        query = query.order_by(ROIConfigDB.created_at.desc())
        
        result = await session.execute(query)
        configs = result.scalars().all()
        
        return [
            ROIConfigResponse(
                id=str(config.id),
                stream_id=str(config.stream_id),
                algorithm_id=config.algorithm_id,
                name=config.name,
                description=config.description,
                regions=config.regions,
                video_width=config.video_width,
                video_height=config.video_height,
                enabled=config.enabled,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in configs
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取ROI配置列表失败: {str(e)}")


@router.get("/{config_id}", response_model=ROIConfigResponse, summary="获取单个ROI配置")
async def get_roi_config(
    config_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """获取指定ID的ROI配置详情"""
    try:
        result = await session.execute(
            select(ROIConfigDB).where(ROIConfigDB.id == UUID(config_id))
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="ROI配置不存在")
            
        return ROIConfigResponse(
            id=str(config.id),
            stream_id=str(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            regions=config.regions,
            video_width=config.video_width,
            video_height=config.video_height,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取ROI配置失败: {str(e)}")


@router.put("/{config_id}", response_model=ROIConfigResponse, summary="更新ROI配置")
async def update_roi_config(
    config_id: str,
    update_data: ROIConfigUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """更新指定ID的ROI配置"""
    try:
        result = await session.execute(
            select(ROIConfigDB).where(ROIConfigDB.id == UUID(config_id))
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="ROI配置不存在")
        
        # 更新字段
        update_dict = update_data.dict(exclude_unset=True)
        if 'regions' in update_dict:
            update_dict['regions'] = [region.dict() for region in update_data.regions] if update_data.regions else []
            
        for field, value in update_dict.items():
            setattr(config, field, value)
        
        await session.commit()
        await session.refresh(config)
        
        return ROIConfigResponse(
            id=str(config.id),
            stream_id=str(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            regions=config.regions,
            video_width=config.video_width,
            video_height=config.video_height,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"更新ROI配置失败: {str(e)}")


@router.delete("/{config_id}", summary="删除ROI配置")
async def delete_roi_config(
    config_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """删除指定ID的ROI配置"""
    try:
        result = await session.execute(
            select(ROIConfigDB).where(ROIConfigDB.id == UUID(config_id))
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="ROI配置不存在")
        
        await session.execute(
            delete(ROIConfigDB).where(ROIConfigDB.id == UUID(config_id))
        )
        await session.commit()
        
        return {"message": "ROI配置已删除", "config_id": config_id}
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"删除ROI配置失败: {str(e)}")


@router.post("/batch", response_model=List[ROIConfigResponse], summary="批量创建ROI配置")
async def create_batch_roi_configs(
    batch_data: ROIConfigBatch,
    session: AsyncSession = Depends(get_async_session)
):
    """批量创建ROI配置"""
    try:
        created_configs = []
        
        for config_data in batch_data.configs:
            # 检查是否已存在相同配置
            existing = await session.execute(
                select(ROIConfigDB).where(
                    and_(
                        ROIConfigDB.stream_id == UUID(config_data.stream_id),
                        ROIConfigDB.algorithm_id == config_data.algorithm_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue  # 跳过已存在的配置
            
            db_config = ROIConfigDB(
                stream_id=UUID(config_data.stream_id),
                algorithm_id=config_data.algorithm_id,
                name=config_data.name,
                description=config_data.description,
                regions=[region.dict() for region in config_data.regions],
                video_width=config_data.video_width,
                video_height=config_data.video_height,
                enabled=config_data.enabled
            )
            
            session.add(db_config)
            created_configs.append(db_config)
        
        await session.commit()
        
        # 刷新所有创建的配置
        for config in created_configs:
            await session.refresh(config)
        
        return [
            ROIConfigResponse(
                id=str(config.id),
                stream_id=str(config.stream_id),
                algorithm_id=config.algorithm_id,
                name=config.name,
                description=config.description,
                regions=config.regions,
                video_width=config.video_width,
                video_height=config.video_height,
                enabled=config.enabled,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in created_configs
        ]
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"批量创建ROI配置失败: {str(e)}")


@router.get("/stream/{stream_id}/algorithm/{algorithm_id}", response_model=ROIConfigResponse, summary="获取指定流和算法的ROI配置")
async def get_roi_config_by_stream_algorithm(
    stream_id: str,
    algorithm_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """获取指定视频流和算法的ROI配置"""
    try:
        result = await session.execute(
            select(ROIConfigDB).where(
                and_(
                    ROIConfigDB.stream_id == UUID(stream_id),
                    ROIConfigDB.algorithm_id == algorithm_id
                )
            )
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="未找到该视频流和算法的ROI配置")
            
        return ROIConfigResponse(
            id=str(config.id),
            stream_id=str(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            regions=config.regions,
            video_width=config.video_width,
            video_height=config.video_height,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取ROI配置失败: {str(e)}")