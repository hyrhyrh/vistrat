"""
API v1 版本化路由模块

将所有现有路由统一注册到 /api/v1/ 前缀下，作为正式的版本化 API 入口。
原有 /api/ 前缀的路由继续保留以实现向后兼容（标记为 deprecated）。

版本策略：
- /api/v1/xxx  — 正式版本化路由（推荐使用）
- /api/xxx     — 旧路由（向后兼容，未来版本可能移除）
"""

from fastapi import APIRouter

# ============================================================
# 引入所有现有的子路由（不移动文件，仅引用）
# ============================================================
from api.prompts import router as prompts_router
from api.alerts import router as alerts_router
from api.streams import router as streams_router
from api.video_streams import router as video_streams_router
from api.stream_monitor import router as stream_monitor_router
from api.ai_models import router as ai_models_router
from api.ai_provider_configs import router as ai_provider_configs_router
from api.auth import router as auth_router
from api.users import router as users_router
from api.video_files import router as video_files_router
from api.analysis_results import router as analysis_results_router
from api.image_proxy import router as image_proxy_router
from api.realtime_streams import router as realtime_streams_router
from api.mjpeg_stream import router as mjpeg_stream_router
from services.flv_stream_service import router as flv_stream_router
from api.snapshot import router as snapshot_router
from api.ai_text_generation import router as ai_text_generation_router
from api.performance_monitor import router as performance_monitor_router
from api.agent import router as agent_router
from api.agent_history import router as agent_history_router
from api.speech import router as speech_router
from api.stream_tasks import router as stream_tasks_router
from api.alert_notifications import router as alert_notifications_router
from api.agent_claude import router as agent_claude_router
from api.daily_alerts_report import router as daily_alerts_report_router
from api.video_compat import router as video_compat_router
from api.ai_model_management import router as ai_model_router
from api.metrics import router as metrics_router
from api.video_streams_ws import router as video_streams_ws_router
from api.task_health import router as task_health_router

# 自带 /api 前缀的路由 — 需要特殊处理
from api.roi_config import router as roi_config_router
from api.schedule_config import router as schedule_config_router
from api.safety_dashboard import router as safety_dashboard_router

# ============================================================
# 创建 v1 版本路由器
#
# 此 router 不设 prefix，在 main.py 中以 prefix="/api/v1" 注册。
# 各子路由自带的 prefix（如 /alerts, /auth）会拼接在 /api/v1 后面，
# 最终形成 /api/v1/alerts, /api/v1/auth 等路径。
# ============================================================
v1_router = APIRouter()

# ---------- 核心业务路由 ----------
v1_router.include_router(prompts_router)
v1_router.include_router(alerts_router)
v1_router.include_router(streams_router)
v1_router.include_router(video_streams_router)
v1_router.include_router(stream_monitor_router)
v1_router.include_router(ai_models_router)
v1_router.include_router(ai_provider_configs_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(video_files_router)
v1_router.include_router(analysis_results_router)
v1_router.include_router(image_proxy_router)
v1_router.include_router(realtime_streams_router)
v1_router.include_router(mjpeg_stream_router)
v1_router.include_router(flv_stream_router)
v1_router.include_router(snapshot_router)
v1_router.include_router(ai_text_generation_router)
v1_router.include_router(performance_monitor_router)
v1_router.include_router(agent_router)
v1_router.include_router(agent_history_router)
v1_router.include_router(speech_router)
v1_router.include_router(stream_tasks_router)
v1_router.include_router(alert_notifications_router)
v1_router.include_router(agent_claude_router)
v1_router.include_router(daily_alerts_report_router)
v1_router.include_router(video_compat_router)

# ---------- 在 main.py 中原本直接注册到 app 的路由 ----------
v1_router.include_router(ai_model_router)
v1_router.include_router(metrics_router)
v1_router.include_router(video_streams_ws_router)

# ---------- 自带 /api 前缀的路由 ----------
# 以下路由的 prefix 自带 "/api"（如 /api/roi-configs, /api/schedule-configs 等），
# 注册到 v1_router 后路径会变成 /api/v1/api/xxx。
# 为保持路径一致性，这些路由在 v1 中也直接包含，
# 最终路径为 /api/v1/api/roi-configs 等（与旧路径 /api/api/roi-configs 对应）。
v1_router.include_router(roi_config_router)
v1_router.include_router(schedule_config_router)
v1_router.include_router(safety_dashboard_router)
v1_router.include_router(task_health_router)

__all__ = ["v1_router"]
