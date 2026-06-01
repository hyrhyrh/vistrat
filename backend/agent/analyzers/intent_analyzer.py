"""
意图分析器(规则引擎版本)
"""
import re
from typing import Optional
from ..core.types import Intent, TimeWindow
from ..exceptions import IntentAnalysisException
from .time_parser import TimeParser


class IntentAnalyzer:
    """
    意图分析器(规则引擎版本)

    负责从自然语言问题中提取:
    1. 时间范围
    2. 实体(区域、设备、告警类型)
    3. 指标(数量、趋势、分布)
    4. 查询类型
    """

    # 实体识别规则
    ENTITY_PATTERNS = {
        "alert_type": [
            r"未戴安全帽", r"没戴安全帽", r"安全帽",
            r"吸烟", r"抽烟",
            r"无关人员", r"闲杂人员", r"陌生人",
            r"违规操作", r"违章", r"不安全行为"
        ],
        "region": [
            r"区域[A-Z]", r"[A-Z]区",
            r"生产区", r"车间",
            r"仓储区", r"仓库",
            r"入口", r"出口", r"通道",
            r"办公区"
        ],
        "severity": [
            r"高危", r"严重", r"紧急",
            r"中危", r"中等",
            r"低危", r"轻微"
        ],
    }

    # 指标识别规则
    METRIC_KEYWORDS = {
        "count": [r"多少", r"数量", r"有几", r"统计", r"总共", r"一共"],
        "trend": [r"趋势", r"变化", r"增长", r"下降", r"波动"],
        "distribution": [r"分布", r"占比", r"比例", r"百分比"],
        "top": [r"最多", r"排名", r"前", r"top"],
        "comparison": [r"对比", r"比较", r"相比"],
    }

    # 查询类型关键词
    QUERY_TYPE_KEYWORDS = {
        "comparison": [r"对比", r"比较", r"相比"],
        "trend": [r"趋势", r"变化"],
        "anomaly": [r"异常", r"不正常"],
        "report": [r"报告", r"分析报告", r"总结"],
    }

    def __init__(self):
        """初始化意图分析器"""
        self.time_parser = TimeParser()

    async def analyze(self, question: str) -> Intent:
        """
        分析用户问题,提取意图

        Args:
            question: 用户问题

        Returns:
            Intent: 结构化意图

        Raises:
            IntentAnalysisException: 分析失败
        """
        try:
            intent = Intent()

            # 1. 解析时间窗口
            intent.time_window = self.time_parser.parse(question)

            # 如果没有识别到时间,默认使用今天
            if not intent.time_window:
                intent.time_window = TimeParser._get_today()

            # 2. 识别实体
            intent.entities = self._extract_entities(question)

            # 3. 识别指标
            intent.metrics = self._extract_metrics(question)

            # 默认指标: count
            if not intent.metrics:
                intent.metrics.append("count")

            # 4. 判断查询类型
            intent.query_type = self._determine_query_type(question)

            # 5. 判断聚合级别
            intent.aggregation_level = self._determine_aggregation_level(question)

            # 6. 提取过滤条件
            intent.filters = self._extract_filters(question)

            return intent

        except Exception as e:
            raise IntentAnalysisException(f"意图分析失败: {str(e)}") from e

    def _extract_entities(self, question: str) -> list:
        """提取实体"""
        entities = []

        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                matches = re.finditer(pattern, question)
                for match in matches:
                    entity = match.group(0)
                    if entity not in entities:
                        entities.append(entity)

        return entities

    def _extract_metrics(self, question: str) -> list:
        """识别指标"""
        metrics = []

        for metric, keywords in self.METRIC_KEYWORDS.items():
            for keyword in keywords:
                if re.search(keyword, question):
                    if metric not in metrics:
                        metrics.append(metric)
                    break

        return metrics

    def _determine_query_type(self, question: str) -> str:
        """判断查询类型"""
        for query_type, keywords in self.QUERY_TYPE_KEYWORDS.items():
            for keyword in keywords:
                if re.search(keyword, question):
                    return query_type

        # 默认统计查询
        return "statistics"

    def _determine_aggregation_level(self, question: str) -> str:
        """判断聚合级别"""
        if re.search(r"小时|每小时", question):
            return "hour"
        elif re.search(r"天|每天|日|每日", question):
            return "day"
        elif re.search(r"周|每周|星期", question):
            return "week"
        elif re.search(r"月|每月", question):
            return "month"

        # 默认按天聚合
        return "day"

    def _extract_filters(self, question: str) -> dict:
        """提取其他过滤条件"""
        filters = {}

        # 检查是否需要高置信度过滤
        if re.search(r"高置信度|可靠", question):
            filters["min_confidence"] = 0.8

        return filters
