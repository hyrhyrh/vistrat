# 视频流复合检测完整方案（最终版）

**文档版本**: v3.0（最终版）
**创建时间**: 2025-10-28
**核心理念**: 基于AI算法模板能力定义 + 用户灵活选择

---

## 📋 目录

1. [架构理念](#架构理念)
2. [四层架构设计](#四层架构设计)
3. [完整数据流](#完整数据流)
4. [数据库设计](#数据库设计)
5. [实施方案](#实施方案)
6. [前端UI设计](#前端ui设计)
7. [后端逻辑设计](#后端逻辑设计)

---

## 架构理念

### 核心思想

**三层分离**：
1. **算法模板定义层**（AIModelPage）：定义AI算法的**能力**
2. **视频流配置层**（VideoStreamPage）：选择**使用哪些能力**
3. **分析执行层**（后端）：根据配置执行分析

### 关键洞察

> **用户纠正**：后续只有复合检测，配置1种检测类型 = 单检测，配置N种检测类型 = 复合检测

**简化设计**：
- ❌ 不需要 `composite_detection` boolean字段
- ❌ 不需要 `prompt_template_strategy` varchar字段
- ✅ 只需要 `detection_capabilities` jsonb字段

**判断逻辑**：
```python
if len(selected_detection_types) == 1:
    # 单检测（传统模式）
    pass
elif len(selected_detection_types) > 1:
    # 复合检测
    pass
```

---

## 四层架构设计

### Layer 1: 算法模板定义层（AIModelPage）

**职责**：配置AI算法的**检测能力**

**表**: `ai_model_configs`

**核心字段**（新增）:
```sql
detection_capabilities jsonb  -- 该算法支持的检测能力列表
```

**字段示例**:
```json
{
  "detection_capabilities": [
    {
      "type_code": "safety_helmet",
      "type_name": "安全帽检测",
      "severity": "high",
      "description": "检测人员是否佩戴安全帽"
    },
    {
      "type_code": "reflective_vest",
      "type_name": "反光衣检测",
      "severity": "medium",
      "description": "检测人员是否穿着反光衣"
    },
    {
      "type_code": "smoking",
      "type_name": "吸烟行为检测",
      "severity": "high",
      "description": "检测是否有人吸烟"
    }
  ]
}
```

**前端AIModelPage新增UI**：
- 勾选框列表：从`detection_type_templates`表读取所有预置检测类型
- 用户勾选该算法支持的检测类型
- 保存到`detection_capabilities`字段

---

### Layer 2: 视频流配置层（VideoStreamPage）

**职责**：为视频流选择AI算法，并选择具体启用哪些检测类型

**表**: `video_stream_algorithm_configs`

**核心字段**（新增）:
```sql
detection_type_codes jsonb  -- 用户选择要启用的检测类型列表
```

**配置流程**：
1. 用户选择AI算法（从`ai_model_configs`下拉框）
2. 系统读取该算法的`detection_capabilities`
3. 使用Transfer组件展示：
   - 左侧：该算法支持的所有检测类型（capabilities）
   - 右侧：用户选择要启用的检测类型
4. 保存到`video_stream_algorithm_configs.detection_type_codes`

**数据示例**：
```json
{
  "stream_id": "uuid-001",
  "template_id": "ai_model_uuid",  // 选择的AI算法
  "detection_type_codes": ["safety_helmet", "smoking"]  // 用户选择的类型
}
```

---

### Layer 3: 任务启动层（stream_analysis_tasks）

**职责**：记录分析任务

**表**: `stream_analysis_tasks`

**关联**：
- `stream_id` → `video_streams.id`
- `algorithm_config_id` → `video_stream_algorithm_configs.id`

**数据流**：
点击"启动分析" → 创建任务记录 → 后端开始执行

---

### Layer 4: 分析执行层（StreamFrameAnalyzer）

**职责**：根据配置执行AI分析

**执行逻辑**：
1. 读取任务 → 读取算法配置 → 读取AI模板
2. 获取`detection_type_codes`（用户选择的检测类型）
3. 判断：
   - `len(detection_type_codes) == 1` → 单检测（传统模式）
   - `len(detection_type_codes) > 1` → 复合检测

---

## 完整数据流

### 场景：配置"违规行为复合检测"算法

#### Step 1: AIModelPage配置算法模板

**操作**：
1. 算法名称：`违规行为复合检测`
2. AI模型：`lanyi/qwen2.5-vl-72b`
3. **勾选检测能力**（新功能）：
   - ☑️ 安全帽检测
   - ☑️ 反光衣检测
   - ☑️ 吸烟行为检测
   - ☑️ 玩手机检测
   - ☑️ 攀爬行为检测
4. 保存

**写入数据库**：
```sql
INSERT INTO ai_model_configs (
    id,
    name,
    provider,
    model_name,
    detection_capabilities
) VALUES (
    'uuid-ai-001',
    '违规行为复合检测',
    'lanyi',
    'lanyi-qwen2.5-vl-72b-instruct',
    '[
        {"type_code": "safety_helmet", "type_name": "安全帽检测", "severity": "high"},
        {"type_code": "reflective_vest", "type_name": "反光衣检测", "severity": "medium"},
        {"type_code": "smoking", "type_name": "吸烟行为检测", "severity": "high"},
        {"type_code": "phone_usage", "type_name": "玩手机检测", "severity": "medium"},
        {"type_code": "climbing", "type_name": "攀爬行为检测", "severity": "critical"}
    ]'::jsonb
);
```

---

#### Step 2: VideoStreamPage配置视频流

**操作**：
1. 选择视频流：`厂房监控01`
2. 点击"配置算法"
3. 下拉框选择：`违规行为复合检测`（从ai_model_configs）
4. **Transfer组件显示**：
   - 左侧（可选）：安全帽、反光衣、吸烟、玩手机、攀爬
   - 右侧（已选）：（初始为空）
5. **用户移动到右侧**：安全帽、吸烟、攀爬
6. 保存配置

**写入数据库**：
```sql
INSERT INTO video_stream_algorithm_configs (
    id,
    stream_id,
    template_id,
    detection_type_codes
) VALUES (
    'uuid-config-001',
    'uuid-stream-001',
    'uuid-ai-001',  -- 关联AI算法
    '["safety_helmet", "smoking", "climbing"]'::jsonb  -- 用户选择的3种类型
);
```

---

#### Step 3: 启动分析

**操作**：
1. 点击"启动分析"
2. 创建任务

**写入数据库**：
```sql
INSERT INTO stream_analysis_tasks (
    id,
    stream_id,
    algorithm_config_id,
    status
) VALUES (
    'uuid-task-001',
    'uuid-stream-001',
    'uuid-config-001',  -- 关联算法配置
    'running'
);
```

---

#### Step 4: 后端执行分析

**执行流程**：

```python
# 1. 读取任务
task = await db.fetchone("SELECT * FROM stream_analysis_tasks WHERE id = :id", {'id': task_id})

# 2. 读取算法配置
config = await db.fetchone("""
    SELECT template_id, detection_type_codes
    FROM video_stream_algorithm_configs
    WHERE id = :id
""", {'id': task.algorithm_config_id})

# 3. 读取AI模板
ai_template = await db.fetchone("""
    SELECT id, name, provider, model_name, detection_capabilities
    FROM ai_model_configs
    WHERE id = :id
""", {'id': config.template_id})

# 4. 获取用户选择的检测类型
detection_types = config.detection_type_codes  # ["safety_helmet", "smoking", "climbing"]

# 5. 判断模式
if len(detection_types) == 1:
    # 单检测模式
    result = await single_detection_service.analyze(
        model_id=ai_template.id,
        detection_type=detection_types[0]
    )
elif len(detection_types) > 1:
    # 复合检测模式
    result = await composite_detection_service.analyze_frame_composite(
        model_id=ai_template.id,
        detection_types=detection_types,  # 3种类型
        image_path=frame_path
    )
    # 一次AI调用 → 返回3个violations
```

**关键点**：
- ✅ 3种检测类型 → 1次AI调用
- ✅ 节省成本：67%（3次调用 → 1次调用）

---

## 数据库设计

### 1. ai_model_configs表（新增字段）

```sql
-- 添加检测能力列表字段
ALTER TABLE public.ai_model_configs
ADD COLUMN IF NOT EXISTS detection_capabilities jsonb DEFAULT '[]'::jsonb;

-- 添加注释
COMMENT ON COLUMN public.ai_model_configs.detection_capabilities
IS '支持的检测能力列表，JSON数组，每项包含type_code、type_name、severity等字段';
```

**字段说明**：
- `detection_capabilities`: 该算法支持的检测类型列表
- 数据结构：
```typescript
[
    {
        type_code: string,      // 检测类型编码（关联detection_type_templates）
        type_name: string,      // 检测类型名称
        severity: string,       // 严重程度：low/medium/high/critical
        description?: string    // 描述（可选）
    }
]
```

---

### 2. video_stream_algorithm_configs表（新增字段）

```sql
-- 添加用户选择的检测类型列表
ALTER TABLE public.video_stream_algorithm_configs
ADD COLUMN IF NOT EXISTS detection_type_codes jsonb DEFAULT '[]'::jsonb;

-- 添加注释
COMMENT ON COLUMN public.video_stream_algorithm_configs.detection_type_codes
IS '用户选择要启用的检测类型编码列表，JSON数组，如["safety_helmet", "smoking"]';
```

**字段说明**：
- `detection_type_codes`: 用户选择要启用的检测类型
- 数据结构：`["safety_helmet", "smoking", "climbing"]`

---

### 3. 索引优化

```sql
-- ai_model_configs表
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_detection_capabilities
ON ai_model_configs USING gin(detection_capabilities);

-- video_stream_algorithm_configs表
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_configs_detection_type_codes
ON video_stream_algorithm_configs USING gin(detection_type_codes);
```

---

## 实施方案

### Phase 1: 数据库迁移

#### Step 1.1: 执行SQL迁移

**文件**: `backend/database/migrations/add_detection_capabilities.sql`

```sql
-- ==========================================
-- 视频流复合检测数据库迁移脚本
-- 版本: v3.0
-- 日期: 2025-10-28
-- ==========================================

BEGIN;

-- 1. 添加ai_model_configs.detection_capabilities字段
ALTER TABLE public.ai_model_configs
ADD COLUMN IF NOT EXISTS detection_capabilities jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.ai_model_configs.detection_capabilities
IS '支持的检测能力列表，JSON数组，每项包含type_code、type_name、severity等字段';

-- 2. 添加video_stream_algorithm_configs.detection_type_codes字段
ALTER TABLE public.video_stream_algorithm_configs
ADD COLUMN IF NOT EXISTS detection_type_codes jsonb DEFAULT '[]'::jsonb;

COMMENT ON COLUMN public.video_stream_algorithm_configs.detection_type_codes
IS '用户选择要启用的检测类型编码列表，JSON数组，如["safety_helmet", "smoking"]';

-- 3. 创建GIN索引（用于高效查询JSONB字段）
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_detection_capabilities
ON ai_model_configs USING gin(detection_capabilities);

CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_configs_detection_type_codes
ON video_stream_algorithm_configs USING gin(detection_type_codes);

COMMIT;
```

#### Step 1.2: 更新ORM模型

**文件1**: `backend/models/ai_model.py`

```python
# 在AIModelConfigDB类中添加
class AIModelConfigDB(Base):
    __tablename__ = 'ai_model_configs'

    # ... 现有字段 ...

    # 新增：检测能力列表
    detection_capabilities = Column(
        JSON,
        default=[],
        comment='支持的检测能力列表JSON数组'
    )
```

**文件2**: `backend/models/video_stream_algorithm_config.py`

```python
# 在VideoStreamAlgorithmConfigDB类中添加
class VideoStreamAlgorithmConfigDB(Base):
    __tablename__ = "video_stream_algorithm_configs"

    # ... 现有字段 ...

    # 新增：用户选择的检测类型编码列表
    detection_type_codes = Column(
        JSON,
        default=[],
        comment='用户选择要启用的检测类型编码列表'
    )
```

#### Step 1.3: 清理Python缓存

```bash
find /root/project/vistrat/backend -type d -name __pycache__ -exec rm -rf {} +
find /root/project/vistrat/backend -name "*.pyc" -delete
```

---

### Phase 2: 前端AIModelPage改造

#### Step 2.1: 添加检测能力配置UI

**文件**: `frontend/src/pages/AIModelPage.tsx`

**新增功能**：
1. 从`detection_type_templates`表读取所有预置检测类型
2. 使用Checkbox.Group展示检测类型列表
3. 用户勾选该算法支持的检测类型
4. 保存到`ai_model_configs.detection_capabilities`

**UI示例**：
```tsx
<Form.Item
  label="检测能力"
  name="detection_capabilities"
  tooltip="选择该算法支持的检测类型"
>
  <Checkbox.Group>
    {detectionTypes.map(type => (
      <Checkbox
        key={type.type_code}
        value={type.type_code}
      >
        <Tag color={getSeverityColor(type.severity)}>
          {type.display_name}
        </Tag>
        <Text type="secondary">{type.description}</Text>
      </Checkbox>
    ))}
  </Checkbox.Group>
</Form.Item>
```

---

### Phase 3: 前端VideoStreamPage改造

#### Step 3.1: 添加Transfer组件配置检测类型

**文件**: `frontend/src/pages/VideoStreamPage.tsx`

**新增功能**：
1. 用户选择AI算法后，读取该算法的`detection_capabilities`
2. 使用Transfer组件让用户选择要启用的检测类型
3. 提交配置时包含`detection_type_codes`

**UI流程**：
```tsx
// 1. 选择AI算法
<Select
  placeholder="选择AI算法"
  onChange={handleAlgorithmChange}
>
  {algorithms.map(alg => (
    <Option key={alg.id} value={alg.id}>
      {alg.name}
    </Option>
  ))}
</Select>

// 2. 如果有detection_capabilities，显示Transfer组件
{selectedAlgorithm?.detection_capabilities?.length > 0 && (
  <Transfer
    dataSource={selectedAlgorithm.detection_capabilities.map(cap => ({
      key: cap.type_code,
      title: cap.type_name,
      description: cap.description,
      severity: cap.severity
    }))}
    targetKeys={selectedDetectionTypes}
    onChange={setSelectedDetectionTypes}
    render={item => (
      <div>
        <Tag color={getSeverityColor(item.severity)}>
          {item.title}
        </Tag>
        <Text type="secondary">{item.description}</Text>
      </div>
    )}
    titles={['可选检测类型', '已选检测类型']}
    listStyle={{ width: 300, height: 400 }}
  />
)}

// 3. 保存配置
const handleSaveConfig = async () => {
  await axios.post(`/api/video-streams/${streamId}/algorithms/configure`, {
    template_id: selectedAlgorithm.id,
    detection_type_codes: selectedDetectionTypes,  // ← 关键
    priority: 1,
    confidence_threshold: 0.7
  });
};
```

---

### Phase 4: 后端API改造

#### Step 4.1: 修改算法配置API

**文件**: `backend/api/video_streams.py`

**修改接口接收detection_type_codes**：

```python
class StreamAlgorithmConfigRequest(BaseModel):
    """视频流算法配置请求"""
    template_id: str = Field(..., description="AI算法模板ID")
    detection_type_codes: List[str] = Field(default=[], description="用户选择的检测类型编码列表")
    priority: int = Field(default=1, description="优先级")
    confidence_threshold: float = Field(default=0.7, description="置信度阈值")


@router.post("/{stream_id}/algorithms/configure")
async def configure_stream_algorithms(
    stream_id: str,
    config: StreamAlgorithmConfigRequest
):
    """配置视频流AI算法（支持复合检测）"""

    # 写入配置
    await db.execute(
        insert(VideoStreamAlgorithmConfigDB).values(
            stream_id=stream_id,
            template_id=config.template_id,
            detection_type_codes=config.detection_type_codes,  # ← 保存用户选择
            priority=config.priority,
            confidence_threshold=config.confidence_threshold,
            is_active=True
        )
    )

    return {
        "success": True,
        "message": f"配置成功，已选择{len(config.detection_type_codes)}种检测类型"
    }
```

---

### Phase 5: 后端分析逻辑改造

#### Step 5.1: 修改StreamAnalysisService读取逻辑

**文件**: `backend/services/stream_analysis_service.py`

**修改配置读取**：

```python
async def start_stream_analysis(self, stream_id: str) -> Dict[str, Any]:
    """启动视频流实时分析"""

    # 读取算法配置
    configs = await db.fetchall("""
        SELECT
            vsac.id as config_id,
            vsac.template_id,
            vsac.detection_type_codes,  -- ← 读取用户选择
            vsac.priority,
            amc.name as algorithm_name,
            amc.provider,
            amc.model_name,
            amc.user_prompt,
            amc.system_prompt,
            amc.detection_capabilities  -- ← 读取算法能力（用于验证）
        FROM video_stream_algorithm_configs vsac
        JOIN ai_model_configs amc ON vsac.template_id = amc.id
        WHERE vsac.stream_id = :stream_id
            AND vsac.is_active = true
        ORDER BY vsac.priority ASC
    """, {'stream_id': stream_id})

    # 构建algorithm_groups（每个配置一个组）
    algorithm_groups = []
    for config in configs:
        detection_types = config['detection_type_codes'] or []

        # 构建prompt（基础prompt）
        base_prompt = config.get('user_prompt') or config.get('system_prompt') or ''

        group = {
            'config_id': config['config_id'],
            'model_id': config['template_id'],
            'model_name': config['algorithm_name'],
            'provider': config['provider'],
            'model_name_full': config['model_name'],
            'detection_types': detection_types,  # ← 用户选择的检测类型
            'base_prompt': base_prompt,
            'priority': config['priority'],
            'is_composite': len(detection_types) > 1  # ← 判断是否复合检测
        }

        algorithm_groups.append(group)

    # 传给StreamFrameAnalyzer
    await stream_frame_analyzer.start_stream_analysis(
        rtsp_url=rtsp_url,
        stream_id=stream_id,
        algorithm_groups=algorithm_groups,  # ← 传算法组
        ...
    )
```

---

#### Step 5.2: 修改StreamFrameAnalyzer分析逻辑

**文件**: `backend/services/stream_frame_analyzer.py`

**修改方法签名**：

```python
async def start_stream_analysis(
    self,
    rtsp_url: str,
    stream_id: str,
    algorithm_groups: List[Dict[str, Any]],  # ← 接收算法组列表
    frame_callback: Callable = None,
    alert_callback: Callable = None
) -> str:
    """启动实时视频流分析"""

    self.current_session = {
        'session_id': session_id,
        'stream_id': stream_id,
        'rtsp_url': rtsp_url,
        'algorithm_groups': algorithm_groups,  # ← 保存算法组
        ...
    }

    # 启动分析任务
    asyncio.create_task(self._analyze_stream_continuously(
        rtsp_url, stream_id, algorithm_groups, ...
    ))
```

**修改帧分析逻辑**：

```python
async def _analyze_frames_batch(
    self,
    frame: np.ndarray,
    frame_index: int,
    timestamp: float,
    stream_id: str,
    algorithm_groups: List[Dict[str, Any]],  # ← 接收算法组
    temp_dir: Path,
    frame_callback: Callable,
    alert_callback: Callable
):
    """异步分析单帧（支持复合检测）"""

    # 保存帧图片并上传
    frame_path = ...
    minio_url = ...

    # ✅ 遍历每个算法组
    analysis_tasks = []
    for group in algorithm_groups:
        detection_types = group.get('detection_types', [])

        if group.get('is_composite'):
            # 复合检测模式：1次AI调用
            logger.info(
                f"帧{frame_index}使用复合检测: "
                f"模型={group['model_name']}, "
                f"检测类型={detection_types}"
            )
            task = asyncio.create_task(
                self._analyze_composite_detection(
                    frame_path, frame_index, timestamp, stream_id,
                    group, minio_url, alert_callback
                )
            )
        else:
            # 单检测模式：1次AI调用
            logger.info(
                f"帧{frame_index}使用单检测: "
                f"模型={group['model_name']}, "
                f"检测类型={detection_types[0] if detection_types else 'unknown'}"
            )
            task = asyncio.create_task(
                self._analyze_single_detection(
                    frame_path, frame_index, timestamp, stream_id,
                    group, minio_url, alert_callback
                )
            )

        analysis_tasks.append(task)

    # 并发执行所有算法组
    logger.debug(f"开始分析 {len(algorithm_groups)} 个算法配置: 帧{frame_index}")
    analysis_results = await asyncio.gather(*analysis_tasks, return_exceptions=True)

    # 处理结果...
```

**新增复合检测方法**：

```python
async def _analyze_composite_detection(
    self,
    frame_path: Path,
    frame_index: int,
    timestamp: float,
    stream_id: str,
    group: Dict[str, Any],
    minio_url: str,
    alert_callback: Callable
) -> List[Dict[str, Any]]:
    """
    复合检测分析

    Args:
        group: {
            'model_id': 'uuid',
            'detection_types': ['safety_helmet', 'smoking', 'climbing'],
            'base_prompt': '...',
            'is_composite': True
        }
    """
    try:
        from services.composite_detection_service import get_composite_detection_service

        composite_service = get_composite_detection_service()
        model_id = group['model_id']
        detection_types = group['detection_types']

        # 构建template_configs（CompositeDetectionService需要的格式）
        template_configs = []
        for type_code in detection_types:
            template_configs.append({
                'id': model_id,
                'detection_type_code': type_code,
                'name': f"{type_code}_detection",
                'category': 'composite',
                'priority': group['priority']
            })

        # 调用复合检测服务（一次AI调用）
        composite_result = await composite_service.analyze_frame_composite(
            image_path=str(frame_path),
            template_configs=template_configs,
            model_config_id=model_id
        )

        if not composite_result.get('success'):
            logger.error(f"复合检测失败: {composite_result.get('error')}")
            return []

        # 转换violations为结果列表
        results = []
        for violation in composite_result['violations']:
            result = {
                'frame_index': frame_index,
                'timestamp': timestamp,
                'stream_id': stream_id,
                'detection_type_code': violation.get('type_code'),
                'has_alert': violation.get('has_violation', False),
                'confidence': violation.get('confidence', 0.0),
                'ai_response': violation.get('conclusion', ''),
                'model_used': model_id,
                'image_url': minio_url,
                'composite_detection': True
            }
            results.append(result)

            # 处理告警
            if result['has_alert']:
                await self._handle_alert_callback_composite(result, alert_callback)

        logger.info(
            f"✅ 帧{frame_index}复合检测完成: "
            f"检测{len(detection_types)}种类型, "
            f"发现{sum(1 for r in results if r['has_alert'])}个告警"
        )

        return results

    except Exception as e:
        logger.error(f"帧{frame_index}复合检测异常: {e}")
        return []
```

---

## 前端UI设计

### AIModelPage新增UI（检测能力配置）

```tsx
<Card title="检测能力配置" bordered={false}>
  <Alert
    message="提示"
    description="选择该算法模板支持的检测类型，后续在配置视频流时可以从中选择"
    type="info"
    showIcon
    style={{ marginBottom: 16 }}
  />

  <Form.Item
    label="支持的检测类型"
    name="detection_capabilities"
    tooltip="勾选该算法能够检测的违规类型"
  >
    <Checkbox.Group style={{ width: '100%' }}>
      <Row gutter={[16, 16]}>
        {detectionTypes.map(type => (
          <Col span={8} key={type.type_code}>
            <Card
              size="small"
              hoverable
              style={{ cursor: 'pointer' }}
            >
              <Checkbox value={type.type_code}>
                <Space direction="vertical" size="small">
                  <Space>
                    <Tag color={getSeverityColor(type.severity)}>
                      {type.severity}
                    </Tag>
                    <Text strong>{type.display_name}</Text>
                  </Space>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {type.description}
                  </Text>
                </Space>
              </Checkbox>
            </Card>
          </Col>
        ))}
      </Row>
    </Checkbox.Group>
  </Form.Item>
</Card>
```

---

### VideoStreamPage新增UI（Transfer组件）

```tsx
<Modal
  title="配置AI算法"
  visible={configModalVisible}
  onOk={handleSaveConfig}
  onCancel={() => setConfigModalVisible(false)}
  width={800}
>
  {/* 1. 选择AI算法 */}
  <Form.Item label="选择AI算法">
    <Select
      placeholder="请选择AI算法模板"
      value={selectedAlgorithm?.id}
      onChange={handleAlgorithmSelect}
      style={{ width: '100%' }}
    >
      {algorithms.map(alg => (
        <Option key={alg.id} value={alg.id}>
          <Space>
            <RobotOutlined />
            <Text>{alg.name}</Text>
            <Tag>{alg.provider}</Tag>
          </Space>
        </Option>
      ))}
    </Select>
  </Form.Item>

  {/* 2. Transfer组件选择检测类型 */}
  {selectedAlgorithm?.detection_capabilities?.length > 0 && (
    <Form.Item
      label="选择检测类型"
      required
      tooltip="从左侧选择要启用的检测类型"
    >
      <Transfer
        dataSource={selectedAlgorithm.detection_capabilities.map(cap => ({
          key: cap.type_code,
          title: cap.type_name,
          description: cap.description,
          severity: cap.severity,
          disabled: false
        }))}
        targetKeys={selectedDetectionTypes}
        onChange={setSelectedDetectionTypes}
        render={item => (
          <Space direction="vertical" size="small" style={{ width: '100%' }}>
            <Space>
              <Tag color={getSeverityColor(item.severity)}>
                {item.severity}
              </Tag>
              <Text strong>{item.title}</Text>
            </Space>
            <Paragraph
              type="secondary"
              ellipsis={{ rows: 2 }}
              style={{ marginBottom: 0, fontSize: 12 }}
            >
              {item.description}
            </Paragraph>
          </Space>
        )}
        titles={['可选检测类型', '已选检测类型']}
        listStyle={{ width: 350, height: 400 }}
        showSearch
        filterOption={(inputValue, item) =>
          item.title.includes(inputValue) ||
          item.description.includes(inputValue)
        }
      />

      {/* 提示信息 */}
      {selectedDetectionTypes.length === 0 && (
        <Alert
          message="请至少选择一种检测类型"
          type="warning"
          showIcon
          style={{ marginTop: 8 }}
        />
      )}

      {selectedDetectionTypes.length === 1 && (
        <Alert
          message="单检测模式"
          description="已选择1种检测类型，将使用传统单检测模式"
          type="info"
          showIcon
          style={{ marginTop: 8 }}
        />
      )}

      {selectedDetectionTypes.length > 1 && (
        <Alert
          message="复合检测模式"
          description={`已选择${selectedDetectionTypes.length}种检测类型，将使用复合检测模式，一次AI调用检测多种违规类型，节省${Math.round((1 - 1/selectedDetectionTypes.length) * 100)}%成本`}
          type="success"
          showIcon
          style={{ marginTop: 8 }}
        />
      )}
    </Form.Item>
  )}
</Modal>
```

---

## 验收标准

### 功能验收

- [ ] AIModelPage可配置算法的detection_capabilities
- [ ] VideoStreamPage显示Transfer组件选择检测类型
- [ ] 配置保存到video_stream_algorithm_configs.detection_type_codes
- [ ] 后端正确读取detection_type_codes
- [ ] 单检测模式正常工作（选1种类型）
- [ ] 复合检测模式正常工作（选N种类型）
- [ ] 告警正确分发到ES

### 性能验收

- [ ] 复合检测相比传统模式减少AI调用次数
- [ ] 单帧分析时间减少 ≥ 50%
- [ ] 准确率下降 ≤ 5%

### 代码质量验收

- [ ] 数据库字段添加成功
- [ ] ORM模型更新正确
- [ ] 前端UI交互流畅
- [ ] 无Python缓存问题
- [ ] 无循环依赖

---

## 实施步骤检查清单

### 开始前
- [ ] 停止所有运行中的视频流分析任务
- [ ] 备份数据库：`pg_dump vision_db > backup.sql`
- [ ] Git打tag: `git tag stream-composite-v3-before`

### Phase 1: 数据库迁移
- [ ] 执行SQL迁移脚本
- [ ] 验证字段已添加
- [ ] 更新ORM模型（ai_model.py + video_stream_algorithm_config.py）
- [ ] 清理Python缓存

### Phase 2: 前端AIModelPage
- [ ] 添加detection_capabilities配置UI
- [ ] 从detection_type_templates读取检测类型列表
- [ ] 使用Checkbox.Group展示
- [ ] 测试保存功能

### Phase 3: 前端VideoStreamPage
- [ ] 添加Transfer组件
- [ ] 动态加载算法的detection_capabilities
- [ ] 实现检测类型选择
- [ ] 提交配置包含detection_type_codes
- [ ] 测试配置功能

### Phase 4: 后端API
- [ ] 修改配置API接收detection_type_codes
- [ ] 验证数据正确写入

### Phase 5: 后端分析逻辑
- [ ] 修改StreamAnalysisService读取逻辑
- [ ] 修改StreamFrameAnalyzer方法签名
- [ ] 实现_analyze_composite_detection方法
- [ ] 实现_analyze_single_detection方法
- [ ] 测试降级逻辑

### Phase 6: 端到端测试
- [ ] 配置算法模板（AIModelPage）
- [ ] 配置视频流（VideoStreamPage）
- [ ] 启动分析
- [ ] 验证AI调用次数减少
- [ ] 验证告警正确生成
- [ ] 检查ES记录

### 完成后
- [ ] Git提交: `git commit -m "feat: 视频流复合检测完整实现"`
- [ ] Git打tag: `git tag stream-composite-v3-complete`
- [ ] 更新文档
- [ ] 监控生产环境

---

**文档状态**: 最终版，等待审查
**核心改进**: 基于AI算法能力定义 + 用户灵活选择
**下一步**: 等待用户确认后开始实施
