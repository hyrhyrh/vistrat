"""
LLM意图分析器(小模型版本,用于复杂查询)
"""
import httpx
import json
import logging
from typing import Optional

from ..core.types import Intent, TimeWindow
from ..exceptions import IntentAnalysisException
from config.settings import APIConfig
from .time_parser import TimeParser

logger = logging.getLogger(__name__)


class LLMIntentAnalyzer:
    """
    基于LLM的意图分析器(使用小模型快速分析)

    适用场景:
    - 复杂的自然语言查询
    - 规则引擎无法覆盖的场景
    - 需要语义理解的情况
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化LLM意图分析器

        Args:
            api_key: API密钥
            model: 模型名称(推荐使用小模型,如deepseek-chat)
        """
        self.api_key = api_key or APIConfig.DEEPSEEK_API_KEY
        self.model = model or "deepseek-chat"  # 使用快速模型
        self.base_url = APIConfig.DEEPSEEK_API_URL
        self.time_parser = TimeParser()

        if not self.api_key:
            raise IntentAnalysisException("未配置DEEPSEEK_API_KEY")

    async def analyze(self, question: str) -> Intent:
        """
        使用LLM分析用户问题

        Args:
            question: 用户问题

        Returns:
            Intent: 结构化意图

        Raises:
            IntentAnalysisException: 分析失败
        """
        try:
            # 构建提示词
            prompt = self._build_intent_prompt(question)

            # 调用LLM
            response = await self._call_llm(prompt)

            # 解析响应
            intent = self._parse_response(response, question)

            return intent

        except Exception as e:
            logger.error(f"LLM意图分析失败: {e}", exc_info=True)
            raise IntentAnalysisException(f"LLM意图分析失败: {str(e)}") from e

    async def _call_llm(self, prompt: str) -> str:
        """
        调用LLM API

        Args:
            prompt: 提示词

        Returns:
            str: LLM响应
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的意图识别助手。请严格按照JSON格式返回结果,不要添加其他文字。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # 低温度,提高稳定性
            "max_tokens": 500,   # 意图分析不需要太长
            "response_format": {"type": "json_object"}  # 强制JSON格式
        }

        logger.info(f"调用LLM意图分析,模型:{self.model}")

        async with httpx.AsyncClient(timeout=10.0) as client:  # 10秒超时
            response = await client.post(
                self.base_url,
                headers=headers,
                json=payload
            )

            if response.status_code != 200:
                raise IntentAnalysisException(
                    f"LLM API调用失败: {response.status_code} - {response.text}"
                )

            result = response.json()
            choices = result.get("choices", [])

            if not choices:
                raise IntentAnalysisException("LLM返回格式异常")

            message = choices[0].get("message", {})
            content = message.get("content", "")

            logger.info(f"LLM意图分析完成,响应长度:{len(content)}")

            return content

    def _build_intent_prompt(self, question: str) -> str:
        """
        构建意图分析提示词

        Args:
            question: 用户问题

        Returns:
            str: 提示词
        """
        prompt = f"""# 任务
分析用户的告警查询问题,提取结构化意图信息。

# 用户问题
{question}

# 输出格式
请严格按照以下JSON格式返回,不要添加其他文字:

{{
    "time_window": {{
        "description": "时间范围描述(如'今天'、'最近一周'、'2024年1月')",
        "relative_type": "today/yesterday/this_week/last_week/this_month/last_month/custom/null"
    }},
    "entities": [
        "识别到的实体(如告警类型、区域、设备等)"
    ],
    "metrics": [
        "需要的指标(从以下选择:count/trend/distribution/top/comparison)"
    ],
    "query_type": "查询类型(从以下选择:statistics/comparison/trend/anomaly/report)",
    "aggregation_level": "聚合级别(从以下选择:hour/day/week/month)",
    "filters": {{
        "其他过滤条件(如min_confidence等)"
    }}
}}

# 示例

用户问题: "今天有多少未戴安全帽的告警?"
{{
    "time_window": {{
        "description": "今天",
        "relative_type": "today"
    }},
    "entities": ["未戴安全帽"],
    "metrics": ["count"],
    "query_type": "statistics",
    "aggregation_level": "day",
    "filters": {{}}
}}

用户问题: "最近一周的告警趋势如何?"
{{
    "time_window": {{
        "description": "最近一周",
        "relative_type": "last_week"
    }},
    "entities": [],
    "metrics": ["count", "trend"],
    "query_type": "trend",
    "aggregation_level": "day",
    "filters": {{}}
}}

# 注意事项
1. 如果无法识别时间范围,relative_type设为null,description设为"未指定"
2. entities数组中只包含具体的实体名称
3. metrics必须从给定的5个选项中选择
4. query_type必须从给定的5个选项中选择
5. aggregation_level必须从给定的4个选项中选择
6. 返回纯JSON,不要添加markdown代码块标记
"""
        return prompt

    def _parse_response(self, response: str, question: str) -> Intent:
        """
        解析LLM响应为Intent对象

        Args:
            response: LLM响应JSON字符串
            question: 原始问题

        Returns:
            Intent: 意图对象
        """
        try:
            # 移除可能的markdown代码块标记
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])

            data = json.loads(response)

            intent = Intent()

            # 解析时间窗口
            time_window_data = data.get("time_window", {})
            relative_type = time_window_data.get("relative_type")

            if relative_type and relative_type != "null":
                # 使用time_parser解析相对时间
                intent.time_window = self.time_parser.parse(
                    time_window_data.get("description", "今天")
                )
            else:
                # 默认今天
                intent.time_window = TimeParser._get_today()

            # 解析实体
            intent.entities = data.get("entities", [])

            # 解析指标
            intent.metrics = data.get("metrics", ["count"])

            # 查询类型
            intent.query_type = data.get("query_type", "statistics")

            # 聚合级别
            intent.aggregation_level = data.get("aggregation_level", "day")

            # 过滤条件
            intent.filters = data.get("filters", {})

            logger.info(f"成功解析LLM意图: {intent.summary()}")

            return intent

        except json.JSONDecodeError as e:
            logger.error(f"解析LLM响应失败: {response}", exc_info=True)
            # 回退到规则引擎
            raise IntentAnalysisException(f"解析LLM响应失败,请重试") from e
        except Exception as e:
            logger.error(f"处理LLM响应异常: {e}", exc_info=True)
            raise IntentAnalysisException(f"处理LLM响应异常: {str(e)}") from e
