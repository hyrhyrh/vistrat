# AI智能体Phase 2-4实现计划

## 📊 Phase 1 完成情况总结

### ✅ 已完成功能
1. **5步AI分析流程**: 意图分析 → 查询数据 → 数据处理 → LLM分析 → 报告生成
2. **DeepSeek AI集成**: OpenAI兼容API,SSE流式响应
3. **Elasticsearch集成**: 告警数据查询和聚合
4. **前端对话界面**: React组件,实时流式显示
5. **多场景测试**: 8个测试场景100%通过

### 📈 Phase 1 测试结果
- **测试场景**: 8个(今天告警、趋势、类型分布、置信度等)
- **通过率**: 100%
- **平均响应时间**: 14.35秒
- **最快响应**: 10.00秒
- **最慢响应**: 17.44秒

---

## 🎯 Phase 2: HTML报告和历史记录功能 (1-2天)

### 目标
实现富文本HTML报告生成和对话历史持久化存储

### 功能清单

#### 2.1 HTML报告生成器
**后端实现** (`backend/agent/reports/html_builder.py`)

```python
class HTMLReportBuilder:
    """
    HTML报告生成器
    支持:
    - 响应式设计(移动端适配)
    - 图表可视化(ECharts集成)
    - PDF导出功能
    - 主题切换(亮色/暗色)
    """

    def build_html(
        self,
        question: str,
        intent: Intent,
        data: ProcessedData,
        insights: str,
        charts: List[ChartConfig]
    ) -> str:
        """生成完整HTML报告"""
        pass

    def generate_chart_script(self, chart_config: ChartConfig) -> str:
        """生成ECharts图表脚本"""
        pass

    def apply_theme(self, html: str, theme: str = "light") -> str:
        """应用主题样式"""
        pass
```

**技术选型**:
- **模板引擎**: Jinja2
- **图表库**: ECharts 5.x
- **样式框架**: Tailwind CSS
- **PDF导出**: WeasyPrint

**HTML模板结构**:
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI分析报告 - {{question}}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2/dist/tailwind.min.css" rel="stylesheet">
    <style>
        /* 自定义样式 */
        @media print { /* 打印样式 */ }
    </style>
</head>
<body class="bg-gray-50 dark:bg-gray-900">
    <div class="container mx-auto px-4 py-8">
        <!-- 报告头部 -->
        <header class="mb-8">
            <h1 class="text-3xl font-bold">{{question}}</h1>
            <div class="text-gray-600">
                <span>生成时间: {{timestamp}}</span>
                <span>查询耗时: {{query_time}}ms</span>
            </div>
        </header>

        <!-- AI分析内容 -->
        <section class="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 class="text-2xl font-semibold mb-4">📊 AI分析</h2>
            <div class="prose max-w-none">{{insights | safe}}</div>
        </section>

        <!-- 数据可视化 -->
        <section class="bg-white rounded-lg shadow-lg p-6 mb-6">
            <h2 class="text-2xl font-semibold mb-4">📈 数据可视化</h2>
            {% for chart in charts %}
            <div id="chart_{{loop.index}}" style="width:100%;height:400px;"></div>
            {% endfor %}
        </section>

        <!-- 数据明细表格 -->
        <section class="bg-white rounded-lg shadow-lg p-6">
            <h2 class="text-2xl font-semibold mb-4">📋 数据明细</h2>
            <table class="min-w-full divide-y divide-gray-200">
                <!-- 表格内容 -->
            </table>
        </section>

        <!-- 页脚 -->
        <footer class="mt-8 text-center text-gray-500">
            <p>AI智能分析系统 | Powered by DeepSeek</p>
        </footer>
    </div>

    <script>
        // ECharts图表渲染
        {% for chart in charts %}
        var chart{{loop.index}} = echarts.init(document.getElementById('chart_{{loop.index}}'));
        chart{{loop.index}}.setOption({{chart.config | tojson}});
        {% endfor %}
    </script>
</body>
</html>
```

#### 2.2 历史记录存储
**数据库设计** (`backend/database/schema.sql`)

```sql
-- AI对话历史表
CREATE TABLE IF NOT EXISTS ai_agent_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,  -- 对话会话ID
    question TEXT NOT NULL,
    intent JSONB NOT NULL,  -- 意图分析结果
    data_summary JSONB,  -- 数据摘要
    insights TEXT,  -- AI分析结果
    report_markdown TEXT,  -- Markdown报告
    report_html TEXT,  -- HTML报告
    metadata JSONB,  -- 元数据(耗时、数据量等)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引优化
CREATE INDEX idx_ai_agent_history_user_id ON ai_agent_history(user_id);
CREATE INDEX idx_ai_agent_history_session_id ON ai_agent_history(session_id);
CREATE INDEX idx_ai_agent_history_created_at ON ai_agent_history(created_at DESC);
CREATE INDEX idx_ai_agent_history_intent ON ai_agent_history USING GIN(intent);

-- 对话会话表
CREATE TABLE IF NOT EXISTS ai_agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT,  -- 会话标题(根据首个问题生成)
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ai_agent_sessions_user_id ON ai_agent_sessions(user_id);
```

**后端服务** (`backend/services/agent_history_service.py`)

```python
class AgentHistoryService:
    """AI Agent历史记录服务"""

    async def save_history(
        self,
        user_id: str,
        session_id: str,
        question: str,
        report: ReportOutput,
        intent: Intent,
        data: ProcessedData
    ) -> str:
        """保存对话历史"""
        pass

    async def get_user_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """获取用户历史记录"""
        pass

    async def get_session_history(
        self,
        session_id: str
    ) -> List[Dict]:
        """获取会话历史"""
        pass

    async def search_history(
        self,
        user_id: str,
        keyword: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict]:
        """搜索历史记录"""
        pass

    async def delete_history(
        self,
        history_id: str,
        user_id: str
    ) -> bool:
        """删除历史记录"""
        pass

    async def export_history_pdf(
        self,
        history_id: str
    ) -> bytes:
        """导出PDF报告"""
        pass
```

#### 2.3 前端历史记录界面
**组件设计** (`frontend/src/components/agent/HistoryPanel.tsx`)

```tsx
interface HistoryPanelProps {
    userId: string;
    onSelectHistory: (history: AgentHistory) => void;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({
    userId,
    onSelectHistory
}) => {
    const [histories, setHistories] = useState<AgentHistory[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchKeyword, setSearchKeyword] = useState('');

    return (
        <div className="history-panel">
            {/* 搜索框 */}
            <Input.Search
                placeholder="搜索历史对话"
                value={searchKeyword}
                onChange={(e) => setSearchKeyword(e.target.value)}
            />

            {/* 历史记录列表 */}
            <List
                dataSource={filteredHistories}
                renderItem={(history) => (
                    <List.Item
                        key={history.id}
                        onClick={() => onSelectHistory(history)}
                        actions={[
                            <Button icon={<DownloadOutlined />}>导出PDF</Button>,
                            <Button icon={<DeleteOutlined />} danger />
                        ]}
                    >
                        <List.Item.Meta
                            title={history.question}
                            description={`${formatTime(history.created_at)} · ${history.metadata.data_count}条数据`}
                        />
                    </List.Item>
                )}
            />
        </div>
    );
};
```

#### 2.4 API端点
**新增接口** (`backend/api/agent.py`)

```python
@router.post("/api/agent/history")
async def save_agent_history(request: SaveHistoryRequest):
    """保存对话历史"""
    pass

@router.get("/api/agent/history")
async def get_agent_history(
    user_id: str,
    limit: int = 50,
    offset: int = 0
):
    """获取用户历史记录"""
    pass

@router.get("/api/agent/history/{history_id}")
async def get_history_detail(history_id: str):
    """获取历史详情"""
    pass

@router.get("/api/agent/history/{history_id}/pdf")
async def export_history_pdf(history_id: str):
    """导出PDF报告"""
    pass

@router.delete("/api/agent/history/{history_id}")
async def delete_history(history_id: str):
    """删除历史记录"""
    pass
```

### 实现步骤
1. **Day 1 上午**: 实现HTML报告生成器,创建Jinja2模板
2. **Day 1 下午**: 数据库表结构创建,历史记录服务实现
3. **Day 2 上午**: API接口开发,前端历史面板组件
4. **Day 2 下午**: 集成测试,PDF导出功能,优化

### 验收标准
- ✅ HTML报告可以在浏览器中正常显示
- ✅ 图表可视化正确渲染
- ✅ 历史记录可以正常保存和查询
- ✅ PDF导出功能正常工作
- ✅ 移动端响应式适配良好

---

## 🎙️ Phase 3: 语音输入和小模型意图分析 (1-2天)

### 目标
集成Web Speech API实现语音输入,使用小模型(如Qwen-7B)优化意图分析速度

### 功能清单

#### 3.1 语音输入
**前端实现** (`frontend/src/components/agent/VoiceInput.tsx`)

```tsx
interface VoiceInputProps {
    onTranscript: (text: string) => void;
    language?: string;  // 默认 zh-CN
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
    onTranscript,
    language = 'zh-CN'
}) => {
    const [isListening, setIsListening] = useState(false);
    const [transcript, setTranscript] = useState('');

    const recognition = useMemo(() => {
        if ('webkitSpeechRecognition' in window) {
            const recognition = new webkitSpeechRecognition();
            recognition.lang = language;
            recognition.continuous = false;
            recognition.interimResults = true;

            recognition.onresult = (event) => {
                const transcript = Array.from(event.results)
                    .map(result => result[0].transcript)
                    .join('');
                setTranscript(transcript);

                if (event.results[0].isFinal) {
                    onTranscript(transcript);
                    setIsListening(false);
                }
            };

            return recognition;
        }
        return null;
    }, [language]);

    const startListening = () => {
        if (recognition) {
            recognition.start();
            setIsListening(true);
        }
    };

    const stopListening = () => {
        if (recognition) {
            recognition.stop();
            setIsListening(false);
        }
    };

    return (
        <div className="voice-input">
            <Button
                type={isListening ? 'danger' : 'primary'}
                icon={<AudioOutlined />}
                onClick={isListening ? stopListening : startListening}
            >
                {isListening ? '停止录音' : '语音输入'}
            </Button>
            {isListening && (
                <div className="listening-indicator">
                    <span className="pulsing-dot"></span>
                    正在聆听...
                </div>
            )}
            {transcript && (
                <div className="transcript-preview">
                    {transcript}
                </div>
            )}
        </div>
    );
};
```

**浏览器兼容性**:
- Chrome/Edge: ✅ 支持 `webkitSpeechRecognition`
- Firefox: ⚠️ 需要后端语音识别服务
- Safari: ⚠️ 需要用户授权

**备用方案**: 集成百度/讯飞语音识别API

#### 3.2 小模型意图分析
**配置管理** (`backend/config/settings.py`)

```python
class AIModelConfig:
    # 意图分析专用小模型(速度优化)
    INTENT_MODEL = os.getenv("INTENT_MODEL", "qwen-7b")
    INTENT_API_KEY = os.getenv("INTENT_API_KEY", "")
    INTENT_API_URL = os.getenv("INTENT_API_URL", "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation")

    # 深度分析大模型
    ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "deepseek-chat")
    ANALYSIS_API_KEY = os.getenv("ANALYSIS_API_KEY", "")
```

**意图分析优化** (`backend/agent/analyzers/intent_analyzer.py`)

```python
class IntentAnalyzer:
    """意图分析器 - 使用小模型快速分析"""

    def __init__(self):
        self.model_client = QwenClient(
            api_key=AIModelConfig.INTENT_API_KEY,
            model=AIModelConfig.INTENT_MODEL
        )

    async def analyze(self, question: str) -> Intent:
        """
        使用Qwen-7B快速分析意图
        目标响应时间: <1秒
        """
        prompt = self._build_intent_prompt(question)

        # 使用非流式API快速获取结果
        response = await self.model_client.generate(
            prompt=prompt,
            max_tokens=500,
            temperature=0.1  # 低温度保证稳定性
        )

        intent_json = self._extract_json(response)
        return Intent(**intent_json)

    def _build_intent_prompt(self, question: str) -> str:
        """构建意图分析提示词(精简版)"""
        return f"""分析用户问题的意图,返回JSON格式:
{{
    "time_window": {{"start": "...", "end": "...", "label": "今天/昨天/最近7天"}},
    "entities": ["实体1", "实体2"],
    "metrics": ["count", "avg", "distribution"],
    "query_type": "statistics/trend/comparison",
    "filters": {{}},
    "aggregation_level": "hour/day/week"
}}

问题: {question}

JSON:"""
```

**性能对比**:
| 模型 | 响应时间 | Token成本 | 准确度 |
|------|---------|----------|--------|
| DeepSeek-Chat (原) | 2-3秒 | 高 | 95% |
| Qwen-7B (新) | <1秒 | 低 | 92% |

#### 3.3 语音命令快捷方式
**预定义命令** (`backend/agent/voice_commands.py`)

```python
VOICE_COMMANDS = {
    "今天告警": "今天有多少告警",
    "本周趋势": "最近一周的告警数量趋势",
    "安全帽违规": "今天未戴安全帽的告警有多少",
    "高风险告警": "今天置信度大于85%的告警",
    "查看帮助": "显示可用的语音命令列表"
}

def match_voice_command(transcript: str) -> Optional[str]:
    """匹配语音命令快捷方式"""
    for shortcut, full_command in VOICE_COMMANDS.items():
        if shortcut in transcript:
            return full_command
    return transcript  # 返回原始输入
```

### 实现步骤
1. **Day 1 上午**: 前端语音输入组件开发
2. **Day 1 下午**: 集成Web Speech API,测试浏览器兼容性
3. **Day 2 上午**: 集成Qwen-7B小模型,优化意图分析速度
4. **Day 2 下午**: 语音命令快捷方式,端到端测试

### 验收标准
- ✅ 语音输入可以正常工作(Chrome/Edge)
- ✅ 语音识别准确率 >90%
- ✅ 意图分析响应时间 <1秒
- ✅ 语音命令快捷方式正常工作

---

## 🚀 Phase 4: 生产优化和测试覆盖 (1天)

### 目标
优化生产环境性能,提高系统稳定性,完善测试覆盖

### 功能清单

#### 4.1 性能优化
**缓存策略** (`backend/services/cache_service.py`)

```python
class AgentCacheService:
    """AI Agent缓存服务"""

    async def cache_intent(self, question: str, intent: Intent, ttl: int = 3600):
        """缓存意图分析结果(1小时)"""
        pass

    async def cache_query_result(self, query_hash: str, data: ProcessedData, ttl: int = 300):
        """缓存查询结果(5分钟)"""
        pass

    async def get_cached_intent(self, question: str) -> Optional[Intent]:
        """获取缓存的意图"""
        pass
```

**数据库连接池优化**:
```python
# backend/database/connection.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,  # 连接池大小
    max_overflow=40,  # 最大溢出连接
    pool_pre_ping=True,  # 连接健康检查
    pool_recycle=3600  # 1小时回收连接
)
```

**ES查询优化**:
```python
# 使用_source过滤,只返回必要字段
query = {
    "_source": ["created_at", "alert_type", "confidence", "location"],
    "query": {...},
    "size": 100
}
```

#### 4.2 错误处理和重试
**智能重试机制** (`backend/agent/core/retry_handler.py`)

```python
class RetryHandler:
    """智能重试处理器"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIError, TimeoutError))
    )
    async def call_llm_with_retry(self, prompt: str) -> str:
        """带重试的LLM调用"""
        pass
```

**降级策略**:
```python
class FallbackHandler:
    """降级处理器"""

    async def handle_llm_failure(self, data: ProcessedData) -> str:
        """LLM失败时使用模板生成基础报告"""
        return f"""
        ### 数据摘要
        - 总计: {data.summary['total_count']}条
        - 平均置信度: {data.statistics.get('mean_confidence', 0):.1%}

        注: AI分析服务暂时不可用,以上为基础统计信息。
        """
```

#### 4.3 监控和日志
**性能监控** (`backend/services/metrics_service.py`)

```python
class MetricsService:
    """性能指标监控"""

    async def record_agent_query(
        self,
        question: str,
        elapsed_time: float,
        data_count: int,
        success: bool
    ):
        """记录Agent查询指标"""
        metrics = {
            "timestamp": datetime.now(),
            "question_length": len(question),
            "elapsed_time": elapsed_time,
            "data_count": data_count,
            "success": success
        }
        await self._save_to_influxdb(metrics)

    async def get_performance_stats(self, days: int = 7) -> Dict:
        """获取性能统计"""
        return {
            "avg_response_time": 0,
            "success_rate": 0,
            "total_queries": 0,
            "p95_response_time": 0
        }
```

**日志结构化**:
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "agent_query_completed",
    user_id=user_id,
    question=question,
    elapsed_time=elapsed,
    data_count=data_count,
    intent_type=intent.query_type
)
```

#### 4.4 单元测试和集成测试
**单元测试** (`backend/tests/test_intent_analyzer.py`)

```python
import pytest
from agent.analyzers.intent_analyzer import IntentAnalyzer

class TestIntentAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return IntentAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_count_query(self, analyzer):
        """测试计数类查询意图识别"""
        result = await analyzer.analyze("今天有多少告警")
        assert result.query_type == "statistics"
        assert "count" in result.metrics
        assert result.time_window.label == "今天"

    @pytest.mark.asyncio
    async def test_analyze_trend_query(self, analyzer):
        """测试趋势类查询意图识别"""
        result = await analyzer.analyze("最近一周的告警趋势")
        assert result.query_type == "statistics"
        assert "trend" in result.metrics
```

**集成测试** (`backend/tests/test_agent_e2e.py`)

```python
@pytest.mark.asyncio
async def test_agent_complete_flow():
    """测试完整AI Agent流程"""
    client = TestClient(app)

    response = client.get("/api/agent/chat?question=今天有多少告警")

    stages = set()
    for line in response.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            stages.add(data['stage'])

    assert 'intent' in stages
    assert 'query' in stages
    assert 'process' in stages
    assert 'analyze' in stages
    assert 'report' in stages
    assert 'completed' in stages
```

**性能基准测试** (`backend/tests/benchmark_agent.py`)

```python
import asyncio
import time

async def benchmark_agent_queries():
    """压力测试AI Agent性能"""
    questions = [
        "今天有多少告警",
        "最近一周的告警趋势",
        "今天未戴安全帽的告警有多少"
    ] * 10  # 30个请求

    start = time.time()
    tasks = [call_agent_api(q) for q in questions]
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start

    success_count = sum(1 for r in results if r['success'])

    print(f"总请求: {len(questions)}")
    print(f"成功: {success_count} ({success_count/len(questions)*100:.1f}%)")
    print(f"总耗时: {elapsed:.2f}秒")
    print(f"QPS: {len(questions)/elapsed:.2f}")
```

#### 4.5 文档完善
**API文档** (OpenAPI/Swagger)

```python
@router.get(
    "/api/agent/chat",
    response_model=None,
    summary="AI智能分析",
    description="""
    使用AI对告警数据进行智能分析

    支持的问题类型:
    - 统计类: "今天有多少告警"
    - 趋势类: "最近一周的告警趋势"
    - 对比类: "昨天和今天的告警对比"
    - 分布类: "各类型告警的分布"

    返回格式: Server-Sent Events (SSE)
    """,
    responses={
        200: {"description": "SSE流式响应"},
        400: {"description": "请求参数错误"},
        500: {"description": "服务器内部错误"}
    }
)
async def agent_chat(question: str = Query(..., description="用户问题")):
    pass
```

**部署文档** (`docs/DEPLOYMENT.md`)

```markdown
# AI Agent生产部署指南

## 环境要求
- Python 3.11+
- PostgreSQL 14+
- Elasticsearch 8.x
- Redis 7.x
- Node.js 18+

## 环境变量配置
```bash
# AI模型配置
DEEPSEEK_API_KEY=sk-xxx
QWEN_API_KEY=sk-xxx

# 数据库配置
DB_HOST=localhost
DB_NAME=ai_watchdog
DB_USER=postgres
DB_PASSWORD=xxx

# Elasticsearch配置
ES_HOST=localhost
ES_PORT=9200

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Docker部署
```bash
docker-compose up -d
```

## 性能调优建议
1. 启用Redis缓存
2. 配置ES连接池
3. 使用CDN加速前端资源
4. 启用Nginx反向代理
```

### 实现步骤
1. **上午**: 性能优化(缓存、连接池、查询优化)
2. **下午前半**: 错误处理、监控日志、单元测试
3. **下午后半**: 集成测试、性能基准测试、文档完善

### 验收标准
- ✅ 响应时间P95 <20秒
- ✅ 并发10用户QPS >0.5
- ✅ 单元测试覆盖率 >80%
- ✅ 集成测试通过率 100%
- ✅ API文档完整
- ✅ 部署文档完整

---

## 📊 总体时间线

| Phase | 功能 | 预计时间 | 关键里程碑 |
|-------|------|---------|-----------|
| Phase 1 ✅ | 基础AI分析流程 | 已完成 | 5步流程+DeepSeek集成 |
| Phase 2 | HTML报告+历史记录 | 1-2天 | HTML生成+数据库存储 |
| Phase 3 | 语音输入+小模型 | 1-2天 | Web Speech API+Qwen-7B |
| Phase 4 | 生产优化+测试 | 1天 | 性能优化+测试覆盖 |
| **总计** | | **3-5天** | 完整企业级AI Agent |

## 🎯 成功指标

### 功能完整性
- ✅ Markdown报告
- ⏳ HTML报告
- ⏳ PDF导出
- ⏳ 历史记录
- ⏳ 语音输入
- ⏳ 小模型意图分析

### 性能指标
- 意图分析: <1秒
- 数据查询: <500ms
- LLM分析: <15秒
- 报告生成: <1秒
- 端到端响应: <20秒(P95)

### 质量指标
- 单元测试覆盖率: >80%
- 集成测试通过率: 100%
- 意图识别准确率: >90%
- 系统可用性: >99%

## 📚 参考资料

### 技术文档
- [Jinja2模板引擎](https://jinja.palletsprojects.com/)
- [ECharts图表库](https://echarts.apache.org/zh/index.html)
- [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API)
- [WeasyPrint PDF生成](https://weasyprint.org/)
- [通义千问API](https://help.aliyun.com/zh/dashscope/)

### 最佳实践
- [FastAPI最佳实践](https://fastapi.tiangolo.com/tutorial/)
- [React最佳实践](https://react.dev/learn)
- [Elasticsearch查询优化](https://www.elastic.co/guide/en/elasticsearch/reference/current/tune-for-search-speed.html)
- [PostgreSQL性能调优](https://www.postgresql.org/docs/current/performance-tips.html)

---

**文档版本**: v1.0
**创建时间**: 2025-10-10
**最后更新**: 2025-10-10
**负责人**: AI Agent开发组
