"""
Agent编排器 - 状态机核心
"""
import logging
from typing import AsyncIterator
from datetime import datetime

from ..core.types import (
    AgentState,
    StreamMessage,
    StreamMessageStage,
    AgentContext
)
from ..analyzers.intent_analyzer import IntentAnalyzer
from ..analyzers.hybrid_intent_analyzer import HybridIntentAnalyzer
from ..analyzers.relevance_checker import RelevanceChecker
from ..analyzers.query_builder import QueryBuilder
from ..processors.normalizer import DataProcessor
from ..llm.qwen_client import QwenAgentClient
from ..llm.deepseek_client import DeepSeekAgentClient
from ..reports.builder import ReportBuilder
from ..exceptions import AgentException

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Agent状态机编排器

    职责:
    1. 管理分析流程的各个步骤
    2. 协调各模块调用
    3. 流式推送进度
    4. 异常处理和重试
    """

    def __init__(
        self,
        intent_analyzer,  # IntentAnalyzer或HybridIntentAnalyzer
        query_builder: QueryBuilder,
        es_service,  # ElasticsearchService实例
        data_processor: DataProcessor,
        llm_client,  # QwenAgentClient或DeepSeekAgentClient
        report_builder: ReportBuilder
    ):
        """
        初始化编排器

        Args:
            intent_analyzer: 意图分析器(支持规则引擎或混合分析器)
            query_builder: 查询构建器
            es_service: Elasticsearch服务
            data_processor: 数据处理器
            llm_client: LLM客户端(支持Qwen或DeepSeek)
            report_builder: 报告构建器
        """
        self.intent_analyzer = intent_analyzer
        self.query_builder = query_builder
        self.es_service = es_service
        self.data_processor = data_processor
        self.llm_client = llm_client
        self.report_builder = report_builder
        # 初始化基于DeepSeek的相关性检查器
        self.relevance_checker = RelevanceChecker()

    async def process_query(
        self,
        question: str,
        user_id: str
    ) -> AsyncIterator[StreamMessage]:
        """
        处理用户查询(流式生成器)

        Args:
            question: 用户问题
            user_id: 用户ID

        Yields:
            StreamMessage: 流式消息
        """
        state = AgentState.IDLE
        context = AgentContext(question=question, user_id=user_id)
        start_time = datetime.now()

        try:
            # ========== Step 0: 相关性检查(使用DeepSeek) ==========
            logger.info(f"[{user_id}] Step 0: 相关性检查 - {question}")

            yield StreamMessage(
                stage=StreamMessageStage.INTENT,
                message="🤔 正在理解您的问题..."
            )

            # 调用DeepSeek进行语义相关性判断
            is_relevant, reason = await self.relevance_checker.check_relevance(question)
            logger.info(f"[{user_id}] 相关性判断: {is_relevant}, 理由: {reason}")

            if not is_relevant:
                logger.info(f"[{user_id}] 问题与告警分析无关,返回友好提示")

                yield StreamMessage(
                    stage=StreamMessageStage.COMPLETED,
                    message="✓ 已理解您的问题",
                    data={
                        "report_markdown": self._generate_irrelevant_response(question, reason),
                        "report_json": {},
                        "metadata": {
                            "is_relevant": False,
                            "relevance_reason": reason,
                            "elapsed_time_seconds": 0
                        }
                    }
                )
                return

            # ========== Step 1: 意图分析 ==========
            state = AgentState.ANALYZING_INTENT
            logger.info(f"[{user_id}] Step 1: 意图分析 - {question}")

            intent = await self.intent_analyzer.analyze(question)
            context.intent = intent.dict()

            yield StreamMessage(
                stage=StreamMessageStage.INTENT,
                message=f"✓ 已识别: {intent.summary()}",
                data={"intent": context.intent}
            )

            # ========== Step 2: 查询数据 ==========
            state = AgentState.QUERYING_DATA
            logger.info(f"[{user_id}] Step 2: 查询数据")

            yield StreamMessage(
                stage=StreamMessageStage.QUERY,
                message="🔍 正在查询数据..."
            )

            # 构建ES查询
            query_dsl = self.query_builder.build(intent)
            logger.debug(f"[{user_id}] ES查询: {query_dsl}")

            # 执行查询（使用 search_alerts 方法）
            raw_data = await self.es_service.search_alerts(
                query=query_dsl,
                size=100
            )
            context.raw_data = raw_data

            data_count = raw_data.get("hits", {}).get("total", {})
            if isinstance(data_count, dict):
                data_count = data_count.get("value", 0)

            yield StreamMessage(
                stage=StreamMessageStage.QUERY,
                message=f"✓ 已查询到 {data_count} 条数据",
                data={"data_count": data_count}
            )

            # ========== Step 3: 数据处理 ==========
            state = AgentState.PROCESSING_DATA
            logger.info(f"[{user_id}] Step 3: 数据处理")

            yield StreamMessage(
                stage=StreamMessageStage.PROCESS,
                message="📊 正在处理数据..."
            )

            processed = self.data_processor.process(raw_data, intent)
            context.processed_data = processed.dict()

            yield StreamMessage(
                stage=StreamMessageStage.PROCESS,
                message="✓ 数据处理完成",
                data={"summary": processed.summary}
            )

            # ========== Step 4: LLM分析 ==========
            state = AgentState.GENERATING_INSIGHTS
            logger.info(f"[{user_id}] Step 4: LLM分析")

            yield StreamMessage(
                stage=StreamMessageStage.ANALYZE,
                message="🤖 AI正在分析数据...\n\n"
            )

            # 流式输出LLM分析
            insights_buffer = ""
            async for chunk in self.llm_client.analyze_stream(
                question=question,
                intent=intent,
                data=processed
            ):
                insights_buffer += chunk
                yield StreamMessage(
                    stage=StreamMessageStage.ANALYZE,
                    content=chunk
                )

            context.insights = insights_buffer

            # ========== Step 5: 报告生成 ==========
            state = AgentState.BUILDING_REPORT
            logger.info(f"[{user_id}] Step 5: 报告生成")

            yield StreamMessage(
                stage=StreamMessageStage.REPORT,
                message="\n\n📄 正在生成报告..."
            )

            report = self.report_builder.build(
                question=question,
                intent=intent,
                data=processed,
                insights=context.insights
            )
            context.report = report.markdown
            context.metadata = report.metadata

            # ========== 完成 ==========
            state = AgentState.COMPLETED
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"[{user_id}] 分析完成,耗时: {elapsed_time:.2f}秒")

            yield StreamMessage(
                stage=StreamMessageStage.COMPLETED,
                message="✓ 分析完成",
                data={
                    "report_markdown": context.report,
                    "report_json": report.json_data,
                    "metadata": {
                        **context.metadata,
                        "elapsed_time_seconds": elapsed_time
                    }
                }
            )

        except Exception as e:
            state = AgentState.ERROR
            logger.error(f"[{user_id}] 分析失败 (状态:{state}): {str(e)}", exc_info=True)

            yield StreamMessage(
                stage=StreamMessageStage.ERROR,
                message=f"❌ 分析失败: {str(e)}\n\n可能原因:\n- 数据查询异常\n- AI服务不可用\n- 网络连接问题\n\n请稍后重试。"
            )
            raise

    def _generate_irrelevant_response(self, question: str, reason: str = "") -> str:
        """
        生成无关问题的友好提示

        Args:
            question: 用户问题
            reason: 判断为不相关的理由

        Returns:
            str: 友好提示消息
        """
        import re

        # 问候语检测
        greetings = [r"你好", r"您好", r"hi", r"hello", r"嗨"]
        is_greeting = any(re.search(pattern, question.lower()) for pattern in greetings)

        if is_greeting:
            return """## 您好！👋

我是**告警分析智能体**,很高兴为您服务。

### 我的专长
我专注于分析和解读告警数据,帮助您了解安全监控系统的运行状态:

- 📊 **告警统计**: 查询告警数量、趋势、分布
- 🔍 **数据分析**: 分析特定类型告警(如未戴安全帽、吸烟等)
- 📈 **趋势洞察**: 识别告警变化趋势和异常模式
- 🎯 **区域分析**: 统计不同区域的告警情况
- ⚠️ **风险评估**: 评估当前的安全风险等级

### 您可以这样问我
- "今天有多少告警?"
- "最近一周的告警趋势如何?"
- "未戴安全帽的告警有多少?"
- "哪个区域的告警最多?"

请告诉我您想了解的告警数据信息,我会基于真实数据为您提供专业分析！"""

        # 其他无关问题
        return f"""## 抱歉,我无法回答这个问题 😔

您的问题: **{question}**

我是一个**告警分析智能体**,专门用于分析和解读视频监控系统的告警数据。

### 我能做什么
- ✅ 分析告警数据(数量、类型、趋势、分布)
- ✅ 统计安全事件(未戴安全帽、吸烟、违规操作等)
- ✅ 评估区域风险和告警模式
- ✅ 提供基于真实数据的专业洞察

### 我不能做什么
- ❌ 回答与告警分析无关的问题
- ❌ 进行闲聊或通用对话
- ❌ 提供告警数据以外的信息

### 试试这些问题
- "今天产生了多少告警?"
- "最近一周的告警趋势如何?"
- "未戴安全帽的告警有多少?"
- "哪个视频流的告警最多?"

**请向我咨询告警相关的问题,我会基于真实监控数据为您提供准确的分析！**"""
