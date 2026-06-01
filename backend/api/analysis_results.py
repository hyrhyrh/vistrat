"""
视频分析结果查询API端点
提供分析结果历史查询、统计和搜索功能
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from services.elasticsearch_service import elasticsearch_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis-results", tags=["分析结果"])


# 请求响应模型
class AnalysisResultQuery(BaseModel):
    """分析结果查询参数"""
    video_id: Optional[str] = Field(None, description="视频ID筛选")
    video_name: Optional[str] = Field(None, description="视频名称关键词")
    template_name: Optional[str] = Field(None, description="模板名称关键词")
    start_date: Optional[str] = Field(None, description="开始时间 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束时间 YYYY-MM-DD")
    status: Optional[str] = Field(None, description="分析状态")
    min_alerts: Optional[int] = Field(None, description="最小告警数量")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class AlertQuery(BaseModel):
    """预警查询参数"""
    video_id: Optional[str] = Field(None, description="视频ID筛选")
    video_name: Optional[str] = Field(None, description="视频名称关键词")
    analysis_type: Optional[str] = Field(None, description="分析类型: video_analysis(离线分析) 或 stream_analysis(实时分析)")
    severity: Optional[str] = Field(None, description="严重程度")
    min_confidence: Optional[float] = Field(None, description="最小置信度")
    start_date: Optional[str] = Field(None, description="开始时间")
    end_date: Optional[str] = Field(None, description="结束时间")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


class FrameResultQuery(BaseModel):
    """帧结果查询参数"""
    task_id: Optional[str] = Field(None, description="任务ID")
    video_id: Optional[str] = Field(None, description="视频ID")
    template_id: Optional[str] = Field(None, description="模板ID")
    has_alert: Optional[bool] = Field(None, description="是否有预警")
    min_confidence: Optional[float] = Field(None, description="最小置信度")
    start_timestamp: Optional[float] = Field(None, description="视频开始时间戳")
    end_timestamp: Optional[float] = Field(None, description="视频结束时间戳")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


@router.get("/analysis-tasks", summary="查询分析任务历史")
async def query_analysis_results(
    video_id: Optional[str] = Query(None, description="视频ID筛选"),
    video_name: Optional[str] = Query(None, description="视频名称关键词"),
    template_name: Optional[str] = Query(None, description="模板名称关键词"),
    start_date: Optional[str] = Query(None, description="开始时间 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束时间 YYYY-MM-DD"),
    status: Optional[str] = Query(None, description="分析状态"),
    min_alerts: Optional[int] = Query(None, description="最小告警数量"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询历史分析任务结果
    支持多种筛选条件和分页
    """
    try:
        # 构建Elasticsearch查询
        query = _build_analysis_query({
            "video_id": video_id,
            "video_name": video_name,
            "template_name": template_name,
            "start_date": start_date,
            "end_date": end_date,
            "status": status,
            "min_alerts": min_alerts
        })
        
        # 计算分页参数
        from_index = (page - 1) * page_size
        
        # 执行搜索
        response = await elasticsearch_service.search_analysis_results(
            query, size=page_size, from_=from_index
        )
        
        # 处理响应
        hits = response.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        results = []
        
        for hit in hits.get("hits", []):
            source = hit["_source"]
            # 格式化结果
            result = {
                "task_id": source.get("task_id"),
                "video_id": source.get("video_id"),
                "video_name": source.get("video_name"),
                "original_filename": source.get("original_filename"),
                "analysis_status": source.get("analysis_status"),
                "total_frames_analyzed": source.get("total_frames_analyzed", 0),
                "total_alerts": source.get("total_alerts", 0),
                "analysis_duration": source.get("analysis_duration", 0.0),
                "created_at": source.get("created_at"),
                "started_at": source.get("started_at"),
                "completed_at": source.get("completed_at"),
                "template_ids": source.get("template_ids", []),
                "results_summary": source.get("results_summary", [])
            }
            results.append(result)
        
        return {
            "success": True,
            "data": {
                "results": results,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
        }
        
    except Exception as e:
        logger.error(f"查询分析结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/alerts", summary="查询预警信息历史")
async def query_alerts(
    video_id: Optional[str] = Query(None, description="视频ID筛选"),
    video_name: Optional[str] = Query(None, description="视频名称关键词"),
    analysis_type: Optional[str] = Query(None, description="分析类型: video_analysis(离线分析) 或 stream_analysis(实时分析)"),
    severity: Optional[str] = Query(None, description="严重程度"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="最小置信度"),
    start_date: Optional[str] = Query(None, description="开始时间 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束时间 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询历史预警信息
    支持按严重程度、置信度、时间范围等筛选
    """
    try:
        # 构建Elasticsearch查询
        query = _build_alerts_query({
            "video_id": video_id,
            "video_name": video_name,
            "analysis_type": analysis_type,
            "severity": severity,
            "min_confidence": min_confidence,
            "start_date": start_date,
            "end_date": end_date
        })
        
        # 计算分页参数
        from_index = (page - 1) * page_size
        
        # 执行搜索
        response = await elasticsearch_service.search_alerts(
            query, size=page_size, from_=from_index
        )
        
        # 处理响应
        hits = response.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        alerts = []
        
        for hit in hits.get("hits", []):
            source = hit["_source"]
            alert = {
                "task_id": source.get("task_id"),
                "video_id": source.get("video_id"),
                "video_name": source.get("video_name"),
                "frame_index": source.get("frame_index", 0),
                "timestamp": source.get("timestamp", 0.0),
                "video_time": source.get("video_time", "00:00"),
                "template_name": source.get("template_name"),
                "analysis_type": source.get("analysis_type"),  # 分析类型: video_analysis 或 stream_analysis
                "confidence": source.get("confidence", 0.0),
                "description": source.get("description"),
                "severity": source.get("severity"),
                "created_at": source.get("created_at"),
                "metadata": source.get("metadata", {}),
                "detection_objects": source.get("detection_objects", []),  # A100 DINO bbox 列表
            }
            alerts.append(alert)
        
        return {
            "success": True,
            "data": {
                "alerts": alerts,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
        }
        
    except Exception as e:
        logger.error(f"查询预警信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/frame-results/{task_id}", summary="查询任务的帧分析结果")
async def query_frame_results(
    task_id: str,
    has_alert: Optional[bool] = Query(None, description="是否有预警"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="最小置信度"),
    start_timestamp: Optional[float] = Query(None, description="视频开始时间戳"),
    end_timestamp: Optional[float] = Query(None, description="视频结束时间戳"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    查询特定任务的帧分析结果
    用于查看单个分析任务的详细结果
    """
    try:
        # 构建Elasticsearch查询
        query = _build_frame_results_query({
            "task_id": task_id,
            "has_alert": has_alert,
            "min_confidence": min_confidence,
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp
        })
        
        # 计算分页参数
        from_index = (page - 1) * page_size
        
        # 执行搜索 (通过 ES 服务的自适应线程池执行同步 ES 客户端调用)
        response = await elasticsearch_service._run_sync(
            lambda: elasticsearch_service.es_client.search(
                index="video_frame_results",
                body=query,
                size=page_size,
                from_=from_index
            ) if elasticsearch_service.es_client else {"hits": {"total": {"value": 0}, "hits": []}}
        )
        
        # 处理响应
        hits = response.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        frames = []
        
        for hit in hits.get("hits", []):
            source = hit["_source"]
            frame = {
                "task_id": source.get("task_id"),
                "video_id": source.get("video_id"),
                "frame_index": source.get("frame_index", 0),
                "timestamp": source.get("timestamp", 0.0),
                "video_time": source.get("video_time", "00:00"),
                "template_id": source.get("template_id"),
                "template_name": source.get("template_name"),
                "ai_response": source.get("ai_response"),
                "confidence": source.get("confidence", 0.0),
                "has_alert": source.get("has_alert", False),
                "analyzed_at": source.get("analyzed_at"),
                "detection_objects": source.get("detection_objects", []),
                "image_url": source.get("image_url") or source.get("image_path")  # 兼容新旧字段名
            }
            frames.append(frame)
        
        return {
            "success": True,
            "data": {
                "task_id": task_id,
                "frames": frames,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": (total + page_size - 1) // page_size
                }
            }
        }
        
    except Exception as e:
        logger.error(f"查询帧结果失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/statistics", summary="获取分析结果统计信息")
async def get_analysis_statistics(
    start_date: Optional[str] = Query(None, description="开始时间 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束时间 YYYY-MM-DD")
):
    """
    获取分析结果的统计信息
    包括任务数量、预警数量、置信度分布等
    """
    try:
        # 构建时间范围查询
        date_filter = []
        if start_date or end_date:
            time_range = {}
            if start_date:
                time_range["gte"] = start_date
            if end_date:
                time_range["lte"] = end_date + "T23:59:59"
            date_filter.append({
                "range": {
                    "created_at": time_range
                }
            })
        
        # 查询分析任务统计
        analysis_query = {
            "size": 0,
            "query": {
                "bool": {
                    "filter": date_filter
                }
            },
            "aggs": {
                "status_distribution": {
                    "terms": {"field": "analysis_status"}
                },
                "avg_duration": {
                    "avg": {"field": "analysis_duration"}
                },
                "total_alerts": {
                    "sum": {"field": "total_alerts"}
                },
                "avg_frames": {
                    "avg": {"field": "total_frames_analyzed"}
                }
            }
        }
        
        # 查询预警统计
        alerts_query = {
            "size": 0,
            "query": {
                "bool": {
                    "filter": date_filter
                }
            },
            "aggs": {
                "severity_distribution": {
                    "terms": {"field": "severity"}
                },
                "confidence_stats": {
                    "stats": {"field": "confidence"}
                },
                "alert_types": {
                    "terms": {"field": "analysis_type"}
                },
                "hourly_distribution": {
                    "date_histogram": {
                        "field": "created_at",
                        "calendar_interval": "hour"
                    }
                }
            }
        }
        
        # 执行查询
        import asyncio
        loop = asyncio.get_event_loop()
        
        analysis_response, alerts_response = await asyncio.gather(
            elasticsearch_service.search_analysis_results(analysis_query),
            elasticsearch_service.search_alerts(alerts_query)
        )
        
        # 处理分析统计
        analysis_aggs = analysis_response.get("aggregations", {})
        alerts_aggs = alerts_response.get("aggregations", {})
        
        statistics = {
            "analysis_tasks": {
                "total": analysis_response.get("hits", {}).get("total", {}).get("value", 0),
                "status_distribution": _format_terms_aggregation(analysis_aggs.get("status_distribution", {})),
                "avg_duration_seconds": analysis_aggs.get("avg_duration", {}).get("value", 0.0),
                "total_alerts_generated": analysis_aggs.get("total_alerts", {}).get("value", 0),
                "avg_frames_analyzed": analysis_aggs.get("avg_frames", {}).get("value", 0.0)
            },
            "alerts": {
                "total": alerts_response.get("hits", {}).get("total", {}).get("value", 0),
                "severity_distribution": _format_terms_aggregation(alerts_aggs.get("severity_distribution", {})),
                "confidence_stats": alerts_aggs.get("confidence_stats", {}),
                "alert_types": _format_terms_aggregation(alerts_aggs.get("alert_types", {})),
                "hourly_distribution": _format_date_histogram(alerts_aggs.get("hourly_distribution", {}))
            },
            "query_range": {
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
        return {
            "success": True,
            "data": statistics
        }
        
    except Exception as e:
        logger.error(f"获取分析统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")


def _build_analysis_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """构建分析任务查询"""
    must_clauses = []
    filter_clauses = []
    
    # 精确匹配
    if params.get("video_id"):
        filter_clauses.append({"term": {"video_id": params["video_id"]}})
    
    if params.get("status"):
        filter_clauses.append({"term": {"analysis_status": params["status"]}})
    
    # 模糊匹配
    if params.get("video_name"):
        must_clauses.append({
            "multi_match": {
                "query": params["video_name"],
                "fields": ["video_name", "original_filename"],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        })
    
    if params.get("template_name"):
        must_clauses.append({
            "nested": {
                "path": "results_summary",
                "query": {
                    "match": {
                        "results_summary.template_name": params["template_name"]
                    }
                }
            }
        })
    
    # 范围查询
    if params.get("min_alerts"):
        filter_clauses.append({
            "range": {"total_alerts": {"gte": params["min_alerts"]}}
        })
    
    # 时间范围
    if params.get("start_date") or params.get("end_date"):
        time_range = {}
        if params.get("start_date"):
            time_range["gte"] = params["start_date"]
        if params.get("end_date"):
            time_range["lte"] = params["end_date"] + "T23:59:59"
        
        filter_clauses.append({
            "range": {"created_at": time_range}
        })
    
    # 构建查询
    query = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses
            }
        },
        "sort": [{"created_at": {"order": "desc"}}]
    }
    
    return query


def _build_alerts_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """构建预警查询"""
    must_clauses = []
    filter_clauses = []
    
    # 精确匹配
    if params.get("video_id"):
        filter_clauses.append({"term": {"video_id": params["video_id"]}})
    
    if params.get("analysis_type"):
        filter_clauses.append({"term": {"analysis_type": params["analysis_type"]}})
    
    if params.get("severity"):
        filter_clauses.append({"term": {"severity": params["severity"]}})
    
    # 模糊匹配
    if params.get("video_name"):
        must_clauses.append({
            "match": {
                "video_name": {
                    "query": params["video_name"],
                    "fuzziness": "AUTO"
                }
            }
        })
    
    # 范围查询
    if params.get("min_confidence"):
        filter_clauses.append({
            "range": {"confidence": {"gte": params["min_confidence"]}}
        })
    
    # 时间范围
    if params.get("start_date") or params.get("end_date"):
        time_range = {}
        if params.get("start_date"):
            time_range["gte"] = params["start_date"]
        if params.get("end_date"):
            time_range["lte"] = params["end_date"] + "T23:59:59"
        
        filter_clauses.append({
            "range": {"created_at": time_range}
        })
    
    # 构建查询
    query = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses
            }
        },
        "sort": [{"created_at": {"order": "desc"}}]
    }
    
    return query


def _build_frame_results_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """构建帧结果查询"""
    filter_clauses = []
    
    # 必须有task_id
    if params.get("task_id"):
        filter_clauses.append({"term": {"task_id": params["task_id"]}})
    
    # 可选筛选条件
    if params.get("has_alert") is not None:
        filter_clauses.append({"term": {"has_alert": params["has_alert"]}})
    
    if params.get("min_confidence"):
        filter_clauses.append({
            "range": {"confidence": {"gte": params["min_confidence"]}}
        })
    
    # 时间戳范围
    if params.get("start_timestamp") or params.get("end_timestamp"):
        time_range = {}
        if params.get("start_timestamp"):
            time_range["gte"] = params["start_timestamp"]
        if params.get("end_timestamp"):
            time_range["lte"] = params["end_timestamp"]
        
        filter_clauses.append({
            "range": {"timestamp": time_range}
        })
    
    # 构建查询
    query = {
        "query": {
            "bool": {
                "filter": filter_clauses
            }
        },
        "sort": [{"frame_index": {"order": "asc"}}]
    }
    
    return query


def _format_terms_aggregation(agg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """格式化terms聚合数据"""
    buckets = agg_data.get("buckets", [])
    return [
        {"key": bucket["key"], "count": bucket["doc_count"]}
        for bucket in buckets
    ]


def _format_date_histogram(agg_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """格式化日期直方图数据"""
    buckets = agg_data.get("buckets", [])
    return [
        {
            "timestamp": bucket["key_as_string"],
            "count": bucket["doc_count"]
        }
        for bucket in buckets
    ]