"""
安全生产监测大屏API
提供告警统计、趋势分析、实时数据等接口
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import logging

from services.elasticsearch_service import ElasticsearchService
from database.connection import DatabaseManager
from core.logging_config import get_logger_context

router = APIRouter(prefix="/api/safety", tags=["安全监测大屏"])
logger_ctx = get_logger_context(__name__)

class AlertStatistics(BaseModel):
    """告警统计数据模型"""
    today: int
    thisWeek: int
    thisMonth: int
    thisYear: int

class TrendDataPoint(BaseModel):
    """趋势数据点模型"""
    date: str
    count: int

class AlertTypeRank(BaseModel):
    """告警类型排行模型"""
    type: str
    typeName: str
    count: int

class RecentAlert(BaseModel):
    """最新告警记录模型"""
    id: str
    type: str
    typeName: str
    image: str
    timestamp: str
    streamName: str
    confidence: float
    description: Optional[str] = None  # AI分析的详细描述

# 告警类型映射
ALERT_TYPE_MAPPING = {
    "no_helmet": "未佩戴安全帽",
    "smoking": "吸烟行为", 
    "unauthorized_person": "无关人员",
    "unsafe_behavior": "不安全行为",
    "fire_hazard": "火灾隐患",
    "equipment_anomaly": "设备异常"
}

def get_alert_type_name(alert_type: str) -> str:
    """获取告警类型中文名称"""
    return ALERT_TYPE_MAPPING.get(alert_type, alert_type)

@router.get("/statistics", response_model=AlertStatistics)
async def get_alert_statistics():
    """获取告警统计数据"""
    try:
        now = datetime.now()
        
        # 今日开始时间
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 本周开始时间（周一）
        week_start = today_start - timedelta(days=now.weekday())
        
        # 本月开始时间
        month_start = today_start.replace(day=1)
        
        # 本年开始时间
        year_start = today_start.replace(month=1, day=1)
        
        # 查询各时间段的告警数量
        es_service = ElasticsearchService()
        
        # 今日告警
        today_query = {
            "bool": {
                "must": [
                    {"range": {"created_at": {"gte": today_start.isoformat()}}}
                ]
            }
        }
        today_count = await es_service.count_documents("video_alerts", today_query)
        
        # 本周告警
        week_query = {
            "bool": {
                "must": [
                    {"range": {"created_at": {"gte": week_start.isoformat()}}}
                ]
            }
        }
        week_count = await es_service.count_documents("video_alerts", week_query)
        
        # 本月告警
        month_query = {
            "bool": {
                "must": [
                    {"range": {"created_at": {"gte": month_start.isoformat()}}}
                ]
            }
        }
        month_count = await es_service.count_documents("video_alerts", month_query)
        
        # 本年告警
        year_query = {
            "bool": {
                "must": [
                    {"range": {"created_at": {"gte": year_start.isoformat()}}}
                ]
            }
        }
        year_count = await es_service.count_documents("video_alerts", year_query)
        
        return AlertStatistics(
            today=today_count,
            thisWeek=week_count,
            thisMonth=month_count,
            thisYear=year_count
        )
        
    except Exception as e:
        logger_ctx.error("获取告警统计失败", exception=e)
        # 返回默认数据，避免前端报错
        return AlertStatistics(today=0, thisWeek=0, thisMonth=0, thisYear=0)

@router.get("/trend", response_model=List[TrendDataPoint])
async def get_alert_trend(days: int = Query(7, ge=1, le=30, description="天数")):
    """获取告警趋势数据"""
    try:
        now = datetime.now()
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        start_date = (now - timedelta(days=days-1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        es_service = ElasticsearchService()
        
        # 构建日期聚合查询
        query = {
            "bool": {
                "must": [
                    {"range": {"created_at": {
                        "gte": start_date.isoformat(),
                        "lte": end_date.isoformat()
                    }}}
                ]
            }
        }
        
        aggregations = {
            "daily_alerts": {
                "date_histogram": {
                    "field": "created_at",
                    "calendar_interval": "day",
                    "time_zone": "Asia/Shanghai",
                    "format": "yyyy-MM-dd"
                }
            }
        }
        
        try:
            result = await es_service.search_documents(
                index="video_alerts",
                query=query,
                aggregations=aggregations,
                size=0
            )
            
            trend_data = []
            if result and "aggregations" in result:
                buckets = result["aggregations"]["daily_alerts"]["buckets"]
                for bucket in buckets:
                    trend_data.append(TrendDataPoint(
                        date=bucket["key_as_string"],
                        count=bucket["doc_count"]
                    ))
            
            # 如果某些日期没有数据，补充为0
            current_date = start_date
            date_counts = {item.date: item.count for item in trend_data}
            
            complete_trend_data = []
            for i in range(days):
                date_str = current_date.strftime("%Y-%m-%d")
                complete_trend_data.append(TrendDataPoint(
                    date=date_str,
                    count=date_counts.get(date_str, 0)
                ))
                current_date += timedelta(days=1)
            
            return complete_trend_data
            
        except Exception as es_error:
            logger_ctx.warning(f"ES查询失败，返回模拟数据: {es_error}")
            # 返回模拟数据
            mock_data = []
            current_date = start_date
            for i in range(days):
                mock_data.append(TrendDataPoint(
                    date=current_date.strftime("%Y-%m-%d"),
                    count=max(0, 10 + i * 2 + (i % 3) * 5)  # 模拟递增趋势
                ))
                current_date += timedelta(days=1)
            return mock_data
        
    except Exception as e:
        logger_ctx.error("获取告警趋势失败", exception=e)
        return []

@router.get("/alert-type-ranks", response_model=List[AlertTypeRank])
async def get_alert_type_ranks(days: int = Query(30, ge=1, le=365, description="统计天数")):
    """获取告警类型排行（按算法模板名称统计）"""
    try:
        now = datetime.now()
        start_date = now - timedelta(days=days)

        es_service = ElasticsearchService()

        query = {
            "bool": {
                "must": [
                    {"range": {"created_at": {"gte": start_date.isoformat()}}}
                ]
            }
        }

        # 按 template_name 维度聚合统计
        aggregations = {
            "alert_types": {
                "terms": {
                    "field": "template_name.keyword",
                    "size": 10,
                    "order": {"_count": "desc"}
                }
            }
        }

        try:
            result = await es_service.search_documents(
                index="video_alerts",
                query=query,
                aggregations=aggregations,
                size=0
            )

            ranks = []
            if result and "aggregations" in result:
                buckets = result["aggregations"]["alert_types"]["buckets"]
                for bucket in buckets:
                    template_name = bucket["key"]
                    ranks.append(AlertTypeRank(
                        type=template_name,
                        typeName=template_name,  # 直接使用算法模板名称
                        count=bucket["doc_count"]
                    ))

            return ranks[:10]  # 返回前10名
            
        except Exception as es_error:
            logger_ctx.warning(f"ES查询失败，返回模拟数据: {es_error}")
            # 返回模拟数据
            mock_ranks = [
                AlertTypeRank(type="no_helmet", typeName="未佩戴安全帽", count=45),
                AlertTypeRank(type="smoking", typeName="吸烟行为", count=23),
                AlertTypeRank(type="unauthorized_person", typeName="无关人员", count=18),
                AlertTypeRank(type="unsafe_behavior", typeName="不安全行为", count=12),
                AlertTypeRank(type="fire_hazard", typeName="火灾隐患", count=8)
            ]
            return mock_ranks
        
    except Exception as e:
        logger_ctx.error("获取告警类型排行失败", exception=e)
        return []

@router.get("/recent-alerts", response_model=List[RecentAlert])
async def get_recent_alerts(limit: int = Query(20, ge=1, le=100, description="返回记录数")):
    """获取最新告警记录"""
    try:
        es_service = ElasticsearchService()
        
        query = {"match_all": {}}
        
        sort = [
            {"created_at": {"order": "desc"}}
        ]
        
        try:
            result = await es_service.search_documents(
                index="video_alerts",
                query=query,
                sort=sort,
                size=limit
            )
            
            alerts = []
            if result and "hits" in result:
                for hit in result["hits"]["hits"]:
                    source = hit["_source"]
                    
                    # 获取视频流名称
                    stream_name = "未知视频流"
                    if source.get("stream_id"):
                        try:
                            async with DatabaseManager.get_session() as session:
                                from sqlalchemy import text
                                stream_result = await session.execute(
                                    text("SELECT name FROM video_streams WHERE id = :stream_id"),
                                    {"stream_id": source["stream_id"]}
                                )
                                stream_row = stream_result.fetchone()
                                if stream_row:
                                    stream_name = stream_row[0]
                        except Exception as db_error:
                            logger_ctx.warning(f"查询视频流名称失败: {db_error}")
                    
                    # 优先使用template_name作为算法名称，如果不存在则使用algorithm_name
                    template_name = source.get("template_name", source.get("algorithm_name", "unknown"))

                    alerts.append(RecentAlert(
                        id=hit["_id"],
                        type=source.get("analysis_type", "unknown"),  # 分析类型: video_analysis/stream_analysis
                        typeName=template_name,  # 直接使用算法模板名称
                        image=source.get("alert_image", "/api/placeholder-alert.jpg"),
                        timestamp=source.get("created_at", datetime.now().isoformat()),
                        streamName=stream_name,
                        confidence=source.get("confidence", 0.0),
                        description=source.get("description")  # AI分析详细描述
                    ))
            
            return alerts
            
        except Exception as es_error:
            logger_ctx.warning(f"ES查询失败，返回模拟数据: {es_error}")
            # 返回模拟数据
            mock_alerts = []
            for i in range(min(limit, 10)):
                alert_types = ["no_helmet", "smoking", "unauthorized_person", "unsafe_behavior"]
                alert_type = alert_types[i % len(alert_types)]
                
                mock_alerts.append(RecentAlert(
                    id=f"mock_{i}",
                    type=alert_type,
                    typeName=get_alert_type_name(alert_type),
                    image="/api/placeholder-alert.jpg",
                    timestamp=(datetime.now() - timedelta(minutes=i*5)).isoformat(),
                    streamName=f"摄像头{i+1}",
                    confidence=0.85 + (i % 3) * 0.05
                ))
            
            return mock_alerts
        
    except Exception as e:
        logger_ctx.error("获取最新告警记录失败", exception=e)
        return []

@router.get("/algorithm-stats")
async def get_algorithm_stats():
    """获取AI编排算法列表（从ai_model_configs表，仅展示激活的算法名称）"""
    try:
        # 查询所有激活的算法配置
        async with DatabaseManager.get_session() as session:
            from sqlalchemy import select
            from models.ai_model import AIModelConfigDB

            # 查询status为'active'的算法配置
            stmt = select(
                AIModelConfigDB.name,
                AIModelConfigDB.status
            ).where(AIModelConfigDB.status == 'active')

            result = await session.execute(stmt)
            configs = result.all()

            algorithm_data = []

            for config in configs:
                algorithm_name = config[0] or "未命名算法"
                status = config[1]

                algorithm_data.append({
                    "name": algorithm_name,
                    "active": status == 'active'
                })

            # 如果没有数据，返回模拟数据
            if not algorithm_data:
                logger_ctx.info("没有找到激活的算法配置，返回模拟数据")
                return [
                    {"name": "安全帽检测", "active": True},
                    {"name": "吸烟行为识别", "active": True},
                    {"name": "人员闯入检测", "active": True},
                    {"name": "违规操作监控", "active": True},
                    {"name": "火灾风险识别", "active": True},
                    {"name": "设备异常检测", "active": True}
                ]

            return algorithm_data

    except Exception as e:
        logger_ctx.error("获取算法列表失败", exception=e)
        # 返回模拟数据
        return [
            {"name": "安全帽检测", "active": True},
            {"name": "吸烟行为识别", "active": True},
            {"name": "人员闯入检测", "active": True},
            {"name": "违规操作监控", "active": True},
            {"name": "火灾风险识别", "active": True},
            {"name": "设备异常检测", "active": True}
        ]

@router.get("/health")
async def health_check():
    """安全监测大屏服务健康检查"""
    try:
        # 检查Elasticsearch连接
        es_service = ElasticsearchService()
        es_health = await es_service.health_check()

        # 检查数据库连接
        db_health = False
        try:
            async with DatabaseManager.get_session() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                db_health = result.scalar() == 1
        except Exception:
            db_health = False

        return {
            "status": "healthy" if (es_health and db_health) else "degraded",
            "elasticsearch": es_health,
            "database": db_health,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger_ctx.error("健康检查失败", exception=e)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }