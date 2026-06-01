# 数据库导出说明

## 导出时间
2025-10-09 09:23

## 数据库信息
- **数据库名称**: vision_db
- **数据库版本**: PostgreSQL 16.10
- **字符编码**: UTF8
- **数据库用户**: vision

## 导出文件说明

### 1. schema_structure.sql (38KB)
**表结构脚本** - 包含完整的数据库表结构定义

此文件包含：
- 所有自定义枚举类型（ENUM）
- 所有表的CREATE TABLE语句
- 所有索引定义
- 所有外键约束
- 所有序列（SEQUENCE）定义

**用途**：
- 用于在新环境中创建完整的数据库结构
- 数据库结构版本控制
- 数据库迁移和升级

**使用方法**：
```bash
# 在目标数据库执行
psql -U vision -d vision_db -f schema_structure.sql
```

### 2. schema_data.sql (2.6MB)
**表数据脚本** - 包含所有表的数据INSERT语句

此文件包含：
- 所有表的完整数据（使用列名插入格式）
- 保留了所有UUID、时间戳等字段
- 使用 --column-inserts 格式，便于阅读和部分导入

**用途**：
- 数据备份和恢复
- 数据迁移到新环境
- 开发/测试环境数据初始化

**使用方法**：
```bash
# 先导入表结构，再导入数据
psql -U vision -d vision_db -f schema_structure.sql
psql -U vision -d vision_db -f schema_data.sql
```

## 数据库表清单（共15张表）

### 核心业务表
1. **users** - 用户表
2. **video_files** - 视频文件表
3. **video_streams** - 视频流表
4. **stream_analysis_tasks** - 流分析任务表

### AI模型配置表
5. **ai_model_configs** - AI模型配置表
6. **ai_provider_configs** - AI服务提供商配置表
7. **ai_test_results** - AI模型测试结果表

### 分析相关表
8. **video_analysis_results** - 视频分析结果表
9. **ai_analysis_logs** - AI分析日志表
10. **video_analysis_templates** - 视频分析模板表
11. **stream_analysis_templates** - 流分析模板表

### 算法配置表
12. **video_stream_algorithm_configs** - 视频流算法配置表
13. **video_stream_algorithm_config_history** - 算法配置历史表

### 系统表
14. **system_configs** - 系统配置表
15. **schema_migrations** - 数据库迁移记录表

## 数据库枚举类型

系统定义了多个枚举类型，用于规范化数据：

- **ai_model_type_enum**: vision, text, multimodal
- **ai_provider_enum**: qwen, moonshot, gpt, claude, gemini, baidu
- **algorithm_status_enum**: 算法状态枚举
- **task_status_enum**: 任务状态枚举
- 等等...

## 注意事项

1. **数据敏感性**
   - schema_data.sql 包含生产数据，请妥善保管
   - 包含用户信息、API密钥等敏感数据
   - 不要将此文件提交到公开代码仓库

2. **导入顺序**
   - 必须先导入 schema_structure.sql（表结构）
   - 再导入 schema_data.sql（表数据）

3. **依赖关系**
   - 脚本包含外键约束，确保按正确顺序导入
   - 枚举类型会在表创建之前定义

4. **字符编码**
   - 导出文件使用 UTF8 编码
   - 导入时确保数据库也使用 UTF8 编码

## 完整恢复示例

```bash
# 1. 创建新数据库（如果需要）
docker exec vision_postgres psql -U vision -c "CREATE DATABASE vision_db_new ENCODING 'UTF8';"

# 2. 导入表结构
docker exec -i vision_postgres psql -U vision -d vision_db_new < /path/to/schema_structure.sql

# 3. 导入表数据
docker exec -i vision_postgres psql -U vision -d vision_db_new < /path/to/schema_data.sql

# 4. 验证导入
docker exec vision_postgres psql -U vision -d vision_db_new -c "\dt"
```

## 导出命令记录

```bash
# 导出表结构
docker exec vision_postgres pg_dump -U vision -d vision_db \
  --schema-only --no-owner --no-acl \
  > schema_structure.sql

# 导出表数据
docker exec vision_postgres pg_dump -U vision -d vision_db \
  --data-only --no-owner --no-acl --column-inserts \
  > schema_data.sql
```

## 维护建议

1. **定期备份**
   - 建议每日备份数据库
   - 保留至少7天的备份历史

2. **版本控制**
   - schema_structure.sql 应纳入版本控制
   - schema_data.sql 仅用于备份，不纳入版本控制

3. **测试验证**
   - 定期测试备份文件的可恢复性
   - 在测试环境验证导入流程

---

**生成时间**: 2025-10-09
**生成工具**: PostgreSQL pg_dump 16.10
**执行环境**: Docker容器 (vision_postgres)
