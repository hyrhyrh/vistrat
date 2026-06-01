# 环境变量文件使用指南

## 📂 文件结构

```
vistrat/
├── .env                  # Docker Compose 使用（容器环境）
├── .env.example          # 环境变量模板（供参考）
└── backend/
    ├── .env              # 本地开发环境使用
    └── .env.README.md    # Backend配置说明
```

## 🎯 两个 `.env` 文件的区别

### 1. 根目录 `.env` - Docker Compose 环境
**用途**: `docker-compose up` 时使用  
**位置**: `/root/project/vistrat/.env`

**关键配置**:
```bash
# Docker容器间通信使用容器服务名
POSTGRES_DB=vision_db
POSTGRES_USER=vision
POSTGRES_PASSWORD=vision123

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# AI API密钥（容器内的backend服务会读取这些）
QWEN_API_KEY=sk-xxx
MOONSHOT_API_KEY=sk-xxx
CLAUDE_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
```

**特点**:
- ✅ Docker Compose 直接读取该文件中的变量
- ✅ 容器服务通过服务名通信（如 `postgres`, `minio`, `redis`）
- ✅ 这些环境变量会传递给容器内的服务

### 2. Backend 目录 `.env` - 本地开发环境
**用途**: 本地运行 `python main.py` 时使用  
**位置**: `/root/project/vistrat/backend/.env`

**关键配置**:
```bash
# 本地开发环境使用 localhost
DB_HOST=localhost          # 不是 postgres
DB_PORT=5432
DB_NAME=vision_db
DB_USER=vision
DB_PASSWORD=vision123

MINIO_ENDPOINT=localhost:9010    # 不是 minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

REDIS_HOST=localhost             # 不是 redis
ES_HOST=localhost               # 不是 elasticsearch

# 完整的AI API配置
CLAUDE_API_KEY=sk-xxx
QWEN_API_KEY=sk-xxx
MOONSHOT_API_KEY=sk-xxx
DEEPSEEK_API_KEY=sk-xxx
```

**特点**:
- ✅ 后端代码通过 `dotenv` 加载（`main.py` 中的 `load_dotenv()`）
- ✅ 使用 `localhost` 连接本地服务
- ✅ 包含更多的后端配置参数（如连接池、性能优化等）

## 🔄 使用场景

### 场景1: 本地开发调试（推荐）
```bash
# 启动基础设施（PostgreSQL, Redis, ES, MinIO）
docker-compose up -d postgres redis elasticsearch minio

# 在本地运行后端（读取 backend/.env）
cd backend
python main.py
```

### 场景2: 完整 Docker 部署
```bash
# 启动所有服务（读取根目录 .env）
docker-compose up -d
```

### 场景3: 混合模式
```bash
# 基础设施用Docker，后端本地运行
docker-compose up -d postgres redis elasticsearch minio
cd backend && python main.py
```

## ⚙️ 配置差异对比

| 配置项 | 根目录 `.env` (Docker) | `backend/.env` (本地) |
|--------|----------------------|---------------------|
| 数据库地址 | `POSTGRES_DB/USER/PASSWORD` | `DB_HOST=localhost` |
| MinIO地址 | `MINIO_ROOT_USER/PASSWORD` | `MINIO_ENDPOINT=localhost:9010` |
| Redis地址 | (docker-compose固定) | `REDIS_HOST=localhost` |
| ES地址 | (docker-compose固定) | `ES_HOST=localhost` |
| AI API密钥 | ✅ 有 | ✅ 有（完整） |
| 连接池配置 | ❌ 无 | ✅ 有 |
| 性能配置 | ❌ 无 | ✅ 有 |

## 🔒 安全提示

1. **永远不要提交 `.env` 文件到 Git**
   - 根目录 `.env` - 已在 `.gitignore`
   - `backend/.env` - 已在 `.gitignore`

2. **使用 `.env.example` 作为模板**
   ```bash
   cp .env.example .env
   # 编辑 .env 填入实际密钥
   ```

3. **生产环境务必修改默认密码和密钥**

## 🐛 故障排查

### Docker Compose 警告
```
WARN[0000] The "POSTGRES_USER" variable is not set.
```

**原因**: 根目录 `.env` 文件缺少配置或格式错误  
**解决**: 
```bash
# 检查文件是否存在
ls -la .env

# 验证配置
grep POSTGRES_USER .env

# 重新生成配置
cp .env.example .env
```

### 本地开发连接失败
```
ERROR: could not connect to server
```

**原因**: `backend/.env` 配置错误或服务未启动  
**解决**:
```bash
# 检查配置文件
cat backend/.env | grep DB_HOST

# 确认服务运行
docker ps | grep postgres

# 测试连接
psql -h localhost -U vision -d vision_db
```

## 📚 参考文档

- [环境变量配置说明](backend/.env.README.md)
- [Docker部署指南](CLAUDE.md)
- [项目主文档](README.md)
