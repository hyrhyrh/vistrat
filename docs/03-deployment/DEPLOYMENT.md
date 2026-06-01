# AI视频监控系统 - 生产环境部署指南

## 📋 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 最低配置: 4核CPU, 8GB内存, 50GB磁盘空间
- 推荐配置: 8核CPU, 16GB内存, 100GB+ SSD

## 🚀 首次部署步骤

### 1. 克隆项目

```bash
git clone <repository-url>
cd vistrat
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件
vim .env
```

**必须配置的环境变量**:
```bash
# 数据库配置
POSTGRES_DB=vision_db
POSTGRES_USER=vision
POSTGRES_PASSWORD=your_secure_password_here

# MinIO配置
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_secure_minio_password_here

# AI API密钥
QWEN_API_KEY=your_qwen_api_key
MOONSHOT_API_KEY=your_moonshot_api_key
```

### 3. 初始化存储目录 ⭐ **重要**

**首次部署前必须执行此步骤**,否则Elasticsearch等服务会因权限问题无法启动:

```bash
# 执行存储目录初始化脚本
./scripts/init_storage.sh
```

该脚本会自动:
- ✅ 创建所有必需的存储目录
- ✅ 为Elasticsearch设置正确的权限 (UID 1000)
- ✅ 为PostgreSQL设置正确的权限 (UID 999)
- ✅ 为Redis设置正确的权限 (UID 999)
- ✅ 为MinIO设置正确的权限 (UID 1000)
- ✅ 为后端应用设置正确的权限

### 4. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 验证部署

```bash
# 检查所有服务健康状态
docker-compose ps

# 测试后端API
curl http://localhost:16532/health

# 访问前端
# 浏览器打开: http://localhost:3009
```

## 🔄 重新部署 / 更新

### 方法1: 完全重新部署 (清空数据)

```bash
# 停止并删除所有容器和数据卷
docker-compose down -v

# 重新初始化存储目录
./scripts/init_storage.sh

# 启动服务
docker-compose up -d
```

### 方法2: 仅更新代码 (保留数据)

```bash
# 拉取最新代码
git pull

# 重启服务
docker-compose restart

# 或者重新构建并启动
docker-compose up -d --build
```

## 🐛 常见问题排查

### 问题1: Elasticsearch容器一直重启

**症状**:
```bash
docker logs vision_elasticsearch
# 显示: AccessDeniedException: /usr/share/elasticsearch/data/node.lock
```

**原因**: 存储目录权限不正确

**解决方案**:
```bash
# 停止服务
docker-compose stop elasticsearch

# 重新初始化权限
./scripts/init_storage.sh

# 或者手动修复
sudo chown -R 1000:1000 ./storage/elasticsearch

# 启动服务
docker-compose up -d elasticsearch
```

### 问题2: PostgreSQL初始化失败

**症状**: 数据库表不存在或登录失败

**解决方案**:
```bash
# 完全清理并重新初始化
docker-compose down -v
rm -rf ./storage/postgres/*
./scripts/init_storage.sh
docker-compose up -d postgres

# 查看初始化日志
docker-compose logs postgres | grep "初始化"
```

### 问题3: Backend容器无法写入文件

**症状**: 日志显示权限拒绝错误

**解决方案**:
```bash
# 修复后端目录权限
sudo chown -R 1000:1000 ./storage/uploads
sudo chown -R 1000:1000 ./storage/data
sudo chown -R 1000:1000 ./storage/logs
sudo chown -R 1000:1000 ./storage/video_warning
sudo chown -R 1000:1000 ./storage/archive
```

## 📊 服务端口说明

| 服务 | 端口 | 说明 |
|------|------|------|
| Frontend | 3009 | Web前端界面 |
| Backend | 16532 | API服务 |
| PostgreSQL | 5432 | 数据库 |
| Elasticsearch | 9200, 9300 | 搜索引擎 |
| Redis | 6379 | 缓存服务 |
| MinIO API | 9010 | 对象存储API |
| MinIO Console | 9011 | MinIO管理界面 |

## 🔒 生产环境安全建议

1. **修改默认密码**: 更改 `.env` 中的所有默认密码
2. **限制端口访问**: 使用防火墙限制数据库端口仅允许内网访问
3. **启用HTTPS**: 配置Nginx反向代理并启用SSL证书
4. **定期备份**: 定时备份PostgreSQL数据库和MinIO对象存储
5. **监控日志**: 配置日志收集和监控告警

## 🔄 数据备份与恢复

### 备份

```bash
# 备份PostgreSQL数据库
docker exec vision_postgres pg_dump -U vision vision_db > backup_$(date +%Y%m%d).sql

# 备份存储目录
tar -czf storage_backup_$(date +%Y%m%d).tar.gz ./storage/
```

### 恢复

```bash
# 恢复PostgreSQL数据库
docker exec -i vision_postgres psql -U vision vision_db < backup_20231201.sql

# 恢复存储目录
tar -xzf storage_backup_20231201.tar.gz
./scripts/init_storage.sh
```

## 📞 技术支持

- 问题反馈: [GitHub Issues](https://github.com/your-repo/issues)
- 文档: [在线文档](https://docs.your-domain.com)
- 邮箱: support@your-domain.com

## 📝 版本历史

- **v2.3.0** (2025-01-09)
  - ✅ 修复Elasticsearch权限问题
  - ✅ 添加自动初始化脚本
  - ✅ 优化数据库架构
  - ✅ 改进Docker EntryPoint模式

- **v2.2.0** (2024-12-15)
  - MJPEG流媒体支持
  - 性能优化

- **v2.1.0** (2024-11-20)
  - 初始生产版本发布
