# 数据库设计文档

## 概述

AI监控系统采用PostgreSQL作为主数据库，支持离线视频文件管理和实时视频流管理两个核心功能模块。

## 表结构设计

### 1. 视频文件管理表 (video_files)

用于存储上传的离线视频文件基本信息和分析状态。

#### 字段说明

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 视频唯一ID |
| name | VARCHAR(255) | NOT NULL | 视频名称 |
| original_filename | VARCHAR(500) | NOT NULL | 原始文件名 |
| file_path | VARCHAR(1000) | NOT NULL | 文件存储路径(MinIO路径) |
| thumbnail_path | VARCHAR(1000) | NULL | 缩略图路径 |
| file_size | INTEGER | NULL | 文件大小(字节) |
| duration | REAL | NULL | 视频时长(秒) |
| fps | REAL | NULL | 帧率 |
| width | INTEGER | NULL | 视频宽度 |
| height | INTEGER | NULL | 视频高度 |
| format | VARCHAR(50) | NULL | 视频格式(mp4/avi/mov等) |
| status | video_status_enum | NOT NULL DEFAULT 'pending' | 视频状态 |
| tags | TEXT[] | DEFAULT '{}' | 视频标签数组 |
| description | TEXT | NULL | 视频描述 |
| analysis_progress | INTEGER | DEFAULT 0 | 分析进度百分比 |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| analyzed_at | TIMESTAMP WITH TIME ZONE | NULL | 分析完成时间 |
| total_alerts | INTEGER | DEFAULT 0 | 总告警数量 |
| last_alert_at | TIMESTAMP WITH TIME ZONE | NULL | 最后告警时间 |

#### 枚举类型

**video_status_enum**: 'pending', 'uploading', 'ready', 'analyzing', 'completed', 'error', 'deleted'

#### 索引

- `idx_video_files_status` ON status
- `idx_video_files_created_at` ON created_at DESC
- `idx_video_files_name` ON name

### 2. 视频流管理表 (video_streams)

用于存储实时视频流的配置、状态和分析信息。

#### 字段说明

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 流唯一ID |
| name | VARCHAR(255) | NOT NULL | 摄像头名称 |
| description | TEXT | NULL | 摄像头描述 |
| stream_url | VARCHAR(1000) | NOT NULL | 视频流地址(RTSP/RTMP等) |
| stream_type | stream_type_enum | NOT NULL DEFAULT 'rtsp' | 流类型 |
| username | VARCHAR(100) | NULL | 认证用户名 |
| password | VARCHAR(100) | NULL | 认证密码 |
| status | stream_status_enum | NOT NULL DEFAULT 'offline' | 流状态 |
| last_online_at | TIMESTAMP WITH TIME ZONE | NULL | 最后在线时间 |
| connection_error | TEXT | NULL | 连接错误信息 |
| fps | REAL | NULL | 实际帧率 |
| width | INTEGER | NULL | 视频宽度 |
| height | INTEGER | NULL | 视频高度 |
| codec | VARCHAR(50) | NULL | 编码格式 |
| thumbnail_path | VARCHAR(1000) | NULL | 缩略图路径(MinIO) |
| latest_frame_path | VARCHAR(1000) | NULL | 最新帧截图路径 |
| analysis_status | stream_analysis_status_enum | NOT NULL DEFAULT 'not_started' | 分析状态 |
| analysis_interval | INTEGER | DEFAULT 10 | 分析间隔(秒) |
| enable_recording | BOOLEAN | DEFAULT false | 是否启用录制 |
| total_analysis_count | INTEGER | DEFAULT 0 | 总分析次数 |
| total_alerts | INTEGER | DEFAULT 0 | 总告警数量 |
| last_analysis_at | TIMESTAMP WITH TIME ZONE | NULL | 最后分析时间 |
| last_alert_at | TIMESTAMP WITH TIME ZONE | NULL | 最后告警时间 |
| location | VARCHAR(255) | NULL | 摄像头位置 |
| group_name | VARCHAR(100) | NULL | 分组名称 |
| tags | TEXT[] | DEFAULT '{}' | 标签数组 |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

#### 枚举类型

**stream_status_enum**: 'offline', 'online', 'connecting', 'error', 'maintenance'

**stream_type_enum**: 'rtsp', 'rtmp', 'hls', 'webrtc', 'http_flv', 'local_camera'

**stream_analysis_status_enum**: 'not_started', 'running', 'paused', 'stopped', 'error'

#### 约束

- `analysis_interval` 范围: 1-300秒

#### 索引

- `idx_video_streams_status` ON status
- `idx_video_streams_group` ON group_name
- `idx_video_streams_location` ON location
- `idx_video_streams_created_at` ON created_at DESC
- `idx_video_streams_name` ON name

### 3. 视频文件分析模板关联表 (video_analysis_templates)

管理视频文件与AI提示词模板的多对多关系。

#### 字段说明

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 关联唯一ID |
| video_id | UUID | NOT NULL | 视频ID |
| template_id | VARCHAR(100) | NOT NULL | 提示词模板ID |
| template_name | VARCHAR(255) | NOT NULL | 模板名称 |
| priority | INTEGER | DEFAULT 1 | 分析优先级(1-5) |
| enabled | BOOLEAN | DEFAULT true | 是否启用 |
| analysis_status | analysis_status_enum | DEFAULT 'not_started' | 分析状态 |
| progress | INTEGER | DEFAULT 0 | 分析进度 |
| alerts_count | INTEGER | DEFAULT 0 | 告警数量 |
| confidence_avg | REAL | NULL | 平均置信度 |
| analysis_duration | REAL | NULL | 分析耗时(秒) |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| started_at | TIMESTAMP WITH TIME ZONE | NULL | 开始分析时间 |
| completed_at | TIMESTAMP WITH TIME ZONE | NULL | 完成分析时间 |
| error_message | TEXT | NULL | 错误信息 |

### 4. 视频流分析模板关联表 (stream_analysis_templates)

管理视频流与AI提示词模板的多对多关系。

#### 字段说明

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | UUID | PRIMARY KEY | 关联唯一ID |
| stream_id | UUID | NOT NULL, FK | 视频流ID |
| template_id | VARCHAR(100) | NOT NULL | 提示词模板ID |
| template_name | VARCHAR(255) | NOT NULL | 模板名称 |
| priority | INTEGER | DEFAULT 1 | 分析优先级(1-5) |
| enabled | BOOLEAN | DEFAULT true | 是否启用 |
| confidence_threshold | REAL | DEFAULT 0.7 | 置信度阈值 |
| analysis_status | stream_analysis_status_enum | DEFAULT 'not_started' | 分析状态 |
| alerts_count | INTEGER | DEFAULT 0 | 告警数量 |
| detection_count | INTEGER | DEFAULT 0 | 检测次数 |
| confidence_avg | REAL | NULL | 平均置信度 |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| last_detection_at | TIMESTAMP WITH TIME ZONE | NULL | 最后检测时间 |
| error_message | TEXT | NULL | 错误信息 |

#### 约束

- `UNIQUE(stream_id, template_id)` - 每个流的每个模板只能关联一次
- `priority` 范围: 1-5
- `confidence_threshold` 范围: 0.1-1.0

#### 外键

- `stream_id` REFERENCES video_streams(id) ON DELETE CASCADE

## 业务逻辑设计

### 视频文件管理流程

1. **文件上传**: 用户上传视频 → 状态设为'uploading' → 存储到MinIO → 提取元数据 → 状态改为'ready'
2. **分析配置**: 为视频关联AI算法模板 → 创建video_analysis_templates记录
3. **分析执行**: 启动分析 → 状态改为'analyzing' → 执行AI分析 → 更新进度 → 完成后状态改为'completed'

### 视频流管理流程

1. **流添加**: 用户配置流地址 → 创建video_streams记录 → 状态默认'offline'
2. **连接测试**: 测试流连接 → 更新状态为'online'或'error'
3. **分析配置**: 为流关联AI算法模板 → 创建stream_analysis_templates记录
4. **实时分析**: 启动分析 → 状态改为'running' → 持续分析视频流 → 实时更新统计信息

### 状态转换图

#### 视频文件状态转换
```
pending → uploading → ready → analyzing → completed
   ↓         ↓         ↓         ↓         ↓
  error    error    error    error    error
```

#### 视频流状态转换
```
offline ⇄ connecting ⇄ online
   ↓         ↓         ↓
  error    error    error
```

#### 分析状态转换
```
not_started → running → completed/stopped
      ↓         ↓         ↓
    error    error    error
```

## 索引优化策略

### 查询优化索引

1. **频繁查询字段**: status, created_at, name
2. **分组查询**: group_name, location
3. **关联查询**: stream_id, template_id

### 性能考虑

1. **分页查询**: 使用LIMIT/OFFSET，created_at DESC排序
2. **模糊搜索**: 使用ILIKE操作符，考虑全文搜索扩展
3. **数组查询**: tags字段使用GIN索引(未来扩展)
4. **统计查询**: 预计算统计信息，避免实时聚合

## 存储设计

### MinIO对象存储布局

```
buckets/
├── multi-videos/           # 视频文件存储
│   ├── {video_id}.mp4
│   └── ...
├── multi-thumbnails/       # 缩略图存储
│   ├── {video_id}.jpg
│   └── ...
├── multi-images/          # 分析截图
│   ├── alerts/
│   └── frames/
└── multi-annotations/     # 标注图像
    └── ...
```

### Redis缓存策略

使用前缀 `multi_watchdog:` 区分业务数据：

- `multi_watchdog:stream:{stream_id}:status` - 流状态缓存
- `multi_watchdog:video:{video_id}:analysis` - 分析进度缓存
- `multi_watchdog:stats:summary` - 统计信息缓存(TTL: 5分钟)

## API设计

### RESTful接口规范

#### 视频文件管理
- `GET /video-files/` - 搜索视频列表
- `GET /video-files/{id}` - 获取视频详情
- `POST /video-files/` - 创建视频记录
- `PUT /video-files/{id}` - 更新视频信息
- `DELETE /video-files/{id}` - 删除视频(软删除)

#### 视频流管理
- `GET /video-streams/` - 搜索视频流列表
- `GET /video-streams/{id}` - 获取流详情
- `POST /video-streams/` - 创建视频流
- `PUT /video-streams/{id}` - 更新流信息
- `DELETE /video-streams/{id}` - 删除流
- `POST /video-streams/{id}/analysis/configure` - 配置分析算法
- `POST /video-streams/{id}/analysis/start` - 启动分析
- `POST /video-streams/{id}/analysis/stop` - 停止分析

### WebSocket接口

- `ws://host:port/alerts` - 实时告警推送
- `ws://host:port/video_feed` - 实时视频流

## 安全考虑

### 数据保护
1. **敏感信息**: 视频流认证密码不在API响应中返回
2. **访问控制**: MinIO预签名URL，临时访问权限
3. **输入验证**: 所有API参数进行Pydantic验证

### 性能优化
1. **连接池**: 异步数据库连接池管理
2. **缓存策略**: Redis缓存热点数据
3. **分页查询**: 避免大量数据一次性加载
4. **索引优化**: 针对查询模式优化索引

## 扩展计划

### 未来功能扩展

1. **流媒体转换**: 集成FFmpeg进行格式转换
2. **边缘计算**: 支持边缘设备视频分析
3. **集群部署**: 多节点视频分析集群
4. **历史数据**: 长期分析结果存储和检索