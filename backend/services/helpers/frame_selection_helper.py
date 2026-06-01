"""
帧选择和AI响应分析辅助模块

从 stream_frame_analyzer.py 中提取的辅助功能：
- AI响应违规信息提取
- 告警回调数据构建
- AI调用日志记录

这些方法原属于 StreamFrameAnalyzer 类，提取为独立函数以降低主类复杂度。
"""

import json
import re
import logging
import uuid
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

from utils.timezone_utils import BEIJING_TZ

logger = logging.getLogger(__name__)


def extract_violation_from_ai_response(ai_response: str) -> bool:
    """
    从AI多模态响应中提取违规信息

    Args:
        ai_response: AI返回的文本响应

    Returns:
        是否检测到违规
    """
    try:
        # 尝试从响应中提取JSON部分
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                response_data = json.loads(json_str)
                # 检查has_violation字段
                if 'has_violation' in response_data:
                    return bool(response_data['has_violation'])
                # 检查violation_count字段，大于0表示有违规
                elif 'violation_count' in response_data:
                    return int(response_data.get('violation_count', 0)) > 0
            except json.JSONDecodeError as e:
                logger.warning(f"解析AI响应JSON失败: {e}")

        # 降级到关键词检查
        response_lower = ai_response.lower()
        violation_keywords = [
            'has_violation": true', '"has_violation":true',
            '违规', '违反', '异常', '不规范', '不合规',
            'violation', 'violate', 'alert', 'warning'
        ]

        return any(keyword in response_lower for keyword in violation_keywords)

    except Exception as e:
        logger.warning(f"提取违规信息失败: {e}")
        return False


def build_alert_data(
    template: Dict[str, Any],
    frame_index: int,
    timestamp: float,
    stream_id: str,
    analysis_result: Dict[str, Any],
    minio_url: str,
    response_time_ms: int
) -> Dict[str, Any]:
    """
    构建标准告警回调数据

    Args:
        template: 算法模板配置
        frame_index: 帧索引
        timestamp: 时间戳
        stream_id: 视频流ID
        analysis_result: AI分析结果
        minio_url: MinIO图片URL
        response_time_ms: 响应时间(毫秒)

    Returns:
        格式化的告警数据字典
    """
    # 格式化置信度为两位小数
    confidence = analysis_result.get('confidence', 0.0)
    if isinstance(confidence, (int, float)):
        confidence = round(float(confidence), 2)

    # timestamp是UTC Unix时间戳，datetime需要明确转换为北京时间
    datetime_beijing_alert = datetime.fromtimestamp(timestamp, tz=BEIJING_TZ).replace(tzinfo=None)

    return {
        'stream_id': stream_id,
        'frame_index': frame_index,
        'timestamp': timestamp,  # UTC Unix时间戳
        'datetime': datetime_beijing_alert.isoformat(),  # 北京时间ISO格式
        'template_name': template['name'],
        'algorithm_name': template['name'],
        'algorithm_category': template.get('category', ''),
        'category': template['category'],
        'priority': template.get('priority', 1),
        'alert_content': analysis_result.get('ai_response', ''),
        'ai_response': analysis_result.get('ai_response', ''),
        'confidence': confidence,
        'image_url': minio_url,
        'metadata': {
            'model_used': analysis_result.get('model_used', ''),
            'response_time_ms': response_time_ms,
            'template_id': template.get('id', ''),
            'analysis_type': 'stream_analysis'
        }
    }


def build_composite_alert_data(
    template: Dict[str, Any],
    frame_index: int,
    timestamp: float,
    stream_id: str,
    violation: Dict[str, Any],
    minio_url: str,
    response_time_ms: int
) -> Dict[str, Any]:
    """
    构建复合检测告警回调数据

    Args:
        template: 算法模板配置
        frame_index: 帧索引
        timestamp: 时间戳
        stream_id: 视频流ID
        violation: 违规检测结果
        minio_url: MinIO图片URL
        response_time_ms: 响应时间(毫秒)

    Returns:
        格式化的复合告警数据字典
    """
    # 格式化置信度为两位小数
    confidence = violation.get('confidence', 0.0)
    if isinstance(confidence, (int, float)):
        confidence = round(float(confidence), 2)

    # 转换为北京时间
    datetime_beijing_alert = datetime.fromtimestamp(timestamp, tz=BEIJING_TZ).replace(tzinfo=None)

    # 构建告警数据
    type_code = violation.get('type_code', 'unknown')
    display_name = violation.get('display_name', type_code)

    logger.info(f"构建告警数据: type_code={type_code}, display_name={display_name}")

    # 提取详细描述（将details数组合并为字符串）
    details_list = violation.get('details', [])
    details_text = '；'.join(details_list) if details_list else ''

    return {
        'stream_id': stream_id,
        'frame_index': frame_index,
        'timestamp': timestamp,
        'datetime': datetime_beijing_alert.isoformat(),
        'template_name': f"{template['name']} - {display_name}",
        'algorithm_name': display_name,
        'algorithm_category': template.get('category', ''),
        'category': violation.get('category', 'unknown'),
        'severity': violation.get('severity', 'medium'),
        'priority': template.get('priority', 1),
        'alert_content': violation.get('conclusion', ''),  # 简短结论
        'alert_details': details_text,  # 详细描述
        'ai_response_full': violation.get('ai_response_full', ''),  # 完整AI响应
        'confidence': confidence,
        'image_url': minio_url,
        'violation_type': type_code,  # 违规类型编码
        'violation_count': violation.get('violation_count', 0),  # 违规数量
        'metadata': {
            'model_used': template.get('model_name', ''),
            'response_time_ms': response_time_ms,
            'template_id': template.get('id', ''),
            'analysis_type': 'composite_detection',
            'detection_mode': 'composite'
        }
    }


async def log_successful_analysis(
    template: Dict[str, Any],
    frame_index: int,
    timestamp: float,
    stream_id: str,
    frame_path: str,
    analysis_result: Dict[str, Any],
    response_time_ms: int,
    rtsp_url: str = ''
):
    """
    记录成功的AI调用日志

    Args:
        template: 算法模板配置
        frame_index: 帧索引
        timestamp: 时间戳
        stream_id: 视频流ID
        frame_path: 帧图片路径
        analysis_result: AI分析结果
        response_time_ms: 响应时间(毫秒)
        rtsp_url: RTSP流地址
    """
    try:
        from services.ai_analysis_log_service import ai_analysis_log_service

        # 获取完整的API调用详情（如果有）
        api_details = analysis_result.get('api_call_details', {})

        # 构建完整的请求数据
        request_data = {
            'image_path': frame_path,
            'prompt': template.get('prompt_content', ''),
            'prompt_used': analysis_result.get('prompt_used', ''),
            'frame_index': frame_index,
            'timestamp': timestamp,
            'algorithm_name': template['name'],
            'algorithm_category': template['category'],
            'stream_id': stream_id,
            'rtsp_url': rtsp_url,
            'api_endpoint': api_details.get('api_endpoint', ''),
            'request_headers': api_details.get('headers', {}),
            'raw_request_body': api_details.get('raw_request', {}),
            'model_config': {
                'provider': analysis_result.get('provider', ''),
                'model_name': analysis_result.get('model', ''),
                'model_config_id': analysis_result.get('model_config_id', '')
            }
        }

        # 构建完整的响应数据（兼容单检测和复合检测）
        ai_response_text = analysis_result.get('raw_response') or analysis_result.get('ai_response', '')
        model_name = analysis_result.get('model_used') or analysis_result.get('model', '')

        response_data = {
            'ai_response': ai_response_text,
            'confidence': analysis_result.get('confidence', ''),
            'model_used': model_name,
            'raw_response_body': api_details.get('raw_response', {}),
            'status_code': api_details.get('status_code', 0),
            'usage': api_details.get('usage', {}),
            'prompt_tokens': api_details.get('usage', {}).get('prompt_tokens', 0),
            'completion_tokens': api_details.get('usage', {}).get('completion_tokens', 0),
            'total_tokens': api_details.get('usage', {}).get('total_tokens', 0)
        }

        await ai_analysis_log_service.log_success_call(
            task_id=str(uuid.uuid4()),
            video_id=stream_id,
            algorithm_id=template['id'],
            algorithm_config_id=template.get('template_id', template['id']),
            model_name=analysis_result.get('model', 'unknown'),
            frame_index=frame_index,
            frame_timestamp=str(timestamp),
            request_data=request_data,
            response_data=response_data,
            response_time_ms=response_time_ms,
            confidence_score=f"{analysis_result.get('confidence', 0.0):.2f}" if analysis_result.get('confidence') is not None else None
        )
    except Exception as e:
        logger.warning(f"记录AI调用日志失败: {e}")


async def log_failed_analysis(
    template: Dict[str, Any],
    frame_index: int,
    timestamp: float,
    stream_id: str,
    frame_path: str,
    error_message: str,
    rtsp_url: str = ''
):
    """
    记录失败的AI调用日志

    Args:
        template: 算法模板配置
        frame_index: 帧索引
        timestamp: 时间戳
        stream_id: 视频流ID
        frame_path: 帧图片路径
        error_message: 错误信息
        rtsp_url: RTSP流地址
    """
    try:
        from services.ai_analysis_log_service import ai_analysis_log_service

        error_request_data = {
            'image_path': frame_path,
            'prompt': template.get('prompt_content', ''),
            'frame_index': frame_index,
            'timestamp': timestamp,
            'algorithm_name': template['name'],
            'algorithm_category': template['category'],
            'stream_id': stream_id,
            'rtsp_url': rtsp_url,
            'error': error_message
        }

        await ai_analysis_log_service.log_failed_call(
            task_id=str(uuid.uuid4()),
            video_id=stream_id,
            algorithm_id=template['id'],
            algorithm_config_id=template.get('template_id', template['id']),
            model_name='unknown',
            frame_index=frame_index,
            frame_timestamp=str(timestamp),
            request_data=error_request_data,
            error_message=error_message,
            error_code='STREAM_ANALYSIS_ERROR'
        )
    except Exception as e:
        logger.warning(f"记录失败日志失败: {e}")
