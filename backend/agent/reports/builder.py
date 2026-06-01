"""
报告构建器
"""
from typing import Dict, Any
from datetime import datetime
from ..core.types import Intent, ProcessedData, ReportOutput
from ..exceptions import ReportGenerationException
from ..config import agent_config
from .html_builder import HTMLReportBuilder


class ReportBuilder:
    """
    报告构建器

    支持格式:
    - Markdown: 富文本(用于对话框显示)
    - HTML: 单页报告(移动端适配,ECharts可视化)
    - JSON: 结构化数据
    """

    def __init__(self):
        self.html_builder = HTMLReportBuilder()

    def build(
        self,
        question: str,
        intent: Intent,
        data: ProcessedData,
        insights: str
    ) -> ReportOutput:
        """
        生成报告

        Args:
            question: 用户问题
            intent: 意图
            data: 处理后的数据
            insights: AI分析结果

        Returns:
            ReportOutput: 报告输出

        Raises:
            ReportGenerationException: 生成失败
        """
        try:
            metadata = {
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "data_count": data.summary.get("total_count", 0),
                "query_time_ms": data.summary.get("took_ms", 0),
                "intent_summary": intent.summary()
            }

            markdown = self._build_markdown(question, data, insights)
            html = self.html_builder.build(question, intent, data, insights)
            json_data = self._build_json(question, data, insights, metadata)

            return ReportOutput(
                markdown=markdown,
                html=html,
                json_data=json_data,
                metadata=metadata
            )

        except Exception as e:
            raise ReportGenerationException(f"报告生成失败: {str(e)}") from e

    def _build_markdown(
        self,
        question: str,
        data: ProcessedData,
        insights: str
    ) -> str:
        """
        生成Markdown格式报告

        Args:
            question: 用户问题
            data: 处理后的数据
            insights: AI分析结果

        Returns:
            str: Markdown文本
        """
        md = f"# {question}\n\n"

        # AI分析部分
        md += "## 📊 AI 分析\n\n"
        md += f"{insights}\n\n"

        # 数据摘要部分
        md += "---\n\n"
        md += "## 📈 数据摘要\n\n"

        total_count = data.summary.get("total_count", 0)
        md += f"- **告警总数**: {total_count}\n"

        if data.statistics:
            mean_conf = data.statistics.get("mean_confidence", 0)
            md += f"- **平均置信度**: {mean_conf:.1%}\n"

        # 图表建议
        if data.charts:
            md += "\n## 📉 可视化建议\n\n"
            for chart in data.charts:
                chart_type = chart.get("type", "未知")
                title = chart.get("title", "图表")
                icon = {"line": "📈", "pie": "🥧", "bar": "📊"}.get(chart_type, "📉")
                md += f"- {icon} **{title}** ({chart_type})\n"

        # 数据明细(可选)
        if data.table_data and len(data.table_data) <= 10:
            md += "\n## 📋 数据明细\n\n"
            md += "| 时间 | 类型 | 位置 | 置信度 |\n"
            md += "|------|------|------|--------|\n"

            for row in data.table_data[:10]:
                # 优先使用 created_at，如果没有则使用 video_time
                timestamp = row.get("created_at", row.get("video_time", "-"))
                if isinstance(timestamp, str) and len(timestamp) > 16:
                    timestamp = timestamp[:16]  # 只取日期和小时分钟部分
                # 使用算法名称或模板名称作为告警类型
                type_name = row.get("algorithm_name", row.get("template_name", row.get("type", "未知")))
                stream = row.get("location", row.get("stream", "-"))
                confidence = row.get("confidence", 0)
                md += f"| {timestamp} | {type_name} | {stream} | {confidence:.1%} |\n"

        return md

    def _build_json(
        self,
        question: str,
        data: ProcessedData,
        insights: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成JSON格式报告

        Args:
            question: 用户问题
            data: 处理后的数据
            insights: AI分析结果
            metadata: 元数据

        Returns:
            dict: JSON数据
        """
        return {
            "question": question,
            "insights": insights,
            "summary": data.summary,
            "statistics": data.statistics,
            "charts": data.charts,
            "table_data": data.table_data[:agent_config.report_max_table_rows],
            "metadata": metadata
        }
