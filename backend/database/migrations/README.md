# 数据库迁移脚本

> 📦 所有数据库Schema变更和迁移脚本

---

## 📁 目录说明

此目录包含所有数据库迁移相关的SQL脚本，用于：
- 初始Schema创建
- 表结构升级
- 数据迁移
- 字段修复

**主Schema文件**: `../schema.sql` （完整的数据库结构定义）

---

## 📋 迁移脚本列表

### 🆕 初始Schema脚本

#### `ai_models_schema.sql`
- **用途**: AI模型配置表初始Schema
- **版本**: v1.0
- **创建时间**: 2024-09-05

#### `ai_models_schema_fixed.sql`
- **用途**: AI模型配置表修复版本
- **版本**: v1.1
- **修复内容**: 修正字段类型和约束

#### `ai_provider_configs_schema.sql`
- **用途**: AI服务提供商配置表Schema
- **版本**: v1.0
- **创建时间**: 2024-09-05

#### `agent_history_schema.sql`
- **用途**: AI Agent历史记录表Schema
- **版本**: v1.0
- **创建时间**: 2024-10-11

#### `video_streams_schema.sql`
- **用途**: 视频流配置表Schema（完整版）
- **版本**: v1.0

#### `video_streams_simple_schema.sql`
- **用途**: 视频流配置表简化版Schema
- **版本**: v1.0

#### `video_streams_minimal_schema.sql`
- **用途**: 视频流配置表最小版Schema
- **版本**: v1.0

---

### 🔄 迁移脚本

#### `migrate_tables.sql`
- **用途**: 主表结构迁移脚本
- **版本**: 通用
- **创建时间**: 2024-09-07

#### `migrate_v2.2.0.sql`
- **用途**: 版本2.2.0升级脚本
- **版本**: v2.2.0 → v2.3.0
- **创建时间**: 2024-09-07

#### `migrate_fix_confidence_field.sql`
- **用途**: 修复置信度字段类型
- **版本**: 字段修复
- **创建时间**: 2024-09-25

#### `migration_system_config.sql`
- **用途**: 系统配置表迁移
- **版本**: 配置升级
- **创建时间**: 2024-09-23

#### `migration_video_stream_algorithm_configs.sql`
- **用途**: 视频流算法配置表迁移
- **版本**: 算法配置升级
- **创建时间**: 2024-09-19

---

### 🎯 流分析任务相关

#### `create_stream_analysis_tasks.sql`
- **用途**: 创建流分析任务表
- **版本**: v1.0
- **创建时间**: 2024-09-26

#### `create_stream_tasks_table.sql`
- **用途**: 创建流任务调度表
- **版本**: v1.0
- **创建时间**: 2024-09-26

#### `add_output_format_config.sql`
- **用途**: 添加输出格式配置字段
- **版本**: 字段扩展
- **创建时间**: 2024-09-26

---

## 🔧 使用说明

### 初次安装

系统会自动使用 `../schema.sql` 初始化数据库，无需手动执行迁移脚本。

### 版本升级

1. **确认当前版本**
   ```sql
   SELECT version FROM schema_versions ORDER BY created_at DESC LIMIT 1;
   ```

2. **按顺序执行迁移脚本**
   ```bash
   psql -U postgres -d vision_db -f migrate_v2.2.0.sql
   ```

3. **验证迁移结果**
   ```sql
   -- 检查表结构
   \d table_name

   -- 检查数据完整性
   SELECT COUNT(*) FROM table_name;
   ```

### 手动迁移

如果需要手动执行某个迁移：

```bash
# 连接数据库
psql -U postgres -d vision_db

# 执行迁移脚本
\i migrations/migrate_xxx.sql

# 或使用命令行
psql -U postgres -d vision_db -f migrations/migrate_xxx.sql
```

---

## ⚠️ 注意事项

1. **备份优先**
   - 执行任何迁移前，先备份数据库
   ```bash
   pg_dump -U postgres vision_db > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **按顺序执行**
   - 迁移脚本有依赖关系，必须按时间顺序执行

3. **测试环境验证**
   - 生产环境执行前，先在测试环境验证

4. **版本记录**
   - 每次迁移后更新 `schema_versions` 表

5. **不可逆操作**
   - 删除字段、修改类型等操作不可逆，需特别谨慎

---

## 📊 版本历史

| 版本 | 日期 | 说明 | 迁移脚本 |
|------|------|------|---------|
| v2.4.0 | 2025-10-28 | 恢复asyncpg驱动 | - |
| v2.3.0 | 2024-10-19 | 流分析任务增强 | `create_stream_analysis_tasks.sql` |
| v2.2.0 | 2024-09-07 | 基础功能完善 | `migrate_v2.2.0.sql` |
| v2.1.0 | 2024-09-05 | AI模型集成 | `ai_models_schema.sql` |
| v2.0.0 | 2024-09-04 | 系统重构 | `schema.sql` |

---

## 🔗 相关文档

- [主Schema文件](../schema.sql)
- [数据库连接管理](../connection.py)
- [数据库工具函数](../db_utils.py)
- [流任务初始化](../init_stream_tasks.py)
- [文档中心](../../../docs/04-database/)

---

**维护者**: AI Watchdog Team
**最后更新**: 2025-10-28
