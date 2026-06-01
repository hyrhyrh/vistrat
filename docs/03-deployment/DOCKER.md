# Docker部署指南

AI视频监控系统支持完整的Docker容器化部署，包含所有必需的基础设施服务。

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker容器架构                            │
├─────────────────────────────────────────────────────────────┤
│  Frontend (React)     │  Backend (FastAPI)                 │
│  端口: 3000          │  端口: 16532                       │
└─────────────────────┬─┴─────────────────────────┬─────────┘
                      │                           │
              ┌───────▼──────┐           ┌────────▼───────┐
              │   数据存储    │           │    AI服务      │
              │              │           │                │
              │ PostgreSQL   │           │ 通义千问 API   │
              │ 端口: 5432   │           │ Moonshot API   │
              │              │           │                │
              │ Redis        │           └────────────────┘
              │ 端口: 6379   │
              │              │           ┌────────────────┐
              │ MinIO        │           │  可选服务      │
              │ 端口: 9000   │◄─────────►│                │
              │ 控制台: 9001 │           │ Elasticsearch  │
              │              │           │ 端口: 9200     │
              └──────────────┘           └────────────────┘
```

## 快速开始

### 1. 环境准备

```bash
# 确保Docker和Docker Compose已安装
docker --version
docker-compose --version

# 克隆代码仓库
git clone <repository-url>
cd vistrat
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量文件，填入API密钥
vim .env
```

**必需配置项：**
```bash
# AI模型API密钥（必需）
QWEN_API_KEY=your-qwen-api-key
MOONSHOT_API_KEY=your-moonshot-api-key
```

### 3. 启动服务

```bash
# 启动所有基础服务
docker-compose up -d postgres redis minio

# 等待服务启动完成（约30秒）
docker-compose ps

# 启动完整系统
docker-compose up -d
```

### 4. 验证部署

```bash
# 检查所有容器状态
docker-compose ps

# 查看服务日志
docker-compose logs -f backend

# 访问服务
curl http://localhost:16532/api/health
```

## 服务地址

| 服务 | 地址 | 用途 |
|-----|------|------|
| 前端界面 | http://localhost:3000 | Web管理界面 |
| 后端API | http://localhost:16532 | REST API |
| MinIO控制台 | http://localhost:9001 | 对象存储管理 |
| PostgreSQL | localhost:5432 | 数据库 |
| Redis | localhost:6379 | 缓存 |

## 部署配置

### 标准部署（推荐）

```bash
# 启动核心服务
docker-compose up -d postgres redis minio backend frontend
```

包含：前端、后端、数据库、缓存、对象存储

### 完整部署

```bash
# 启动所有服务，包括Elasticsearch
docker-compose --profile full up -d
```

包含：标准服务 + Elasticsearch（用于日志分析）

### 开发模式

```bash
# 使用开发配置
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

启用：代码热重载、详细日志、调试模式

## 数据持久化

系统使用Docker卷来持久化重要数据：

```yaml
volumes:
  postgres_data:    # 数据库数据
  minio_data:       # 对象存储数据  
  redis_data:       # 缓存数据
  elasticsearch_data: # 搜索索引数据（可选）
```

## 常用操作

### 查看日志
```bash
# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 查看所有服务日志
docker-compose logs -f
```

### 重启服务
```bash
# 重启单个服务
docker-compose restart backend

# 重启所有服务
docker-compose restart
```

### 更新服务
```bash
# 重新构建并启动
docker-compose up -d --build

# 仅重新构建后端
docker-compose build backend
docker-compose up -d backend
```

### 清理数据
```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（谨慎使用）
docker-compose down -v

# 清理未使用的镜像
docker system prune
```

## 故障排除

### 常见问题

1. **端口冲突**
   ```bash
   # 检查端口占用
   netstat -tulpn | grep :5432
   
   # 修改docker-compose.yml中的端口映射
   ports:
     - "15432:5432"  # 使用其他端口
   ```

2. **容器启动失败**
   ```bash
   # 查看详细错误信息
   docker-compose logs container-name
   
   # 检查健康状态
   docker-compose ps
   ```

3. **数据库连接失败**
   ```bash
   # 检查数据库是否准备就绪
   docker-compose exec postgres pg_isready -U vision
   
   # 手动连接测试
   docker-compose exec postgres psql -U vision -d vistrat
   ```

4. **MinIO访问失败**
   ```bash
   # 检查MinIO状态
   curl http://localhost:9000/minio/health/live
   
   # 查看MinIO日志
   docker-compose logs minio
   ```

### 性能调优

1. **内存分配**
   ```yaml
   # 在docker-compose.yml中限制内存使用
   deploy:
     resources:
       limits:
         memory: 2G
       reservations:
         memory: 1G
   ```

2. **Elasticsearch优化**
   ```yaml
   # 调整JVM堆大小
   environment:
     - "ES_JAVA_OPTS=-Xms512m -Xmx1g"
   ```

## 生产环境部署

### 安全配置

1. **更改默认密码**
   ```bash
   # 在.env文件中设置强密码
   DB_PASSWORD=your-strong-password
   MINIO_SECRET_KEY=your-strong-secret
   ```

2. **启用HTTPS**
   ```yaml
   # 添加Nginx反向代理
   nginx:
     image: nginx:alpine
     ports:
       - "443:443"
       - "80:80"
   ```

3. **网络隔离**
   ```yaml
   # 使用内部网络
   networks:
     internal:
       driver: bridge
       internal: true
   ```

### 监控配置

```yaml
# 添加监控服务
monitoring:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
```

## 备份与恢复

### 数据备份
```bash
# 备份数据库
docker-compose exec postgres pg_dump -U vision vistrat > backup.sql

# 备份MinIO数据
docker run --rm -v minio_data:/data -v $(pwd):/backup busybox tar czf /backup/minio_backup.tar.gz /data
```

### 数据恢复
```bash
# 恢复数据库
docker-compose exec -T postgres psql -U vision vistrat < backup.sql

# 恢复MinIO数据
docker run --rm -v minio_data:/data -v $(pwd):/backup busybox tar xzf /backup/minio_backup.tar.gz -C /
```

## 开发指南

### 本地开发

```bash
# 仅启动基础设施服务
docker-compose up -d postgres redis minio

# 在本地运行后端和前端进行开发
cd backend && python main.py
cd frontend && npm run dev
```

### 调试模式

```bash
# 启用调试模式
export DEBUG=true
docker-compose up -d
```