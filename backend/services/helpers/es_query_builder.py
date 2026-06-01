"""
Elasticsearch索引映射和查询构建辅助模块

从 elasticsearch_service.py 中提取的索引映射定义和查询构建相关功能：
- 分析结果索引mapping定义
- 帧分析结果索引mapping定义
- 预警索引mapping定义
- 索引创建和更新逻辑

这些定义原内嵌在 ElasticsearchService._create_indices 方法中，
提取为独立函数以降低主类复杂度。
"""

import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def get_analysis_results_mapping() -> Dict[str, Any]:
    """
    获取分析结果索引的mapping定义

    Returns:
        ES索引mapping配置
    """
    return {
        "mappings": {
            "properties": {
                "task_id": {"type": "keyword"},
                "video_id": {"type": "keyword"},
                "video_name": {"type": "text", "analyzer": "standard"},
                "original_filename": {"type": "keyword"},
                "template_ids": {"type": "keyword"},
                "analysis_status": {"type": "keyword"},
                "total_frames_analyzed": {"type": "integer"},
                "total_alerts": {"type": "integer"},
                "analysis_duration": {"type": "float"},
                "created_at": {"type": "date"},
                "started_at": {"type": "date"},
                "completed_at": {"type": "date"},
                "results_summary": {
                    "type": "nested",
                    "properties": {
                        "template_id": {"type": "keyword"},
                        "template_name": {"type": "text"},
                        "alerts_count": {"type": "integer"},
                        "avg_confidence": {"type": "float"}
                    }
                }
            }
        }
    }


def get_frame_results_mapping() -> Dict[str, Any]:
    """
    获取帧分析结果索引的mapping定义

    Returns:
        ES索引mapping配置
    """
    return {
        "mappings": {
            "properties": {
                "task_id": {"type": "keyword"},
                "video_id": {"type": "keyword"},
                "stream_id": {"type": "keyword"},
                "frame_index": {"type": "integer"},
                "timestamp": {"type": "float"},
                "datetime": {"type": "date"},
                "video_time": {"type": "keyword"},
                "template_id": {"type": "keyword"},
                "template_name": {"type": "text"},
                "category": {"type": "keyword"},
                "priority": {"type": "integer"},
                "ai_response": {"type": "text", "analyzer": "standard"},
                "confidence": {"type": "float"},
                "model_used": {"type": "keyword"},
                "has_alert": {"type": "boolean"},
                "analyzed_at": {"type": "date"},
                "created_at": {"type": "date"},
                "image_url": {"type": "keyword"},
                "data_type": {"type": "keyword"},
                "detection_objects": {
                    "type": "nested",
                    "properties": {
                        "class_name": {"type": "keyword"},
                        "confidence": {"type": "float"},
                        "bbox": {"type": "object"}
                    }
                }
            }
        }
    }


def get_alerts_mapping() -> Dict[str, Any]:
    """
    获取预警索引的mapping定义

    Returns:
        ES索引mapping配置
    """
    return {
        "mappings": {
            "properties": {
                "task_id": {"type": "keyword"},
                "video_id": {"type": "keyword"},
                "stream_id": {"type": "keyword"},
                "video_name": {"type": "text", "analyzer": "standard"},
                "frame_index": {"type": "integer"},
                "timestamp": {"type": "float"},
                "video_time": {"type": "keyword"},
                "datetime": {"type": "date"},
                "template_name": {"type": "text"},
                "analysis_type": {"type": "keyword"},
                "confidence": {"type": "float"},
                "description": {"type": "text", "analyzer": "standard"},
                "alert_content": {"type": "text", "analyzer": "standard"},
                "severity": {"type": "keyword"},
                "category": {"type": "keyword"},
                "priority": {"type": "integer"},
                "alert_level": {"type": "keyword"},
                "resolved": {"type": "boolean"},
                "created_at": {"type": "date"},
                "location": {"type": "text"},
                "metadata": {"type": "object"},
                "image_url": {"type": "keyword"},
                "algorithm_name": {"type": "text"},
                "algorithm_category": {"type": "keyword"},
                "ai_response": {"type": "text", "analyzer": "standard"},
                "camera_name": {"type": "text"},
                "detection_details": {"type": "object"},
                "data_type": {"type": "keyword"}
            }
        }
    }


def get_all_index_mappings(config) -> List[Tuple[str, Dict[str, Any]]]:
    """
    获取所有索引的mapping定义列表

    Args:
        config: ElasticsearchConfig 配置对象

    Returns:
        [(索引名, mapping配置)] 列表
    """
    return [
        (config.ANALYSIS_RESULTS_INDEX, get_analysis_results_mapping()),
        (config.FRAME_RESULTS_INDEX, get_frame_results_mapping()),
        (config.ALERTS_INDEX, get_alerts_mapping())
    ]


def create_indices(es_client, config):
    """
    创建必需的ES索引

    Args:
        es_client: Elasticsearch客户端实例
        config: ElasticsearchConfig 配置对象
    """
    try:
        for index_name, mapping in get_all_index_mappings(config):
            if not es_client.indices.exists(index=index_name):
                es_client.indices.create(index=index_name, body=mapping)
                logger.info(f"创建Elasticsearch索引: {index_name}")
            else:
                # 检查是否需要更新映射（对于video_alerts索引）
                if index_name == config.ALERTS_INDEX:
                    try:
                        es_client.indices.put_mapping(
                            index=index_name,
                            body=mapping["mappings"]
                        )
                        logger.info(f"更新Elasticsearch索引映射: {index_name}")
                    except Exception as mapping_error:
                        logger.warning(f"映射更新失败: {mapping_error}")
                        logger.warning(f"索引 {index_name} 映射可能过时，建议手动重新创建")

    except Exception as e:
        logger.error(f"创建Elasticsearch索引失败: {e}")
