"""
缓冲区管理辅助模块

从 stream_analysis_service.py 中提取的缓冲区管理相关功能：
- 帧分析结果缓冲和批量写入ES
- 告警结果缓冲和批量写入ES
- 缓冲区数据刷新
- 自适应缓冲区回调处理

这些方法原属于 StreamAnalysisService 类，提取为独立函数以降低主类复杂度。
"""

import asyncio
import logging
from typing import Dict, List, Any

from utils.timezone_utils import now_isoformat

logger = logging.getLogger(__name__)


async def flush_buffered_data(
    stream_id: str,
    frame_results_buffer: Dict[str, List],
    alerts_buffer: Dict[str, List],
    elasticsearch_service
):
    """
    刷新指定流的缓冲数据

    Args:
        stream_id: 视频流ID
        frame_results_buffer: 帧结果缓冲区字典
        alerts_buffer: 告警缓冲区字典
        elasticsearch_service: ES服务实例
    """
    try:
        # 处理帧结果
        frame_results = frame_results_buffer.get(stream_id, [])
        if frame_results:
            await save_frame_results_to_elasticsearch(stream_id, frame_results, elasticsearch_service)
            frame_results_buffer[stream_id] = []
            logger.debug(f"已保存 {len(frame_results)} 个帧结果到Elasticsearch: 流={stream_id}")

        # 处理告警
        alerts = alerts_buffer.get(stream_id, [])
        if alerts:
            await save_alerts_to_elasticsearch(stream_id, alerts, elasticsearch_service)
            alerts_buffer[stream_id] = []
            logger.debug(f"已保存 {len(alerts)} 个告警到Elasticsearch: 流={stream_id}")

    except Exception as e:
        logger.error(f"刷新缓冲数据失败: 流={stream_id}, 错误={e}")


async def save_frame_results_to_elasticsearch(
    stream_id: str,
    frame_results: List[Dict[str, Any]],
    elasticsearch_service
):
    """
    保存帧分析结果到Elasticsearch

    Args:
        stream_id: 视频流ID
        frame_results: 帧分析结果列表
        elasticsearch_service: ES服务实例
    """
    try:
        documents = []
        for result in frame_results:
            # 格式化置信度为两位小数
            confidence = result.get('confidence', 0.0)
            if isinstance(confidence, (int, float)):
                confidence = round(float(confidence), 2)

            doc = {
                'task_id': result.get('task_id'),
                'stream_id': stream_id,
                'frame_index': result.get('frame_index'),
                'timestamp': result.get('timestamp'),
                'datetime': result.get('datetime'),
                'template_id': result.get('template_id'),
                'template_name': result.get('template_name'),
                'category': result.get('category'),
                'priority': result.get('priority', 1),
                'has_alert': result.get('has_alert', False),
                'image_url': result.get('image_url'),
                'ai_response': result.get('ai_response', ''),
                'confidence': confidence,
                'model_used': result.get('model_used', ''),
                'created_at': now_isoformat(),
                'data_type': 'stream_frame_result'
            }
            documents.append(doc)

        # 批量保存到Elasticsearch
        await elasticsearch_service.bulk_index_documents('video_frame_results', documents)

    except Exception as e:
        logger.error(f"保存帧结果到Elasticsearch失败: {e}")


async def save_alerts_to_elasticsearch(
    stream_id: str,
    alerts: List[Dict[str, Any]],
    elasticsearch_service,
    get_stream_info_func=None
):
    """
    保存告警到Elasticsearch

    Args:
        stream_id: 视频流ID
        alerts: 告警数据列表
        elasticsearch_service: ES服务实例
        get_stream_info_func: 获取流信息的异步函数
    """
    try:
        documents = []
        for alert in alerts:
            # 获取流相关信息
            if get_stream_info_func:
                stream_info = await get_stream_info_func(stream_id)
            else:
                stream_info = {
                    'name': f'实时流_{stream_id[:8]}',
                    'camera_name': f'摄像头_{stream_id[:8]}',
                    'location': '未知位置'
                }

            # 格式化置信度为两位小数
            confidence = alert.get('confidence', 0.0)
            if isinstance(confidence, (int, float)):
                confidence = round(float(confidence), 2)

            # 计算视频时间
            frame_index = alert.get('frame_index', 0)
            video_seconds = frame_index / 15  # 假设15FPS
            minutes = int(video_seconds // 60)
            seconds = int(video_seconds % 60)
            video_time = f"{minutes:02d}:{seconds:02d}"

            # 获取算法信息
            algorithm_name = alert.get('algorithm_name', alert.get('template_name', '未知算法'))
            algorithm_category = alert.get('category', 'analysis')

            logger.info(f"stream_analysis告警: template_name={alert.get('template_name')}, algorithm_name={algorithm_name}")

            # 确定告警严重程度
            priority = alert.get('priority', 1)
            if confidence >= 0.9:
                severity = "critical"
            elif confidence >= 0.7:
                severity = "high"
            elif confidence >= 0.5:
                severity = "medium"
            else:
                severity = "low"

            doc = {
                'task_id': f"stream_{stream_id}",
                'video_id': stream_id,
                'stream_id': stream_id,
                'video_name': stream_info.get('name', f'实时流_{stream_id[:8]}'),
                'frame_index': frame_index,
                'timestamp': alert.get('timestamp', 0.0),
                'video_time': video_time,
                'datetime': alert.get('datetime'),
                'template_name': alert.get('template_name'),
                'algorithm_name': algorithm_name,
                'algorithm_category': algorithm_category,
                'analysis_type': 'stream_analysis',
                'category': alert.get('category'),
                'priority': priority,
                'severity': severity,
                'alert_level': 'HIGH' if priority >= 3 else 'MEDIUM',
                'confidence': confidence,
                'alert_content': alert.get('alert_content', ''),
                'description': alert.get('alert_details', alert.get('alert_content', '')),
                'ai_response': alert.get('ai_response_full', alert.get('alert_content', '')),
                'image_url': alert.get('image_url'),
                'location': stream_info.get('location'),
                'camera_name': stream_info.get('camera_name', f'摄像头_{stream_id[:8]}'),
                'detection_details': {
                    'confidence': confidence,
                    'frame_index': frame_index,
                    'source': 'stream_analysis_service',
                    'template_category': algorithm_category,
                    'stream_id': stream_id
                },
                'resolved': False,
                'metadata': alert.get('metadata', {}),
                'created_at': now_isoformat(),
                'data_type': 'stream_alert'
            }
            documents.append(doc)

        # 批量保存到Elasticsearch
        await elasticsearch_service.bulk_index_documents('video_alerts', documents)

    except Exception as e:
        logger.error(f"保存告警到Elasticsearch失败: {e}")


async def adaptive_flush_callback(
    buffer_key: str,
    items: List[Dict[str, Any]],
    elasticsearch_service
):
    """
    自适应缓冲区刷新回调

    Args:
        buffer_key: 缓冲区键名
        items: 待刷新的数据项列表
        elasticsearch_service: ES服务实例
    """
    try:
        if not items:
            return

        if buffer_key.startswith("frame_results_"):
            stream_id = buffer_key.replace("frame_results_", "")
            await save_frame_results_to_elasticsearch(stream_id, items, elasticsearch_service)
            logger.debug(f"自适应刷新帧结果: 流={stream_id}, 数量={len(items)}")

        elif buffer_key.startswith("alerts_"):
            stream_id = buffer_key.replace("alerts_", "")
            await save_alerts_to_elasticsearch(stream_id, items, elasticsearch_service)
            logger.debug(f"自适应刷新告警: 流={stream_id}, 数量={len(items)}")

        else:
            logger.warning(f"未知的缓冲区类型: {buffer_key}")

    except Exception as e:
        logger.error(f"自适应刷新回调失败: buffer_key={buffer_key}, 错误={e}")
        raise  # 重新抛出异常，让缓冲区管理器处理重试逻辑
