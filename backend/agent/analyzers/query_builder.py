"""
Elasticsearch查询构建器
"""
from typing import Dict, Any
from ..core.types import Intent
from ..exceptions import QueryBuildException
from ..config import agent_config


class QueryBuilder:
    """
    ES查询构建器

    根据用户意图生成Elasticsearch DSL查询
    """

    def __init__(self):
        """初始化查询构建器"""
        self.default_size = agent_config.default_query_size
        self.max_size = agent_config.max_query_size

    def build(self, intent: Intent) -> Dict[str, Any]:
        """
        构建ES查询

        Args:
            intent: 用户意图

        Returns:
            dict: ES查询DSL

        Raises:
            QueryBuildException: 构建失败
        """
        try:
            query = {
                "query": {
                    "bool": {
                        "must": [],
                        "filter": []
                    }
                },
                "size": min(self.default_size, self.max_size),
                "sort": [{"timestamp": {"order": "desc"}}]
            }

            # 1. 添加时间范围过滤
            if intent.time_window:
                # created_at 字段存储的是毫秒级时间戳,使用epoch_millis格式查询
                start_ms = int(intent.time_window.start.timestamp() * 1000)
                end_ms = int(intent.time_window.end.timestamp() * 1000)

                query["query"]["bool"]["filter"].append({
                    "range": {
                        "created_at": {
                            "gte": start_ms,
                            "lte": end_ms,
                            "format": "epoch_millis"
                        }
                    }
                })

            # 2. 添加实体过滤
            if intent.entities:
                # 使用should实现OR逻辑(任一实体匹配即可)
                entity_queries = []
                for entity in intent.entities:
                    entity_queries.append({
                        "match": {
                            "type_name": entity
                        }
                    })

                if entity_queries:
                    query["query"]["bool"]["must"].append({
                        "bool": {
                            "should": entity_queries,
                            "minimum_should_match": 1
                        }
                    })

            # 3. 添加置信度过滤
            if "min_confidence" in intent.filters:
                query["query"]["bool"]["filter"].append({
                    "range": {
                        "confidence": {
                            "gte": intent.filters["min_confidence"]
                        }
                    }
                })

            # 4. 构建聚合
            if intent.query_type in ["statistics", "trend", "distribution"]:
                query["aggs"] = self._build_aggregations(intent)

            # 5. 调整size(如果只需要聚合结果,可以减少返回文档数)
            if "distribution" in intent.metrics and intent.query_type != "statistics":
                query["size"] = 0  # 只返回聚合,不返回文档

            return query

        except Exception as e:
            raise QueryBuildException(f"构建查询失败: {str(e)}") from e

    def _build_aggregations(self, intent: Intent) -> Dict[str, Any]:
        """
        构建聚合查询

        Args:
            intent: 用户意图

        Returns:
            dict: 聚合配置
        """
        aggs = {}

        # 1. 时间趋势聚合
        if "trend" in intent.metrics or intent.query_type == "trend":
            interval_map = {
                "hour": "1h",
                "day": "1d",
                "week": "1w",
                "month": "1M"
            }
            interval = interval_map.get(intent.aggregation_level, "1d")

            aggs["trend_over_time"] = {
                "date_histogram": {
                    "field": "timestamp",
                    "calendar_interval": interval,
                    "time_zone": "Asia/Shanghai",
                    "min_doc_count": 0
                }
            }

        # 2. 告警类型分布聚合
        if "distribution" in intent.metrics or intent.query_type == "statistics":
            aggs["distribution_by_type"] = {
                "terms": {
                    "field": "type_name.keyword",
                    "size": agent_config.report_chart_max_items
                }
            }

        # 3. 区域分布聚合
        if any("区域" in e or "区" in e for e in intent.entities):
            aggs["distribution_by_region"] = {
                "terms": {
                    "field": "stream_name.keyword",
                    "size": agent_config.report_chart_max_items
                }
            }

        # 4. 严重程度聚合(如果有)
        if any(s in str(intent.entities) for s in ["高危", "中危", "低危"]):
            aggs["distribution_by_severity"] = {
                "terms": {
                    "field": "severity.keyword",
                    "size": 5
                }
            }

        # 5. Top告警聚合
        if "top" in intent.metrics:
            aggs["top_alerts"] = {
                "terms": {
                    "field": "type_name.keyword",
                    "size": 10,
                    "order": {"_count": "desc"}
                }
            }

        # 6. 置信度统计
        aggs["confidence_stats"] = {
            "stats": {
                "field": "confidence"
            }
        }

        return aggs
