"""
ROI和时间调度服务
提供视频流分析的ROI裁剪和时间调度判断功能
纯异步版本


"""

import cv2
import numpy as np
import logging
from datetime import datetime, time
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, and_

from database.connection import DatabaseManager
from models.roi_config import ROIConfigDB, ROIRegion
from models.schedule_config import ScheduleConfigDB
from utils.timezone_utils import now

logger = logging.getLogger(__name__)


class ROIScheduleService:
    """ROI和时间调度服务（纯异步版本）"""

    def __init__(self):
        self._roi_cache: Dict[str, List[Dict[str, Any]]] = {}  # stream_id:algorithm_id -> roi_regions
        self._schedule_cache: Dict[str, Dict[str, Any]] = {}  # stream_id:algorithm_id -> schedule_config
        self._cache_ttl = 300  # 缓存5分钟
        self._last_cache_update = {}

    async def should_analyze_frame(
        self,
        stream_id: str,
        algorithm_id: str,
        check_time: Optional[datetime] = None
    ) -> Tuple[bool, str]:
        """
        检查是否应该分析帧

        Returns:
            (should_analyze, reason): 是否应该分析和原因
        """
        try:
            check_time = check_time or now()

            # 获取时间调度配置
            schedule_config = await self._get_schedule_config(stream_id, algorithm_id)

            if not schedule_config:
                return True, "未配置时间调度，默认允许分析"

            if not schedule_config.get('enabled', True):
                return False, "时间调度已禁用"

            # 检查星期几
            current_weekday = check_time.weekday() + 1  # 转换为1-7格式
            if current_weekday == 7:
                current_weekday = 0  # 兼容周日为0的格式

            weekdays = schedule_config.get('weekdays', [])
            in_weekday_range = (current_weekday in weekdays) or (7 in weekdays and current_weekday == 0)

            if not in_weekday_range:
                return False, f"不在运行日期范围内 (当前: 星期{current_weekday})"

            # 检查时间范围
            current_time = check_time.time()
            start_time = schedule_config.get('start_time')
            end_time = schedule_config.get('end_time')

            if start_time and end_time:
                # 处理字符串格式的时间
                if isinstance(start_time, str):
                    start_time = time.fromisoformat(start_time)
                if isinstance(end_time, str):
                    end_time = time.fromisoformat(end_time)

                in_time_range = False

                if start_time <= end_time:
                    # 不跨天的情况
                    in_time_range = start_time <= current_time <= end_time
                else:
                    # 跨天的情况 (如22:00-06:00)
                    in_time_range = current_time >= start_time or current_time <= end_time

                # 检查多时间段配置
                time_ranges = schedule_config.get('time_ranges', [])
                if time_ranges and not in_time_range:
                    for time_range in time_ranges:
                        range_start = time.fromisoformat(time_range['start_time'])
                        range_end = time.fromisoformat(time_range['end_time'])

                        if range_start <= range_end:
                            if range_start <= current_time <= range_end:
                                in_time_range = True
                                break
                        else:
                            if current_time >= range_start or current_time <= range_end:
                                in_time_range = True
                                break

                if not in_time_range:
                    return False, f"不在运行时间范围内 (当前: {current_time})"

            return True, "允许分析"

        except Exception as e:
            logger.error(f"检查时间调度失败: {e}")
            return True, f"时间调度检查异常，默认允许分析: {str(e)}"

    async def apply_roi_crop(
        self,
        frame: np.ndarray,
        stream_id: str,
        algorithm_id: str
    ) -> Tuple[List[np.ndarray], List[Dict[str, Any]]]:
        """
        应用ROI裁剪

        Args:
            frame: 原始帧图像
            stream_id: 视频流ID
            algorithm_id: 算法ID

        Returns:
            (cropped_frames, roi_info): 裁剪后的帧列表和ROI信息
        """
        try:
            # 获取ROI配置
            roi_configs = await self._get_roi_configs(stream_id, algorithm_id)

            if not roi_configs:
                # 没有ROI配置，返回原始帧
                return [frame], [{'x': 0, 'y': 0, 'width': frame.shape[1], 'height': frame.shape[0], 'is_full_frame': True}]

            cropped_frames = []
            roi_info = []

            frame_height, frame_width = frame.shape[:2]

            for roi in roi_configs:
                try:
                    x = max(0, min(roi['x'], frame_width - 1))
                    y = max(0, min(roi['y'], frame_height - 1))
                    width = max(1, min(roi['width'], frame_width - x))
                    height = max(1, min(roi['height'], frame_height - y))

                    # 裁剪ROI区域
                    cropped_frame = frame[y:y+height, x:x+width]

                    if cropped_frame.size > 0:
                        cropped_frames.append(cropped_frame)
                        roi_info.append({
                            'x': x,
                            'y': y,
                            'width': width,
                            'height': height,
                            'is_full_frame': False,
                            'original_roi': roi
                        })

                        logger.debug(f"ROI裁剪成功: ({x}, {y}, {width}, {height})")
                    else:
                        logger.warning(f"ROI区域无效: ({x}, {y}, {width}, {height})")

                except Exception as roi_error:
                    logger.error(f"单个ROI裁剪失败: {roi_error}")
                    continue

            # 如果没有有效的ROI，返回原始帧
            if not cropped_frames:
                return [frame], [{'x': 0, 'y': 0, 'width': frame_width, 'height': frame_height, 'is_full_frame': True}]

            return cropped_frames, roi_info

        except Exception as e:
            logger.error(f"ROI裁剪失败: {e}")
            # 出错时返回原始帧
            return [frame], [{'x': 0, 'y': 0, 'width': frame.shape[1], 'height': frame.shape[0], 'is_full_frame': True, 'error': str(e)}]

    async def _get_roi_configs(self, stream_id: str, algorithm_id: str) -> List[Dict[str, Any]]:
        """获取ROI配置（带缓存）"""
        cache_key = f"{stream_id}:{algorithm_id}"

        # 检查缓存
        if self._is_cache_valid(cache_key, 'roi'):
            return self._roi_cache.get(cache_key, [])

        # 从数据库加载
        async with DatabaseManager.get_session() as session:
            try:
                result = await session.execute(
                    select(ROIConfigDB).where(
                        and_(
                            ROIConfigDB.stream_id == stream_id,
                            ROIConfigDB.algorithm_id == algorithm_id,
                            ROIConfigDB.enabled == True
                        )
                    )
                )

                config = result.scalar_one_or_none()

                roi_regions = []
                if config and config.regions:
                    roi_regions = config.regions

                # 更新缓存
                self._roi_cache[cache_key] = roi_regions
                self._last_cache_update[f"roi_{cache_key}"] = now()

                return roi_regions
            except Exception as e:
                logger.error(f"获取ROI配置失败: {e}")
                return []

    async def _get_schedule_config(self, stream_id: str, algorithm_id: str) -> Optional[Dict[str, Any]]:
        """获取时间调度配置（带缓存）"""
        cache_key = f"{stream_id}:{algorithm_id}"

        # 检查缓存
        if self._is_cache_valid(cache_key, 'schedule'):
            return self._schedule_cache.get(cache_key)

        # 从数据库加载
        async with DatabaseManager.get_session() as session:
            try:
                result = await session.execute(
                    select(ScheduleConfigDB).where(
                        and_(
                            ScheduleConfigDB.stream_id == stream_id,
                            ScheduleConfigDB.algorithm_id == algorithm_id
                        )
                    )
                )

                config = result.scalar_one_or_none()

                schedule_data = None
                if config:
                    schedule_data = {
                        'enabled': config.enabled,
                        'start_time': config.start_time,
                        'end_time': config.end_time,
                        'weekdays': config.weekdays,
                        'time_ranges': config.time_ranges,
                        'timezone': config.timezone
                    }

                # 更新缓存
                self._schedule_cache[cache_key] = schedule_data
                self._last_cache_update[f"schedule_{cache_key}"] = now()

                return schedule_data
            except Exception as e:
                logger.error(f"获取时间调度配置失败: {e}")
                return None

    def _is_cache_valid(self, cache_key: str, cache_type: str) -> bool:
        """检查缓存是否有效"""
        cache_time_key = f"{cache_type}_{cache_key}"
        last_update = self._last_cache_update.get(cache_time_key)

        if not last_update:
            return False

        age = (now() - last_update).total_seconds()
        return age < self._cache_ttl

    def clear_cache(self, stream_id: Optional[str] = None, algorithm_id: Optional[str] = None):
        """清除缓存"""
        if stream_id and algorithm_id:
            cache_key = f"{stream_id}:{algorithm_id}"
            self._roi_cache.pop(cache_key, None)
            self._schedule_cache.pop(cache_key, None)
            self._last_cache_update.pop(f"roi_{cache_key}", None)
            self._last_cache_update.pop(f"schedule_{cache_key}", None)
        else:
            # 清除所有缓存
            self._roi_cache.clear()
            self._schedule_cache.clear()
            self._last_cache_update.clear()

        logger.info(f"缓存已清除: stream_id={stream_id}, algorithm_id={algorithm_id}")

    async def validate_frame_for_analysis(
        self,
        frame: np.ndarray,
        stream_id: str,
        algorithm_id: str,
        check_time: Optional[datetime] = None
    ) -> Tuple[bool, List[np.ndarray], List[Dict[str, Any]], str]:
        """
        验证帧是否应该分析，并应用ROI裁剪

        Returns:
            (should_analyze, cropped_frames, roi_info, reason)
        """
        # 检查时间调度
        should_analyze, reason = await self.should_analyze_frame(stream_id, algorithm_id, check_time)

        if not should_analyze:
            return False, [], [], reason

        # 应用ROI裁剪
        cropped_frames, roi_info = await self.apply_roi_crop(frame, stream_id, algorithm_id)

        return True, cropped_frames, roi_info, reason


# 创建全局实例
roi_schedule_service = ROIScheduleService()
