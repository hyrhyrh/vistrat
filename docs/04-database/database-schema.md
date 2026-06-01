# 数据库设计文档

## 概述

AI视频监控系统使用PostgreSQL作为主数据库，存储视频元数据、分析配置和结果统计。系统采用异步ORM (SQLAlchemy + asyncpg) 实现高性能数据访问。

## 数据库连接配置

### 环境变量
```bash
DB_HOST=localhost           # 数据库主机
DB_PORT=5432               # 数据库端口  
DB_NAME=ai_watchdog        # 数据库名称
DB_USER=postgres           # 用户名
DB_PASSWORD=password       # 密码
DB_POOL_SIZE=5            # 连接池大小
DB_MAX_OVERFLOW=10        # 最大溢出连接数
```

### 连接URL格式
- **异步连接**: `postgresql+asyncpg://user:pass@host:port/dbname`
- **同步连接**: `postgresql://user:pass@host:port/dbname`

## 数据表设计

### 1. video_files - 视频文件信息表

**表用途**: 存储上传的离线视频基本信息和分析状态

| 字段名 | 类型 | 约束 | 注释 |
|--------|------|------|------|
| `id` | UUID | PRIMARY KEY | 视频唯一ID |
| `name` | VARCHAR(255) | NOT NULL | 视频名称 |
| `original_filename` | VARCHAR(500) | NOT NULL | 原始文件名 |
| `file_path` | VARCHAR(1000) | NOT NULL | 文件存储路径(MinIO路径) |
| `thumbnail_path` | VARCHAR(1000) | | 缩略图路径 |
| `file_size` | BIGINT | | 文件大小(字节) |
| `duration` | FLOAT | | 视频时长(秒) |
| `fps` | FLOAT | | 帧率 |
| `width` | INTEGER | | 视频宽度 |
| `height` | INTEGER | | 视频高度 |
| `format` | VARCHAR(50) | | 视频格式(mp4/avi/mov等) |
| `status` | video_status_enum | DEFAULT 'pending' | 视频状态 |
| `tags` | TEXT[] | DEFAULT '{}' | 视频标签数组 |
| `description` | TEXT | | 视频描述 |
| `analysis_progress` | INTEGER | DEFAULT 0, CHECK (0-100) | 分析进度百分比 |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| `analyzed_at` | TIMESTAMP WITH TIME ZONE | | 分析完成时间 |
| `total_alerts` | INTEGER | DEFAULT 0 | 总告警数量 |
| `last_alert_at` | TIMESTAMP WITH TIME ZONE | | 最后告警时间 |

**索引设计**:
- `idx_video_files_status` - 按状态查询
- `idx_video_files_created_at` - 按创建时间排序
- `idx_video_files_tags` - GIN索引支持标签搜索
- `idx_video_files_name` - 按名称搜索

**状态枚举 (video_status_enum)**:
- `pending` - 待处理
- `uploading` - 上传中
- `ready` - 就绪
- `analyzing` - 分析中  
- `completed` - 已完成
- `error` - 错误
- `deleted` - 已删除

### 2. video_analysis_templates - 视频分析模板关联表

**表用途**: 管理视频与AI提示词模板的多对多关系

| 字段名 | 类型 | 约束 | 注释 |
|--------|------|------|------|
| `id` | UUID | PRIMARY KEY | 关联ID |
| `video_id` | UUID | NOT NULL, FK | 视频ID |
| `template_id` | VARCHAR(100) | NOT NULL | 提示词模板ID |
| `template_name` | VARCHAR(255) | NOT NULL | 模板名称 |
| `priority` | INTEGER | DEFAULT 1 | 分析优先级(1-5) |
| `enabled` | BOOLEAN | DEFAULT TRUE | 是否启用 |
| `analysis_status` | analysis_status_enum | DEFAULT 'not_started' | 分析状态 |
| `progress` | INTEGER | DEFAULT 0, CHECK (0-100) | 分析进度 |
| `alerts_count` | INTEGER | DEFAULT 0 | 告警数量 |
| `confidence_avg` | FLOAT | | 平均置信度 |
| `analysis_duration` | FLOAT | | 分析耗时(秒) |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| `updated_at` | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| `started_at` | TIMESTAMP WITH TIME ZONE | | 开始分析时间 |
| `completed_at` | TIMESTAMP WITH TIME ZONE | | 完成分析时间 |
| `error_message` | TEXT | | 错误信息 |

**唯一约束**: `UNIQUE(video_id, template_id)` - 每个视频对每个模板只能有一条分析记录

**分析状态枚举 (analysis_status_enum)**:
- `not_started` - 未开始
- `queued` - 排队中
- `processing` - 处理中
- `completed` - 已完成
- `failed` - 失败
- `stopped` - 已停止

### 3. video_analysis_results - 视频分析结果表

**表用途**: 存储每帧的详细分析结果和告警信息

| 字段名 | 类型 | 约束 | 注释 |
|--------|------|------|------|
| `id` | UUID | PRIMARY KEY | 结果ID |
| `video_id` | UUID | NOT NULL, FK | 视频ID |
| `template_id` | VARCHAR(100) | NOT NULL | 使用的模板ID |
| `frame_index` | INTEGER | NOT NULL | 帧索引 |
| `timestamp_sec` | FLOAT | NOT NULL | 视频时间戳(秒) |
| `detection_result` | JSONB | NOT NULL | 检测结果JSON |
| `confidence` | FLOAT | | 置信度 |
| `is_alert` | BOOLEAN | DEFAULT FALSE | 是否为告警 |
| `alert_level` | VARCHAR(20) | | 告警级别(low/medium/high/critical) |
| `bounding_boxes` | JSONB | | 边界框信息 |
| `detected_objects` | TEXT[] | DEFAULT '{}' | 检测到的对象类型 |
| `created_at` | TIMESTAMP WITH TIME ZONE | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引设计**:
- `idx_video_analysis_results_video_id` - 按视频查询
- `idx_video_analysis_results_timestamp` - 按时间戳查询
- `idx_video_analysis_results_alert` - 按告警状态查询

## 数据库触发器

### 自动更新时间戳
```sql
-- 更新updated_at字段的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 应用到相关表
CREATE TRIGGER update_video_files_updated_at
    BEFORE UPDATE ON video_files
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## 数据访问层

### ORM配置
- **框架**: SQLAlchemy 2.0 (异步)
- **驱动**: asyncpg (PostgreSQL异步驱动)
- **连接池**: 5个基础连接，最大溢出10个
- **会话管理**: 自动提交/回滚，异常处理

### 主要服务类
- `VideoFileService` - 视频文件CRUD操作
- `DatabaseManager` - 数据库连接和会话管理
- `AIResponseParser` - AI结果解析和存储

## API接口映射

### 视频管理接口
- `GET /api/video-files` - 搜索视频列表
- `GET /api/video-files/{id}` - 获取视频详情
- `POST /api/video-files` - 创建视频记录
- `PUT /api/video-files/{id}` - 更新视频信息
- `DELETE /api/video-files/{id}` - 删除视频(软删除)

### 分析配置接口  
- `POST /api/video-files/{id}/analysis/configure` - 配置分析模板
- `GET /api/video-files/{id}/analysis/templates` - 获取分析配置
- `POST /api/video-files/{id}/analysis/start` - 启动分析任务

### 统计接口
- `GET /api/video-files/statistics/summary` - 获取统计信息

## 查询优化建议

### 常用查询模式
1. **按名称搜索**: 使用 `ILIKE` 模糊匹配
2. **标签过滤**: 使用 `@>` 数组包含操作符
3. **状态筛选**: 直接等值查询，有索引支持
4. **分页查询**: 使用 `LIMIT/OFFSET` + `ORDER BY created_at DESC`

### 性能监控
- 监控慢查询日志 (>100ms)
- 定期分析表统计信息
- 关注连接池使用情况
- 监控磁盘空间使用

## 数据迁移

### 初始化数据库
```bash
# 执行schema.sql创建表结构
psql -h localhost -U postgres -d ai_watchdog -f backend/database/schema.sql
```

### 从文件系统迁移
现有的JSON文件数据可通过以下步骤迁移:
1. 读取 `templates.json` 和 `data/` 目录下的现有数据
2. 转换为对应的Pydantic模型
3. 批量插入到PostgreSQL表中
4. 验证数据完整性

## 备份策略

### 定期备份
- **全量备份**: 每日凌晨执行 `pg_dump`
- **增量备份**: 启用WAL归档
- **文件备份**: MinIO存储的视频文件同步备份

### 恢复测试
- 月度恢复演练
- 验证备份文件完整性
- 测试故障切换流程