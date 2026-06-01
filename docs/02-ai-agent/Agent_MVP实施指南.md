# Agent MVP实施指南 (多LLM版本)

## 一、MVP目标

**核心功能**: 实现多LLM驱动的智能告警分析Agent

**架构**: LLM（Claude/DeepSeek/Qwen可选） + ES工具调用 + 上下文工程

**效果目标**:
- 自动生成精确的ES查询
- 深度数据分析和洞察
- 优雅的Markdown输出
- 流式显示分析过程
- 支持多个LLM模型选择
- 灵活的成本控制

---

## 二、技术架构(最终确定版)

### 2.1 架构图

```
前端UI [模型选择] → /api/agent/chat?model=xxx&question=xxx
  ↓
agent.py (模型路由)
  ↓
  ├─ model=claude   → ClaudeESClient
  ├─ model=deepseek → DeepSeekESClient
  └─ model=qwen     → QwenESClient
       ↓
  LLM API + Function Calling
       ↓
  执行ES查询 → 分析数据 → 流式返回Markdown
       ↓
  前端SSE流式渲染
```

### 2.2 核心特点

1. **统一架构**: 三个LLM使用相同的实现模式
2. **Function Calling**: 利用LLM原生的工具调用能力
3. **上下文工程**: 完整的ES Schema文档作为系统提示词
4. **无Orchestrator**: 抛弃复杂的编排层，直接调用ES
5. **成本可控**: 用户可选择不同成本的模型

---

## 三、核心文件清单

### 后端文件
1. **agent/llm/claude_es_client.py** ✅ 已完成
   - Claude + ES客户端
   - Function Calling工具定义
   - 流式分析方法

2. **api/agent.py** 🔄 需修改
   - 添加model参数(默认deepseek)
   - model=claude时调用claude_es_client
   - 统一SSE输出格式

3. **config/settings.py** 🔄 需检查
   - 确保ANTHROPIC_API_KEY配置

### 前端文件(暂不修改)
- 先用现有前端测试
- 后续再优化UI(添加模型选择)

---

## 四、实施步骤

### Step 1: 安装依赖

```bash
cd backend
uv pip install anthropic  # Claude SDK
```

### Step 2: 配置API密钥

在 `.env` 或环境变量中添加:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxx
```

### Step 3: 修改API端点

修改 `backend/api/agent.py`,在chat函数添加model参数并实现分支逻辑:

```python
@router.get("/chat")
async def chat(
    question: str = Query(..., description="用户问题"),
    model: str = Query("deepseek", description="模型选择: deepseek, qwen, claude"),
    session_id: Optional[str] = Query(None),
    user_id: str = Query("anonymous"),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    db: AsyncSession = Depends(get_db)
):
    logger.info(f"[{user_id}] Agent查询: {question}, 模型: {model}")

    if model == "claude":
        # Claude分支
        from agent.llm.claude_es_client import ClaudeESClient

        async def generate():
            try:
                claude_client = ClaudeESClient()

                async for chunk in claude_client.analyze_stream(question):
                    # 统一SSE格式
                    yield f"data: {json.dumps({'stage': 'analyzing', 'content': chunk}, ensure_ascii=False)}\n\n"

                yield f"data: {json.dumps({'stage': 'completed'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.error(f"Claude分析失败: {e}", exc_info=True)
                yield f"data: {json.dumps({'stage': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    else:
        # DeepSeek/Qwen分支(现有逻辑)
        async def generate():
            try:
                async for message in orchestrator.process_query(question, user_id):
                    yield f"data: {message.model_dump_json(exclude_none=True)}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'stage': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

### Step 4: 测试Claude Agent

#### 测试脚本

```python
# test_claude_agent.py
import asyncio
from agent.llm.claude_es_client import ClaudeESClient

async def test():
    client = ClaudeESClient()

    question = "今天有多少条告警?按类型统计"

    print("=" * 60)
    print(f"问题: {question}")
    print("=" * 60)

    async for chunk in client.analyze_stream(question):
        print(chunk, end="", flush=True)

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(test())
```

运行测试:
```bash
cd backend
ANTHROPIC_API_KEY=sk-ant-xxx python test_claude_agent.py
```

#### API测试

```bash
curl "http://localhost:16532/api/agent/chat?model=claude&question=今天有多少条告警"
```

---

## 五、前端集成(后续优化)

### 添加模型选择器

```tsx
// AgentPage.tsx
const [selectedModel, setSelectedModel] = useState('deepseek');

<Radio.Group value={selectedModel} onChange={e => setSelectedModel(e.target.value)}>
  <Radio.Button value="deepseek">DeepSeek (经济)</Radio.Button>
  <Radio.Button value="qwen">通义千问 (均衡)</Radio.Button>
  <Radio.Button value="claude">Claude (高级)</Radio.Button>
</Radio.Group>

// 调用API时传递model参数
const url = `/api/agent/chat?model=${selectedModel}&question=${encodeURIComponent(question)}`;
```

### 优化Markdown渲染

```tsx
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';  // 支持表格等

<ReactMarkdown
  remarkPlugins={[remarkGfm]}
  components={{
    table: ({children}) => <Table bordered>{children}</Table>,
    // 自定义其他组件
  }}
>
  {analysisContent}
</ReactMarkdown>
```

---

## 六、MVP验证清单

### ✅ 功能验证
- [ ] Claude Agent能正常调用
- [ ] ES查询能正常执行
- [ ] 流式输出正常工作
- [ ] Markdown格式正确

### ✅ 效果验证
- [ ] 能回答"今天有多少告警"
- [ ] 能按类型统计告警
- [ ] 能对比本周vs上周
- [ ] 能识别异常和趋势

### ✅ 体验验证
- [ ] 响应速度可接受(<5秒开始输出)
- [ ] 流式输出流畅
- [ ] 错误提示友好
- [ ] 分析结果准确

---

## 七、常见问题

### Q1: ANTHROPIC_API_KEY未配置
**错误**: `ValueError: Claude API密钥未配置`

**解决**:
```bash
export ANTHROPIC_API_KEY=sk-ant-xxx
# 或在config/settings.py中添加
```

### Q2: elasticsearch库版本不兼容
**错误**: `AttributeError: 'AsyncElasticsearch' object has no attribute 'esql'`

**解决**:
```bash
uv pip install --upgrade elasticsearch>=8.11.0
```

### Q3: Claude响应慢
**原因**: Claude API在海外,网络延迟

**优化**:
- 使用HTTP代理
- 考虑使用Claude的中国区API
- 添加超时和重试机制

### Q4: ES查询失败
**检查**:
```python
# 测试ES连接
from elasticsearch import AsyncElasticsearch
es = AsyncElasticsearch(["http://localhost:9200"])
result = await es.search(index="video_alerts", body={"query": {"match_all": {}}, "size": 1})
print(result)
```

---

## 八、后续优化方向

### Phase 2: 增强功能
1. **多轮对话**: 支持上下文记忆
2. **数据可视化**: 自动生成图表配置
3. **定时报表**: 自动生成每日/每周报表
4. **告警预测**: 基于历史数据预测趋势

### Phase 3: 性能优化
1. **查询缓存**: 缓存常见查询结果
2. **并发控制**: 限制同时分析请求数
3. **流式优化**: 减少首字节时间
4. **成本控制**: 添加Token使用统计

### Phase 4: 企业功能
1. **权限控制**: 不同用户访问不同数据
2. **审计日志**: 记录所有分析请求
3. **导出功能**: 导出分析报告为PDF/Word
4. **API限流**: 防止滥用

---

## 九、成本估算

### Claude Sonnet 4 定价
- Input: $3 / 1M tokens
- Output: $15 / 1M tokens

### 单次分析成本估算
- 系统提示词: ~3000 tokens (一次性)
- 用户问题: ~50 tokens
- ES查询结果: ~2000 tokens (取决于数据量)
- Claude输出: ~1000 tokens

**单次成本**: 约 $0.02-0.05 (2-5分钱人民币)

### 月度成本估算 (按1000次查询)
- 月度成本: $20-50 (140-350元)
- 如切换到DeepSeek: ~10元/月

---

## 十、部署检查清单

### 环境配置
- [ ] ANTHROPIC_API_KEY 已配置
- [ ] Elasticsearch 正常运行 (http://localhost:9200)
- [ ] Python依赖已安装 (`anthropic`, `elasticsearch`)

### 代码检查
- [ ] claude_es_client.py 无语法错误
- [ ] agent.py 已添加model参数
- [ ] 日志配置正确

### 测试
- [ ] 单元测试通过
- [ ] API测试通过
- [ ] 端到端测试通过

### 监控
- [ ] 添加性能监控
- [ ] 添加错误告警
- [ ] 添加成本追踪

---

## 附录: 完整代码示例

详见:
- `backend/agent/llm/claude_es_client.py` - 已实现
- `backend/api/agent.py` - 需要的修改见Step 3
- `docs/Agent重构设计方案.md` - 完整架构文档

---

*MVP版本: v0.1*
*预计完成时间: 即刻可用*
*后续迭代: 持续优化*
