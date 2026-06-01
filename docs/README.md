# AI智能视频监控预警系统 - 文档中心

> 📚 完整的技术文档、部署指南和架构设计

---

## 📖 文档导航

### [01-architecture](./01-architecture/) - 架构设计
系统架构设计、技术选型和设计模式分析

- `architecture.md` - 系统总体架构
- `SYSTEM_ARCHITECTURE.md` - 详细架构说明
- `DESIGN_PATTERNS_ANALYSIS.md` - 19种设计模式深度分析
- `MJPEG_STREAMING_ARCHITECTURE.md` - MJPEG流媒体架构
- `video_processing_architecture_assessment.md` - 视频处理架构评估
- `技术架构与修复对比.md` - 技术架构演进对比

### [02-ai-agent](./02-ai-agent/) - AI智能体
Claude AI Agent集成、MVP实施和阶段性报告

- `AI_AGENT_ARCHITECTURE.md` - AI智能体架构设计
- `AI_AGENT_MVP_README.md` - MVP版本说明
- `Agent重构设计方案.md` - 智能体重构方案
- `Claude_Agent_MVP使用说明.md` - Claude智能体使用指南
- `AI_AGENT_PHASE1_COMPLETION_REPORT.md` - 第一阶段完成报告
- `AI_AGENT_PHASES_SUMMARY.md` - 阶段总结

### [03-deployment](./03-deployment/) - 部署指南
Docker部署、多架构构建、边缘设备部署和生产环境配置

- `DEPLOYMENT.md` - 基础部署指南
- `DOCKER_DEPLOYMENT.md` - Docker部署详解
- `DOCKER_AUTO_DEPLOYMENT.md` - Docker自动化部署
- `BUILD_MULTIARCH_GUIDE.md` - 多架构镜像构建指南
- `EDGE_DEPLOYMENT_GUIDE.md` - 边缘设备部署指南
- `PRODUCTION_CONFIG.md` - 生产环境配置
- `ENV_FILES_GUIDE.md` - 环境变量配置指南
- `DOCKER_CACHE_OPTIMIZATION.md` - Docker缓存优化
- `DOCKER_PROXY_FIX.md` - Docker代理配置修复
- `PROXY_QUICK_REFERENCE.md` - 代理配置快速参考

### [04-database](./04-database/) - 数据库
数据库Schema设计、迁移记录和优化方案

- `database-schema.md` - 数据库Schema设计
- `database_schema.md` - Schema详细说明
- `PSYCOPG3_MIGRATION.md` - Psycopg3迁移记录
- `database_structure_summary.md` - 数据库结构总结
- `README.md` - 数据库文档索引

### [05-video-streaming](./05-video-streaming/) - 视频流处理
MJPEG/WebRTC流媒体、实时分析和性能优化

- `MJPEG_QUICK_START.md` - MJPEG流媒体快速开始
- `REALTIME_STREAM_ANALYSIS_TECHNICAL_DOC.md` - 实时流分析技术文档
- `REALTIME_STREAM_OPTIMIZATION_PLAN.md` - 实时流优化方案
- `WebRTC黑屏问题解决总结.md` - WebRTC问题排查
- `VideoPlayerModal_Optimization.md` - 视频播放器优化
- `FFMPEG_FIX.md` - FFmpeg问题修复
- `TESTING_FFMPEG.md` - FFmpeg测试文档

### [06-integrations](./06-integrations/) - 第三方集成
百度语音、企业微信等第三方服务集成

- `BAIDU_SPEECH_SETUP.md` - 百度语音识别配置
- `企业微信告警统计报表功能说明.md` - 企业微信集成说明

### [07-performance](./07-performance/) - 性能优化
系统性能分析和优化方案

- `PERFORMANCE_OPTIMIZATION_STAGE1.md` - 第一阶段性能优化

### [08-migration](./08-migration/) - 迁移记录
版本迁移、重构记录和完成报告

- `MIGRATION_COMPLETED_v3.5.md` - v3.5版本迁移完成
- `PHASE_3_COMPLETION_REPORT.md` - 第三阶段完成报告

### [09-demo](./09-demo/) - 演示文档
竞赛演示、功能展示和演讲脚本

- `COMPETITION_DEMO_SCRIPT.md` - 竞赛演示脚本

### [10-arm-issues](./10-arm-issues/) - ARM架构问题
ARM边缘设备部署问题排查和解决方案

- `DOCKER_UPGRADE_GUIDE.md` - **✅ Docker升级指南（最终解决方案）**

---

## 🚀 快速开始

### 新手入门
1. 阅读 [架构设计](./01-architecture/SYSTEM_ARCHITECTURE.md)
2. 查看 [部署指南](./03-deployment/DEPLOYMENT.md)
3. 配置 [环境变量](./03-deployment/ENV_FILES_GUIDE.md)

### 开发人员
1. 了解 [设计模式](./01-architecture/DESIGN_PATTERNS_ANALYSIS.md)
2. 查看 [数据库Schema](./04-database/database-schema.md)
3. 学习 [AI智能体架构](./02-ai-agent/AI_AGENT_ARCHITECTURE.md)

### 运维人员
1. 阅读 [Docker部署](./03-deployment/DOCKER_DEPLOYMENT.md)
2. 配置 [生产环境](./03-deployment/PRODUCTION_CONFIG.md)
3. 参考 [边缘设备部署](./03-deployment/EDGE_DEPLOYMENT_GUIDE.md)

### ARM设备部署
1. **重要**：先阅读 [Docker升级指南](./10-arm-issues/DOCKER_UPGRADE_GUIDE.md)
2. 确保Docker版本 ≥ 20.10.10
3. 按照 [边缘设备部署指南](./03-deployment/EDGE_DEPLOYMENT_GUIDE.md) 进行

---

## 📊 文档统计

| 分类 | 文档数量 | 说明 |
|------|---------|------|
| 架构设计 | 6 | 系统架构和设计模式 |
| AI智能体 | 9 | Claude Agent集成 |
| 部署指南 | 11 | Docker和边缘设备部署 |
| 数据库 | 5 | Schema和迁移记录 |
| 视频流处理 | 7 | MJPEG/WebRTC流媒体 |
| 第三方集成 | 2 | 百度语音、企业微信 |
| 性能优化 | 1 | 性能分析和优化 |
| 迁移记录 | 2 | 版本迁移记录 |
| 演示文档 | 1 | 竞赛演示脚本 |
| ARM问题 | 1 | Docker升级解决方案 |
| **总计** | **45** | |

---

## 🎯 核心技术栈

- **后端**: Python 3.10 + FastAPI + asyncpg + uvloop
- **前端**: React 18 + TypeScript + Ant Design 5
- **数据库**: PostgreSQL 16 + Elasticsearch 8.11
- **缓存**: Redis 7
- **存储**: MinIO
- **容器**: Docker 20.10+ / Docker Compose
- **AI模型**: 通义千问、Kimi、Claude
- **流媒体**: MJPEG (OpenCV) / WebRTC

---

## 📝 文档维护

- **最后更新**: 2025-10-28
- **版本**: v2.4.0
- **维护者**: AI Watchdog Team

---

## 💡 贡献指南

1. 所有文档使用Markdown格式
2. 文件命名使用大写英文 + 下划线（如：`SYSTEM_ARCHITECTURE.md`）
3. 中文文档使用中文命名（如：`技术架构与修复对比.md`）
4. 新增文档请放入对应的分类文件夹
5. 更新文档后请同步更新此README

---

## 🔗 相关链接

- [项目主README](../README.md)
- [CLAUDE.md - 项目指南](../CLAUDE.md)
- [后端代码](../backend/)
- [前端代码](../frontend/)
