"""
DeepSeek大模型客户端(用于Agent数据分析)
使用OpenAI兼容的API接口
"""
import httpx
import json
import asyncio
from typing import AsyncIterator, Dict, Any
import logging

from ..core.types import Intent, ProcessedData
from ..exceptions import LLMException
from config.settings import APIConfig

logger = logging.getLogger(__name__)


class DeepSeekAgentClient:
    """
    DeepSeek大模型客户端(用于数据分析)

    支持流式和非流式调用,使用OpenAI兼容接口
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化客户端

        Args:
            api_key: API密钥(可选,默认从配置读取)
            model: 模型名称(可选,默认从配置读取)
        """
        self.api_key = api_key or APIConfig.DEEPSEEK_API_KEY
        self.model = model or APIConfig.DEEPSEEK_MODEL
        self.base_url = APIConfig.DEEPSEEK_API_URL

        if not self.api_key:
            raise LLMException("未配置DEEPSEEK_API_KEY,请设置环境变量")

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
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": """你是一个严谨的企业级告警数据分析师。

【核心原则】
1. 数据真实性: 严格基于提供的真实数据进行分析,绝不捏造、臆测或编造数据
2. 科学态度: 保持客观、严谨的分析态度,避免主观臆断
3. 准确性优先: 如果数据不足或不明确,明确说明数据缺失,而不是猜测

【输出要求】
- 回答要有明确结构: 核心结论、关键发现、行动建议
- 所有结论必须有数据支撑,引用具体数字
- 发现数据质量问题时,优先指出数据完整性问题
- 使用简洁专业的中文表达

【禁止行为】
- ❌ 禁止编造不存在的数据
- ❌ 禁止对空数据或缺失字段进行推测性分析
- ❌ 禁止将系统问题(如字段缺失)误导为业务问题
- ❌ 禁止使用"可能"、"大概"等模糊表述来掩盖数据缺失

记住: 你是企业级分析师,数据真实性和准确性是第一要务！"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": True,
                "temperature": APIConfig.TEMPERATURE,
                "max_tokens": 2000
            }

            logger.info(f"开始调用DeepSeek API流式分析,模型:{self.model}")

            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    self.base_url,
                    headers=headers,
                    json=payload
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise LLMException(f"DeepSeek API调用失败: {response.status_code} - {error_text.decode()}")

                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            try:
                                data_str = line[5:].strip()
                                if not data_str or data_str == "[DONE]":
                                    continue

                                chunk = json.loads(data_str)

                                # 提取增量内容 (OpenAI格式)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                                        # 添加小延迟,避免前端渲染过快
                                        await asyncio.sleep(0.01)

                                    # 检查是否结束
                                    finish_reason = choices[0].get("finish_reason")
                                    if finish_reason:
                                        logger.info(f"DeepSeek API流式分析完成,原因:{finish_reason}")
                                        break

                            except json.JSONDecodeError as e:
                                logger.warning(f"解析SSE数据失败: {line}, 错误: {e}")
                                continue

        except Exception as e:
            logger.error(f"DeepSeek API流式分析失败: {e}", exc_info=True)
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
                "messages": [
                    {
                        "role": "system",
                        "content": """你是一个严谨的企业级告警数据分析师。

【核心原则】
1. 数据真实性: 严格基于提供的真实数据进行分析,绝不捏造、臆测或编造数据
2. 科学态度: 保持客观、严谨的分析态度,避免主观臆断
3. 准确性优先: 如果数据不足或不明确,明确说明数据缺失,而不是猜测

【输出要求】
- 所有结论必须有数据支撑,引用具体数字
- 发现数据质量问题时,优先指出数据完整性问题
- 使用简洁专业的中文表达

【禁止行为】
- ❌ 禁止编造不存在的数据
- ❌ 禁止对空数据或缺失字段进行推测性分析
- ❌ 禁止将系统问题(如字段缺失)误导为业务问题"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": APIConfig.TEMPERATURE,
                "max_tokens": 2000
            }

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

                choices = result.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    return message.get("content", "")

                raise LLMException("DeepSeek API返回格式异常")

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
            # 优先使用 created_at，如果没有则使用 video_time
            timestamp = row.get("created_at", row.get("video_time", "-"))
            if isinstance(timestamp, str) and len(timestamp) > 16:
                timestamp = timestamp[:16]  # 只取日期和小时分钟部分
            # 使用算法名称或模板名称作为类型
            type_name = row.get("algorithm_name", row.get("template_name", row.get("alert_type", "未知")))
            # 使用视频名称作为位置
            location = row.get("video_name", row.get("location", row.get("stream", "-")))
            confidence = row.get("confidence", 0)

            md += f"| {timestamp} | {type_name} | {location} | {confidence:.1%} |\n"

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
