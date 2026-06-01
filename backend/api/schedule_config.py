"""
时间调度配置API
提供视频流分析时间调度配置的管理接口
"""

from datetime import datetime, time
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from sqlalchemy.exc import IntegrityError

from database.connection import get_async_session
from models.schedule_config import (
    ScheduleConfigDB,
    ScheduleConfigCreate,
    ScheduleConfigUpdate,
    ScheduleConfigResponse,
    ScheduleConfigBatch,
    ScheduleCheckRequest,
    ScheduleCheckResponse
)

router = APIRouter(prefix="/api/schedule-configs", tags=["时间调度配置"])


@router.post("/", response_model=ScheduleConfigResponse, summary="创建时间调度配置")
async def create_schedule_config(
    config: ScheduleConfigCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    创建新的时间调度配置
    
    - **stream_id**: 视频流ID
    - **algorithm_id**: 算法ID  
    - **name**: 调度配置名称
    - **start_time**: 开始时间 (HH:MM格式)
    - **end_time**: 结束时间 (HH:MM格式)
    - **weekdays**: 运行星期几 (1=周一, 7=周日)
    """
    try:
        # 检查是否已存在相同的配置
        existing = await session.execute(
            select(ScheduleConfigDB).where(
                and_(
                    ScheduleConfigDB.stream_id == UUID(config.stream_id),
                    ScheduleConfigDB.algorithm_id == config.algorithm_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, 
                detail=f"该视频流和算法已存在时间调度配置，请使用更新接口"
            )
        
        # 转换时间格式
        start_time = time.fromisoformat(config.start_time)
        end_time = time.fromisoformat(config.end_time)
        
        # 处理time_ranges
        time_ranges_json = None
        if config.time_ranges:
            time_ranges_json = [range_model.dict() for range_model in config.time_ranges]
        
        # 创建新配置
        db_config = ScheduleConfigDB(
            stream_id=UUID(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            start_time=start_time,
            end_time=end_time,
            weekdays=config.weekdays,
            time_ranges=time_ranges_json,
            timezone=config.timezone,
            enabled=config.enabled
        )
        
        session.add(db_config)
        await session.commit()
        await session.refresh(db_config)
        
        return ScheduleConfigResponse(
            id=str(db_config.id),
            stream_id=str(db_config.stream_id),
            algorithm_id=db_config.algorithm_id,
            name=db_config.name,
            description=db_config.description,
            start_time=str(db_config.start_time),
            end_time=str(db_config.end_time),
            weekdays=db_config.weekdays,
            time_ranges=db_config.time_ranges,
            timezone=db_config.timezone,
            enabled=db_config.enabled,
            created_at=db_config.created_at,
            updated_at=db_config.updated_at
        )
        
    except IntegrityError as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"数据完整性错误: {str(e)}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"创建时间调度配置失败: {str(e)}")


@router.get("/", response_model=List[ScheduleConfigResponse], summary="获取时间调度配置列表")
async def get_schedule_configs(
    stream_id: Optional[str] = None,
    algorithm_id: Optional[str] = None,
    enabled: Optional[bool] = None,
    session: AsyncSession = Depends(get_async_session)
):
    """
    获取时间调度配置列表，支持按条件筛选
    
    - **stream_id**: 视频流ID (可选)
    - **algorithm_id**: 算法ID (可选)
    - **enabled**: 是否启用 (可选)
    """
    try:
        query = select(ScheduleConfigDB)
        
        # 添加筛选条件
        if stream_id:
            query = query.where(ScheduleConfigDB.stream_id == UUID(stream_id))
        if algorithm_id:
            query = query.where(ScheduleConfigDB.algorithm_id == algorithm_id)
        if enabled is not None:
            query = query.where(ScheduleConfigDB.enabled == enabled)
            
        query = query.order_by(ScheduleConfigDB.created_at.desc())
        
        result = await session.execute(query)
        configs = result.scalars().all()
        
        return [
            ScheduleConfigResponse(
                id=str(config.id),
                stream_id=str(config.stream_id),
                algorithm_id=config.algorithm_id,
                name=config.name,
                description=config.description,
                start_time=str(config.start_time),
                end_time=str(config.end_time),
                weekdays=config.weekdays,
                time_ranges=config.time_ranges,
                timezone=config.timezone,
                enabled=config.enabled,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in configs
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取时间调度配置列表失败: {str(e)}")


@router.get("/{config_id}", response_model=ScheduleConfigResponse, summary="获取单个时间调度配置")
async def get_schedule_config(
    config_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """获取指定ID的时间调度配置详情"""
    try:
        result = await session.execute(
            select(ScheduleConfigDB).where(ScheduleConfigDB.id == UUID(config_id))
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="时间调度配置不存在")
            
        return ScheduleConfigResponse(
            id=str(config.id),
            stream_id=str(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            start_time=str(config.start_time),
            end_time=str(config.end_time),
            weekdays=config.weekdays,
            time_ranges=config.time_ranges,
            timezone=config.timezone,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取时间调度配置失败: {str(e)}")


@router.put("/{config_id}", response_model=ScheduleConfigResponse, summary="更新时间调度配置")
async def update_schedule_config(
    config_id: str,
    update_data: ScheduleConfigUpdate,
    session: AsyncSession = Depends(get_async_session)
):
    """更新指定ID的时间调度配置"""
    try:
        result = await session.execute(
            select(ScheduleConfigDB).where(ScheduleConfigDB.id == UUID(config_id))
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="时间调度配置不存在")
        
        # 更新字段
        update_dict = update_data.dict(exclude_unset=True)
        
        # 处理时间字段
        if 'start_time' in update_dict:
            update_dict['start_time'] = time.fromisoformat(update_data.start_time)
        if 'end_time' in update_dict:
            update_dict['end_time'] = time.fromisoformat(update_data.end_time)
            
        # 处理time_ranges
        if 'time_ranges' in update_dict and update_data.time_ranges:
            update_dict['time_ranges'] = [range_model.dict() for range_model in update_data.time_ranges]
            
        for field, value in update_dict.items():
            setattr(config, field, value)
        
        await session.commit()
        await session.refresh(config)
        
        return ScheduleConfigResponse(
            id=str(config.id),
            stream_id=str(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            start_time=str(config.start_time),
            end_time=str(config.end_time),
            weekdays=config.weekdays,
            time_ranges=config.time_ranges,
            timezone=config.timezone,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"时间格式错误: {str(e)}")
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"更新时间调度配置失败: {str(e)}")


@router.delete("/{config_id}", summary="删除时间调度配置")
async def delete_schedule_config(
    config_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """删除指定ID的时间调度配置"""
    try:
        result = await session.execute(
            select(ScheduleConfigDB).where(ScheduleConfigDB.id == UUID(config_id))
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="时间调度配置不存在")
        
        await session.execute(
            delete(ScheduleConfigDB).where(ScheduleConfigDB.id == UUID(config_id))
        )
        await session.commit()
        
        return {"message": "时间调度配置已删除", "config_id": config_id}
        
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"删除时间调度配置失败: {str(e)}")


@router.post("/batch", response_model=List[ScheduleConfigResponse], summary="批量创建时间调度配置")
async def create_batch_schedule_configs(
    batch_data: ScheduleConfigBatch,
    session: AsyncSession = Depends(get_async_session)
):
    """批量创建时间调度配置"""
    try:
        created_configs = []
        
        for config_data in batch_data.configs:
            # 检查是否已存在相同配置
            existing = await session.execute(
                select(ScheduleConfigDB).where(
                    and_(
                        ScheduleConfigDB.stream_id == UUID(config_data.stream_id),
                        ScheduleConfigDB.algorithm_id == config_data.algorithm_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue  # 跳过已存在的配置
            
            # 转换时间格式
            start_time = time.fromisoformat(config_data.start_time)
            end_time = time.fromisoformat(config_data.end_time)
            
            # 处理time_ranges
            time_ranges_json = None
            if config_data.time_ranges:
                time_ranges_json = [range_model.dict() for range_model in config_data.time_ranges]
            
            db_config = ScheduleConfigDB(
                stream_id=UUID(config_data.stream_id),
                algorithm_id=config_data.algorithm_id,
                name=config_data.name,
                description=config_data.description,
                start_time=start_time,
                end_time=end_time,
                weekdays=config_data.weekdays,
                time_ranges=time_ranges_json,
                timezone=config_data.timezone,
                enabled=config_data.enabled
            )
            
            session.add(db_config)
            created_configs.append(db_config)
        
        await session.commit()
        
        # 刷新所有创建的配置
        for config in created_configs:
            await session.refresh(config)
        
        return [
            ScheduleConfigResponse(
                id=str(config.id),
                stream_id=str(config.stream_id),
                algorithm_id=config.algorithm_id,
                name=config.name,
                description=config.description,
                start_time=str(config.start_time),
                end_time=str(config.end_time),
                weekdays=config.weekdays,
                time_ranges=config.time_ranges,
                timezone=config.timezone,
                enabled=config.enabled,
                created_at=config.created_at,
                updated_at=config.updated_at
            )
            for config in created_configs
        ]
        
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"批量创建时间调度配置失败: {str(e)}")


@router.get("/stream/{stream_id}/algorithm/{algorithm_id}", response_model=ScheduleConfigResponse, summary="获取指定流和算法的时间调度配置")
async def get_schedule_config_by_stream_algorithm(
    stream_id: str,
    algorithm_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """获取指定视频流和算法的时间调度配置"""
    try:
        result = await session.execute(
            select(ScheduleConfigDB).where(
                and_(
                    ScheduleConfigDB.stream_id == UUID(stream_id),
                    ScheduleConfigDB.algorithm_id == algorithm_id
                )
            )
        )
        config = result.scalar_one_or_none()
        
        if not config:
            raise HTTPException(status_code=404, detail="未找到该视频流和算法的时间调度配置")
            
        return ScheduleConfigResponse(
            id=str(config.id),
            stream_id=str(config.stream_id),
            algorithm_id=config.algorithm_id,
            name=config.name,
            description=config.description,
            start_time=str(config.start_time),
            end_time=str(config.end_time),
            weekdays=config.weekdays,
            time_ranges=config.time_ranges,
            timezone=config.timezone,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取时间调度配置失败: {str(e)}")


@router.post("/check", response_model=ScheduleCheckResponse, summary="检查是否应该运行分析")
async def check_should_run_analysis(
    check_request: ScheduleCheckRequest,
    session: AsyncSession = Depends(get_async_session)
):
    """
    检查指定时间是否应该运行分析
    根据时间调度配置判断当前时间或指定时间是否在运行范围内
    """
    try:
        # 获取配置
        result = await session.execute(
            select(ScheduleConfigDB).where(
                and_(
                    ScheduleConfigDB.stream_id == UUID(check_request.stream_id),
                    ScheduleConfigDB.algorithm_id == check_request.algorithm_id
                )
            )
        )
        config = result.scalar_one_or_none()
        
        # 检查时间，默认为当前时间
        check_time = check_request.check_time or datetime.now()
        
        if not config:
            return ScheduleCheckResponse(
                should_run=True,  # 没有配置时默认运行
                reason="未找到时间调度配置，默认允许运行",
                current_time=check_time,
                config_enabled=False,
                in_time_range=True,
                in_weekday_range=True
            )
        
        if not config.enabled:
            return ScheduleCheckResponse(
                should_run=False,
                reason="时间调度配置已禁用",
                current_time=check_time,
                config_enabled=False,
                in_time_range=False,
                in_weekday_range=False
            )
        
        # 检查星期几
        current_weekday = check_time.weekday() + 1  # 转换为1-7格式
        if current_weekday == 7:
            current_weekday = 0  # 兼容周日为0的格式
            
        in_weekday_range = (current_weekday in config.weekdays) or (7 in config.weekdays and current_weekday == 0)
        
        # 检查时间范围
        current_time = check_time.time()
        in_time_range = False
        
        # 主要时间范围检查
        if config.start_time <= config.end_time:
            # 不跨天的情况
            in_time_range = config.start_time <= current_time <= config.end_time
        else:
            # 跨天的情况 (如22:00-06:00)
            in_time_range = current_time >= config.start_time or current_time <= config.end_time
        
        # 检查多时间段配置
        if config.time_ranges and not in_time_range:
            for time_range in config.time_ranges:
                start = time.fromisoformat(time_range['start_time'])
                end = time.fromisoformat(time_range['end_time'])
                
                if start <= end:
                    if start <= current_time <= end:
                        in_time_range = True
                        break
                else:
                    if current_time >= start or current_time <= end:
                        in_time_range = True
                        break
        
        should_run = in_weekday_range and in_time_range
        
        reason = "允许运行" if should_run else f"不在运行时间范围内 (星期{current_weekday}, {current_time})"
        
        return ScheduleCheckResponse(
            should_run=should_run,
            reason=reason,
            current_time=check_time,
            config_enabled=config.enabled,
            in_time_range=in_time_range,
            in_weekday_range=in_weekday_range
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查时间调度失败: {str(e)}")