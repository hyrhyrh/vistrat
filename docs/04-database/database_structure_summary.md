# AI视频监控系统数据库结构总结

## 导出信息
- **导出时间**: 2025-09-07 14:51
- **数据库名**: vistrat  
- **表总数**: 10个
- **用户数据**: 1条管理员记录

## 表结构概览

### 1. 核心业务表

#### `video_files` - 视频文件表
- **主键**: UUID
- **核心字段**: 
  - `name` - 视频名称
  - `original_filename` - 原始文件名  
  - `file_path` - 文件存储路径
  - `status` - 视频状态枚举(PENDING/READY/ANALYZING等)
  - `tags` - 标签数组
- **统计字段**: `analysis_progress`, `total_alerts`

#### `users` - 用户表
- **主键**: UUID  
- **核心字段**:
  - `username` - 用户名(唯一)
  - `email` - 邮箱(唯一) 
  - `password_hash` - 密码哈希
  - `role` - 角色枚举(admin/user/viewer)
- **包含数据**: admin用户(用户名:admin, 邮箱:admin@example.com)

#### `video_streams` - 视频流表
- **主键**: UUID
- **核心字段**:
  - `name` - 流名称
  - `url` - 流地址
  - `stream_type` - 流类型枚举(RTSP/RTMP/HLS等)
  - `status` - 流状态枚举

### 2. 分析相关表

#### `video_analysis_results` - 视频分析结果表
- **主键**: UUID
- **关联**: `video_file_id`, `template_id`
- **核心字段**: `analysis_result`, `confidence_score`, `status`

#### `video_analysis_templates` - 视频分析模板表  
- **主键**: UUID
- **核心字段**: `name`, `prompt_content`, `category`

#### `stream_analysis_templates` - 流分析模板表
- **主键**: UUID
- **关联**: `stream_id`, `template_id`
- **核心字段**: `priority`, `enabled`, `confidence_threshold`

### 3. AI模型相关表

#### `ai_model_configs` - AI模型配置表
- **主键**: UUID
- **核心字段**: 
  - `name`, `description`
  - `provider` - 提供商枚举(qwen/moonshot/gpt等)
  - `model_type` - 模型类型枚举(vision/text/multimodal)
  - `system_prompt`, `user_prompt`
  - `temperature`, `top_p`, `max_tokens`

#### `ai_provider_configs` - AI提供商配置表
- **主键**: UUID
- **核心字段**: `provider_name`, `api_key`, `base_url`

#### `ai_test_results` - AI测试结果表
- **主键**: UUID
- **关联**: `config_id`
- **核心字段**: `is_success`, `response_time`, `error_message`

### 4. 系统表

#### `schema_migrations` - 数据库迁移表
- **主键**: version (VARCHAR)
- **核心字段**: `applied_at`, `description`

## 枚举类型定义

### 视频相关枚举
- `video_status_enum`: PENDING, UPLOADING, READY, ANALYZING, COMPLETED, ERROR, DELETED
- `analysis_status_enum`: not_started, queued, processing, completed, failed, cancelled

### 流相关枚举  
- `stream_status_enum`: OFFLINE, ONLINE, CONNECTING, ERROR, MAINTENANCE
- `stream_type_enum`: RTSP, RTMP, HLS, WEBRTC, HTTP_FLV, LOCAL_CAMERA
- `stream_analysis_status_enum`: NOT_STARTED, RUNNING, PAUSED, STOPPED, ERROR

### AI相关枚举
- `ai_provider_enum`: qwen, moonshot, gpt, claude, gemini, baidu
- `ai_model_type_enum`: vision, text, multimodal
- `algorithm_status_enum`: draft, testing, active, deprecated

### 用户相关枚举
- `user_role_enum`: admin, user, viewer

## 索引设计

### 性能优化索引
- **时间查询**: 各表的`created_at`, `updated_at`使用DESC索引
- **状态筛选**: `status`字段建立B-Tree索引
- **标签搜索**: `tags`字段使用GIN索引(PostgreSQL数组)
- **全文搜索**: `name`, `username`, `email`等建立索引

### 唯一约束索引
- `users.username`, `users.email` - 唯一索引
- `ai_provider_configs.provider_name` - 唯一索引
- `stream_analysis_templates(stream_id, template_id)` - 复合唯一索引

## 数据一致性

### 主键设计
- **统一UUID**: 所有表使用UUID作为主键，支持分布式部署
- **自动生成**: 使用PostgreSQL的`gen_random_uuid()`函数

### 时间戳管理
- **创建时间**: `created_at`默认`CURRENT_TIMESTAMP`
- **更新时间**: `updated_at`通过触发器自动维护
- **时区支持**: 使用`TIMESTAMPTZ`类型

### 软删除机制
- `video_files.status`包含DELETED状态实现软删除
- 其他表通过`is_active`字段控制状态

## 部署说明

1. **先决条件**: PostgreSQL 12+支持
2. **执行顺序**: 
   - 创建枚举类型 
   - 创建表结构
   - 添加主键约束
   - 创建索引
   - 插入初始用户数据
3. **初始账户**: admin/密码需重置
4. **扩展需求**: 支持UUID、数组、JSONB等PostgreSQL特性

## 文件位置
- **完整SQL脚本**: `/root/project/vistrat/database_export.sql`
- **结构总结**: `/root/project/vistrat/database_structure_summary.md`