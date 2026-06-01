# AI智能体架构设计文档

> **告警分析AI智能体** - 面向业务人员的智能数据分析助手
>
> 版本: v1.0
> 日期: 2025-10-10
> 设计者: Claude Code

---

## 一、需求分析

### 1.1 核心目标

实现一个智能对话式数据分析助手,让业务人员能够用自然语言提问,系统自动:
1. 理解问题意图(时间范围、实体、指标等)
2. 从Elasticsearch查询告警数据
3. 进行统计分析和趋势判断
4. 生成结构化报告(文本 + 图表建议 + 结论与建议)

### 1.2 典型场景

| 用户问题 | 意图解析 | 预期输出 |
|---------|---------|---------|
| "最近一周有多少告警?" | 时间窗口:最近7天<br>指标:count | 统计数字 + 趋势图建议 + 结论 |
| "今天的高危告警都在哪些区域?" | 时间:今天<br>过滤:高危<br>分组:区域 | 区域分布表 + 饼图建议 |
| "对比上个月,告警趋势如何?" | 时间对比:本月vs上月<br>指标:趋势 | 对比数据 + 折线图 + 分析 |
| "给我一份今日告警分析报告" | 时间:今天<br>类型:综合报告 | 完整HTML报告(含多维分析) |

### 1.3 技术要求

- ✅ **模块化设计**: Agent模块与现有系统解耦,易于扩展
- ✅ **流式响应**: 使用SSE实时反馈分析进度,提升体验
- ✅ **移动端适配**: 报告支持响应式布局,适配手机查看
- ✅ **扩展性**: 支持后续接入更多数据源(非仅ES)

---

## 二、架构设计

### 2.1 整体流程

```
┌─────────────┐
│ 用户提问     │  "最近一周有多少告警?"
└──────┬──────┘
       │ HTTP POST /api/agent/chat (SSE)
       ▼
┌─────────────────────────────────────────────────────┐
│                  API Gateway层                       │
│  - 鉴权 (JWT Token)                                 │
│  - 审计日志 (记录用户问题、时间戳)                    │
│  - 限流 (防止滥用)                                   │
└──────────────────────┬─────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Agent Orchestrator (状态机)             │
│  - 管理分析流程的各个步骤                            │
│  - 协调各模块调用                                   │
│  - 流式推送进度                                     │
└──────────────────────┬─────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│Step 1:      │ │Step 2:      │ │Step 3:      │
│意图分析      │ │查询数据      │ │数据处理      │
├─────────────┤ ├─────────────┤ ├─────────────┤
│IntentAnalyzer│ │ESQueryBuilder│ │DataProcessor│
│             │ │             │ │             │
│输入: 问题    │ │输入: 意图    │ │输入: 原始数据 │
│输出: 结构化  │ │输出: ES结果  │ │输出: 统计数据 │
│- time_window│ │             │ │- 均值/中位数 │
│- entities   │ │             │ │- top-N      │
│- metrics    │ │             │ │- 分布       │
│- query_type │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
         │             │             │
         └─────────────┼─────────────┘
                       ▼
         ┌─────────────────────────┐
         │Step 4: LLM分析 (大模型)  │
         ├─────────────────────────┤
         │Qwen VL-Max              │
         │                         │
         │提示词结构:               │
         │1. 用户问题 + 意图槽位    │
         │2. 数据表格(top-N)       │
         │3. 统计描述(均值/分位数)  │
         │4. 业务语气要求          │
         │                         │
         │输出: 流式文本分析        │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │Step 5: 报告生成          │
         ├─────────────────────────┤
         │ReportBuilder            │
         │                         │
         │格式:                    │
         │- JSON (结构化数据)       │
         │- Markdown (富文本)      │
         │- HTML (单页报告)        │
         │                         │
         │包含:                    │
         │- 问题标题               │
         │- 数据摘要表格           │
         │- AI分析结论             │
         │- 图表建议               │
         │- 行动建议               │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │前端渲染                  │
         │- 流式显示分析过程        │
         │- 报告查看器(HTML)        │
         │- 可导出/分享             │
         └─────────────────────────┘
```

### 2.2 技术栈选型

#### 后端技术栈

| 组件 | 技术选型 | 理由 |
|-----|---------|------|
| **状态机** | 自研轻量级状态机 | 场景简单,5个状态足够,无需引入LangGraph |
| **意图分析** | Phase 1: 规则引擎<br>Phase 2: Qwen-Turbo小模型 | 规则引擎快速验证MVP<br>小模型提升准确率 |
| **ES访问** | 直接使用现有`ElasticsearchService` | 避免引入MCP Server额外复杂度 |
| **LLM** | Qwen VL-Max (通义千问) | 已集成,支持中文,分析能力强 |
| **流式响应** | SSE (Server-Sent Events) | 单向推送足够,浏览器原生支持 |
| **报告格式** | HTML优先 (Jinja2模板) | 移动端友好,样式可控,易分享 |

#### 前端技术栈

| 组件 | 技术选型 | 理由 |
|-----|---------|------|
| **对话框UI** | Ant Design Modal + 自定义样式 | 与现有UI风格一致 |
| **消息渲染** | Markdown + HTML渲染器 | 支持富文本和图表建议 |
| **流式接收** | EventSource API | 原生SSE客户端 |
| **语音输入** | Web Speech API | 浏览器原生支持,无需第三方库 |
| **状态管理** | React Hooks (useState/useEffect) | 轻量场景无需Redux |

### 2.3 MCP协议方案评估与决策

#### 方案对比

| 方案 | 优势 | 劣势 | 适用场景 |
|-----|------|------|---------|
| **方案A: 使用Elasticsearch MCP Server** | 标准化接口<br>工具封装完善<br>易于替换数据源 | 需部署额外服务<br>增加网络跳转<br>学习成本高 | 需要接入多种数据源的场景 |
| **方案B: 直接使用现有ES Service** ✅ | 无额外依赖<br>性能最优<br>代码简洁 | 与ES强耦合<br>不符合MCP标准 | 单一数据源,快速交付 |

#### 最终决策: **方案B - 直接使用ES Service**

**理由**:
1. 我们已有`ElasticsearchService`,功能完善
2. 当前场景仅需查询ES,无需多数据源切换
3. 减少架构复杂度,降低维护成本
4. 性能更优(减少一层网络调用)

**未来扩展路径**:
- 当需要接入PostgreSQL、Redis等多数据源时,再引入MCP架构
- 可以在`Agent`模块内部抽象`DataSourceAdapter`接口,预留扩展点

---

## 三、模块设计

### 3.1 后端目录结构

```
backend/
├── agent/                           # 🆕 AI智能体模块
│   ├── __init__.py
│   ├── core/                        # 核心模块
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # Agent状态机编排器
│   │   ├── context.py               # 对话上下文管理
│   │   └── types.py                 # 数据类型定义
│   ├── analyzers/                   # 分析器模块
│   │   ├── __init__.py
│   │   ├── intent_analyzer.py       # 意图分析
│   │   │   - IntentAnalyzer (规则引擎)
│   │   │   - LLMIntentAnalyzer (小模型版本)
│   │   ├── query_builder.py         # ES查询构建器
│   │   │   - QueryBuilder.build_query()
│   │   │   - QueryBuilder.build_aggregations()
│   │   └── time_parser.py           # 时间表达式解析
│   │       - parse_time_window("最近一周")
│   ├── processors/                  # 数据处理模块
│   │   ├── __init__.py
│   │   ├── normalizer.py            # 数据规范化
│   │   ├── statistics.py            # 统计计算
│   │   └── aggregator.py            # 聚合处理
│   ├── llm/                         # LLM集成模块
│   │   ├── __init__.py
│   │   ├── client.py                # LLM客户端抽象
│   │   ├── qwen_client.py           # Qwen实现
│   │   └── prompt_templates.py      # 提示词模板
│   ├── reports/                     # 报告生成模块
│   │   ├── __init__.py
│   │   ├── builder.py               # 报告构建器
│   │   ├── formatters/              # 格式化器
│   │   │   ├── __init__.py
│   │   │   ├── json_formatter.py
│   │   │   ├── markdown_formatter.py
│   │   │   └── html_formatter.py
│   │   └── templates/               # HTML模板
│   │       └── analysis_report.html.j2
│   ├── config.py                    # 配置管理
│   └── exceptions.py                # 自定义异常
├── api/
│   ├── agent.py                     # 🆕 /api/agent/* 端点
│   └── ...
```

### 3.2 前端目录结构

```
frontend/src/
├── components/agent/                # 🆕 AI智能体组件
│   ├── AgentButton.tsx              # 触发按钮(大屏左上角)
│   ├── AgentDialog.tsx              # 对话框容器(60%屏幕)
│   ├── ChatInterface.tsx            # 聊天界面
│   ├── MessageList.tsx              # 消息列表
│   ├── ChatMessage.tsx              # 单条消息组件
│   ├── InputArea.tsx                # 输入区域
│   ├── VoiceInput.tsx               # 语音输入按钮
│   ├── ReportViewer.tsx             # 报告查看器(HTML渲染)
│   └── LoadingIndicator.tsx        # 流式加载动画
├── services/
│   └── agentService.ts              # 🆕 Agent API服务
├── types/
│   └── agent.ts                     # 🆕 类型定义
├── hooks/
│   └── useAgentChat.ts              # 🆕 聊天逻辑Hook
├── pages/
│   └── SafetyMonitoringDashboardWithAI.tsx  # 集成AgentButton
```

### 3.3 核心组件详细设计

#### 3.3.1 Agent Orchestrator (状态机)

```python
# backend/agent/core/orchestrator.py

from enum import Enum
from typing import Callable, AsyncIterator
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

class AgentState(str, Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    ANALYZING_INTENT = "analyzing_intent"
    QUERYING_DATA = "querying_data"
    PROCESSING_DATA = "processing_data"
    GENERATING_INSIGHTS = "generating_insights"
    BUILDING_REPORT = "building_report"
    COMPLETED = "completed"
    ERROR = "error"

class StreamMessage(BaseModel):
    """流式消息"""
    stage: str          # 当前阶段: intent/query/process/analyze/report/error
    message: str        # 提示文本
    content: str = ""   # 内容(用于analyze阶段的流式输出)
    data: dict = {}     # 附加数据

class AgentContext(BaseModel):
    """对话上下文"""
    question: str
    user_id: str
    intent: dict = {}
    raw_data: list = []
    processed_data: dict = {}
    insights: str = ""
    report: str = ""
    metadata: dict = {}

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
        intent_analyzer,
        query_builder,
        es_service,
        data_processor,
        llm_client,
        report_builder
    ):
        self.intent_analyzer = intent_analyzer
        self.query_builder = query_builder
        self.es_service = es_service
        self.data_processor = data_processor
        self.llm_client = llm_client
        self.report_builder = report_builder

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

        try:
            # Step 1: 意图分析
            state = AgentState.ANALYZING_INTENT
            logger.info(f"[{user_id}] Step 1: 意图分析 - {question}")
            yield StreamMessage(stage="intent", message="🤔 正在理解您的问题...")

            intent = await self.intent_analyzer.analyze(question)
            context.intent = intent.dict()

            yield StreamMessage(
                stage="intent",
                message=f"✓ 已识别: {intent.summary()}",
                data={"intent": context.intent}
            )

            # Step 2: 查询数据
            state = AgentState.QUERYING_DATA
            logger.info(f"[{user_id}] Step 2: 查询数据")
            yield StreamMessage(stage="query", message="🔍 正在查询数据...")

            query = self.query_builder.build(intent)
            raw_data = await self.es_service.search(
                index="video_alerts",
                query=query["query"],
                aggs=query.get("aggs"),
                size=query.get("size", 100)
            )
            context.raw_data = raw_data

            data_count = len(raw_data.get("hits", {}).get("hits", []))
            yield StreamMessage(
                stage="query",
                message=f"✓ 已查询到 {data_count} 条数据",
                data={"data_count": data_count}
            )

            # Step 3: 数据处理
            state = AgentState.PROCESSING_DATA
            logger.info(f"[{user_id}] Step 3: 数据处理")
            yield StreamMessage(stage="process", message="📊 正在处理数据...")

            processed = self.data_processor.process(raw_data, intent)
            context.processed_data = processed

            yield StreamMessage(
                stage="process",
                message="✓ 数据处理完成",
                data={"summary": processed.get("summary")}
            )

            # Step 4: LLM分析
            state = AgentState.GENERATING_INSIGHTS
            logger.info(f"[{user_id}] Step 4: LLM分析")
            yield StreamMessage(stage="analyze", message="🤖 AI正在分析数据...\n\n")

            # 流式输出LLM分析
            async for chunk in self.llm_client.analyze_stream(
                question=question,
                intent=intent,
                data=processed
            ):
                yield StreamMessage(stage="analyze", content=chunk)
                context.insights += chunk

            # Step 5: 报告生成
            state = AgentState.BUILDING_REPORT
            logger.info(f"[{user_id}] Step 5: 报告生成")
            yield StreamMessage(stage="report", message="\n\n📄 正在生成报告...")

            report = self.report_builder.build(
                question=question,
                intent=intent,
                data=processed,
                insights=context.insights
            )
            context.report = report["html"]
            context.metadata = report["metadata"]

            # 完成
            state = AgentState.COMPLETED
            logger.info(f"[{user_id}] 分析完成")
            yield StreamMessage(
                stage="completed",
                message="✓ 分析完成",
                data={
                    "report_html": context.report,
                    "metadata": context.metadata
                }
            )

        except Exception as e:
            state = AgentState.ERROR
            logger.error(f"[{user_id}] 分析失败: {str(e)}", exc_info=True)
            yield StreamMessage(
                stage="error",
                message=f"❌ 分析失败: {str(e)}"
            )
            raise
```

#### 3.3.2 Intent Analyzer (意图分析)

```python
# backend/agent/analyzers/intent_analyzer.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import re

class TimeWindow(BaseModel):
    """时间窗口"""
    start: datetime
    end: datetime
    label: str  # "今天"、"最近一周"等

class Intent(BaseModel):
    """用户意图"""
    time_window: Optional[TimeWindow] = None
    entities: List[str] = []        # 区域、设备、告警类型等
    metrics: List[str] = []         # count、severity、trend等
    query_type: str = "statistics"  # statistics/trend/comparison/anomaly
    aggregation_level: str = "day"  # hour/day/week/month
    filters: dict = {}              # 其他过滤条件

    def summary(self) -> str:
        """生成意图摘要"""
        parts = []
        if self.time_window:
            parts.append(f"时间:{self.time_window.label}")
        if self.entities:
            parts.append(f"实体:{','.join(self.entities)}")
        if self.metrics:
            parts.append(f"指标:{','.join(self.metrics)}")
        return " | ".join(parts) if parts else "统计查询"

class IntentAnalyzer:
    """
    意图分析器(规则引擎版本)

    负责从自然语言问题中提取:
    1. 时间范围
    2. 实体(区域、设备、告警类型)
    3. 指标(数量、趋势、分布)
    4. 查询类型
    """

    # 时间表达式规则
    TIME_PATTERNS = {
        r"今天|今日": lambda: TimeWindow(
            start=datetime.now().replace(hour=0, minute=0, second=0),
            end=datetime.now(),
            label="今天"
        ),
        r"昨天": lambda: TimeWindow(
            start=(datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0),
            end=(datetime.now() - timedelta(days=1)).replace(hour=23, minute=59, second=59),
            label="昨天"
        ),
        r"最近(\d+)天|近(\d+)天": lambda d: TimeWindow(
            start=datetime.now() - timedelta(days=int(d)),
            end=datetime.now(),
            label=f"最近{d}天"
        ),
        r"本周": lambda: TimeWindow(
            start=datetime.now() - timedelta(days=datetime.now().weekday()),
            end=datetime.now(),
            label="本周"
        ),
        r"本月": lambda: TimeWindow(
            start=datetime.now().replace(day=1, hour=0, minute=0, second=0),
            end=datetime.now(),
            label="本月"
        ),
    }

    # 实体识别规则
    ENTITY_PATTERNS = {
        "alert_type": [r"未戴安全帽", r"吸烟", r"无关人员", r"违规操作"],
        "region": [r"区域[A-Z]", r"生产区", r"仓储区", r"入口"],
        "severity": [r"高危", r"中危", r"低危"],
    }

    # 指标识别规则
    METRIC_KEYWORDS = {
        "count": [r"多少", r"数量", r"有几", r"统计"],
        "trend": [r"趋势", r"变化", r"增长", r"下降"],
        "distribution": [r"分布", r"占比", r"比例"],
    }

    async def analyze(self, question: str) -> Intent:
        """
        分析用户问题,提取意图

        Args:
            question: 用户问题

        Returns:
            Intent: 结构化意图
        """
        intent = Intent()

        # 1. 解析时间窗口
        for pattern, handler in self.TIME_PATTERNS.items():
            match = re.search(pattern, question)
            if match:
                groups = match.groups()
                if groups:
                    intent.time_window = handler(groups[0])
                else:
                    intent.time_window = handler()
                break

        # 默认时间窗口: 今天
        if not intent.time_window:
            intent.time_window = TimeWindow(
                start=datetime.now().replace(hour=0, minute=0, second=0),
                end=datetime.now(),
                label="今天"
            )

        # 2. 识别实体
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, question):
                    intent.entities.append(pattern)

        # 3. 识别指标
        for metric, keywords in self.METRIC_KEYWORDS.items():
            for keyword in keywords:
                if re.search(keyword, question):
                    intent.metrics.append(metric)
                    break

        # 默认指标: count
        if not intent.metrics:
            intent.metrics.append("count")

        # 4. 判断查询类型
        if "对比" in question or "比较" in question:
            intent.query_type = "comparison"
        elif "趋势" in question or "变化" in question:
            intent.query_type = "trend"
        elif "异常" in question:
            intent.query_type = "anomaly"
        else:
            intent.query_type = "statistics"

        # 5. 判断聚合级别
        if "小时" in question:
            intent.aggregation_level = "hour"
        elif "天" in question or "日" in question:
            intent.aggregation_level = "day"
        elif "周" in question:
            intent.aggregation_level = "week"
        elif "月" in question:
            intent.aggregation_level = "month"

        return intent
```

#### 3.3.3 Query Builder (ES查询构建器)

```python
# backend/agent/analyzers/query_builder.py

from typing import Dict, Any
from .intent_analyzer import Intent

class QueryBuilder:
    """
    ES查询构建器

    根据意图生成Elasticsearch DSL查询
    """

    def build(self, intent: Intent) -> Dict[str, Any]:
        """
        构建ES查询

        Args:
            intent: 用户意图

        Returns:
            dict: ES查询DSL
        """
        query = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": []
                }
            },
            "size": 100,
            "sort": [{"timestamp": {"order": "desc"}}]
        }

        # 1. 时间范围过滤
        if intent.time_window:
            query["query"]["bool"]["filter"].append({
                "range": {
                    "timestamp": {
                        "gte": intent.time_window.start.isoformat(),
                        "lte": intent.time_window.end.isoformat()
                    }
                }
            })

        # 2. 实体过滤
        for entity in intent.entities:
            query["query"]["bool"]["filter"].append({
                "match": {
                    "type_name": entity
                }
            })

        # 3. 构建聚合
        if intent.query_type in ["statistics", "trend"]:
            query["aggs"] = self._build_aggregations(intent)

        return query

    def _build_aggregations(self, intent: Intent) -> Dict[str, Any]:
        """构建聚合查询"""
        aggs = {}

        # 时间聚合(趋势分析)
        if "trend" in intent.metrics or intent.query_type == "trend":
            aggs["trend_over_time"] = {
                "date_histogram": {
                    "field": "timestamp",
                    "calendar_interval": intent.aggregation_level,
                    "time_zone": "Asia/Shanghai"
                }
            }

        # 分类聚合(分布分析)
        if "distribution" in intent.metrics:
            aggs["distribution_by_type"] = {
                "terms": {
                    "field": "type.keyword",
                    "size": 10
                }
            }

        return aggs
```

#### 3.3.4 Data Processor (数据处理器)

```python
# backend/agent/processors/normalizer.py

from typing import Dict, List, Any
import statistics

class DataProcessor:
    """
    数据处理器

    负责:
    1. 数据规范化
    2. 统计计算
    3. 结果整理
    """

    def process(self, raw_data: Dict[str, Any], intent) -> Dict[str, Any]:
        """
        处理ES查询结果

        Args:
            raw_data: ES原始数据
            intent: 用户意图

        Returns:
            dict: 处理后的结构化数据
        """
        result = {
            "summary": {},
            "table_data": [],
            "statistics": {},
            "charts": []
        }

        # 1. 提取hits
        hits = raw_data.get("hits", {}).get("hits", [])
        result["summary"]["total_count"] = raw_data.get("hits", {}).get("total", {}).get("value", 0)

        # 2. 转换为表格数据
        result["table_data"] = [
            {
                "timestamp": hit["_source"]["timestamp"],
                "type": hit["_source"].get("type_name", "未知"),
                "stream": hit["_source"].get("stream_name", ""),
                "confidence": hit["_source"].get("confidence", 0)
            }
            for hit in hits[:20]  # Top 20
        ]

        # 3. 统计计算
        if result["table_data"]:
            confidences = [d["confidence"] for d in result["table_data"]]
            result["statistics"] = {
                "mean_confidence": statistics.mean(confidences),
                "median_confidence": statistics.median(confidences),
                "max_confidence": max(confidences),
                "min_confidence": min(confidences)
            }

        # 4. 处理聚合数据
        aggs = raw_data.get("aggregations", {})
        if "trend_over_time" in aggs:
            result["charts"].append({
                "type": "line",
                "title": "告警趋势",
                "data": [
                    {
                        "time": bucket["key_as_string"],
                        "count": bucket["doc_count"]
                    }
                    for bucket in aggs["trend_over_time"]["buckets"]
                ]
            })

        if "distribution_by_type" in aggs:
            result["charts"].append({
                "type": "pie",
                "title": "告警类型分布",
                "data": [
                    {
                        "type": bucket["key"],
                        "count": bucket["doc_count"]
                    }
                    for bucket in aggs["distribution_by_type"]["buckets"]
                ]
            })

        return result
```

#### 3.3.5 LLM Client (大模型客户端)

```python
# backend/agent/llm/qwen_client.py

from typing import AsyncIterator
import httpx
import json

class QwenAgentClient:
    """
    Qwen大模型客户端(用于数据分析)
    """

    def __init__(self, api_key: str, model: str = "qwen-max"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    async def analyze_stream(
        self,
        question: str,
        intent,
        data: dict
    ) -> AsyncIterator[str]:
        """
        流式分析数据

        Args:
            question: 用户问题
            intent: 意图
            data: 处理后的数据

        Yields:
            str: 分析文本片段
        """
        prompt = self._build_prompt(question, intent, data)

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
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
                        "incremental_output": True,
                        "result_format": "message"
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        try:
                            data_str = line[5:].strip()
                            if data_str:
                                chunk = json.loads(data_str)
                                content = chunk.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

    def _build_prompt(self, question: str, intent, data: dict) -> str:
        """构建分析提示词"""

        # 构建数据表格
        table_md = self._format_table(data.get("table_data", []))

        # 构建统计摘要
        stats = data.get("statistics", {})
        stats_md = f"""
## 统计摘要
- 总数: {data.get('summary', {}).get('total_count', 0)}
- 平均置信度: {stats.get('mean_confidence', 0):.2%}
- 中位数置信度: {stats.get('median_confidence', 0):.2%}
"""

        prompt = f"""
# 用户问题
{question}

# 查询意图
{intent.summary()}

# 数据详情

{table_md}

{stats_md}

# 任务要求
请分析以上数据,提供:
1. **核心结论**(3-5句话,直接回答用户问题)
2. **关键发现**(数据中的重要模式或异常)
3. **行动建议**(基于数据的具体改进措施)

要求:
- 使用简洁专业的中文
- 重点突出,逻辑清晰
- 包含具体数字
- 提供可执行的建议
"""
        return prompt

    def _format_table(self, table_data: list) -> str:
        """格式化数据表格"""
        if not table_data:
            return "无数据"

        md = "## 数据明细(Top 20)\n\n"
        md += "| 时间 | 类型 | 位置 | 置信度 |\n"
        md += "|------|------|------|--------|\n"
        for row in table_data[:20]:
            md += f"| {row['timestamp'][:16]} | {row['type']} | {row['stream']} | {row['confidence']:.2%} |\n"
        return md
```

#### 3.3.6 Report Builder (报告生成器)

```python
# backend/agent/reports/builder.py

from jinja2 import Template
from typing import Dict, Any
from datetime import datetime
import json

class ReportBuilder:
    """
    报告构建器

    支持格式:
    - JSON: 结构化数据
    - Markdown: 富文本
    - HTML: 单页报告(移动端适配)
    """

    def build(
        self,
        question: str,
        intent,
        data: Dict[str, Any],
        insights: str
    ) -> Dict[str, Any]:
        """
        生成报告

        Returns:
            dict: {
                "json": {...},
                "markdown": "...",
                "html": "...",
                "metadata": {...}
            }
        """
        metadata = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "data_count": data.get("summary", {}).get("total_count", 0),
            "query_time_ms": 0  # TODO: 添加性能追踪
        }

        return {
            "json": self._build_json(question, data, insights, metadata),
            "markdown": self._build_markdown(question, data, insights),
            "html": self._build_html(question, data, insights, metadata),
            "metadata": metadata
        }

    def _build_html(
        self,
        question: str,
        data: Dict[str, Any],
        insights: str,
        metadata: Dict[str, Any]
    ) -> str:
        """生成HTML报告(移动端适配)"""

        template_str = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ question }} - AI分析报告</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', sans-serif;
            line-height: 1.8;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 16px;
        }
        .report-container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 32px 24px;
        }
        .header h1 {
            font-size: 28px;
            margin-bottom: 12px;
            font-weight: 600;
        }
        .header .meta {
            opacity: 0.95;
            font-size: 14px;
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
        }
        .section {
            padding: 32px 24px;
            border-bottom: 1px solid #f0f0f0;
        }
        .section:last-child {
            border-bottom: none;
        }
        .section-title {
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 20px;
            color: #667eea;
            display: flex;
            align-items: center;
        }
        .section-title::before {
            content: '';
            width: 4px;
            height: 20px;
            background: #667eea;
            margin-right: 12px;
            border-radius: 2px;
        }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 16px 0;
            font-size: 14px;
        }
        .data-table th,
        .data-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #f0f0f0;
        }
        .data-table th {
            background: #f8f9ff;
            font-weight: 600;
            color: #667eea;
        }
        .data-table tr:hover {
            background: #fafafa;
        }
        .insight {
            background: linear-gradient(135deg, #f8f9ff 0%, #fff 100%);
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 16px 0;
            border-radius: 8px;
            white-space: pre-wrap;
            line-height: 1.8;
        }
        .chart-suggestion {
            background: linear-gradient(135deg, #fff4e6 0%, #fff 100%);
            border-left: 4px solid #fa8c16;
            padding: 20px;
            margin: 16px 0;
            border-radius: 8px;
        }
        .chart-suggestion ul {
            margin-left: 20px;
            margin-top: 12px;
        }
        .chart-suggestion li {
            margin: 8px 0;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin: 16px 0;
        }
        .stat-card {
            background: linear-gradient(135deg, #f8f9ff 0%, #fff 100%);
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #e6e8ff;
        }
        .stat-card .label {
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }
        .stat-card .value {
            font-size: 32px;
            font-weight: 600;
            color: #667eea;
        }
        @media (max-width: 768px) {
            body {
                padding: 8px;
            }
            .header {
                padding: 24px 16px;
            }
            .header h1 {
                font-size: 22px;
            }
            .section {
                padding: 24px 16px;
            }
            .data-table {
                font-size: 12px;
            }
            .data-table th,
            .data-table td {
                padding: 8px 6px;
            }
            .stat-card .value {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="report-container">
        <div class="header">
            <h1>{{ question }}</h1>
            <div class="meta">
                <span>📅 {{ metadata.timestamp[:16] }}</span>
                <span>📊 数据量: {{ metadata.data_count }} 条</span>
                <span>⚡ 查询耗时: {{ metadata.query_time_ms }} ms</span>
            </div>
        </div>

        <div class="section">
            <div class="section-title">数据摘要</div>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="label">总告警数</div>
                    <div class="value">{{ data.summary.total_count }}</div>
                </div>
                {% if data.statistics.mean_confidence %}
                <div class="stat-card">
                    <div class="label">平均置信度</div>
                    <div class="value">{{ "%.1f"|format(data.statistics.mean_confidence * 100) }}%</div>
                </div>
                {% endif %}
            </div>

            {% if data.table_data %}
            <table class="data-table">
                <thead>
                    <tr>
                        <th>时间</th>
                        <th>类型</th>
                        <th>位置</th>
                        <th>置信度</th>
                    </tr>
                </thead>
                <tbody>
                    {% for row in data.table_data[:10] %}
                    <tr>
                        <td>{{ row.timestamp[:16] }}</td>
                        <td>{{ row.type }}</td>
                        <td>{{ row.stream }}</td>
                        <td>{{ "%.1f"|format(row.confidence * 100) }}%</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}
        </div>

        <div class="section">
            <div class="section-title">AI 分析</div>
            <div class="insight">{{ insights }}</div>
        </div>

        {% if data.charts %}
        <div class="section">
            <div class="section-title">可视化建议</div>
            <div class="chart-suggestion">
                <strong>建议创建以下图表:</strong>
                <ul>
                    {% for chart in data.charts %}
                    <li>
                        {% if chart.type == 'line' %}📈{% elif chart.type == 'pie' %}🥧{% else %}📊{% endif %}
                        <strong>{{ chart.title }}</strong> ({{ chart.type }})
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

        template = Template(template_str)
        return template.render(
            question=question,
            data=data,
            insights=insights,
            metadata=metadata
        )

    def _build_markdown(self, question: str, data: dict, insights: str) -> str:
        """生成Markdown报告"""
        md = f"# {question}\n\n"
        md += f"## AI 分析\n\n{insights}\n\n"
        md += f"## 数据摘要\n\n"
        md += f"- 总数: {data.get('summary', {}).get('total_count', 0)}\n"
        return md

    def _build_json(self, question: str, data: dict, insights: str, metadata: dict) -> dict:
        """生成JSON报告"""
        return {
            "question": question,
            "insights": insights,
            "data": data,
            "metadata": metadata
        }
```

---

## 四、API设计

### 4.1 端点列表

| 端点 | 方法 | 说明 |
|-----|------|------|
| `/api/agent/chat` | POST (SSE) | 发起对话分析(流式响应) |
| `/api/agent/history` | GET | 获取历史对话记录 |
| `/api/agent/report/:id` | GET | 获取历史报告 |

### 4.2 核心端点实现

```python
# backend/api/agent.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import json

router = APIRouter(prefix="/api/agent", tags=["agent"])

class ChatRequest(BaseModel):
    question: str
    context: Optional[dict] = None

@router.post("/chat")
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator)
):
    """
    AI智能体对话端点(SSE流式响应)

    Args:
        request.question: 用户问题
        request.context: 上下文(可选)

    Returns:
        StreamingResponse: SSE流
    """

    async def generate():
        try:
            async for message in orchestrator.process_query(
                question=request.question,
                user_id=user_id
            ):
                # SSE格式
                yield f"data: {json.dumps(message.dict(), ensure_ascii=False)}\n\n"
        except Exception as e:
            error_msg = {
                "stage": "error",
                "message": f"分析失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
```

---

## 五、前端实现

### 5.1 AgentDialog 组件

```typescript
// frontend/src/components/agent/AgentDialog.tsx

import React, { useState, useRef, useEffect } from 'react';
import { Modal } from 'antd';
import { RobotOutlined } from '@ant-design/icons';
import ChatInterface from './ChatInterface';
import './AgentDialog.css';

interface AgentDialogProps {
  visible: boolean;
  onClose: () => void;
}

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  report?: string;  // HTML报告
  timestamp: Date;
}

const AgentDialog: React.FC<AgentDialogProps> = ({ visible, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: '您好，我是AI分析助手，很高兴为您服务。您可以问我关于告警数据的任何问题。',
      timestamp: new Date()
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  // 发送消息
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isStreaming) return;

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsStreaming(true);

    // 创建SSE连接
    const url = `/api/agent/chat?question=${encodeURIComponent(text)}`;
    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    let currentMessage = '';
    let assistantMessageId = (Date.now() + 1).toString();

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.stage) {
          case 'intent':
          case 'query':
          case 'process':
            // 进度提示
            setMessages(prev => {
              const newMessages = [...prev];
              const lastMsg = newMessages[newMessages.length - 1];
              if (lastMsg && lastMsg.role === 'system' && lastMsg.id === 'progress') {
                lastMsg.content = data.message;
              } else {
                newMessages.push({
                  id: 'progress',
                  role: 'system',
                  content: data.message,
                  timestamp: new Date()
                });
              }
              return newMessages;
            });
            break;

          case 'analyze':
            // 流式追加AI分析
            if (data.content) {
              currentMessage += data.content;
              setMessages(prev => {
                const newMessages = [...prev];
                const assistantMsg = newMessages.find(m => m.id === assistantMessageId);
                if (assistantMsg) {
                  assistantMsg.content = currentMessage;
                } else {
                  newMessages.push({
                    id: assistantMessageId,
                    role: 'assistant',
                    content: currentMessage,
                    timestamp: new Date()
                  });
                }
                return newMessages;
              });
            }
            break;

          case 'completed':
            // 分析完成
            setMessages(prev => {
              const newMessages = prev.filter(m => m.id !== 'progress');
              const assistantMsg = newMessages.find(m => m.id === assistantMessageId);
              if (assistantMsg && data.data?.report_html) {
                assistantMsg.report = data.data.report_html;
              }
              return newMessages;
            });
            eventSource.close();
            setIsStreaming(false);
            break;

          case 'error':
            setMessages(prev => [...prev, {
              id: Date.now().toString(),
              role: 'system',
              content: data.message,
              timestamp: new Date()
            }]);
            eventSource.close();
            setIsStreaming(false);
            break;
        }
      } catch (error) {
        console.error('解析SSE消息失败:', error);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
      setIsStreaming(false);
    };
  };

  // 清理SSE连接
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <RobotOutlined style={{ fontSize: 20, color: '#667eea' }} />
          <span>AI分析助手</span>
        </div>
      }
      open={visible}
      onCancel={onClose}
      width="60%"
      style={{ top: '10%' }}
      footer={null}
      bodyStyle={{
        height: '70vh',
        padding: 0,
        display: 'flex',
        flexDirection: 'column'
      }}
    >
      <ChatInterface
        messages={messages}
        inputValue={inputValue}
        isStreaming={isStreaming}
        onInputChange={setInputValue}
        onSendMessage={handleSendMessage}
      />
    </Modal>
  );
};

export default AgentDialog;
```

### 5.2 AgentButton 组件

```typescript
// frontend/src/components/agent/AgentButton.tsx

import React from 'react';
import { RobotOutlined } from '@ant-design/icons';
import './AgentButton.css';

interface AgentButtonProps {
  onClick: () => void;
}

const AgentButton: React.FC<AgentButtonProps> = ({ onClick }) => {
  return (
    <div className="agent-button-container" onClick={onClick}>
      <div className="agent-icon">
        <RobotOutlined />
      </div>
      <div className="agent-text">AI分析助手</div>
    </div>
  );
};

export default AgentButton;
```

```css
/* frontend/src/components/agent/AgentButton.css */

.agent-button-container {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.agent-button-container:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
}

.agent-icon {
  font-size: 24px;
  color: white;
  animation: pulse 2s infinite;
}

.agent-text {
  font-size: 16px;
  font-weight: 600;
  color: white;
  white-space: nowrap;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}
```

---

## 六、实施计划

### Phase 1: MVP核心功能 (2-3天)

**目标**: 基础对话 + 简单查询 + 文本分析

| 任务 | 工时 | 优先级 |
|-----|------|--------|
| 后端Agent框架搭建 | 4h | P0 |
| 意图分析(规则引擎) | 3h | P0 |
| ES查询构建器 | 2h | P0 |
| 数据处理器 | 2h | P0 |
| LLM集成(Qwen) | 3h | P0 |
| API端点(SSE) | 2h | P0 |
| 前端AgentDialog | 4h | P0 |
| 前端集成到大屏 | 1h | P0 |
| **合计** | **21h** | |

### Phase 2: 报告生成 + 流式优化 (1-2天)

| 任务 | 工时 | 优先级 |
|-----|------|--------|
| HTML报告模板 | 3h | P1 |
| 报告生成器 | 2h | P1 |
| 流式响应优化 | 2h | P1 |
| 前端报告查看器 | 3h | P1 |
| 移动端样式适配 | 2h | P1 |
| **合计** | **12h** | |

### Phase 3: 增强功能 (1-2天)

| 任务 | 工时 | 优先级 |
|-----|------|--------|
| 语音输入集成 | 4h | P2 |
| 历史记录功能 | 3h | P2 |
| 小模型意图分析 | 4h | P2 |
| 图表建议优化 | 2h | P2 |
| **合计** | **13h** | |

### Phase 4: 生产优化 (1天)

| 任务 | 工时 | 优先级 |
|-----|------|--------|
| 错误处理和重试 | 3h | P1 |
| 性能优化 | 2h | P1 |
| 单元测试 | 3h | P2 |
| 文档完善 | 2h | P2 |
| **合计** | **10h** | |

---

## 七、关键技术点

### 7.1 SSE流式响应

**优势**:
- 浏览器原生支持(`EventSource`)
- 自动断线重连
- 单向推送足够

**实现要点**:
```python
# 后端
async def generate():
    async for chunk in process():
        yield f"data: {json.dumps(chunk)}\n\n"

return StreamingResponse(
    generate(),
    media_type="text/event-stream"
)
```

```typescript
// 前端
const eventSource = new EventSource('/api/agent/chat?q=xxx');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // 处理数据
};
```

### 7.2 意图分析策略

**Phase 1: 规则引擎** (快速验证)
- 时间正则: `r"最近(\d+)天"` → 提取天数
- 实体匹配: 关键词字典
- 指标识别: `"多少"` → `count`, `"趋势"` → `trend`

**Phase 2: 小模型** (提升准确率)
- 使用`Qwen-Turbo`(轻量快速)
- 提示词:
  ```
  提取JSON: {
    "time_window": {"start": "...", "end": "...", "label": "今天"},
    "entities": ["区域A", "未戴安全帽"],
    "metrics": ["count", "trend"],
    "query_type": "statistics"
  }
  ```

### 7.3 报告移动端适配

**关键CSS**:
```css
@media (max-width: 768px) {
  body { padding: 8px; }
  .header h1 { font-size: 20px; }
  .data-table { font-size: 12px; }
}
```

**响应式布局**:
- 使用`grid`自适应列数
- 表格横向滚动
- 字体大小自适应

---

## 八、风险与挑战

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| LLM响应慢 | 用户体验差 | 流式输出 + 进度提示 |
| 意图识别不准 | 查询结果错误 | Phase 1规则足够,Phase 2升级小模型 |
| ES查询复杂 | 开发周期长 | 先支持简单查询,逐步增强 |
| 移动端兼容性 | 部分浏览器不支持SSE | 降级到轮询方案 |

---

## 九、后续扩展

### 9.1 多数据源支持

当需要接入PostgreSQL、Redis等数据源时:

```python
# 抽象数据源适配器
class DataSourceAdapter(ABC):
    @abstractmethod
    async def query(self, intent: Intent) -> Dict[str, Any]:
        pass

class ESAdapter(DataSourceAdapter):
    async def query(self, intent: Intent):
        # ES查询逻辑
        pass

class PostgreSQLAdapter(DataSourceAdapter):
    async def query(self, intent: Intent):
        # SQL查询逻辑
        pass

# Orchestrator使用适配器
orchestrator = AgentOrchestrator(
    data_source=ESAdapter()  # 可切换为其他适配器
)
```

### 9.2 多模态支持

- 图片上传: "分析这张告警截图"
- 语音问答: Web Speech API
- 视频片段分析: 集成视频理解模型

### 9.3 个性化学习

- 记录用户常问问题
- 学习用户偏好的报告格式
- 智能推荐相关分析

---

## 十、总结

本架构设计遵循以下原则:

1. **模块化解耦**: Agent模块完全独立,易于扩展和维护
2. **渐进式实现**: Phase 1快速验证,后续逐步增强
3. **用户体验优先**: 流式响应、移动端适配、语音输入
4. **技术务实**: 避免过度设计,优先使用现有组件
5. **可扩展性**: 预留接口,支持多数据源、多模态

**核心优势**:
- ✅ 解耦合: Agent模块与现有系统松耦合
- ✅ 高性能: 直接访问ES,减少网络跳转
- ✅ 好体验: SSE流式响应,实时反馈
- ✅ 易维护: 清晰的模块划分,单一职责
- ✅ 可扩展: 支持后续接入MCP、多数据源

**下一步行动**:
1. 用户确认架构方案
2. 启动Phase 1开发(MVP)
3. 快速迭代验证

---

**文档版本**: v1.0
**最后更新**: 2025-10-10
**维护者**: Claude Code
