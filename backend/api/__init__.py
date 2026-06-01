"""
API模块初始化

[DEPRECATED] 此模块中的 api_router (prefix="/api") 为旧版无版本路由，
保留用于向后兼容。新客户端应使用 /api/v1/ 版本化路由。
详见: api/v1/__init__.py 和 api/API_VERSIONING.md
"""

from fastapi import APIRouter
from .prompts import router as prompts_router
from .alerts import router as alerts_router
from .streams import router as streams_router
from .video_streams import router as video_streams_router
from .stream_monitor import router as stream_monitor_router
from .ai_models import router as ai_models_router
from .ai_provider_configs import router as ai_provider_configs_router
from .auth import router as auth_router
from .users import router as users_router
from .video_files import router as video_files_router
from .analysis_results import router as analysis_results_router
from .image_proxy import router as image_proxy_router
from .realtime_streams import router as realtime_streams_router
from .mjpeg_stream import router as mjpeg_stream_router
from services.flv_stream_service import router as flv_stream_router  # HTTP-FLV无损视频流
from .roi_config import router as roi_config_router
from .schedule_config import router as schedule_config_router
from .snapshot import router as snapshot_router
from .ai_text_generation import router as ai_text_generation_router
from .performance_monitor import router as performance_monitor_router
from .agent import router as agent_router
from .agent_history import router as agent_history_router
from .speech import router as speech_router
from .stream_tasks import router as stream_tasks_router
from .safety_dashboard import router as safety_dashboard_router
from .alert_notifications import router as alert_notifications_router
from .agent_claude import router as agent_claude_router
from .daily_alerts_report import router as daily_alerts_report_router

# 创建主API路由器
# [DEPRECATED] 此路由器为旧版无版本前缀，保留向后兼容。
# 新客户端请使用 /api/v1/ 前缀（见 api/v1/__init__.py）。
api_router = APIRouter(prefix="/api")

# 注册子路由
api_router.include_router(prompts_router)
api_router.include_router(alerts_router)
api_router.include_router(streams_router)
api_router.include_router(video_streams_router)
api_router.include_router(stream_monitor_router)
api_router.include_router(ai_models_router)
api_router.include_router(ai_provider_configs_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(video_files_router)
api_router.include_router(analysis_results_router)
api_router.include_router(image_proxy_router)
api_router.include_router(realtime_streams_router)
api_router.include_router(mjpeg_stream_router)  # MJPEG方案（旧）
api_router.include_router(flv_stream_router)    # HTTP-FLV方案（新，无损）
api_router.include_router(roi_config_router)
api_router.include_router(schedule_config_router)
api_router.include_router(snapshot_router)
api_router.include_router(ai_text_generation_router)
api_router.include_router(performance_monitor_router)
api_router.include_router(agent_router)  # AI智能体分析助手
api_router.include_router(agent_history_router)  # AI智能体历史记录
api_router.include_router(speech_router)  # 语音识别服务(百度AI)
api_router.include_router(stream_tasks_router)  # 视频流分析任务管理
api_router.include_router(safety_dashboard_router)  # 安全监控大屏API
api_router.include_router(alert_notifications_router)  # 告警通知服务
api_router.include_router(agent_claude_router)  # Claude Agent (LLM + ES + Context Engineering)
api_router.include_router(daily_alerts_report_router)  # 每日预警报表(企业微信推送)

# 为了向后兼容，创建video路由别名
# 这样前端可以继续使用 /api/video/upload 等旧路径
from .video_compat import router as video_compat_router
api_router.include_router(video_compat_router)

__all__ = ["api_router"]