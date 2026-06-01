"""
Qwen大模型客户端(用于Agent数据分析)
"""
import httpx
import json
import asyncio
from typing import AsyncIterator, Dict, Any
import logging

from ..core.types import Intent, ProcessedData
from ..exceptions import LLMException
from ..config import agent_config

logger = logging.getLogger(__name__)


class QwenAgentClient:
    """
    Qwen大模型客户端(用于数据分析)

    支持流式和非流式调用
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化客户端

        Args:
            api_key: API密钥(可选,默认从配置读取)
            model: 模型名称(可选,默认从配置读取)
        """
        self.api_key = api_key or agent_config.qwen_api_key
        self.model = model or agent_config.qwen_model
        self.base_url = agent_config.qwen_base_url

        if not self.api_key:
            raise LLMException("未配置QWEN_API_KEY,请设置环境变量AGENT_QWEN_API_KEY或QWEN_API_KEY")

    async def analyze_stream(
        self,
        question: str,
        intent: Intent,
        data: ProcessedData
    ) -> AsyncIterator[str]:
        """
        流式分析数据

        Args:
            question: 用户问题
            intent: 意图
            data: 处理后的数据

        Yields:
            str: 分析文本片段

        Raises:
            LLMException: 调用失败
        """
        try:
            prompt = self._build_prompt(question, intent, data)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-DashScope-SSE": "enable"  # 启用SSE流式输出
            }

            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的数据分析师,擅长解读告警数据。请用简洁专业的中文回答,包含结论和行动建议。回答要有结构,分为:核心结论、关键发现、行动建议三个部分。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                "parameters": {
                    "incremental_output": True,  # 增量输出
                    "result_format": "message"
                }
            }

            logger.info(f"开始调用Qwen API流式分析,模型:{self.model}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise LLMException(f"Qwen API调用失败: {response.status_code} - {error_text.decode()}")

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            try:
                                data_str = line[5:].strip()
                                if not data_str:
                                    continue

                                chunk = json.loads(data_str)

                                # 提取增量内容
                                output = chunk.get("output", {})
                                choices = output.get("choices", [])
                                if choices:
                                    message = choices[0].get("message", {})
                                    content = message.get("content", "")
                                    if content:
                                        yield content
                                        # 添加小延迟,避免前端渲染过快
                                        await asyncio.sleep(agent_config.stream_chunk_delay)

                                # 检查是否结束
                                finish_reason = output.get("finish_reason")
                                if finish_reason:
                                    logger.info(f"Qwen API流式分析完成,原因:{finish_reason}")
                                    break

                            except json.JSONDecodeError as e:
                                logger.warning(f"解析SSE数据失败: {line}, 错误: {e}")
                                continue

        except Exception as e:
            logger.error(f"Qwen API流式分析失败: {e}", exc_info=True)
            raise LLMException(f"LLM分析失败: {str(e)}") from e

    async def analyze(
        self,
        question: str,
        intent: Intent,
        data: ProcessedData
    ) -> str:
        """
        非流式分析(用于测试)

        Args:
            question: 用户问题
            intent: 意图
            data: 处理后的数据

        Returns:
            str: 分析结果

        Raises:
            LLMException: 调用失败
        """
        try:
            prompt = self._build_prompt(question, intent, data)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "input": {
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个专业的数据分析师,擅长解读告警数据。请用简洁专业的中文回答,包含结论和行动建议。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                },
                "parameters": {
                    "result_format": "message"
                }
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                output = result.get("output", {})
                choices = output.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")

                raise LLMException("Qwen API返回格式异常")

        except Exception as e:
            raise LLMException(f"LLM分析失败: {str(e)}") from e

    def _build_prompt(
        self,
        question: str,
        intent: Intent,
        data: ProcessedData
    ) -> str:
        """
        构建分析提示词

        Args:
            question: 用户问题
            intent: 意图
            data: 处理后的数据

        Returns:
            str: 提示词
        """
        # 构建数据表格
        table_md = self._format_table(data.table_data)

        # 构建统计摘要
        stats_md = self._format_statistics(data.summary, data.statistics)

        # 构建图表建议(用于参考)
        charts_md = self._format_charts(data.charts)

        prompt = f"""# 用户问题
{question}

# 查询意图
{intent.summary()}

# 数据详情

{table_md}

{stats_md}

{charts_md}

# 分析任务
请基于以上数据,提供专业的分析报告,包含:

## 1. 核心结论
用3-5句话直接回答用户问题,给出最重要的发现。

## 2. 关键发现
分析数据中的重要模式、趋势或异常,用数据说话。

## 3. 行动建议
基于分析结果,提供3-5条具体可执行的改进建议。

# 要求
- 使用简洁专业的中文
- 重点突出,逻辑清晰
- 包含具体数字支撑结论
- 行动建议要具体可执行
- 如果发现异常,要明确指出风险等级
"""
        return prompt

    def _format_table(self, table_data: list) -> str:
        """格式化数据表格为Markdown"""
        if not table_data:
            return "## 数据明细\n无数据"

        md = f"## 数据明细 (Top {len(table_data)})\n\n"
        md += "| 时间 | 类型 | 位置 | 置信度 |\n"
        md += "|------|------|------|--------|\n"

        for row in table_data[:20]:  # 限制最多20行
            timestamp = row.get("timestamp", "")[:16] if row.get("timestamp") else "-"
            type_name = row.get("type", "未知")
            stream = row.get("stream", "-")
            confidence = row.get("confidence", 0)

            md += f"| {timestamp} | {type_name} | {stream} | {confidence:.1%} |\n"

        return md

    def _format_statistics(self, summary: dict, statistics: dict) -> str:
        """格式化统计摘要"""
        md = "## 统计摘要\n\n"

        # 总数
        total = summary.get("total_count", 0)
        md += f"- **告警总数**: {total}\n"

        # 置信度统计
        if statistics:
            mean_conf = statistics.get("mean_confidence", 0)
            median_conf = statistics.get("median_confidence", 0)
            max_conf = statistics.get("max_confidence", 0)
            min_conf = statistics.get("min_confidence", 0)

            md += f"- **平均置信度**: {mean_conf:.1%}\n"
            md += f"- **中位数置信度**: {median_conf:.1%}\n"
            md += f"- **最高置信度**: {max_conf:.1%}\n"
            md += f"- **最低置信度**: {min_conf:.1%}\n"

            if "std_confidence" in statistics:
                std_conf = statistics["std_confidence"]
                md += f"- **置信度标准差**: {std_conf:.2%}\n"

        return md

    def _format_charts(self, charts: list) -> str:
        """格式化图表建议"""
        if not charts:
            return ""

        md = "## 图表数据\n\n"

        for chart in charts:
            chart_type = chart.get("type", "未知")
            title = chart.get("title", "图表")
            data = chart.get("data", [])

            md += f"### {title} ({chart_type})\n\n"

            if chart_type == "line":
                md += "| 时间 | 数量 |\n|------|------|\n"
                for item in data[:10]:
                    time = item.get("time", "-")
                    count = item.get("count", 0)
                    md += f"| {time} | {count} |\n"
            elif chart_type in ["pie", "bar"]:
                md += "| 名称 | 数值 |\n|------|------|\n"
                for item in data[:10]:
                    name = item.get("name", "-")
                    value = item.get("value", 0)
                    md += f"| {name} | {value} |\n"

            md += "\n"

        return md
