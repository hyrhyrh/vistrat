"""
数据规范化和处理器
"""
from typing import Dict, List, Any
import statistics as stats
from datetime import datetime
from ..core.types import Intent, ProcessedData
from ..exceptions import DataProcessingException
from ..config import agent_config


class DataProcessor:
    """
    数据处理器

    负责:
    1. 数据规范化
    2. 统计计算
    3. 结果整理
    """

    def process(self, raw_data: Dict[str, Any], intent: Intent) -> ProcessedData:
        """
        处理ES查询结果

        Args:
            raw_data: ES原始数据
            intent: 用户意图

        Returns:
            ProcessedData: 处理后的结构化数据

        Raises:
            DataProcessingException: 处理失败
        """
        try:
            result = ProcessedData()

            # 1. 处理基础统计
            result.summary = self._process_summary(raw_data)

            # 2. 提取表格数据
            result.table_data = self._extract_table_data(raw_data)

            # 3. 计算统计指标
            result.statistics = self._calculate_statistics(result.table_data)

            # 4. 处理聚合数据,生成图表建议
            result.charts = self._process_aggregations(raw_data, intent)

            return result

        except Exception as e:
            raise DataProcessingException(f"数据处理失败: {str(e)}") from e

    def _process_summary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理摘要信息"""
        summary = {}

        # 总数
        total = raw_data.get("hits", {}).get("total", {})
        if isinstance(total, dict):
            summary["total_count"] = total.get("value", 0)
        else:
            summary["total_count"] = total

        # 查询耗时
        summary["took_ms"] = raw_data.get("took", 0)

        return summary

    def _extract_table_data(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取表格数据"""
        table_data = []

        hits = raw_data.get("hits", {}).get("hits", [])
        max_rows = agent_config.report_max_table_rows

        for hit in hits[:max_rows]:
            source = hit.get("_source", {})
            row = {
                "timestamp": source.get("timestamp", ""),
                "type": source.get("type_name", source.get("type", "未知")),
                "stream": source.get("stream_name", ""),
                "confidence": source.get("confidence", 0),
                "image": source.get("image_url", ""),
            }
            table_data.append(row)

        return table_data

    def _calculate_statistics(self, table_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算统计指标"""
        statistics_result = {}

        if not table_data:
            return statistics_result

        # 提取置信度数据
        confidences = [row.get("confidence", 0) for row in table_data if row.get("confidence", 0) > 0]

        if confidences:
            statistics_result["mean_confidence"] = stats.mean(confidences)
            statistics_result["median_confidence"] = stats.median(confidences)
            statistics_result["max_confidence"] = max(confidences)
            statistics_result["min_confidence"] = min(confidences)

            # 标准差(如果数据量足够)
            if len(confidences) > 1:
                statistics_result["std_confidence"] = stats.stdev(confidences)

        return statistics_result

    def _process_aggregations(
        self,
        raw_data: Dict[str, Any],
        intent: Intent
    ) -> List[Dict[str, Any]]:
        """
        处理聚合数据,生成图表建议

        Args:
            raw_data: ES原始数据
            intent: 用户意图

        Returns:
            list: 图表建议列表
        """
        charts = []
        aggs = raw_data.get("aggregations", {})

        # 1. 时间趋势图
        if "trend_over_time" in aggs:
            trend_chart = {
                "type": "line",
                "title": "告警趋势",
                "data": []
            }

            for bucket in aggs["trend_over_time"]["buckets"]:
                trend_chart["data"].append({
                    "time": bucket.get("key_as_string", bucket.get("key")),
                    "count": bucket["doc_count"]
                })

            charts.append(trend_chart)

        # 2. 告警类型分布饼图
        if "distribution_by_type" in aggs:
            type_chart = {
                "type": "pie",
                "title": "告警类型分布",
                "data": []
            }

            for bucket in aggs["distribution_by_type"]["buckets"]:
                type_chart["data"].append({
                    "name": bucket["key"],
                    "value": bucket["doc_count"]
                })

            charts.append(type_chart)

        # 3. 区域分布柱状图
        if "distribution_by_region" in aggs:
            region_chart = {
                "type": "bar",
                "title": "区域告警分布",
                "data": []
            }

            for bucket in aggs["distribution_by_region"]["buckets"]:
                region_chart["data"].append({
                    "name": bucket["key"],
                    "value": bucket["doc_count"]
                })

            charts.append(region_chart)

        # 4. Top告警排行
        if "top_alerts" in aggs:
            top_chart = {
                "type": "bar",
                "title": "Top告警类型",
                "data": []
            }

            for bucket in aggs["top_alerts"]["buckets"]:
                top_chart["data"].append({
                    "name": bucket["key"],
                    "value": bucket["doc_count"]
                })

            charts.append(top_chart)

        return charts
