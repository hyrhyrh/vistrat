"""
每日预警报表API
提供独立的报表页面数据查询接口，用于企业微信推送
"""

import logging
from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field
from services.elasticsearch_service import elasticsearch_service
from config.settings import ElasticsearchConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daily-alerts-report", tags=["每日预警报表"])


class FilterOptions(BaseModel):
    """筛选选项响应模型"""
    algorithm_names: List[str] = Field(description="算法名称列表")
    camera_names: List[str] = Field(description="相机名称列表")


class AlertRecord(BaseModel):
    """告警记录响应模型"""
    id: str = Field(description="告警ID")
    camera_name: str = Field(description="相机名称")
    algorithm_name: str = Field(description="算法名称")
    image_url: str = Field(description="图片地址")
    confidence: float = Field(description="置信度")
    description: str = Field(description="AI描述")
    created_at: str = Field(description="创建时间")


class AlertsResponse(BaseModel):
    """告警查询响应模型"""
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页记录数")
    records: List[AlertRecord] = Field(description="告警记录列表")


@router.get("/filter-options", response_model=FilterOptions)
async def get_filter_options():
    """
    获取筛选选项

    返回所有去重后的算法名称和相机名称列表
    """
    try:
        # 构建聚合查询，获取所有唯一的算法名称和相机名称
        query = {
            "size": 0,  # 不返回文档，只返回聚合结果
            "aggs": {
                "unique_algorithms": {
                    "terms": {
                        "field": "algorithm_name.keyword",
                        "size": 1000,  # 最多返回1000个不同的算法
                        "order": {"_key": "asc"}  # 按名称排序
                    }
                },
                "unique_cameras": {
                    "terms": {
                        "field": "camera_name.keyword",
                        "size": 1000,  # 最多返回1000个不同的相机
                        "order": {"_key": "asc"}  # 按名称排序
                    }
                }
            }
        }

        # 执行查询
        result = await elasticsearch_service.search_documents(
            index=ElasticsearchConfig.ALERTS_INDEX,
            query={"match_all": {}},
            size=0,
            aggregations=query["aggs"]
        )

        # 提取聚合结果
        algorithm_buckets = result.get("aggregations", {}).get("unique_algorithms", {}).get("buckets", [])
        camera_buckets = result.get("aggregations", {}).get("unique_cameras", {}).get("buckets", [])

        algorithm_names = [bucket["key"] for bucket in algorithm_buckets if bucket["key"]]
        camera_names = [bucket["key"] for bucket in camera_buckets if bucket["key"]]

        return FilterOptions(
            algorithm_names=algorithm_names,
            camera_names=camera_names
        )

    except Exception as e:
        logger.error(f"获取筛选选项失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取筛选选项失败: {str(e)}")


@router.get("/alerts", response_model=AlertsResponse)
async def get_daily_alerts(
    algorithm_name: Optional[str] = Query(None, description="算法名称"),
    camera_name: Optional[str] = Query(None, description="相机名称"),
    date_str: Optional[str] = Query(None, description="日期(YYYY-MM-DD格式)，默认当天"),
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(5, ge=1, le=100, description="每页记录数，默认5条")
):
    """
    查询每日告警数据

    支持按算法名称、相机名称和日期筛选，分页展示
    """
    try:
        # 处理日期参数
        if date_str:
            try:
                query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")
        else:
            # 默认查询当天
            query_date = date.today()

        # 构建日期范围查询（查询当天的数据）
        start_time = datetime.combine(query_date, datetime.min.time()).isoformat()
        end_time = datetime.combine(query_date, datetime.max.time()).isoformat()

        # 构建查询条件
        must_conditions = [
            {
                "range": {
                    "created_at": {
                        "gte": start_time,
                        "lte": end_time
                    }
                }
            }
        ]

        # 添加算法名称筛选
        if algorithm_name:
            must_conditions.append({
                "term": {
                    "algorithm_name.keyword": algorithm_name
                }
            })

        # 添加相机名称筛选
        if camera_name:
            must_conditions.append({
                "term": {
                    "camera_name.keyword": camera_name
                }
            })

        # 构建完整查询
        query = {
            "bool": {
                "must": must_conditions
            }
        }

        # 计算分页偏移量
        from_index = (page - 1) * page_size

        # 执行查询
        result = await elasticsearch_service.search_documents(
            index=ElasticsearchConfig.ALERTS_INDEX,
            query=query,
            size=page_size,
            from_=from_index,
            sort=[{"created_at": {"order": "desc"}}]  # 按创建时间倒序
        )

        # 解析结果
        hits = result.get("hits", {})
        total = hits.get("total", {}).get("value", 0)
        records = []

        # 辅助函数：将完整URL转换为相对路径
        def convert_image_url(url: str) -> str:
            """将图片URL转换为相对路径，让前端自己拼接域名"""
            if not url:
                return url

            # 如果已经是相对路径，直接返回
            if url.startswith("/api/"):
                return url

            # 从完整URL中提取相对路径部分（/api/image-proxy/...）
            # 支持各种格式：
            # http://localhost:16532/api/image-proxy/... → /api/image-proxy/...
            # http://<INTERNAL_HOST>:16532/api/image-proxy/... → /api/image-proxy/...
            if "/api/" in url:
                return "/api/" + url.split("/api/", 1)[1]

            return url

        for hit in hits.get("hits", []):
            source = hit["_source"]
            raw_image_url = source.get("image_url", "")
            # 转换图片URL为公网地址
            public_image_url = convert_image_url(raw_image_url)

            records.append(AlertRecord(
                id=hit["_id"],
                camera_name=source.get("camera_name", "未知相机"),
                algorithm_name=source.get("algorithm_name", "未知算法"),
                image_url=public_image_url,
                confidence=source.get("confidence", 0.0),
                description=source.get("description", ""),
                created_at=source.get("created_at", "")
            ))

        return AlertsResponse(
            total=total,
            page=page,
            page_size=page_size,
            records=records
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询每日告警数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")
