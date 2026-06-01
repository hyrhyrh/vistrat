# API 版本控制策略

## 概述

本项目采用 **URL 路径前缀** 方式进行 API 版本控制。所有 API 端点通过路径中的版本号区分不同版本。

## 版本路径

| 路径前缀 | 状态 | 说明 |
|----------|------|------|
| `/api/v1/xxx` | **正式版本（推荐）** | 当前稳定版本，新客户端应使用此路径 |
| `/api/xxx` | **向后兼容（Deprecated）** | 旧版无版本路径，保留向后兼容，未来版本可能移除 |

## 响应头

所有 `/api/v1/` 路径的响应会自动携带版本标识头：

```
X-API-Version: v1
```

客户端可通过此 header 确认请求命中了哪个 API 版本。

## 示例

```
# 旧路径（仍可工作，但不推荐）
GET /api/alerts/

# 新路径（推荐）
GET /api/v1/alerts/
```

两个路径返回相同结果，但 `/api/v1/` 路径的响应会额外包含 `X-API-Version: v1` header。

## 向后兼容规则

1. **旧路径不会被突然移除**。在引入 v2 之前，`/api/xxx` 路径将持续工作。
2. **v1 版本冻结后不做破坏性变更**。新增字段、新增端点属于兼容性变更，允许在 v1 中进行。删除字段、修改字段类型、修改行为语义等破坏性变更必须在新版本（v2）中进行。
3. **废弃流程**：旧版本 API 废弃前至少提前一个大版本通知，通过响应头 `Deprecation: true` 和文档标注告知客户端。

## 目录结构

```
backend/api/
  __init__.py          # 旧版 api_router (prefix="/api")，已标记 deprecated
  v1/
    __init__.py        # v1_router — 引用所有现有路由，不移动文件
  # 未来版本:
  # v2/
  #   __init__.py      # v2_router — 新版本路由
```

## 如何创建 v2 版本

1. 创建 `backend/api/v2/__init__.py`：

```python
from fastapi import APIRouter

v2_router = APIRouter()

# 引入 v2 版本的路由（可以是新文件，也可以引用并覆盖 v1 的路由）
# from api.v2.alerts import router as alerts_v2_router
# v2_router.include_router(alerts_v2_router)
```

2. 在 `main.py` 的 `create_app()` 中注册：

```python
from api.v2 import v2_router
app.include_router(v2_router, prefix="/api/v2", tags=["v2"])
```

3. 更新版本响应头中间件，为 `/api/v2/` 路径返回 `X-API-Version: v2`。

4. 可选：为 `/api/v1/` 路径添加 `Deprecation` 响应头，引导客户端升级。

## 技术细节

- 版本路由通过 FastAPI 的 `APIRouter` 前缀机制实现，不涉及 URL 重写或反向代理。
- 各子路由文件（如 `api/alerts.py`）不需要修改，它们自带的 prefix（如 `/alerts`）会自动拼接到版本前缀后面。
- `X-API-Version` 响应头通过 Starlette `BaseHTTPMiddleware` 注入，仅对 `/api/v1/` 路径生效。
