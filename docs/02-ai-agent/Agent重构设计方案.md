# Agent智能分析重构设计方案 (最终确定版)

## 一、核心理念

### ✅ 最终确定的架构
**LLM（多模型可选） + ES工具调用 + 上下文工程**

这是经过深思熟虑后确定的生产架构，**完全抛弃复杂的Orchestrator模式**。

### 核心特性
1. **LLM可选**: 支持Claude、DeepSeek、Qwen等多种大模型
2. **统一架构**: 所有LLM都使用相同的"工具调用+上下文工程"模式
3. **简洁高效**: 直接利用LLM的Function Calling能力，无需中间层
4. **效果卓越**: 通过丰富的上下文工程，达到Claude + MCP的分析水平
5. **成本灵活**: 用户可根据需求选择不同成本的模型

### 为什么选择这个架构？
1. **简洁性**: 无需Orchestrator、IntentAnalyzer等复杂组件
2. **统一性**: 一套架构支持多个LLM，代码复用度高
3. **易维护**: 代码量少，逻辑清晰，bug更少
4. **可扩展**: 轻松添加新的LLM（如GPT-4、Gemini等）

### 抛弃的旧架构
❌ **Orchestrator模式** - 复杂的编排层
❌ **IntentAnalyzer** - 意图识别组件
❌ **QueryBuilder** - 查询构建器
❌ **DataProcessor** - 数据处理器
❌ **多层消息传递** - 复杂的状态管理

---

## 二、架构设计（最终版）

### 2.1 整体架构

```
┌─────────────────────────────┐
│         前端UI              │
│  [模型选择: Claude/DeepSeek/Qwen] │
└──────────┬──────────────────┘
           │ HTTP GET /api/agent/chat?model=xxx&question=xxx
           ↓
┌──────────────────────────────────────────────┐
│         API Layer (agent.py)                 │
│  - 参数验证                                   │
│  - 模型路由                                   │
│  - SSE流式响应                                │
└──────────┬───────────────────────────────────┘
           │ 根据model参数选择客户端
           │
     ┌─────┴─────┬─────────────┐
     ↓           ↓             ↓
┌─────────┐ ┌──────────┐ ┌──────────┐
│ Claude  │ │DeepSeek  │ │  Qwen    │
│ESClient │ │ESClient  │ │ESClient  │
└─────────┘ └──────────┘ └──────────┘
     │           │             │
     └─────┬─────┴─────────────┘
           │ 统一的实现模式
           ↓
┌──────────────────────────────────────────────┐
│      LLM ES Client (统一实现模式)            │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │  1. 上下文工程                       │    │
│  │     - 加载 ES Schema 文档           │    │
│  │     - 业务场景说明                  │    │
│  │     - 查询模式示例                  │    │
│  └─────────────────────────────────────┘    │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │  2. Function Calling 工具定义        │    │
│  │     - elasticsearch_search          │    │
│  │     - elasticsearch_aggregate       │    │
│  │     - elasticsearch_esql (可选)     │    │
│  └─────────────────────────────────────┘    │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │  3. 工具执行器                       │    │
│  │     - 调用 ES Python 客户端         │    │
│  │     - 错误处理和重试                │    │
│  └─────────────────────────────────────┘    │
│                                               │
│  ┌─────────────────────────────────────┐    │
│  │  4. 流式输出                         │    │
│  │     - 异步生成器                    │    │
│  │     - 逐块返回 Markdown 分析        │    │
│  └─────────────────────────────────────┘    │
└───────────┬───────────────────────────────────┘
            │ 直接查询
            ↓
┌───────────────────────┐
│   Elasticsearch       │
│  - video_alerts       │
│  - 其他业务索引       │
└───────────────────────┘
```

### 2.2 多LLM统一实现

#### 基础抽象（最小化）
```python
class BaseLLMESClient(ABC):
    """LLM + ES客户端基类"""

    @abstractmethod
    async def analyze_stream(
        self,
        question: str
    ) -> AsyncGenerator[str, None]:
        """流式分析，返回Markdown片段"""
        pass

    async def _load_es_context(self) -> str:
        """加载ES上下文文档（共享）"""
        # 读取 elasticsearch_schema.md
        pass

    async def _execute_es_tool(
        self,
        tool_name: str,
        parameters: dict
    ) -> dict:
        """执行ES工具（共享）"""
        # 统一的ES查询执行逻辑
        pass
```

#### 具体实现
```python
# Claude实现
class ClaudeESClient(BaseLLMESClient):
    def __init__(self):
        self.client = anthropic.Anthropic()
        self.es_client = AsyncElasticsearch()

    async def analyze_stream(self, question: str):
        # 使用Claude API + Function Calling
        pass

# DeepSeek实现
class DeepSeekESClient(BaseLLMESClient):
    def __init__(self):
        self.client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )
        self.es_client = AsyncElasticsearch()

    async def analyze_stream(self, question: str):
        # 使用OpenAI兼容API + Function Calling
        pass

# Qwen实现
class QwenESClient(BaseLLMESClient):
    def __init__(self):
        self.client = dashscope.Generation()
        self.es_client = AsyncElasticsearch()

    async def analyze_stream(self, question: str):
        # 使用通义千问API + Function Calling
        pass
```

### 2.3 核心优势

#### ✅ 完全抛弃Orchestrator
- **不需要**: IntentAnalyzer、QueryBuilder、DataProcessor等中间组件
- **不需要**: 复杂的AgentFactory和消息传递
- **不需要**: 多层抽象和状态管理

#### ✅ 统一的实现模式
- 所有LLM使用相同的架构模式
- 共享ES上下文加载和工具执行逻辑
- 代码复用，易于维护

#### ✅ LLM原生能力
- 直接利用各LLM的Function Calling能力
- DeepSeek、Qwen都支持OpenAI格式的Function Calling
- 无中间层损耗，查询效率更高

#### ✅ 上下文工程是关键
- 提供完整的ES索引Schema文档
- 包含字段说明、类型、查询示例
- 说明业务场景和分析模式
- 比复杂的Orchestrator更强大

---

## 三、数据流设计（最终版）

### 3.1 完整分析流程

```
用户提问: "今天有多少条告警？按类型统计"
  ↓
前端发起请求: GET /api/agent-claude/chat?question=xxx
  ↓
agent_claude.py 处理请求
  ↓
创建 ClaudeESClient 实例
  ↓
调用 analyze_stream(question) 方法
  ↓
┌─────────────────────────────────────────────┐
│         Claude API 处理流程                  │
│                                              │
│  1. 加载系统提示词                           │
│     - 读取 elasticsearch_schema.md          │
│     - 包含完整的业务上下文                  │
│                                              │
│  2. Claude理解问题                           │
│     - 识别意图: 统计查询                    │
│     - 确定索引: video_alerts                │
│     - 规划查询: 按alert_type分组统计        │
│                                              │
│  3. Claude调用工具                           │
│     Tool: elasticsearch_aggregate            │
│     Index: video_alerts                      │
│     Query: {"range": {"datetime": ...}}      │
│     Aggs: {"terms": {"field": "alert_type"}} │
│                                              │
│  4. 执行ES查询                               │
│     ClaudeESClient._execute_tool()          │
│     → ES Python客户端                       │
│     → 返回聚合结果                          │
│                                              │
│  5. Claude分析结果                           │
│     - 解读数据                              │
│     - 生成洞察                              │
│     - 格式化为Markdown                      │
│                                              │
│  6. 流式输出                                 │
│     yield "## 📊 告警统计\n"                │
│     yield "今天共有14条告警...\n"           │
│     yield "| 类型 | 数量 |\n"               │
│     ...                                      │
└─────────────────────────────────────────────┘
  ↓
SSE流式传输到前端
  ↓
前端ReactMarkdown渲染
  ↓
用户看到优雅的分析报告
```

### 3.2 工具调用示例

#### 场景1: 简单统计
```json
{
  "tool": "elasticsearch_search",
  "parameters": {
    "index": "video_alerts",
    "query": {
      "range": {
        "datetime": {"gte": "now-1d"}
      }
    },
    "size": 0
  }
}
```

#### 场景2: 聚合分析
```json
{
  "tool": "elasticsearch_aggregate",
  "parameters": {
    "index": "video_alerts",
    "query": {...},
    "aggregations": {
      "by_type": {
        "terms": {"field": "alert_type"}
      },
      "by_location": {
        "terms": {"field": "location"}
      }
    }
  }
}
```

#### 场景3: ES|QL查询
```json
{
  "tool": "elasticsearch_esql",
  "parameters": {
    "query": "FROM video_alerts | WHERE datetime >= NOW() - 1 day | STATS count = COUNT(*) BY alert_type | SORT count DESC"
  }
}
```

---

## 四、SSE消息格式（最终版）

### 4.1 消息结构

```typescript
interface ClaudeAgentMessage {
    stage: 'analyzing' | 'completed' | 'error';
    content?: string;        // Markdown格式的分析内容（流式输出）
    message?: string;        // 状态消息
}
```

**设计理念**: 极简，只关注核心功能
- `analyzing`: 分析进行中，content包含Markdown内容片段
- `completed`: 分析完成
- `error`: 发生错误，message包含错误描述

### 4.2 实际消息流示例

用户问题: "今天有多少条告警？按类型统计"

```
data: {"stage": "analyzing", "content": "## 📊 "}

data: {"stage": "analyzing", "content": "今天的告警"}

data: {"stage": "analyzing", "content": "数据统计\n\n"}

data: {"stage": "analyzing", "content": "**查询时间**: 2025-10-15\n\n"}

data: {"stage": "analyzing", "content": "### 告警总览\n"}

data: {"stage": "analyzing", "content": "- **告警总数**: 14条\n"}

data: {"stage": "analyzing", "content": "- **告警级别**: 全部为critical(严重)\n\n"}

data: {"stage": "analyzing", "content": "### 告警类型分布\n\n"}

data: {"stage": "analyzing", "content": "| 告警类型 | 数量 | 占比 |\n"}

data: {"stage": "analyzing", "content": "|---------|------|------|\n"}

data: {"stage": "analyzing", "content": "| 未佩戴安全帽 | 8 | 57.1% |\n"}

data: {"stage": "analyzing", "content": "| 佩戴安全帽(违规) | 6 | 42.9% |\n\n"}

data: {"stage": "analyzing", "content": "### 关键发现\n"}

data: {"stage": "analyzing", "content": "- 📈 所有告警都与安全帽检测相关\n"}

data: {"stage": "analyzing", "content": "- ⏰ 告警集中在早班(6点)和上午(11点)\n"}

data: {"stage": "analyzing", "content": "- 📍 示例摄像头01产生了6条告警，需要重点关注\n"}

data: {"stage": "completed", "message": "分析完成"}
```

### 4.3 前端处理

```typescript
const eventSource = new EventSource(
  `/api/agent-claude/chat?question=${encodeURIComponent(question)}`
);

let analysisContent = '';

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.stage === 'analyzing') {
    // 累积Markdown内容
    analysisContent += data.content;
    // 实时渲染
    setMarkdown(analysisContent);
  } else if (data.stage === 'completed') {
    eventSource.close();
    setAnalyzing(false);
  } else if (data.stage === 'error') {
    message.error(data.message);
    eventSource.close();
  }
};
```

---

## 五、前端交互设计

### 5.1 模型选择UI

```tsx
<Select defaultValue="deepseek" onChange={handleModelChange}>
  <Option value="deepseek">
    <Badge color="green" text="DeepSeek (经济)" />
  </Option>
  <Option value="qwen">
    <Badge color="blue" text="通义千问 (均衡)" />
  </Option>
  <Option value="claude">
    <Badge color="gold" text="Claude (高级)" />
  </Option>
</Select>
```

### 5.2 分析过程展示

```tsx
<Timeline>
  <Timeline.Item color="blue">
    <Spin /> 正在理解问题...
  </Timeline.Item>
  <Timeline.Item color="blue">
    <Spin /> 正在查询数据... (30%)
  </Timeline.Item>
  <Timeline.Item color="green">
    <CheckCircle /> 查询完成，正在分析...
  </Timeline.Item>
</Timeline>

<ReactMarkdown>{analysisContent}</ReactMarkdown>
```

### 5.3 流式渲染效果

- **打字机效果**: 逐字显示分析内容
- **状态图标**: 不同阶段显示不同图标(🤔💭🔍📊✅)
- **进度提示**: 查询和分析的进度条
- **Markdown渲染**: 表格、列表、代码块等

---

## 六、实施计划（MVP优先）

### Phase 1: MVP核心功能 (2-3天) ✅ 优先
**目标**: 快速实现可用的多模型Agent

#### 1.1 基础架构
- [x] 创建ClaudeESClient (已完成)
- [ ] 创建DeepSeekESClient
- [ ] 创建QwenESClient
- [ ] 创建BaseLLMESClient抽象基类（提取共享逻辑）

#### 1.2 统一API
- [ ] 修改 `api/agent.py` 支持model参数
- [ ] 实现模型路由逻辑
- [ ] 统一SSE消息格式
- [ ] 添加基础错误处理

#### 1.3 ES上下文工程
- [x] ES Schema文档已存在
- [ ] 优化Schema文档的结构和示例
- [ ] 添加更多业务场景说明

#### 1.4 基础测试
- [ ] 测试Claude模型
- [ ] 测试DeepSeek模型
- [ ] 测试Qwen模型
- [ ] 验证ES查询执行

### Phase 2: 前端集成 (2-3天)
**目标**: 提供优雅的用户交互

#### 2.1 模型选择UI
- [ ] 添加模型选择下拉框
- [ ] 显示模型特性（成本、速度、质量）
- [ ] 记住用户选择的模型

#### 2.2 流式渲染优化
- [ ] 优化Markdown实时渲染
- [ ] 添加打字机效果
- [ ] 支持表格、代码块等复杂格式

#### 2.3 状态反馈
- [ ] 显示分析进度
- [ ] 显示使用的模型
- [ ] 显示预估成本

### Phase 3: 功能增强 (1-2天)
**目标**: 提升用户体验和系统稳定性

#### 3.1 错误处理
- [ ] API调用失败重试
- [ ] ES查询错误处理
- [ ] 友好的错误提示

#### 3.2 性能优化
- [ ] ES上下文缓存
- [ ] 并发请求控制
- [ ] 响应时间监控

#### 3.3 成本监控
- [ ] Token使用统计
- [ ] 成本计算和展示
- [ ] 月度成本报表

### Phase 4: 高级功能 (后续迭代)
**目标**: 企业级功能完善

- [ ] 多轮对话支持（会话管理）
- [ ] 自动生成可视化配置
- [ ] 定时分析报表
- [ ] 告警预测功能
- [ ] 模型性能对比
- [ ] 用户偏好学习

---

## 七、技术要点

### 7.1 Claude Function Calling

```python
tools = [
    {
        "name": "elasticsearch_search",
        "description": "搜索Elasticsearch数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "index": {"type": "string"},
                "query": {"type": "object"},
                "size": {"type": "integer"}
            }
        }
    }
]

response = client.messages.create(
    model="claude-sonnet-4",
    tools=tools,
    messages=[{"role": "user", "content": question}],
    stream=True
)
```

### 7.2 异步流式处理

```python
async def analyze_stream(self, question: str):
    for event in response:  # Claude SDK是同步的
        if event.type == "text":
            yield AgentMessage(stage="analyzing", content=event.text)
        elif event.type == "tool_use":
            # 执行工具调用
            result = await self._execute_tool(event)
            # 继续分析
```

### 7.3 ES查询优化

**优先使用ES|QL** (简洁语法):
```sql
FROM video_alerts
| WHERE datetime >= NOW() - 1 day
| STATS count = COUNT(*) BY alert_type
| SORT count DESC
```

**复杂场景用Query DSL**:
```json
{
  "query": {
    "bool": {
      "must": [
        {"range": {"datetime": {"gte": "now-1d"}}}
      ]
    }
  },
  "aggs": {
    "by_type": {
      "terms": {"field": "alert_type"}
    }
  }
}
```

---

## 八、模型对比与选择

### 8.1 模型特性对比

| 特性 | Claude Sonnet 4 | DeepSeek V3 | Qwen Max |
|------|----------------|-------------|----------|
| **Function Calling** | ✅ 原生支持 | ✅ OpenAI格式 | ✅ OpenAI格式 |
| **上下文长度** | 200K tokens | 64K tokens | 32K tokens |
| **成本（输入）** | ¥0.02/1K | ¥0.001/1K | ¥0.004/1K |
| **成本（输出）** | ¥0.10/1K | ¥0.002/1K | ¥0.012/1K |
| **响应速度** | 中 | 快 | 快 |
| **分析质量** | 优秀 | 良好 | 良好 |
| **API稳定性** | 高 | 高 | 高 |

### 8.2 成本估算

#### 单次分析成本（典型场景）
```
输入tokens:
  - ES Schema上下文: 3000 tokens
  - 用户问题: 50 tokens
  - ES查询结果: 2000 tokens
  Total Input: ~5000 tokens

输出tokens:
  - Markdown分析报告: 1000 tokens
```

| 模型 | 输入成本 | 输出成本 | 单次总成本 |
|------|---------|---------|-----------|
| Claude | ¥0.10 | ¥0.10 | **¥0.20** |
| DeepSeek | ¥0.005 | ¥0.002 | **¥0.007** |
| Qwen | ¥0.02 | ¥0.012 | **¥0.032** |

#### 月度成本（1000次查询）
- **Claude**: ¥200/月（高质量场景）
- **DeepSeek**: ¥7/月（日常使用）
- **Qwen**: ¥32/月（平衡选择）

### 8.3 使用建议

#### 场景1: 日常告警查询
**推荐**: DeepSeek
- 成本最低，响应快
- 足以应对简单统计和查询
- 示例："今天有多少条告警"

#### 场景2: 趋势分析和对比
**推荐**: Qwen
- 性价比适中
- 分析能力良好
- 示例："对比本周和上周的告警趋势"

#### 场景3: 深度洞察和异常检测
**推荐**: Claude
- 分析质量最高
- 提供深度洞察
- 示例："分析告警数据中的异常模式并给出改进建议"

#### 场景4: 定时报表
**推荐**: Qwen或DeepSeek
- 根据报表复杂度选择
- 批量生成时考虑成本

### 8.4 成本控制策略

1. **默认模型**: DeepSeek（日常使用）
2. **智能升级**: 检测到复杂问题时提示用户切换Claude
3. **用户偏好**: 支持用户设置默认模型
4. **成本监控**: 统计每个用户的模型使用量和成本
5. **配额管理**: 为Claude设置月度配额

---

## 九、预期效果

### 9.1 分析能力提升

- ✅ 自动生成复杂ES查询
- ✅ 深度数据洞察和趋势分析
- ✅ 多维度对比分析(本周vs上周等)
- ✅ 异常检测和预警

### 9.2 用户体验提升

- ✅ 流式输出,实时反馈
- ✅ 清晰的状态提示
- ✅ 优雅的Markdown渲染
- ✅ 灵活的模型选择

### 9.3 系统质量提升

- ✅ 清晰的架构分层
- ✅ 易于扩展新模型
- ✅ 统一的API接口
- ✅ 完善的错误处理

---

## 十、附录

### A. 核心文件结构

#### 后端文件（最终版）
```
backend/
├── agent/
│   ├── llm/                              # LLM客户端目录
│   │   ├── base_llm_es_client.py        # LLM+ES基类 [待创建]
│   │   ├── claude_es_client.py          # Claude实现 [已完成]
│   │   ├── deepseek_es_client.py        # DeepSeek实现 [待创建]
│   │   └── qwen_es_client.py            # Qwen实现 [待创建]
│   └── docs/
│       └── elasticsearch_schema.md       # ES Schema文档 [已存在]
├── api/
│   ├── agent.py                          # 统一Agent API [需修改]
│   └── agent_claude.py                   # 临时Claude专用API [已完成，后续可删除]
└── config/
    └── settings.py                       # 系统配置
```

#### 前端文件
```
frontend/src/
├── pages/
│   └── AgentPage.tsx                     # Agent分析页面 [需增强]
├── components/
│   └── agent/
│       ├── ModelSelector.tsx             # 模型选择器 [待创建]
│       └── MarkdownRenderer.tsx          # Markdown渲染器 [待创建]
└── services/
    └── agentService.ts                   # Agent API服务 [需更新]
```

### B. 环境变量配置

```bash
# ===================
# LLM API密钥
# ===================
# Claude API
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# DeepSeek API (OpenAI兼容)
DEEPSEEK_API_KEY=sk-xxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com

# Qwen API (DashScope)
DASHSCOPE_API_KEY=sk-xxxxx

# ===================
# Elasticsearch
# ===================
ES_HOST=localhost
ES_PORT=9200
ES_SSL=false
ES_INDEX_PREFIX=video_

# ===================
# Agent配置
# ===================
# 默认模型 (claude/deepseek/qwen)
DEFAULT_LLM_MODEL=deepseek

# ES上下文文档路径
ES_SCHEMA_DOC_PATH=agent/docs/elasticsearch_schema.md

# 最大并发分析请求数
MAX_CONCURRENT_ANALYSIS=10

# 分析超时时间（秒）
ANALYSIS_TIMEOUT=120
```

### C. API端点规范

#### 统一Agent API（最终版本）
```
GET /api/agent/chat

Query Parameters:
  - model: string (required) - claude | deepseek | qwen
  - question: string (required) - 用户问题
  - session_id: string (optional) - 会话ID
  - user_id: string (optional) - 用户ID

Response: SSE Stream
  Content-Type: text/event-stream

  data: {"stage": "analyzing", "content": "Markdown片段"}
  data: {"stage": "analyzing", "content": "更多内容"}
  data: {"stage": "completed", "message": "分析完成"}
```

#### 健康检查
```
GET /api/agent/health

Response:
{
  "status": "healthy",
  "supported_models": ["claude", "deepseek", "qwen"],
  "elasticsearch": "connected",
  "version": "2.0-llm-es"
}
```

### D. 参考资料

#### LLM Function Calling
- [Claude Tool Use](https://docs.anthropic.com/claude/docs/tool-use)
- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling) (DeepSeek兼容)
- [DashScope Tools](https://help.aliyun.com/zh/dashscope/developer-reference/use-qwen-by-calling-api)

#### Elasticsearch
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [Query DSL](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl.html)
- [ES|QL Reference](https://www.elastic.co/guide/en/elasticsearch/reference/current/esql.html)

#### SSE (Server-Sent Events)
- [MDN SSE Guide](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

---

## 十一、总结

### 核心设计原则
1. **简洁至上**: 抛弃Orchestrator，直接使用LLM + ES
2. **统一架构**: 多个LLM使用相同的实现模式
3. **上下文工程**: 完整的ES Schema文档是关键
4. **成本可控**: 支持多模型选择，灵活控制成本

### 关键成功因素
- ✅ **LLM原生能力**: 充分利用Function Calling
- ✅ **丰富上下文**: 完整的ES Schema + 业务场景
- ✅ **流式输出**: 优雅的用户体验
- ✅ **多模型支持**: Claude/DeepSeek/Qwen可选

### 下一步行动
1. 实现DeepSeekESClient和QwenESClient
2. 创建BaseLLMESClient提取共享逻辑
3. 修改API支持model参数路由
4. 前端添加模型选择UI
5. 完整测试三个模型的分析效果

---

*文档版本: v2.0 (多LLM最终版)*
*最后更新: 2025-10-15*
*架构: LLM(可选) + ES工具调用 + 上下文工程*
