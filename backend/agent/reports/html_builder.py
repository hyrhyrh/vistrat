"""
HTML报告生成器
支持响应式设计、图表可视化、PDF导出
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from jinja2 import Template
import json

from ..core.types import Intent, ProcessedData, ReportOutput
from ..exceptions import ReportGenerationException


class HTMLReportBuilder:
    """
    HTML报告生成器

    功能:
    - 响应式设计(移动端适配)
    - ECharts图表可视化
    - 主题切换(亮色/暗色)
    - 打印优化
    """

    def __init__(self):
        self.template = self._load_template()

    def build(
        self,
        question: str,
        intent: Intent,
        data: ProcessedData,
        insights: str
    ) -> str:
        """
        生成完整HTML报告

        Args:
            question: 用户问题
            intent: 意图分析结果
            data: 处理后的数据
            insights: AI分析内容(Markdown格式)

        Returns:
            str: HTML报告内容

        Raises:
            ReportGenerationException: 生成失败
        """
        try:
            # 准备模板数据
            template_data = {
                "question": question,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "intent": self._format_intent(intent),
                "summary": data.summary,
                "statistics": data.statistics,
                "insights": self._markdown_to_html(insights),
                "charts": self._prepare_charts(data.charts),
                "table_data": data.table_data[:20],  # 最多显示20行
                "metadata": {
                    "total_count": data.summary.get("total_count", 0),
                    "query_time": data.summary.get("took_ms", 0)
                }
            }

            # 渲染模板
            html = self.template.render(**template_data)
            return html

        except Exception as e:
            raise ReportGenerationException(f"HTML报告生成失败: {str(e)}") from e

    def _load_template(self) -> Template:
        """加载Jinja2模板"""
        template_str = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI分析报告 - {{ question }}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        /* 头部样式 */
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 16px;
            font-weight: 700;
        }

        .header-meta {
            display: flex;
            gap: 24px;
            flex-wrap: wrap;
            opacity: 0.9;
            font-size: 0.95rem;
        }

        .header-meta-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        /* 主要内容区域 */
        .content {
            padding: 40px;
        }

        .section {
            margin-bottom: 40px;
            background: #f8f9fa;
            border-radius: 12px;
            padding: 32px;
            border-left: 4px solid #667eea;
        }

        .section-title {
            font-size: 1.8rem;
            margin-bottom: 24px;
            color: #2d3748;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .section-title .icon {
            font-size: 2rem;
        }

        /* AI分析内容 */
        .insights {
            background: white;
            padding: 24px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }

        .insights h3 {
            color: #667eea;
            margin-top: 24px;
            margin-bottom: 12px;
            font-size: 1.4rem;
        }

        .insights p {
            margin-bottom: 16px;
            color: #4a5568;
        }

        .insights ul, .insights ol {
            margin-left: 24px;
            margin-bottom: 16px;
        }

        .insights li {
            margin-bottom: 8px;
            color: #4a5568;
        }

        .insights strong {
            color: #2d3748;
            font-weight: 600;
        }

        /* 数据摘要卡片 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: white;
            padding: 24px;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            text-align: center;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 8px;
        }

        .stat-label {
            color: #718096;
            font-size: 0.9rem;
        }

        /* 图表容器 */
        .chart-container {
            background: white;
            padding: 24px;
            border-radius: 8px;
            margin-bottom: 24px;
            border: 1px solid #e2e8f0;
        }

        .chart {
            width: 100%;
            height: 400px;
        }

        /* 数据表格 */
        .data-table {
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }

        .data-table table {
            width: 100%;
            border-collapse: collapse;
        }

        .data-table th {
            background: #667eea;
            color: white;
            padding: 16px;
            text-align: left;
            font-weight: 600;
        }

        .data-table td {
            padding: 14px 16px;
            border-bottom: 1px solid #e2e8f0;
        }

        .data-table tr:hover {
            background: #f7fafc;
        }

        /* 页脚 */
        .footer {
            background: #2d3748;
            color: white;
            padding: 32px 40px;
            text-align: center;
        }

        .footer p {
            opacity: 0.8;
            font-size: 0.9rem;
        }

        /* 徽章 */
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .badge-success {
            background: #c6f6d5;
            color: #22543d;
        }

        .badge-info {
            background: #bee3f8;
            color: #2c5282;
        }

        /* 响应式设计 */
        @media (max-width: 768px) {
            body {
                padding: 10px;
            }

            .header h1 {
                font-size: 1.8rem;
            }

            .content {
                padding: 20px;
            }

            .section {
                padding: 20px;
            }

            .section-title {
                font-size: 1.4rem;
            }

            .stat-value {
                font-size: 2rem;
            }

            .chart {
                height: 300px;
            }
        }

        /* 打印样式 */
        @media print {
            body {
                background: white;
                padding: 0;
            }

            .container {
                box-shadow: none;
                border-radius: 0;
            }

            .header {
                background: #667eea !important;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            .chart {
                page-break-inside: avoid;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>{{ question }}</h1>
            <div class="header-meta">
                <div class="header-meta-item">
                    <span>📅</span>
                    <span>生成时间: {{ timestamp }}</span>
                </div>
                <div class="header-meta-item">
                    <span>📊</span>
                    <span>数据量: {{ metadata.total_count }} 条</span>
                </div>
                <div class="header-meta-item">
                    <span>⚡</span>
                    <span>查询耗时: {{ metadata.query_time }} ms</span>
                </div>
            </div>
        </div>

        <!-- 主要内容 -->
        <div class="content">
            <!-- AI分析 -->
            <div class="section">
                <h2 class="section-title">
                    <span class="icon">🤖</span>
                    AI 智能分析
                </h2>
                <div class="insights">
                    {{ insights | safe }}
                </div>
            </div>

            <!-- 数据摘要 -->
            <div class="section">
                <h2 class="section-title">
                    <span class="icon">📈</span>
                    数据摘要
                </h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-value">{{ summary.total_count }}</div>
                        <div class="stat-label">告警总数</div>
                    </div>
                    {% if statistics.mean_confidence %}
                    <div class="stat-card">
                        <div class="stat-value">{{ "%.1f" | format(statistics.mean_confidence * 100) }}%</div>
                        <div class="stat-label">平均置信度</div>
                    </div>
                    {% endif %}
                    {% if statistics.max_confidence %}
                    <div class="stat-card">
                        <div class="stat-value">{{ "%.1f" | format(statistics.max_confidence * 100) }}%</div>
                        <div class="stat-label">最高置信度</div>
                    </div>
                    {% endif %}
                    <div class="stat-card">
                        <div class="stat-value">{{ summary.took_ms }} ms</div>
                        <div class="stat-label">查询时间</div>
                    </div>
                </div>
            </div>

            <!-- 数据可视化 -->
            {% if charts %}
            <div class="section">
                <h2 class="section-title">
                    <span class="icon">📉</span>
                    数据可视化
                </h2>
                {% for chart in charts %}
                <div class="chart-container">
                    <h3>{{ chart.title }}</h3>
                    <div id="chart_{{ loop.index }}" class="chart"></div>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            <!-- 数据明细 -->
            {% if table_data %}
            <div class="section">
                <h2 class="section-title">
                    <span class="icon">📋</span>
                    数据明细
                    <span class="badge badge-info">前 {{ table_data | length }} 条</span>
                </h2>
                <div class="data-table">
                    <table>
                        <thead>
                            <tr>
                                <th>时间</th>
                                <th>类型</th>
                                <th>位置</th>
                                <th>置信度</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for row in table_data %}
                            <tr>
                                <td>{{ row.get("created_at", row.get("video_time", "-")) }}</td>
                                <td>{{ row.get("algorithm_name", row.get("template_name", row.get("type", "未知"))) }}</td>
                                <td>{{ row.get("location", row.get("stream", "-")) }}</td>
                                <td>{{ "%.1f" | format(row.get("confidence", 0) * 100) }}%</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            {% endif %}
        </div>

        <!-- 页脚 -->
        <div class="footer">
            <p>🤖 AI智能分析系统 | Powered by DeepSeek AI</p>
            <p>© 2025 Vistrat（观策）. All rights reserved.</p>
        </div>
    </div>

    <script>
        // ECharts图表渲染
        {% for chart in charts %}
        (function() {
            var chart = echarts.init(document.getElementById('chart_{{ loop.index }}'));
            var option = {{ chart.config | tojson }};
            chart.setOption(option);

            // 响应式
            window.addEventListener('resize', function() {
                chart.resize();
            });
        })();
        {% endfor %}
    </script>
</body>
</html>'''
        return Template(template_str)

    def _format_intent(self, intent: Intent) -> Dict[str, Any]:
        """格式化意图信息"""
        return {
            "time_label": intent.time_window.label if intent.time_window else "全部",
            "metrics": ", ".join(intent.metrics) if intent.metrics else "count",
            "query_type": intent.query_type,
            "entities": ", ".join(intent.entities) if intent.entities else "无"
        }

    def _markdown_to_html(self, markdown_text: str) -> str:
        """
        将Markdown转换为HTML
        使用简单的替换规则
        """
        html = markdown_text

        # 标题
        html = html.replace("### ", "<h3>")
        html = html.replace("\n\n", "</p><p>")
        html = html.replace("**", "<strong>").replace("**", "</strong>")

        # 包装段落
        if not html.startswith("<h3>"):
            html = f"<p>{html}</p>"

        # 修复标题闭合
        html = html.replace("<h3>", "<h3>").replace("\n", "</h3>\n", 1)

        return html

    def _prepare_charts(self, charts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        准备图表配置(ECharts格式)
        """
        prepared_charts = []

        for chart in charts:
            chart_type = chart.get("type", "line")
            title = chart.get("title", "图表")
            data = chart.get("data", [])

            # 构建ECharts配置
            if chart_type == "line":
                config = self._build_line_chart(title, data)
            elif chart_type == "pie":
                config = self._build_pie_chart(title, data)
            elif chart_type == "bar":
                config = self._build_bar_chart(title, data)
            else:
                continue

            prepared_charts.append({
                "title": title,
                "type": chart_type,
                "config": config
            })

        return prepared_charts

    def _build_line_chart(self, title: str, data: List[Dict]) -> Dict:
        """构建折线图配置"""
        return {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": [item.get("label", "") for item in data]
            },
            "yAxis": {"type": "value"},
            "series": [{
                "data": [item.get("value", 0) for item in data],
                "type": "line",
                "smooth": True,
                "itemStyle": {"color": "#667eea"}
            }]
        }

    def _build_pie_chart(self, title: str, data: List[Dict]) -> Dict:
        """构建饼图配置"""
        return {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "item"},
            "series": [{
                "type": "pie",
                "radius": "60%",
                "data": [
                    {"name": item.get("label", ""), "value": item.get("value", 0)}
                    for item in data
                ],
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }]
        }

    def _build_bar_chart(self, title: str, data: List[Dict]) -> Dict:
        """构建柱状图配置"""
        return {
            "title": {"text": title, "left": "center"},
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "category",
                "data": [item.get("label", "") for item in data]
            },
            "yAxis": {"type": "value"},
            "series": [{
                "data": [item.get("value", 0) for item in data],
                "type": "bar",
                "itemStyle": {"color": "#667eea"}
            }]
        }
