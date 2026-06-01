# AI智能体分析助手 - MVP版本

> **告警分析AI智能体** Phase 1 MVP 已完成开发
>
> 版本: v1.0.0-mvp
> 完成时间: 2025-10-10

---

## ✅ 已完成功能

### 后端核心模块

| 模块 | 文件路径 | 功能描述 |
|-----|---------|---------|
| **核心类型** | `backend/agent/core/types.py` | 数据结构定义(Intent, ProcessedData, StreamMessage等) |
| **意图分析器** | `backend/agent/analyzers/intent_analyzer.py` | 规则引擎版本,支持中文时间表达式识别 |
| **时间解析** | `backend/agent/analyzers/time_parser.py` | 支持"今天"、"最近一周"等自然语言 |
| **ES查询构建** | `backend/agent/analyzers/query_builder.py` | 根据意图生成Elasticsearch DSL |
| **数据处理器** | `backend/agent/processors/normalizer.py` | 数据规范化、统计计算、图表建议 |
| **LLM客户端** | `backend/agent/llm/qwen_client.py` | Qwen大模型流式分析 |
| **报告生成器** | `backend/agent/reports/builder.py` | Markdown格式报告生成 |
| **Agent编排器** | `backend/agent/core/orchestrator.py` | 5步分析流程状态机 |
| **API端点** | `backend/api/agent.py` | SSE流式响应API |

### 前端组件

| 组件 | 文件路径 | 功能描述 |
|-----|---------|---------|
| **AgentButton** | `frontend/src/components/agent/AgentButton.tsx` | 触发按钮(渐变紫色,带动画) |
| **AgentDialog** | `frontend/src/components/agent/AgentDialog.tsx` | 对话框容器(60%屏幕,居中) |
| **类型定义** | `frontend/src/types/agent.ts` | TypeScript类型 |
| **样式文件** | `frontend/src/components/agent/*.css` | 响应式CSS样式 |

---

## 🎯 核心特性

### 1. 完整5步分析流程

```
用户提问 → 意图分析 → ES查询 → 数据处理 → LLM分析 → 报告生成
```

**示例流程**:
```
用户: "最近一周有多少告警?"
  ↓
Step 1: 意图分析
  ✓ 时间窗口: 最近7天
  ✓ 指标: count
  ↓
Step 2: ES查询
  ✓ 已查询到 42 条数据
  ↓
Step 3: 数据处理
  ✓ 平均置信度: 87.5%
  ↓
Step 4: LLM分析
  🤖 AI正在分析数据...
  (流式输出分析结果)
  ↓
Step 5: 报告生成
  ✓ 分析完成
```

### 2. SSE流式响应

- **实时进度推送**: 每个步骤实时反馈
- **流式AI分析**: 逐字输出,体验流畅
- **浏览器原生支持**: EventSource API
- **自动重连**: 网络断开后自动恢复

### 3. 规则引擎意图分析

支持的时间表达式:
- 今天/今日
- 昨天
- 最近N天/近N天
- 本周/上周
- 本月/上月
- 最近N小时

支持的实体识别:
- 告警类型: 未戴安全帽、吸烟、无关人员、违规操作
- 区域: 区域A、生产区、仓储区
- 严重程度: 高危、中危、低危

支持的指标:
- count: 数量统计
- trend: 趋势分析
- distribution: 分布分析

### 4. Markdown报告输出

```markdown
# 最近一周有多少告警?

## 📊 AI 分析

### 核心结论
根据数据分析,最近一周共记录42条告警...

### 关键发现
- 周一和周五告警数量较高
- 未戴安全帽占比35%
- 平均置信度87.5%

### 行动建议
1. 加强周一和周五的安全巡查
2. 重点培训安全帽佩戴规范
3. ...

---

## 📈 数据摘要
- **告警总数**: 42
- **平均置信度**: 87.5%

## 📉 可视化建议
- 📈 **告警趋势** (line)
- 🥧 **告警类型分布** (pie)
```

---

## 📡 API端点

### 1. 对话分析 (SSE流式)

```bash
POST /api/agent/chat?question=最近一周有多少告警
```

**SSE响应格式**:
```javascript
data: {"stage":"intent","message":"✓ 已识别: 时间:最近7天 | 指标:count"}

data: {"stage":"query","message":"✓ 已查询到 42 条数据"}

data: {"stage":"analyze","content":"根据数据分析,最近一周共记录42条告警..."}

data: {"stage":"completed","message":"✓ 分析完成","data":{...}}
```

### 2. 健康检查

```bash
GET /api/agent/health
```

**响应**:
```json
{
  "status": "healthy",
  "service": "agent",
  "version": "1.0.0"
}
```

---

## 🚀 快速开始

### 1. 启动依赖服务

```bash
docker-compose up -d --no-deps minio redis postgres elasticsearch
```

### 2. 启动后端

```bash
cd backend
source .venv/bin/activate
python main.py
```

后端将在 `http://localhost:16532` 启动

### 3. 启动前端

```bash
cd frontend
npm run dev
```

前端将在 `http://localhost:3000` 启动

### 4. 访问AI智能体

1. 打开浏览器访问 `http://localhost:3000/safety-dashboard-with-ai`
2. 点击左上角的 **"AI分析助手"** 按钮
3. 在弹出的对话框中输入问题,例如:
   - "今天有多少告警?"
   - "最近一周的告警趋势如何?"
   - "未戴安全帽的告警有多少?"

---

## 🎨 UI设计

### AgentButton (触发按钮)

- **位置**: 大屏左上角
- **样式**: 渐变紫色 (667eea → 764ba2)
- **效果**:
  - Hover悬浮上移
  - 图标脉冲动画
  - 阴影过渡

### AgentDialog (对话框)

- **尺寸**: 占屏幕60%
- **布局**: 居中显示
- **高度**: 70vh
- **功能**:
  - 消息列表(自动滚动)
  - Markdown渲染
  - 流式显示
  - 元数据展示(耗时、数据量)

---

## 📦 依赖说明

### 后端新增依赖

```toml
[project.dependencies]
pydantic-settings = "^2.11.0"
httpx = "^0.27.0"  # 已有
```

### 前端新增依赖

```json
{
  "dependencies": {
    "react-markdown": "^9.0.1"
  }
}
```

---

## 🔧 配置说明

### 环境变量

```bash
# Qwen API密钥 (必需)
QWEN_API_KEY=your-qwen-api-key

# Agent配置 (可选)
AGENT_QWEN_MODEL=qwen-max
AGENT_DEFAULT_QUERY_SIZE=100
AGENT_REPORT_MAX_TABLE_ROWS=20
```

---

## 📊 测试示例

### 测试用例1: 简单统计查询

**输入**: "今天有多少告警?"

**预期输出**:
```
🤔 正在理解您的问题...
✓ 已识别: 时间:今天 | 指标:count
🔍 正在查询数据...
✓ 已查询到 14 条数据
📊 正在处理数据...
✓ 数据处理完成
🤖 AI正在分析数据...

根据数据分析,今天共记录14条告警...
(流式输出完整分析)

✓ 分析完成
```

### 测试用例2: 趋势分析

**输入**: "最近一周的告警趋势如何?"

**预期输出**: 包含时间趋势图建议和逐日数据分析

### 测试用例3: 实体过滤

**输入**: "未戴安全帽的告警有多少?"

**预期输出**: 过滤特定类型的告警统计

---

## 🐛 已知问题

### Python文件编码问题 ✅ 已修复

- **问题**: `agent/exceptions.py` 和 `agent/config.py` 包含中文注释导致UTF-8解码错误
- **解决**: 已替换为英文注释

### 路由前缀问题 ✅ 已修复

- **问题**: `router = APIRouter(prefix="/api/agent")` 导致路径变成 `/api/api/agent/*`
- **解决**: 改为 `prefix="/agent"`

---

## 📈 后续Phase计划

### Phase 2: 报告增强 (1-2天)

- [ ] HTML单页报告生成
- [ ] 移动端样式适配
- [ ] 报告导出功能
- [ ] 历史记录查询

### Phase 3: 高级功能 (1-2天)

- [ ] 语音输入集成 (Web Speech API)
- [ ] 小模型意图分析 (Qwen-Turbo)
- [ ] 多轮对话上下文
- [ ] 用户认证集成

### Phase 4: 生产优化 (1天)

- [ ] 错误处理和重试
- [ ] 性能优化 (缓存、并发)
- [ ] 单元测试覆盖
- [ ] 监控和日志

---

## 📚 参考文档

- [完整架构设计](./AI_AGENT_ARCHITECTURE.md)
- [项目主文档](../CLAUDE.md)
- [Elasticsearch MCP Server (暂未使用)](https://github.com/elastic/mcp-server-elasticsearch)

---

## 👥 开发者

- **架构设计**: Claude Code
- **实现开发**: Claude Code + Human collaboration
- **测试验证**: In progress

---

**🎉 Phase 1 MVP开发完成!**

如有问题或建议,请查看 [GitHub Issues](../../issues)
