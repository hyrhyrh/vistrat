# AI 智能视频监控预警系统 — 项目现状全面审计报告

> 审计日期：2026-04-12
> 审计范围：video-multi 全代码库（回退至 0c5acc2 - 2026/2/2）
> 审计版本：v2.2.0

---

## 一、目录结构总览与模块完成度

### 1.1 顶层目录

```
video-multi/
├── backend/              # Python FastAPI 后端服务
├── frontend/             # React 前端应用
├── docs/                 # 项目文档
├── scripts/              # 部署和运维脚本
├── .env.example          # 环境变量模板
├── docker-compose.yml    # Docker 编排配置
├── docker-compose.init.yml
├── docker-compose.final.yml
├── docker-compose.middleware.prod.yml
├── CLAUDE.md             # Claude 开发指南
├── FSAR.md               # 目录架构规范
├── AGENTS.md             # AI 智能体文档
└── README.md
```

### 1.2 后端模块完成度

| 模块 | 文件数 | 大小 | 状态 | 完成度 | 优先级 |
|------|--------|------|------|--------|--------|
| api/ | 33 | 10,369 行 | 已完成 | 98% | 核心 |
| services/ | 44 | 18,085 行 | 已完成 | 95% | 核心 |
| models/ | 21 | 141KB | 已完成 | 95% | 核心 |
| database/ | 6 | 336KB | 已完成 | 100% | 核心 |
| core/ | 7 | 57KB | 已完成 | 90% | 重要 |
| utils/ | 10 | 97KB | 已完成 | 90% | 重要 |
| config/ | 2 | 17KB | 已完成 | 90% | 重要 |
| scripts/ | 23 | 156KB | 已完成 | 100% | 辅助 |
| agent/ | 27 | 244KB | 部分完成 | 75% | 重要 |
| analysis/ | 6 | 49KB | 部分完成 | 70% | 重要 |
| prompts/ | 4 | 46KB | 部分完成 | 75% | 辅助 |
| parsers/ | 2 | 17KB | 已完成 | 80% | 低 |
| tests/ | 11 | 73KB | 骨架 | 40% | 需改进 |
| videos/ | 5 | 42KB | 骨架 | 50% | 低（冗余） |
| storage/ | 2 | 17KB | 骨架 | 40% | 低（冗余） |
| streams/ | 3 | 14KB | 骨架 | 45% | 低（冗余） |

### 1.3 前端模块完成度

| 模块 | 文件数 | 大小 | 状态 | 完成度 |
|------|--------|------|------|--------|
| pages/ | 20 | 472KB | 已完成 | 100% |
| components/ | 26 | 65KB | 已完成 | 95% |
| hooks/ | 4 | 20KB | 已完成 | 90% |
| types/ | 4 | 15KB | 已完成 | 95% |
| contexts/ | 1 | 3.6KB | 已完成 | 90% |
| services/ | 2 | 5.9KB | 基础 | 50% |

### 1.4 冗余/废弃模块

- `videos/`, `storage/`, `streams/` 与 services/ 功能重叠
- `api/__init__.py` 中标记了 8 个已删除的 RTSP/MJPEG 旧实现
- `scripts/` 中 23 个一次性迁移脚本

---

## 二、技术栈和关键依赖版本

### 2.1 后端依赖

| 类别 | 依赖 | 版本 | 状态 |
|------|------|------|------|
| Web 框架 | FastAPI | 0.117.1 | 最新 |
| ASGI 服务器 | Uvicorn | 0.24.0 | 最新 |
| 生产服务器 | Gunicorn | 23.0.0 | 最新 |
| ORM | SQLAlchemy | 2.0.41 | 最新 |
| PostgreSQL 驱动 | asyncpg | 0.30.0 | 最新 |
| 数据验证 | Pydantic | 2.10.3 | 最新 |
| 搜索引擎 | Elasticsearch | 8.11.0 | 最新 |
| 缓存 | Redis | 5.0.1 | 最新 |
| 对象存储 | MinIO | 7.2.16 | 最新 |
| 视频处理 | OpenCV | 4.12.0.88 | 最新 |
| HTTP 客户端 | httpx | 0.25.2 | 最新 |
| AI SDK | OpenAI | 1.58.1 | 最新 |
| AI SDK | Anthropic | 0.39.0 | 最新 |
| 认证 | PyJWT | 2.10.1 | 最新 |
| 密码哈希 | bcrypt | 4.3.0 | 最新 |

Python 版本要求：>=3.9
锁文件：uv.lock

### 2.2 前端依赖

| 类别 | 依赖 | 版本 | 状态 |
|------|------|------|------|
| UI 框架 | React | 18.3.1 | 最新 |
| 类型系统 | TypeScript | 5.9.2 | 最新 |
| 构建工具 | Vite | 4.5.14 | 最新 |
| UI 组件库 | Ant Design | 5.27.4 | 最新 |
| HTTP 客户端 | Axios | 1.12.2 | 最新 |
| 路由 | React Router | 6.30.1 | 最新 |
| 图表 | Recharts | 3.2.1 | 最新 |
| HLS 播放 | HLS.js | 1.6.13 | 最新 |
| FLV 播放 | FLV.js | 1.6.2 | 稳定 |
| 虚拟列表 | React Window | 2.2.1 | 最新 |

Node.js 版本：未指定（建议 >=16）
锁文件：package-lock.json

---

## 三、数据库现状

### 3.1 PostgreSQL 表清单（18 张）

| 表名 | ORM 模型 | 状态 |
|------|----------|------|
| users | UserDB | 一致 |
| video_files | VideoFileDB | 一致 |
| video_streams | VideoStreamDB | 一致 |
| ai_model_configs | AIModelConfigDB | 一致 |
| ai_provider_configs | AIProviderConfigDB | 一致 |
| ai_analysis_logs | AIAnalysisLogDB | 一致 |
| ai_test_results | AITestResultDB | 一致 |
| video_analysis_templates | VideoAnalysisTemplateDB | 一致 |
| video_stream_algorithm_configs | VideoStreamAlgorithmConfigDB | 一致 |
| video_stream_algorithm_config_history | VideoStreamAlgorithmConfigHistoryDB | 一致 |
| system_configs | SystemConfigDB | 一致 |
| ai_agent_history | AgentHistoryDB | 一致 |
| ai_agent_sessions | AgentSessionDB | 一致 |
| detection_type_templates | **缺失 ORM** | 仅 SQL |
| stream_analysis_tasks | **缺失 ORM** | 仅 SQL |
| stream_analysis_templates | **缺失 ORM** | 仅 SQL |
| video_analysis_results | **缺失 ORM** | 仅 SQL |
| schema_migrations | 系统表 | 正常 |

### 3.2 Elasticsearch 索引（2 个）

| 索引名 | 用途 | 字段数 |
|--------|------|--------|
| video_alerts | 告警记录 | 30+ |
| video_frame_results | 帧分析结果 | 20+ |

### 3.3 数据库问题

- 4 张表缺少 ORM 模型
- 未使用 Alembic，手动 SQL 迁移（18 个迁移脚本）
- ES 索引定义仅在 Markdown 文档中，无结构化 mapping 文件
- 迁移版本：v2.3.0 → v2.4.0 → v3.0.0

---

## 四、API 端点清单

总计：200+ 个端点，31 个路由模块，3 个 WebSocket 端点

### 4.1 已实现模块（全部已实现）

| 模块 | 前缀 | 端点数 | 状态 |
|------|------|--------|------|
| 认证 | /api/auth | 6 | 100% |
| 用户管理 | /api/users | 6 | 100% |
| 视频流管理 | /api/video-streams | 15 | 100% |
| 流分析任务 | /api/stream-tasks | 13 | 100% |
| AI 模型配置 | /api/ai-models | 18 | 100% |
| AI 供应商配置 | /api/ai-provider-configs | 11 | 100% |
| 告警管理 | /api/alerts | 4 | 100% |
| 告警通知 | /api/alert-notifications | 5 | 100% |
| 分析结果 | /api/analysis-results | 4 | 100% |
| 视频文件 | /api/video-files | 20 | 100% |
| 流监控 | /api/stream-monitor | 13 | 100% |
| 性能监控 | /api/performance | 8 | 100% |
| 安全大屏 | /api/safety | 6 | 100% |
| AI Agent | /api/agent* | 11 | 100% |
| ROI 配置 | /api/roi-configs | 7 | 100% |
| 时间调度 | /api/schedule-configs | 7 | 100% |
| 提示词模板 | /api/prompts/templates | 7 | 100% |
| 实时流 | /api/realtime-streams | 11 | 100% |
| MJPEG 流 | /api/mjpeg | 2 | 100% |
| 快照 | /api/snapshot | 2 | 100% |
| 图片代理 | /api/image-proxy | 4 | 100% |
| 语音识别 | /api/speech | 2 | 100% |
| AI 文本生成 | /api/ai-text | 3 | 100% |
| 指标 | /api/metrics | 4 | 100% |
| 任务健康 | /api/task-health | 6 | 100% |
| 每日报表 | /api/daily-alerts-report | 2 | 100% |

### 4.2 WebSocket 端点

| 路径 | 用途 | 状态 |
|------|------|------|
| ws://host/alerts | 告警实时推送 | 已实现 |
| ws://host/video_feed | 视频流推送 | 已实现 |
| ws://host/api/video-streams/ws/health-status | 流健康状态 | 已实现 |

### 4.3 API 架构问题

- 无 API 版本控制（统一 /api 前缀）
- CORS 配置过宽（allow_origins=["*"]）
- 缺乏请求限流
- 缺乏审计日志

---

## 五、前端路由和页面清单

### 5.1 路由清单（17 个，100% 已完成）

| 路由路径 | 页面组件 | 大小 | 状态 |
|---------|---------|------|------|
| / | 重定向至 /live-preview | - | 已完成 |
| /live-preview | LivePreviewPage | 37KB | 已完成 |
| /stream-management | VideoStreamPage | 39KB | 已完成 |
| /video-management | VideoManagementPage | 14KB | 已完成 |
| /video-comparison | VideoComparisonPage | 8.5KB | 已完成 |
| /alerts | AlertsPage | 14KB | 已完成 |
| /analysis-results | AnalysisResultsPage | 27KB | 已完成 |
| /prompts | PromptManagePage | 13KB | 已完成 |
| /detection-templates | DetectionTemplatesPage | 21KB | 已完成 |
| /ai-model | AIModelPage | 43KB | 已完成 |
| /ai-provider-config | AIProviderConfigPage | 16KB | 已完成 |
| /performance | PerformanceMonitorPage | 13KB | 已完成 |
| /safety-dashboard | SafetyMonitoringDashboard | 19KB | 已完成 |
| /safety-dashboard-ai | SafetyMonitoringDashboardWithAI | 45KB | 已完成 |
| /daily-alerts-report | DailyAlertsReportPage | 10KB | 已完成 |
| /user-management | UserManagementPage | 21KB | 已完成 |
| /login | LoginPage | 20KB | 已完成 |
| /sso-login | SSOLoginPage | 5.5KB | 已完成 |

### 5.2 公共组件（25 个）

| 分类 | 组件数 | 主要组件 |
|------|--------|---------|
| stream/ | 9 | FLVPlayer, MJPEGPlayer, StreamPlayerModal 等 |
| video/ | 5 | VideoListTable, VideoPlayerModal 等 |
| agent/ | 3 | AgentButton, AgentDialog, HistoryPanel |
| prompt/ | 3 | PromptTable, PromptModals, PromptStatsCards |
| alert/ | 2 | AlertDrawer, VirtualAlertList |
| 核心 | 3 | ProtectedRoute, AIProcessFlow |

---

## 六、测试现状

| 维度 | 状态 | 详情 |
|------|------|------|
| 后端框架 | pytest + pytest-asyncio | 已配置 |
| 后端测试文件 | 9 个 | 帧质量、AI API、复合检测、JSONB 等 |
| 前端测试 | **缺失** | 无 Jest/Vitest 配置 |
| E2E 测试 | **缺失** | 无 |
| CI/CD | **缺失** | 无 .gitlab-ci.yml / GitHub Actions |
| 覆盖率 | 后端 ~15-20%，前端 0% | 严重不足 |

---

## 七、代码问题清单

### 7.1 安全问题（高严重度）

| # | 问题 | 位置 | 修复成本 |
|---|------|------|---------|
| S1 | CORS 完全开放 `allow_origins=["*"]` + `allow_credentials=True` | main.py:202 | 低 |
| S2 | JWT 密钥使用默认值 | auth_service.py:22 | 低 |
| S3 | 日志泄露 Token 片段 `token[:10]` | api/auth.py:42,52 | 低 |
| S4 | MinIO 默认凭证 `minioadmin/minioadmin` | config/settings.py:111 | 低 |
| S5 | WebSocket 无认证 | alert_service.py:30 | 中 |

### 7.2 架构问题（中严重度）

| # | 问题 | 影响 | 修复成本 |
|---|------|------|---------|
| A1 | 超长类：6 个 services 超 700 行（最大 1004 行） | 难维护/测试 | 高 |
| A2 | API 层职责混乱：mjpeg_stream.py 711 行含编解码逻辑 | 违反分层 | 高 |
| A3 | 43 个 services 过度耦合 | 循环依赖风险 | 高 |
| A4 | 异步/同步混用：asyncio + threading + subprocess | 潜在死锁 | 高 |
| A5 | 全局单例滥用（ES/Storage/Metrics） | 可测试性差 | 中 |

### 7.3 代码坏味道

| # | 问题 | 数量 | 修复成本 |
|---|------|------|---------|
| C1 | 裸 `except: pass` | 15 处 | 中 |
| C2 | 魔法数字 | 20+ 处 | 低 |
| C3 | TODO/FIXME 注释 | 4 个文件 | 低 |
| C4 | 硬编码 IP 地址 | config/settings.py | 低 |
| C5 | `RELOAD` 默认 True | config/settings.py:133 | 低 |
| C6 | 缺少 API 速率限制 | 全局 | 中 |
| C7 | 缺少审计日志 | auth/db 层 | 中 |

---

## 八、环境配置文件情况

| 文件 | 状态 | 说明 |
|------|------|------|
| .env.example | 存在（133行） | 完整的变量模板 |
| .env.middleware.prod | 存在 | 中间件生产配置 |
| backend/.env.example | 存在（19行） | 后端配置示例 |
| docker-compose.yml | 存在 | 8 个服务完整编排 |
| docker-compose.init.yml | 存在 | 初始化配置 |
| docker-compose.final.yml | 存在 | 最终部署配置 |
| backend/Dockerfile | 存在 | 多阶段构建，非 root 用户 |
| frontend/Dockerfile | 存在 | 多阶段构建，Nginx |
| frontend/nginx.conf | 存在 | 反代 + Gzip + 缓存 + WS |
| gunicorn.conf.py | 存在 | 生产服务器配置 |
| .gitlab-ci.yml | **缺失** | 无 CI/CD |
| .github/workflows/ | **缺失** | 无 CI/CD |

---

## 九、技术债修复优先级

### P0 — 立即修复（< 2 小时）

1. CORS 限制具体域名
2. JWT 密钥强制环境变量（禁止默认值）
3. 日志移除 Token 敏感信息
4. MinIO 凭证强制配置
5. RELOAD 默认改为 false

### P1 — 本周内（1-3 天）

1. WebSocket 增加 Token 认证
2. 裸 except 改为具体异常类型（15 处）
3. 为 4 张表补充 ORM 模型
4. 硬编码 IP 移入环境变量

### P2 — 中期（1-2 月）

1. 拆分超长 services
2. API 层与业务逻辑解耦
3. 补充测试覆盖
4. 配置 CI/CD
5. 集成 Alembic 数据库迁移

### P3 — 长期（2-3 月）

1. 统一异步框架
2. 解耦 services 依赖关系
3. 清理废弃模块
4. 实现 API 版本控制
5. ES 索引 mapping 结构化管理

---

## 十、整体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 功能完成度 | 95% | 核心业务全部实现 |
| 代码质量 | 70% | 安全配置和架构耦合需改进 |
| 测试覆盖 | 20% | 严重不足 |
| 部署配置 | 85% | Docker 完善，缺 CI/CD |
| 文档完整度 | 75% | 主要文档齐全，部分模块缺失 |
| **综合评分** | **8.0/10** | 功能完整可生产，技术债需系统清理 |
