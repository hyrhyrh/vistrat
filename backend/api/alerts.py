"""
告警相关API端点
"""

import logging
from datetime import datetime
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from core.alert_service import AlertService
from services.elasticsearch_service import ElasticsearchService
from config.settings import StorageConfig
from utils.timezone_utils import format_beijing_time

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def convert_minio_url_to_proxy(minio_url: Optional[str]) -> Optional[str]:
    """
    将MinIO直接URL转换为代理URL
    
    Args:
        minio_url: 原始MinIO URL (如: http://localhost:9000/images/analysis/xxx.jpg)
        
    Returns:
        代理URL (如: /api/image-proxy/minio/images/analysis/xxx.jpg)
    """
    if not minio_url:
        return None
    
    try:
        # 解析URL
        parsed_url = urlparse(minio_url)
        
        # 检查是否是MinIO URL
        if not parsed_url.netloc.startswith(StorageConfig.MINIO_ENDPOINT.split(':')[0]):
            return minio_url  # 如果不是MinIO URL，直接返回原URL
        
        # 提取路径部分（去除开头的'/'）
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            return minio_url  # 路径格式不正确，返回原URL
        
        bucket_name = path_parts[0]
        object_path = '/'.join(path_parts[1:])
        
        # 生成代理URL
        proxy_url = f"/api/image-proxy/minio/{bucket_name}/{object_path}"
        
        logger.debug(f"URL转换: {minio_url} -> {proxy_url}")
        return proxy_url
        
    except Exception as e:
        logger.warning(f"转换MinIO URL失败: {minio_url} - {e}")
        return minio_url  # 转换失败，返回原URL


class AlertSearchResponse(BaseModel):
    """告警搜索响应模型"""
    id: str
    timestamp: str
    alert_type: str
    algorithm_name: Optional[str] = None
    camera_name: Optional[str] = None
    video_name: Optional[str] = None
    image_path: Optional[str] = None
    confidence: Optional[float] = None
    detection_details: Optional[Dict] = None
    detection_objects: Optional[List[Dict]] = None  # A100 DINO 返回的检测框列表
    description: Optional[str] = None  # AI分析详细描述
    clip_url: Optional[str] = None  # 视频片段 URL（异步生成，Week 3B）
    clip_status: str = "pending"  # 片段状态：pending/ready/failed/skipped


@router.get("/search")
async def search_alerts(
    algorithm_name: Optional[str] = Query(None, description="算法名称"),
    camera_name: Optional[str] = Query(None, description="相机名称"),
    video_id: Optional[str] = Query(None, description="视频ID"),
    stream_id: Optional[str] = Query(None, description="视频流ID"),
    video_name: Optional[str] = Query(None, description="视频名称"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO格式"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO格式"),
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(8, ge=1, le=100, description="每页大小")
) -> Dict[str, Any]:
    """从Elasticsearch搜索告警数据"""
    try:
        # 构建Elasticsearch查询条件
        query_filters = []
        
        # 时间范围过滤
        if start_time and end_time:
            # 将前端传来的ISO时间字符串转换为北京时间毫秒时间戳（与存储格式一致）
            from dateutil.parser import parse as parse_date
            from datetime import timezone, timedelta
            try:
                # 解析ISO时间字符串（前端传来的是UTC时间或带时区的时间）
                start_dt = parse_date(start_time)
                end_dt = parse_date(end_time)

                # 转换为北京时区（UTC+8）
                beijing_tz = timezone(timedelta(hours=8))
                if start_dt.tzinfo is None:
                    # 如果没有时区信息，假设是UTC
                    start_dt = start_dt.replace(tzinfo=timezone.utc)
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=timezone.utc)

                # 转换到北京时区
                start_beijing = start_dt.astimezone(beijing_tz)
                end_beijing = end_dt.astimezone(beijing_tz)

                # 转换为北京时间的毫秒时间戳
                start_ms = int(start_beijing.timestamp() * 1000)
                end_ms = int(end_beijing.timestamp() * 1000)

                time_filter = {
                    "range": {
                        "created_at": {  # created_at存储的是北京时间毫秒时间戳
                            "gte": start_ms,
                            "lte": end_ms
                        }
                    }
                }
                query_filters.append(time_filter)
                logger.debug(f"时间范围查询(北京时间毫秒时间戳): {start_ms} - {end_ms} (原始: {start_time} - {end_time})")
            except Exception as e:
                logger.warning(f"时间格式转换失败: {e}, 跳过时间过滤")
        
        # 算法名称过滤
        if algorithm_name:
            query_filters.append({
                "term": {
                    "algorithm_name.keyword": algorithm_name
                }
            })
        
        # 相机名称过滤
        if camera_name:
            query_filters.append({
                "wildcard": {
                    "camera_name.keyword": f"*{camera_name}*"
                }
            })
        
        # 视频ID精确过滤（优先级最高）
        if video_id:
            query_filters.append({
                "term": {
                    "video_id": video_id  # video_id本身就是keyword类型，不需要.keyword
                }
            })
        
        # 视频流ID精确过滤（优先级最高）  
        if stream_id:
            query_filters.append({
                "term": {
                    "stream_id": stream_id  # stream_id本身就是keyword类型，不需要.keyword
                }
            })
        
        # 视频名称过滤
        if video_name:
            query_filters.append({
                "wildcard": {
                    "video_name.keyword": f"*{video_name}*"
                }
            })
        
        # 构建查询体
        if query_filters:
            es_query = {
                "query": {
                    "bool": {
                        "filter": query_filters
                    }
                },
                "sort": [
                    {"created_at": {"order": "desc"}}
                ],
                "from": (page - 1) * size,
                "size": size
            }
        else:
            es_query = {
                "query": {
                    "match_all": {}
                },
                "sort": [
                    {"created_at": {"order": "desc"}}
                ],
                "from": (page - 1) * size,
                "size": size
            }
        
        # 从Elasticsearch查询
        es_service = ElasticsearchService()
        results = await es_service.search_alerts(es_query)
        
        # 格式化响应数据
        alerts = []
        if results and 'hits' in results:
            for hit in results['hits']['hits']:
                source = hit['_source']
                # 处理timestamp字段类型转换
                created_at = source.get('created_at', '')
                if isinstance(created_at, (int, float)):
                    # 如果是数字类型（毫秒时间戳），转换为北京时间ISO字符串
                    utc_datetime = datetime.utcfromtimestamp(created_at / 1000)
                    beijing_datetime_str = format_beijing_time(utc_datetime)
                    # 转换为标准ISO格式，但保持北京时间 
                    timestamp_str = beijing_datetime_str.replace(' ', 'T') + '+08:00'
                else:
                    # 如果已经是字符串，直接使用
                    timestamp_str = str(created_at)
                
                # 转换MinIO URL为代理URL
                original_image_url = source.get('image_url')
                proxy_image_path = convert_minio_url_to_proxy(original_image_url)
                
                alert = AlertSearchResponse(
                    id=hit['_id'],
                    timestamp=timestamp_str,
                    alert_type=source.get('analysis_type', '未知'),  # 读取analysis_type字段
                    algorithm_name=source.get('algorithm_name') or source.get('template_name'),  # 优先algorithm_name，备选template_name
                    camera_name=source.get('camera_name'),
                    video_name=source.get('video_name'),
                    image_path=proxy_image_path,  # 使用代理URL
                    confidence=source.get('confidence'),
                    detection_details=source.get('detection_details', {}),
                    detection_objects=source.get('detection_objects') or [],  # A100 检测框
                    description=source.get('description'),  # AI分析详细描述
                    clip_url=source.get('clip_url'),  # 视频片段 URL（Week 3B）
                    clip_status=source.get('clip_status') or 'pending'
                )
                alerts.append(alert.dict())
            
            total = results['hits']['total']['value'] if isinstance(results['hits']['total'], dict) else results['hits']['total']
        else:
            total = 0
        
        logger.info(f"搜索告警数据: 返回 {len(alerts)} 条记录，总计 {total} 条")
        
        return {
            "success": True,
            "data": alerts,
            "total": total,
            "page": page,
            "size": size,
            "pages": (total + size - 1) // size if total > 0 else 0
        }
        
    except Exception as e:
        logger.error(f"搜索告警数据失败: {e}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "total": 0
        }


@router.get("/history")
async def get_alert_history(
    limit: int = Query(default=100, ge=1, le=1000, description="返回记录数量"),
    offset: int = Query(default=0, ge=0, description="偏移量")
) -> Dict[str, Any]:
    """获取告警历史记录"""
    try:
        history = AlertService.get_history(limit=limit, offset=offset)
        
        logger.info(f"获取告警历史: {len(history['data'])} 条记录")
        return history
        
    except Exception as e:
        logger.error(f"获取告警历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取告警历史失败: {str(e)}")


@router.delete("/history")
async def clear_alert_history():
    """清空告警历史记录"""
    try:
        AlertService.clear_history()
        
        logger.info("告警历史已清空")
        return {"message": "告警历史已清空"}
        
    except Exception as e:
        logger.error(f"清空告警历史失败: {e}")
        raise HTTPException(status_code=500, detail=f"清空告警历史失败: {str(e)}")


@router.get("/stats")
async def get_alert_stats():
    """
    获取告警统计信息（从Elasticsearch video_alerts索引）

    Returns:
        包含总告警数和今日告警数的统计信息
    """
    try:
        # 从Elasticsearch获取准确的告警统计
        es_service = ElasticsearchService()
        stats = await es_service.get_alert_statistics()

        # 添加时间戳
        from utils.timezone_utils import now_isoformat
        stats["last_updated"] = now_isoformat()

        logger.info(f"告警统计: 总数={stats['total_alerts']}, 今日={stats['today_alerts']}")
        return stats

    except Exception as e:
        logger.error(f"获取告警统计失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取告警统计失败: {str(e)}")