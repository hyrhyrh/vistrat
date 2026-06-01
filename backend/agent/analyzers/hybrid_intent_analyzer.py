"""
混合意图分析器
结合规则引擎和LLM,优先使用规则引擎(快速),复杂查询回退到LLM
"""
import logging
from typing import Optional

from ..core.types import Intent
from ..exceptions import IntentAnalysisException
from .intent_analyzer import IntentAnalyzer
from .llm_intent_analyzer import LLMIntentAnalyzer

logger = logging.getLogger(__name__)


class HybridIntentAnalyzer:
    """
    混合意图分析器

    策略:
    1. 优先使用规则引擎(快速,<50ms)
    2. 规则引擎置信度低时,回退到LLM(<1s)
    3. 缓存常见查询模式

    优势:
    - 简单查询快速响应
    - 复杂查询准确理解
    - 平衡速度和准确度
    """

    def __init__(self, enable_llm: bool = True):
        """
        初始化混合分析器

        Args:
            enable_llm: 是否启用LLM回退
        """
        self.rule_analyzer = IntentAnalyzer()
        self.llm_analyzer = None
        self.enable_llm = enable_llm

        # 懒加载LLM分析器
        if enable_llm:
            try:
                self.llm_analyzer = LLMIntentAnalyzer()
                logger.info("混合意图分析器初始化完成,LLM回退已启用")
            except Exception as e:
                logger.warning(f"LLM意图分析器初始化失败,将仅使用规则引擎: {e}")
                self.enable_llm = False
        else:
            logger.info("混合意图分析器初始化完成,LLM回退已禁用")

    async def analyze(self, question: str) -> Intent:
        """
        分析用户问题

        Args:
            question: 用户问题

        Returns:
            Intent: 结构化意图

        Raises:
            IntentAnalysisException: 分析失败
        """
        try:
            # 1. 先使用规则引擎(快速)
            rule_intent = await self.rule_analyzer.analyze(question)

            # 2. 评估规则引擎置信度
            confidence = self._evaluate_confidence(question, rule_intent)

            logger.info(
                f"规则引擎分析完成,置信度:{confidence:.2f}, "
                f"实体:{len(rule_intent.entities)}个, "
                f"指标:{len(rule_intent.metrics)}个"
            )

            # 3. 高置信度直接返回
            if confidence >= 0.8:
                logger.info("规则引擎置信度高,直接返回结果")
                return rule_intent

            # 4. 低置信度且启用LLM时,回退到LLM
            if confidence < 0.6 and self.enable_llm and self.llm_analyzer:
                logger.info("规则引擎置信度低,回退到LLM分析...")
                try:
                    llm_intent = await self.llm_analyzer.analyze(question)
                    logger.info("LLM分析成功,使用LLM结果")
                    return llm_intent
                except Exception as e:
                    logger.warning(f"LLM分析失败,回退到规则引擎结果: {e}")
                    return rule_intent

            # 5. 中等置信度或LLM未启用,返回规则引擎结果
            return rule_intent

        except Exception as e:
            logger.error(f"意图分析失败: {e}", exc_info=True)
            raise IntentAnalysisException(f"意图分析失败: {str(e)}") from e

    def _evaluate_confidence(self, question: str, intent: Intent) -> float:
        """
        评估规则引擎结果的置信度

        Args:
            question: 原始问题
            intent: 规则引擎分析结果

        Returns:
            float: 置信度分数(0-1)
        """
        score = 0.5  # 基础分数

        # 1. 时间窗口清晰 (+0.2)
        if intent.time_window and intent.time_window.label != "未指定":
            score += 0.2

        # 2. 识别到实体 (+0.1)
        if intent.entities:
            score += 0.1

        # 3. 识别到指标 (+0.1)
        if intent.metrics:
            score += 0.1

        # 4. 查询类型明确 (+0.1)
        if intent.query_type != "statistics":
            score += 0.1

        # 降低置信度的情况:

        # 1. 问题过长(可能复杂) (-0.2)
        if len(question) > 50:
            score -= 0.2

        # 2. 包含复杂语义词汇 (-0.3)
        complex_keywords = ["为什么", "如何", "怎么", "原因", "建议", "应该"]
        for keyword in complex_keywords:
            if keyword in question:
                score -= 0.3
                break

        # 3. 包含否定词汇 (-0.2)
        negative_keywords = ["不", "没有", "未"]
        for keyword in negative_keywords:
            if keyword in question:
                score -= 0.1

        # 限制在0-1范围
        return max(0.0, min(1.0, score))
