# 视频流复合检测深度架构分析

> **文档版本**: v4.0 深度分析版
> **创建时间**: 2025-10-28
> **分析范围**: 前端配置层 → 数据库层 → 后端分析层 → 完整调用链
> **目标**: 为视频流分析集成复合检测功能，实现"N帧×1次AI调用"

---

## 一、核心问题陈述

### 1.1 当前状态
- ✅ **视频文件分析**: 已完成复合检测改造（Phase 1-4）
- ❌ **视频流分析**: 仍使用传统"N帧×N次AI调用"模式
- ❌ **前端UI**: 缺少检测类型选择界面

### 1.2 目标状态
- ✅ 用户在AIModelPage配置算法时，定义该算法支持的检测能力（detection_capabilities）
- ✅ 用户在VideoStreamPage配置视频流时，从算法能力中选择需要的检测类型（detection_type_codes）
- ✅ 后端分析时，根据用户选择的检测类型组装复合提示词，一次AI调用完成多类型检测
- ✅ 支持同一视频流配置多个复合检测组合（不同算法+不同检测类型组合）

---

## 二、现有架构深度剖析

### 2.1 Layer 1: AIModelPage 算法模板配置层

#### 文件位置
- **前端**: `/root/project/vistrat/frontend/src/pages/AIModelPage.tsx` (968行)
- **后端模型**: `/root/project/vistrat/backend/models/ai_model.py` (260行)
- **数据库表**: `ai_model_configs`

#### 当前字段结构
```typescript
// 前端表单字段 (AIModelPage.tsx 第533-735行)
interface ConfigForm {
  name: string              // 算法名称
  description: string       // 算法描述
  provider: string          // AI供应商
  model_name: string        // 模型名称
  system_prompt: string     // 系统提示词
  user_prompt: string       // 用户提示词
  temperature: number
  top_p: number
  max_tokens: number
  confidence_threshold: number
  tags: string[]
}
```

```python
# 后端数据库模型 (ai_model.py 第44-104行)
class AIModelConfigDB(Base):
    __tablename__ = 'ai_model_configs'

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    provider = Column(String(100), nullable=False)
    model_name = Column(String(200), nullable=False)
    model_type = Column(ENUM('vision', 'text', 'multimodal'))
    system_prompt = Column(Text)
    user_prompt = Column(Text)
    temperature = Column(Float, default=0.7)
    top_p = Column(Float, default=0.9)
    max_tokens = Column(Integer, default=1000)
    confidence_threshold = Column(Float, default=0.7)
    tags = Column(ARRAY(String), default=[])
    status = Column(ENUM('draft', 'testing', 'active', 'deprecated'))
    # ❌ 缺失: detection_capabilities
```

#### 关键API端点
- `POST /api/ai-models/configs/` - 创建算法配置 (AIModelPage.tsx 第467行)
- `PUT /api/ai-models/configs/${id}` - 更新算法配置 (AIModelPage.tsx 第456行)

#### ❌ 缺失的功能
1. **前端UI**: 没有选择detection_capabilities的Checkbox.Group
2. **数据库字段**: ai_model_configs表缺少`detection_capabilities`字段（JSONB类型）
3. **表单处理**: 没有处理detection_capabilities的数据提交逻辑

---

### 2.2 Layer 2: VideoStreamPage 视频流配置层

#### 文件位置
- **前端页面**: `/root/project/vistrat/frontend/src/pages/VideoStreamPage.tsx` (1250行)
- **配置组件**: `/root/project/vistrat/frontend/src/components/stream/SimpleStreamAlgorithmModal.tsx` (1625行)
- **后端模型**: `/root/project/vistrat/backend/models/video_stream_algorithm_config.py` (124行)
- **数据库表**: `video_stream_algorithm_configs`, `stream_analysis_tasks`

#### SimpleStreamAlgorithmModal 当前流程

```typescript
// 配置步骤 (SimpleStreamAlgorithmModal.tsx 第109行)
type CurrentStep = 'algorithm' | 'roi' | 'schedule' | 'ready' | 'analyzing'

// Step 1: 选择算法 (第832-929行)
// - 从 ai_model_configs 加载已激活算法
// - 用户多选算法 (Select mode="multiple")
// - ❌ 没有选择detection_type_codes的环节

// Step 2: 配置ROI区域 (第931-1187行)
// - 为每个算法独立配置ROI
// - 支持矩形和多边形

// Step 3: 配置时间 (第1189-1388行)
// - 为每个算法配置运行时间段
// - 支持多个时间段

// Step 4: 保存配置 (第185-307行)
// - 为每个算法创建独立的 stream_analysis_task
// - 写入数据库: stream_analysis_tasks表
```

#### 数据流追踪

```typescript
// 用户选择算法后的数据结构 (第390-393行)
selectedAlgorithms: string[]  // ['algo-uuid-1', 'algo-uuid-2']

// 保存时的数据结构 (第203-232行)
const taskData = {
  stream_id: string,
  algorithm_config_id: string,  // 单个算法ID
  task_name: string,
  time_config: {...},
  roi_config: {...},
  priority: 1,
  confidence_threshold: 0.7,
  analysis_interval: 10
  // ❌ 缺失: detection_type_codes字段
}

// API调用 (第237行)
POST /api/stream-tasks/
```

#### 后端数据库模型

```python
# video_stream_algorithm_config.py 第16-35行
class VideoStreamAlgorithmConfigDB(Base):
    __tablename__ = "video_stream_algorithm_configs"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    stream_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("video_streams.id"))
    template_id = Column(String(255), nullable=False)  # 对应ai_model_configs.id
    template_name = Column(String(255))
    priority = Column(Integer, default=1)
    confidence_threshold = Column(Float, default=0.7)
    is_active = Column(Boolean, default=True)
    # ❌ 缺失: detection_type_codes
```

#### ❌ 缺失的功能
1. **前端UI**: 选择算法后，没有从算法的detection_capabilities中选择具体要使用的检测类型
2. **Transfer组件**: 用户无法看到"可用检测类型"和"已选检测类型"的双栏选择界面
3. **数据库字段**: video_stream_algorithm_configs表缺少`detection_type_codes`字段（JSONB类型）
4. **API传递**: POST /api/stream-tasks/ 没有传递detection_type_codes

---

### 2.3 Layer 3: 后端分析启动层

#### 文件位置
- **服务**: `/root/project/vistrat/backend/services/stream_analysis_service.py`
- **关键方法**: `start_stream_analysis()` (第78-277行)

#### 当前读取逻辑

```python
# stream_analysis_service.py 第131-195行
async def start_stream_analysis(self, stream_id: str):
    # 1. 获取流配置
    stream_config = await VideoStreamService.get_stream_configuration(stream_id)

    # 2. 获取算法配置列表
    analysis_config = await VideoStreamService.get_analysis_templates(stream_id)
    # 返回: {'templates': [{'template_id': 'uuid-1', 'priority': 1}, ...]}

    # 3. 从ai_model_configs表读取算法详情
    for template_config in analysis_config['templates']:
        template_id = template_config['template_id']

        query = text("""
        SELECT
            id, name, description, provider, model_name,
            system_prompt, user_prompt, temperature, top_p, max_tokens,
            confidence_threshold, tags
        FROM ai_model_configs
        WHERE id = :template_id
        """)
        # ❌ 没有读取 detection_capabilities
        # ❌ 没有读取 video_stream_algorithm_configs.detection_type_codes

        template = {
            'id': str(row[0]),
            'name': row[1],
            'provider': row[3],
            'model_name': row[4],
            'system_prompt': row[5],
            'user_prompt': row[6],
            # ...
            'prompt_content': row[6] if row[6] else row[5]
        }
        templates.append(template)

    # 4. 启动分析器
    await stream_frame_analyzer.analyze_stream_task(...)
```

#### ❌ 缺失的逻辑
1. 没有读取`ai_model_configs.detection_capabilities`
2. 没有从`video_stream_algorithm_configs`读取用户选择的`detection_type_codes`
3. 没有按(template_id, priority)分组形成复合检测组合
4. 直接传递了单个模板列表，而不是复合组合列表

---

### 2.4 Layer 4: 后端分析执行层

#### 文件位置
- **服务**: `/root/project/vistrat/backend/services/stream_frame_analyzer.py`
- **关键方法**: `_process_frame()` (第342-367行)

#### 当前执行逻辑

```python
# stream_frame_analyzer.py 第342-367行
async def _process_frame(self, ...):
    # 创建并发分析任务列表
    analysis_tasks = []
    for template in templates:  # ❌ 遍历单个模板，不是复合组合
        task = asyncio.create_task(
            self._analyze_single_template(
                frame_path, frame_index, timestamp,
                stream_id, template, minio_url, alert_callback
            )
        )
        analysis_tasks.append(task)

    # 并发执行所有算法分析
    logger.debug(f"开始并发分析 {len(templates)} 个算法: 帧{frame_index}")
    analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)
```

#### ❌ 问题所在
- **N个模板 = N次AI调用**: 每个模板独立调用AI
- **没有复合检测逻辑**: 没有检查是否应该组合多个检测类型
- **没有调用composite_detection_service**: 现有的复合检测服务未被使用

---

## 三、完整数据流追踪

### 3.1 视频文件分析的复合检测流程（已实现，作为参考）

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. 前端VideoManagementPage配置                                   │
│    - 用户选择detection_type_codes: ['safety_helmet', 'smoking'] │
│    - 保存到 video_analysis_templates.detection_type_code       │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. 后端VideoAnalysisService启动                                  │
│    - 读取 video_analysis_templates                              │
│    - 按detection_type_code分组                                  │
│    - 检测到复合模式（多个type_code）                             │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. CompositeDetectionService处理                                 │
│    - PromptTemplateEngine.build_composite_prompt()              │
│    - 从detection_type_templates读取模板                         │
│    - 组装复合提示词                                              │
│    - UnifiedAIClient.analyze_image() → 1次AI调用                │
│    - CompositeResponseParser.parse_composite_response()         │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 视频流分析的理想流程（需要实现）

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. AIModelPage: 配置算法能力                                     │
│    ┌─────────────────────────────────────────────────────────┐ │
│    │ 用户创建算法: "违规行为复合检测"                           │ │
│    │ - 选择provider: qwen                                      │ │
│    │ - 选择model: qwen-vl-max                                  │ │
│    │ - ✅ 新增: 勾选detection_capabilities:                    │ │
│    │   ☑ safety_helmet (未佩戴安全帽)                          │ │
│    │   ☑ smoking (吸烟)                                        │ │
│    │   ☑ using_phone (使用手机)                                │ │
│    │   ☑ climbing (攀爬)                                       │ │
│    │   ☑ intrusion (越界)                                      │ │
│    │ - 配置提示词、参数等                                       │ │
│    └─────────────────────────────────────────────────────────┘ │
│    保存到: ai_model_configs.detection_capabilities              │
│    格式: ["safety_helmet", "smoking", "using_phone", ...]       │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. VideoStreamPage: 配置视频流分析                               │
│    ┌─────────────────────────────────────────────────────────┐ │
│    │ Step 1: 选择算法                                           │ │
│    │   - 用户从算法列表选择: "违规行为复合检测"                 │ │
│    │                                                           │ │
│    │ ✅ Step 1.5: 选择检测类型 (新增)                          │ │
│    │   Transfer组件:                                           │ │
│    │   ┌──────────────────┬──────────────────┐               │ │
│    │   │ 可用检测类型      │ 已选检测类型      │               │ │
│    │   ├──────────────────┼──────────────────┤               │ │
│    │   │ safety_helmet  →│→ smoking          │               │ │
│    │   │ climbing       →│→ using_phone      │               │ │
│    │   │ intrusion       │                   │               │ │
│    │   └──────────────────┴──────────────────┘               │ │
│    │   说明: 从该算法的detection_capabilities中选择           │ │
│    │                                                           │ │
│    │ Step 2: 配置ROI区域 (保持不变)                            │ │
│    │ Step 3: 配置时间 (保持不变)                                │ │
│    │ Step 4: 保存配置                                          │ │
│    └─────────────────────────────────────────────────────────┘ │
│    保存到: video_stream_algorithm_configs.detection_type_codes  │
│    格式: ["smoking", "using_phone"]                             │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. 后端StreamAnalysisService启动分析                             │
│    ┌─────────────────────────────────────────────────────────┐ │
│    │ async def start_stream_analysis(stream_id):               │ │
│    │   # 读取配置                                              │ │
│    │   configs = query("""                                    │ │
│    │     SELECT                                                │ │
│    │       vsac.id, vsac.template_id, vsac.priority,          │ │
│    │       vsac.detection_type_codes,  ← 新增                 │ │
│    │       amc.name, amc.provider, amc.model_name,            │ │
│    │       amc.system_prompt, amc.user_prompt,                │ │
│    │       amc.detection_capabilities  ← 新增                 │ │
│    │     FROM video_stream_algorithm_configs vsac            │ │
│    │     JOIN ai_model_configs amc ON vsac.template_id = amc.id│ │
│    │     WHERE vsac.stream_id = :stream_id                    │ │
│    │       AND vsac.is_active = true                          │ │
│    │   """)                                                    │ │
│    │                                                           │ │
│    │   # 按(template_id, priority)分组 ← 关键改造              │ │
│    │   algorithm_groups = {}                                   │ │
│    │   for config in configs:                                 │ │
│    │     group_key = (config.template_id, config.priority)    │ │
│    │     if group_key not in algorithm_groups:                │ │
│    │       algorithm_groups[group_key] = {                    │ │
│    │         'template_id': config.template_id,               │ │
│    │         'template_name': config.name,                    │ │
│    │         'priority': config.priority,                     │ │
│    │         'provider': config.provider,                     │ │
│    │         'model_name': config.model_name,                 │ │
│    │         'detection_type_codes': [],                      │ │
│    │         'detection_capabilities': config.capabilities    │ │
│    │       }                                                   │ │
│    │     algorithm_groups[group_key]['detection_type_codes']\ │ │
│    │       .extend(config.detection_type_codes)               │ │
│    │                                                           │ │
│    │   # 传递给分析器                                          │ │
│    │   await stream_frame_analyzer.analyze_stream_task(       │ │
│    │     algorithm_groups=list(algorithm_groups.values())     │ │
│    │   )                                                       │ │
│    └─────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. StreamFrameAnalyzer执行分析                                   │
│    ┌─────────────────────────────────────────────────────────┐ │
│    │ async def _process_frame(..., algorithm_groups):          │ │
│    │   analysis_tasks = []                                     │ │
│    │   for group in algorithm_groups:  ← 遍历组合而非单模板    │ │
│    │     detection_types = group['detection_type_codes']      │ │
│    │                                                           │ │
│    │     if len(detection_types) == 1:                        │ │
│    │       # 单检测模式 - 传统调用                              │ │
│    │       task = self._analyze_single_template(...)          │ │
│    │     elif len(detection_types) > 1:                       │ │
│    │       # 复合检测模式 - 一次AI调用 ← 关键                  │ │
│    │       task = self._analyze_composite_detection(          │ │
│    │         frame_path=frame_path,                           │ │
│    │         detection_types=detection_types,                 │ │
│    │         model_config_id=group['template_id']             │ │
│    │       )                                                   │ │
│    │     analysis_tasks.append(task)                          │ │
│    │                                                           │ │
│    │   # 并发执行所有组合（复合检测+单检测）                   │ │
│    │   results = await asyncio.gather(*analysis_tasks)        │ │
│    └─────────────────────────────────────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. CompositeDetectionService处理（复用现有服务）                │
│    - build_composite_prompt(detection_types)                    │
│    - analyze_image_with_config(model_config_id)                │
│    - parse_composite_response() → 多个违规结果                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、detection_type_templates 表分析

### 4.1 表结构

```sql
CREATE TABLE detection_type_templates (
  type_code VARCHAR(50) PRIMARY KEY,     -- 类型编码 (如 'safety_helmet')
  type_name VARCHAR(100) NOT NULL,       -- 类型名称 (如 '未佩戴安全帽')
  category VARCHAR(50),                  -- 类别 (如 'safety', 'behavior')
  description TEXT,                      -- 详细描述
  severity VARCHAR(20),                  -- 严重程度 (low/medium/high/critical)
  template_content TEXT,                 -- 检测提示词模板
  output_schema JSONB,                   -- 输出格式定义
  enabled BOOLEAN DEFAULT TRUE,          -- 是否启用
  sort_order INTEGER DEFAULT 0,          -- 排序
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

### 4.2 数据示例

```json
[
  {
    "type_code": "safety_helmet",
    "type_name": "未佩戴安全帽",
    "category": "safety",
    "severity": "high",
    "template_content": "检测画面中是否存在未佩戴安全帽的人员。需要识别人员的头部区域，判断是否佩戴了安全帽。",
    "enabled": true
  },
  {
    "type_code": "smoking",
    "type_name": "吸烟行为",
    "category": "behavior",
    "severity": "medium",
    "template_content": "检测画面中是否有人在吸烟。注意识别人员手部持烟、嘴部吸烟等动作。",
    "enabled": true
  }
]
```

### 4.3 在系统中的使用

- **PromptTemplateEngine**: 从该表读取模板组装复合提示词
- **CompositeDetectionService**: 调用该引擎构建提示词
- **前端**: 通过`GET /api/video-files/detection-types/templates`获取列表用于UI展示

---

## 五、架构关键设计决策

### 5.1 为什么需要两层配置？

```
┌────────────────────────────────────────────────────────────┐
│ ai_model_configs.detection_capabilities                    │
│ 定义: 这个算法**能够**检测哪些类型                          │
│ 设置者: 算法配置人员（专业人员）                             │
│ 示例: ["safety_helmet", "smoking", "using_phone", ...]     │
└────────────────────────────────────────────────────────────┘
                            ▼
┌────────────────────────────────────────────────────────────┐
│ video_stream_algorithm_configs.detection_type_codes        │
│ 定义: 用户**想要**检测哪些类型（从上述能力中选择）          │
│ 设置者: 视频流配置人员（业务人员）                           │
│ 示例: ["smoking", "using_phone"]  ← 用户只选了2个           │
└────────────────────────────────────────────────────────────┘
```

**设计原理**:
- **能力定义与使用分离**: 算法能力由专业人员定义，使用由业务人员按需选择
- **灵活性**: 同一算法可在不同场景使用不同的检测类型组合
- **权限控制**: 算法能力配置需要更高权限，流配置权限可下放

### 5.2 为什么要按(template_id, priority)分组？

**场景**: 同一视频流可能配置多个复合检测组合

```python
# 示例配置
configs = [
  # 组合1: 算法A检测[helmet, vest]
  {'template_id': 'algo-A', 'priority': 1, 'detection_type_codes': ['safety_helmet', 'safety_vest']},

  # 组合2: 算法B检测[smoking, phone]
  {'template_id': 'algo-B', 'priority': 1, 'detection_type_codes': ['smoking', 'using_phone']},

  # 组合3: 算法A检测[climbing]
  {'template_id': 'algo-A', 'priority': 2, 'detection_type_codes': ['climbing']},
]

# 分组后
algorithm_groups = {
  ('algo-A', 1): {
    'detection_type_codes': ['safety_helmet', 'safety_vest'],  # 1次AI调用
  },
  ('algo-B', 1): {
    'detection_type_codes': ['smoking', 'using_phone'],        # 1次AI调用
  },
  ('algo-A', 2): {
    'detection_type_codes': ['climbing'],                      # 1次AI调用
  }
}
# 总计: 3次AI调用（而不是5次）
```

**分组规则**:
- **相同算法 + 相同优先级** → 合并为一个复合检测组
- **不同算法** → 独立的AI调用
- **不同优先级** → 独立的AI调用（用于控制执行顺序）

---

## 六、关键技术要点

### 6.1 JSONB字段的处理

```python
# PostgreSQL定义
ALTER TABLE ai_model_configs
ADD COLUMN detection_capabilities jsonb DEFAULT '[]'::jsonb;

# Python ORM (SQLAlchemy)
from sqlalchemy.dialects.postgresql import JSONB
detection_capabilities = Column(JSONB, default=[], comment='支持的检测能力列表')

# 查询示例
from sqlalchemy import text
query = text("""
SELECT
  id,
  name,
  detection_capabilities,  -- 直接读取JSONB
  provider
FROM ai_model_configs
WHERE id = :template_id
""")
result = await db.execute(query, {'template_id': template_id})
row = result.fetchone()

capabilities = row[2]  # 已自动反序列化为Python list
# capabilities = ['safety_helmet', 'smoking', ...]
```

```typescript
// TypeScript前端
interface AIAlgorithm {
  id: string
  name: string
  detection_capabilities: string[]  // 自动解析JSON
}

// API响应
{
  "id": "uuid",
  "name": "算法名",
  "detection_capabilities": ["safety_helmet", "smoking"]  // JSON数组
}
```

### 6.2 Transfer组件的数据流

```typescript
// Ant Design Transfer组件
import { Transfer } from 'antd'

// 数据源: 从算法的detection_capabilities构建
const dataSource = algorithm.detection_capabilities.map(code => ({
  key: code,
  title: getDetectionTypeName(code),  // 从detection_type_templates获取显示名
  description: getDetectionTypeDesc(code)
}))

// 已选择的key列表
const [selectedKeys, setSelectedKeys] = useState<string[]>([])

<Transfer
  dataSource={dataSource}
  titles={['可用检测类型', '已选检测类型']}
  targetKeys={selectedKeys}
  onChange={(newTargetKeys) => setSelectedKeys(newTargetKeys)}
  render={item => item.title}
/>

// 提交时
const taskData = {
  ...otherFields,
  detection_type_codes: selectedKeys  // ['smoking', 'using_phone']
}
```

### 6.3 复合检测服务的调用

```python
# stream_frame_analyzer.py
from services.composite_detection_service import CompositeDetectionService

composite_service = CompositeDetectionService()

async def _analyze_composite_detection(
    self,
    frame_path: str,
    detection_types: List[str],
    model_config_id: str
) -> Dict:
    """
    复合检测分析一帧

    Args:
        frame_path: 帧图片路径
        detection_types: 检测类型列表 ['safety_helmet', 'smoking']
        model_config_id: AI模型配置ID

    Returns:
        {
            'success': True,
            'violations': [...],  # 多个检测结果
            'model_used': 'qwen-vl-max',
            'response_time': 3.2
        }
    """
    # 构建template_configs（从detection_type_templates查询）
    template_configs = []
    for type_code in detection_types:
        template = await get_detection_type_template(type_code)
        template_configs.append({
            'detection_type_code': type_code,
            'type_name': template['type_name'],
            'category': template['category'],
            'severity': template['severity']
        })

    # 调用复合检测服务
    result = await composite_service.analyze_frame_composite(
        image_path=frame_path,
        template_configs=template_configs,
        model_config_id=model_config_id
    )

    return result
```

---

## 七、测试验证要点

### 7.1 数据库层测试

```sql
-- 测试1: 添加detection_capabilities字段
ALTER TABLE ai_model_configs
ADD COLUMN IF NOT EXISTS detection_capabilities jsonb DEFAULT '[]'::jsonb;

-- 测试2: 更新现有算法配置
UPDATE ai_model_configs
SET detection_capabilities = '["safety_helmet", "smoking", "using_phone"]'::jsonb
WHERE name = '违规行为复合检测';

-- 测试3: 查询验证
SELECT id, name, detection_capabilities
FROM ai_model_configs
WHERE detection_capabilities IS NOT NULL;

-- 测试4: 添加detection_type_codes字段
ALTER TABLE video_stream_algorithm_configs
ADD COLUMN IF NOT EXISTS detection_type_codes jsonb DEFAULT '[]'::jsonb;

-- 测试5: 创建索引
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_detection_capabilities
ON ai_model_configs USING gin(detection_capabilities);
```

### 7.2 前端UI测试

```typescript
// 测试AIModelPage
// 1. 加载detection_type_templates列表
// 2. 渲染Checkbox.Group
// 3. 用户勾选detection_capabilities
// 4. 提交表单，验证数据格式
// 5. 后端返回成功，验证数据库写入

// 测试SimpleStreamAlgorithmModal
// 1. 选择算法后显示Transfer组件
// 2. 从算法的detection_capabilities构建dataSource
// 3. 用户移动detection types到右侧
// 4. 保存配置，验证detection_type_codes传递
// 5. 后端验证video_stream_algorithm_configs写入
```

### 7.3 后端分析测试

```python
# 测试场景1: 单检测类型
detection_type_codes = ["safety_helmet"]
# 预期: 使用单检测模式，传统AI调用

# 测试场景2: 复合检测（2种类型）
detection_type_codes = ["safety_helmet", "smoking"]
# 预期: 使用复合检测模式，1次AI调用返回2种违规结果

# 测试场景3: 多组复合检测
algorithm_groups = [
  {'detection_type_codes': ['helmet', 'vest']},     # 组1: 1次调用
  {'detection_type_codes': ['smoking', 'phone']},  # 组2: 1次调用
]
# 预期: 2次AI调用，每次返回多个违规结果

# 测试场景4: 性能对比
# 传统模式: 5种类型 = 5次AI调用 = ~20秒
# 复合模式: 5种类型 = 1次AI调用 = ~4秒
```

---

## 八、实施风险与注意事项

### 8.1 向后兼容性

**问题**: 现有视频流配置没有detection_type_codes

**解决方案**:
```python
# 后端读取逻辑
detection_type_codes = config.get('detection_type_codes')

if not detection_type_codes or len(detection_type_codes) == 0:
    # 向后兼容: 使用算法的所有能力
    detection_type_codes = config.get('detection_capabilities', [])

if len(detection_type_codes) == 0:
    # 继续兼容: 降级为传统模式
    await self._analyze_single_template(...)
else:
    # 新模式: 复合检测
    await self._analyze_composite_detection(...)
```

### 8.2 数据迁移策略

```python
# 迁移脚本: 为现有算法填充detection_capabilities
UPDATE ai_model_configs
SET detection_capabilities = (
  SELECT jsonb_agg(DISTINCT detection_type_code)
  FROM video_analysis_templates
  WHERE video_analysis_templates.id = ai_model_configs.id
)
WHERE detection_capabilities IS NULL OR detection_capabilities = '[]'::jsonb;
```

### 8.3 UI/UX注意事项

1. **Transfer组件提示**: "从左侧选择您需要的检测类型，移动到右侧"
2. **空状态提示**: 如果算法的detection_capabilities为空，显示"该算法尚未配置检测能力"
3. **验证逻辑**: 至少选择1个检测类型才能保存
4. **性能提示**: "使用复合检测可大幅提升分析速度"

---

## 九、总结

### 9.1 核心改造点

| 层级 | 文件 | 改造内容 | 工作量 |
|-----|------|---------|--------|
| **数据库** | PostgreSQL | 添加2个JSONB字段 | 5min |
| **后端模型** | ai_model.py | 添加detection_capabilities字段 | 10min |
| **后端模型** | video_stream_algorithm_config.py | 添加detection_type_codes字段 | 10min |
| **前端UI** | AIModelPage.tsx | 添加Checkbox.Group选择capabilities | 30min |
| **前端UI** | SimpleStreamAlgorithmModal.tsx | 添加Transfer组件选择type_codes | 60min |
| **后端服务** | stream_analysis_service.py | 读取字段+分组逻辑 | 45min |
| **后端分析** | stream_frame_analyzer.py | 复合检测判断+调用 | 30min |
| **测试** | 端到端测试 | 全流程验证 | 60min |

**总计**: ~4小时

### 9.2 实施步骤建议

1. ✅ Phase 1: 数据库迁移（添加字段、索引）
2. ✅ Phase 2: 后端模型层（更新ORM模型）
3. ✅ Phase 3: 前端AIModelPage（配置检测能力）
4. ✅ Phase 4: 前端SimpleStreamAlgorithmModal（选择检测类型）
5. ✅ Phase 5: 后端分析服务（读取配置+分组）
6. ✅ Phase 6: 后端分析执行（复合检测调用）
7. ✅ Phase 7: 端到端测试（完整流程验证）

---

**文档结束**
