<div align="center">

# Vistrat（观策）

**Vision + Strategy — 多模态大模型驱动的智能视频监控预警系统**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Node 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.117-009688.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![GitHub stars](https://img.shields.io/github/stars/hyrhyrh/vistrat?style=social)](https://github.com/hyrhyrh/vistrat)

</div>

> **观**（多模态感知）+ **策**（策略与主动预警）—— 用云端 VLM 替代传统 YOLO，让"提示词即场景"成为可能。

## What & Why

传统视频监控算法依赖 YOLO 这类闭集检测器：**类别封死、误报率高、加一个场景就要重训模型**。Vistrat 把"看"这件事交给多模态视觉大模型（Qwen-VL / Moonshot / 本地 vLLM），再叠一层 Grounding DINO 提供 bbox 定位。

**核心主张**：

- **准确率高于硬件盒子方案** —— VLM 理解上下文，不会把"工地反光衣"识别成"杂物"
- **新场景一天内上线** —— 改提示词，不训模型
- **闭环可追溯** —— 检测 → 告警 → 视频片段回放 → 处置 → 反馈

## ✨ 核心特性

- 🎯 **开放词表检测**：通过提示词描述任意检测目标，无需训练
- 📦 **bbox 可视化**：Grounding DINO 提供告警目标的精确边界框
- 🎞️ **告警视频回放**：mediamtx 自动录制告警发生前后 N 秒片段
- 🔁 **多模型路由**：Qwen-VL / Moonshot / 本地 vLLM，按任务智能选择 + 性能跟踪
- 🌊 **多路并发流处理**：基于 OpenCV 的 MJPEG/HLS 流媒体，最多 10 路并发
- 🔔 **实时告警推送**：WebSocket 毫秒级，支持企业微信通知
- 👮 **认证与权限**：JWT + SSO 登录，admin/user/viewer 三级角色
- 📊 **历史检索与统计**：PostgreSQL + Elasticsearch 双存储，告警/任务/帧数据全留痕
- 🐳 **一键 Docker 部署**：`docker compose up` 起整个栈

## 🏗️ 架构概览

Vistrat 采用**三层分布式架构**，把算力密集型的 VLM + Grounding DINO 推理抽到独立的中台 GPU 服务器，让边缘盒子和 CPU 主机各司其职。

```mermaid
flowchart TB
    subgraph T1["Tier 1 · 边缘盒子 / 摄像头"]
        CAM[RTSP 摄像头]
        EDGE[AI 边缘盒子]
    end

    subgraph T2["Tier 2 · 中台推理服务 (GPU)"]
        INFER["vistrat-inference<br/>FastAPI + Grounding DINO"]
        VLM["云端 VLM<br/>Qwen-VL / Moonshot"]
        INFER -. HTTPS .-> VLM
    end

    subgraph T3["Tier 3 · 业务服务器 (CPU)"]
        FE["React 前端<br/>(Ant Design + SWR)"]
        BE["FastAPI 主后端<br/>业务编排 / 告警 / 权限"]
        MTX[mediamtx<br/>RTSP→HLS + 录制]
        PG[(PostgreSQL)]
        ES[(Elasticsearch)]
        RD[(Redis)]
        MN[(MinIO)]
        BE --- PG
        BE --- ES
        BE --- RD
        BE --- MN
        BE --- MTX
        FE -. WebSocket .- BE
    end

    CAM -- RTSP --> MTX
    CAM -- RTSP --> EDGE
    EDGE -- 抽帧 --> BE
    BE -- 帧 + 预签名 URL --> INFER
    INFER -- bbox + 场景判定 --> BE
    BE -- 告警 + 视频片段 --> FE

    classDef gpu fill:#fff0d4,stroke:#d97706,stroke-width:2px;
    classDef cpu fill:#dbeafe,stroke:#2563eb,stroke-width:2px;
    classDef edge fill:#dcfce7,stroke:#16a34a,stroke-width:2px;
    class INFER,VLM gpu;
    class FE,BE,MTX,PG,ES,RD,MN cpu;
    class CAM,EDGE edge;
```

**关键设计**：
- **Tier 2 无状态**：A100 只跑推理，不存图、不存视频、不存业务数据
- **预签名 URL 拉帧**：业务后端把帧落 MinIO 后生成 15 分钟预签名 URL 交给推理服务，避免大 body POST 和密钥暴露
- **降级开关**：推理服务不可达时自动切纯 VLM 文字路径，告警照发只是没有 bbox
- **片段回放本地化**：mediamtx 录制目录在 CPU 主机，ClipService 直接读本地文件 ffmpeg concat copy 出 MP4，零跨网络

详细架构与设计模式：[docs/01-architecture/](./docs/01-architecture/)

## 🚀 Quick Start

### 前置依赖

- Docker + Docker Compose v2
- 至少一个云端 VLM 的 API Key（Qwen / Moonshot / Claude / GPT 任选其一）
- 可选：NVIDIA GPU + nvidia-container-toolkit（本地 vLLM 推理）

### 启动

```bash
git clone https://github.com/hyrhyrh/vistrat.git
cd vistrat

# 准备配置
cp .env.example .env
# 编辑 .env：至少填一个 AI API Key、设置 DB 密码

# 启动全栈
docker compose up -d --build

# 访问
# Frontend:   http://localhost:3009
# Backend:    http://localhost:16532
# API Docs:   http://localhost:16532/docs
# 默认管理员: admin / change_me_strong_password （请立即在 .env 修改）
```

### 本地开发

```bash
# Backend
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
python main.py

# Frontend (另开终端)
cd frontend
npm install
npm run dev
```

## 📚 文档

- [架构与设计模式](./docs/01-architecture/)
- [AI Agent 子系统](./docs/02-ai-agent/)
- [部署指南](./docs/03-deployment/)
- [数据库 Schema](./docs/04-database/)
- [视频流处理](./docs/05-video-streaming/)
- [集成（百度语音、公众号通知等）](./docs/06-integrations/)
- [性能优化](./docs/07-performance/)
- [迁移记录](./docs/08-migration/)

## 🗺️ Roadmap

- [ ] 边缘盒子部署（ARM64 + Jetson）
- [ ] 接入更多开源 VLM（InternVL、MiniCPM-V）
- [ ] 告警视频自动剪辑与摘要生成
- [ ] 多租户与组织隔离
- [ ] 移动端推送（iOS/Android）
- [ ] 国际化（English / 繁體中文）

欢迎在 [Issues](https://github.com/hyrhyrh/vistrat/issues) 中反馈优先级。

## 🤝 贡献

我们欢迎所有形式的贡献——bug 报告、功能建议、文档改进、代码 PR。开始前请阅读：

- [CONTRIBUTING.md](./CONTRIBUTING.md) — 贡献流程与代码规范
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) — 社区行为准则
- [SECURITY.md](./SECURITY.md) — 漏洞披露

## 📄 License

[MIT License](./LICENSE) © 2026 Vistrat Contributors

## 🙏 Acknowledgements

Vistrat 站在以下优秀开源项目和服务的肩膀上：

- [FastAPI](https://fastapi.tiangolo.com/) · [SQLAlchemy](https://www.sqlalchemy.org/) · [Pydantic](https://pydantic.dev/)
- [React](https://react.dev/) · [Ant Design](https://ant.design/) · [Vite](https://vitejs.dev/)
- [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO) — 开放词表目标检测
- [mediamtx](https://github.com/bluenviron/mediamtx) — RTSP/HLS 流媒体网关
- [Qwen-VL](https://github.com/QwenLM/Qwen-VL) · [Moonshot AI](https://www.moonshot.cn/) · [vLLM](https://github.com/vllm-project/vllm)
- [OpenCV](https://opencv.org/) · [FFmpeg](https://ffmpeg.org/)

特别感谢所有贡献者。 If Vistrat helps your project, please consider giving it a ⭐.
