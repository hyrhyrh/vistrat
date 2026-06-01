# 贡献指南 / Contributing

感谢你对 Vistrat（观策）感兴趣！本文档介绍如何参与贡献。

Thanks for your interest in Vistrat. This document covers how to contribute.

## 项目简介 / About

Vistrat = **观**（多模态感知）+ **策**（策略与主动预警）—— 用云端 VLM 替代传统 YOLO，让"提示词即场景"成为可能。

Vistrat replaces traditional YOLO pipelines with cloud VLMs so that "a prompt is a scene".

## 开发环境 / Dev Environment

- Python 3.10+ with [`uv`](https://github.com/astral-sh/uv)
- Node.js 18+ with `npm`
- Docker + Docker Compose v2
- FFmpeg + OpenCV system libs

```bash
# Backend
cd backend && uv venv .venv && uv pip install -e ".[dev]"

# Frontend
cd frontend && npm install

# Full stack
cp .env.example .env  # 编辑后再启动
docker compose up --build
```

## 工作流 / Workflow

1. **Fork** 本仓库
2. 基于 `main` 创建分支：`git checkout -b feat/your-feature` 或 `fix/your-bug`
3. 提交变更（小步提交，每个 commit 自洽）
4. 推送并提 PR，关联对应 Issue

## 提交信息 / Commit Convention

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新增 RTSP 多路并发支持
fix: 修复告警时间戳时区错误
docs: 更新部署文档
refactor: 抽取告警通知服务
test: 增加帧抽样单元测试
chore: 升级 fastapi 到 0.118
```

## 代码质量 / Code Quality

- **Python**：`black --check .` + `isort --check .` + `mypy backend/`
- **TypeScript**：`npm run lint`
- 新功能请附测试；修 bug 请加回归测试
- 不要提交 `.env`、密钥、本地数据

## 报告问题 / Reporting Issues

- 一般 bug / 需求 → GitHub Issue
- 安全漏洞 → 见 [SECURITY.md](./SECURITY.md)，**请勿**公开提 Issue

## 许可协议 / License

提交 PR 即表示你同意贡献内容以 MIT 协议授权。

By submitting a PR you agree your contributions are licensed under MIT.
