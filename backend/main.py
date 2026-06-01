"""
AI监控系统主入口文件
提供统一的应用启动入口，支持FastAPI服务和WebSocket连接
"""

import sys
import io
# Windows控制台UTF-8编码修复 — 避免emoji字符输出时GBK编码崩溃
if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    pass  # 非标准stdout(如重定向)不处理
elif sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import warnings
# 抑制Pydantic v2中model_字段与保护命名空间冲突的警告
warnings.filterwarnings("ignore", message="Field.*has conflict with protected namespace.*model_.*", category=UserWarning)

# 加载.env环境变量(必须在导入其他模块前)
from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import sys
import platform

# ============ 跨平台事件循环策略配置 ============
# 检测平台和架构，选择最优事件循环
def detect_platform_and_loop() -> tuple[str, str]:
    """
    检测平台架构并返回合适的事件循环类型

    Returns:
        (platform_info, loop_type): 平台信息和事件循环类型
        - Windows: ("Windows x64", "asyncio")
        - Linux x86_64: ("Linux x86_64", "auto")  # uvloop高性能
        - Linux ARM: ("Linux ARM64", "asyncio")   # 兼容性优先
    """
    system = platform.system()
    machine = platform.machine().lower()

    # Windows: 必须使用asyncio + SelectorEventLoop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        return f"Windows {machine.upper()}", "asyncio"

    # Linux/Unix: 根据架构选择
    if system == "Linux":
        # ARM架构: 使用asyncio避免uvloop兼容性问题
        if "aarch64" in machine or "arm" in machine:
            return f"Linux {machine.upper()}", "asyncio"
        # x86_64: 使用uvloop高性能事件循环
        else:
            return f"Linux {machine.upper()}", "auto"

    # 其他平台: 默认auto
    return f"{system} {machine}", "auto"

PLATFORM_INFO, EVENT_LOOP_TYPE = detect_platform_and_loop()
print(f"✅ 平台检测: {PLATFORM_INFO}, 事件循环: {EVENT_LOOP_TYPE}")

import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from api import api_router
from api.v1 import v1_router
from api.analysis_results import router as analysis_results_router
from api.ai_model_management import router as ai_model_router
from api.stream_tasks import router as stream_tasks_router
from api.safety_dashboard import router as safety_dashboard_router
from api.metrics import router as metrics_router
from api.alert_notifications import router as alert_notifications_router
from api.video_streams_ws import router as video_streams_ws_router
from api.task_health import router as task_health_router
from services.flv_stream_service import router as flv_stream_router
from core.alert_service import AlertService
from core.error_handlers import register_error_handlers
from core.logging_config import get_logger_context
from config.settings import ServerConfig, PathConfig
from services.storage import StorageService
from services.auth_service import AuthService
from database.connection import DatabaseManager, init_database

# 使用统一的日志系统
logger_ctx = get_logger_context(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger_ctx.info("AI监控系统启动中...")

    # 确保所有必要目录存在
    PathConfig.ensure_directories()
    
    # 初始化数据库连接
    try:
        await DatabaseManager.initialize()
        logger_ctx.info("✅ 数据库连接初始化成功")

        # 创建数据库表结构
        logger_ctx.info("🔄 开始初始化数据库表结构...")
        await init_database()
        logger_ctx.info("✅ 数据库表结构初始化完成")

        # 初始化stream_analysis_tasks表
        logger_ctx.info("🔄 开始初始化流任务表...")
        from database.init_stream_tasks import ensure_stream_tasks_table
        await ensure_stream_tasks_table()
        logger_ctx.info("✅ 流任务表初始化完成")

        # 初始化管理员用户
        logger_ctx.info("🔄 开始初始化管理员用户...")
        await AuthService.init_admin_user()
        logger_ctx.info("✅ 管理员用户初始化完成")

        # 初始化任务管理器
        logger_ctx.info("🔄 开始初始化任务管理器...")
        from services.stream_task_manager import stream_task_manager
        await stream_task_manager.initialize()
        logger_ctx.info("✅ 任务管理器初始化完成")

        # 执行任务自动恢复（后台异步执行，不阻塞应用启动）
        logger_ctx.info("🔄 启动任务自动恢复（后台异步）...")
        asyncio.create_task(stream_task_manager.auto_recover_tasks())
        logger_ctx.info("✅ 任务自动恢复已在后台启动")

        # 启动性能指标收集器
        logger_ctx.info("🔄 开始启动性能指标收集器...")
        from services.metrics_collector import metrics_collector
        await metrics_collector.start()
        logger_ctx.info("✅ 性能指标收集器已启动")

        # 启动 Vistrat 推理客户端（A100 Tier 2）
        try:
            from services.inference_client import inference_client
            from config.settings import InferenceConfig
            if InferenceConfig.ENABLED:
                await inference_client.startup()
                logger_ctx.info(f"✅ 推理客户端已启动: {InferenceConfig.BASE_URL}")
            else:
                logger_ctx.info("⚠️  推理客户端已禁用（INFERENCE_ENABLED=false）")
        except Exception as e:
            logger_ctx.warning(f"推理客户端启动失败（将走降级路径）: {e}")

        # 启动告警通知服务
        logger_ctx.info("🔄 开始启动告警通知服务...")
        from services.alert_notification_service import alert_notification_service
        await alert_notification_service.initialize()
        await alert_notification_service.start()
        logger_ctx.info("✅ 告警通知服务已启动")

        # 启动任务健康监控服务
        from config.settings import HealthMonitorConfig
        if HealthMonitorConfig.ENABLE_HEALTH_MONITOR:
            logger_ctx.info("🔄 开始启动任务健康监控服务...")
            from services.task_health_monitor import task_health_monitor
            # 使用配置初始化监控器
            task_health_monitor.check_interval = HealthMonitorConfig.TASK_HEALTH_CHECK_INTERVAL
            task_health_monitor.stream_check_interval = HealthMonitorConfig.STREAM_HEALTH_CHECK_INTERVAL
            task_health_monitor.retry_delay_base = HealthMonitorConfig.RETRY_DELAY_BASE
            task_health_monitor.max_retry_delay = HealthMonitorConfig.MAX_RETRY_DELAY
            task_health_monitor.max_consecutive_failures = HealthMonitorConfig.MAX_CONSECUTIVE_FAILURES
            await task_health_monitor.start()
            logger_ctx.info("✅ 任务健康监控服务已启动")
        else:
            logger_ctx.info("⚠️  任务健康监控已禁用（通过ENABLE_HEALTH_MONITOR=false）")

    except Exception as e:
        logger_ctx.error("❌ 初始化失败", exception=e)
        import traceback
        logger_ctx.error(f"详细错误: {traceback.format_exc()}")
        # 继续启动但不退出，让服务可以部分运行

    # 清理临时文件
    StorageService.cleanup_temp_files()

    logger_ctx.info("AI监控系统启动完成")
    yield
    
    # 关闭时清理
    logger_ctx.info("AI监控系统关闭中...")

    # 停止任务健康监控服务
    try:
        from services.task_health_monitor import task_health_monitor
        await task_health_monitor.stop()
        logger_ctx.info("✅ 任务健康监控服务已停止")
    except Exception as e:
        logger_ctx.warning(f"停止任务健康监控失败: {e}")

    # 停止推理客户端
    try:
        from services.inference_client import inference_client
        await inference_client.shutdown()
    except Exception as e:
        logger_ctx.warning(f"推理客户端关闭失败: {e}")

    # 停止告警通知服务
    from services.alert_notification_service import alert_notification_service
    await alert_notification_service.stop()

    # 停止性能指标收集器
    from services.metrics_collector import metrics_collector
    await metrics_collector.stop()

    await DatabaseManager.close()
    StorageService.cleanup_temp_files()
    logger_ctx.info("AI监控系统已关闭")


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title="Vistrat（观策）· 智能视频监控预警系统",
        description="Vistrat = 观（多模态感知）+ 策（策略与主动预警）。基于多模态 AI 的视频监控分析系统",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # 配置CORS中间件
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3009").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    )
    
    # 注册错误处理器
    register_error_handlers(app)

    # ============================================================
    # API 版本控制策略
    # ============================================================
    # 1. /api/v1/xxx — 正式版本化路由（推荐使用）
    # 2. /api/xxx    — 旧路由（向后兼容，标记为 deprecated，未来版本可能移除）
    #
    # 新客户端应使用 /api/v1/ 前缀。旧客户端使用 /api/ 前缀仍可正常工作。
    # 创建 v2 时，新增 api/v2/__init__.py 并注册 prefix="/api/v2" 即可。
    # ============================================================

    # --- v1 版本化路由（推荐） ---
    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])

    # --- 旧路由（向后兼容，deprecated） ---
    app.include_router(api_router)  # /api/xxx 旧路径，保持向后兼容
    app.include_router(analysis_results_router)
    app.include_router(ai_model_router)
    app.include_router(stream_tasks_router)
    app.include_router(safety_dashboard_router)
    app.include_router(metrics_router)
    app.include_router(alert_notifications_router)
    app.include_router(video_streams_ws_router)  # WebSocket路由
    app.include_router(task_health_router)  # 任务健康监控路由
    app.include_router(flv_stream_router, prefix="/api")  # HTTP-FLV流媒体路由

    # --- API 版本响应头中间件 ---
    # 为所有 /api/v1/ 响应添加 X-API-Version header
    class APIVersionHeaderMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            if request.url.path.startswith("/api/v1/"):
                response.headers["X-API-Version"] = "v1"
            return response

    app.add_middleware(APIVersionHeaderMiddleware)
    
    # 静态文件服务
    if PathConfig.WARNING_DIR.exists():
        app.mount("/files", StaticFiles(directory=str(PathConfig.WARNING_DIR)), name="files")
    
    # 上传文件静态服务
    if PathConfig.UPLOAD_DIR.exists():
        app.mount("/uploads", StaticFiles(directory=str(PathConfig.UPLOAD_DIR)), name="uploads")
    
    return app


# 创建应用实例
app = create_app()


@app.websocket("/alerts")
async def websocket_alerts(websocket: WebSocket, token: str = None):
    """告警WebSocket端点，支持通过query parameter传递token认证

    使用方式: ws://host/alerts?token=your_jwt_token
    """
    registered = await AlertService.register(websocket, token=token)
    if not registered:
        return
    try:
        while True:
            # 保持连接活跃
            await websocket.receive_text()
    except WebSocketDisconnect:
        await AlertService.unregister(websocket)
    except Exception as e:
        logger_ctx.error("WebSocket告警连接异常", exception=e)
        await AlertService.unregister(websocket)


@app.websocket("/video_feed")
async def websocket_video_feed(websocket: WebSocket):
    """视频流WebSocket端点"""
    await websocket.accept()
    try:
        # 这里可以添加实时视频流推送逻辑
        while True:
            await asyncio.sleep(1)
            # 发送心跳包
            import time
            await websocket.send_json({"type": "heartbeat", "timestamp": time.time()})
    except WebSocketDisconnect:
        logger_ctx.info("视频流WebSocket连接已断开")
    except Exception as e:
        logger_ctx.error("视频流WebSocket连接异常", exception=e)


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "message": "Vistrat（观策）· 智能视频监控预警系统",
        "status": "running",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    import time
    return {
        "status": "healthy",
        "timestamp": time.time()
    }


@app.get("/api/placeholder-alert.jpg")
async def placeholder_alert_image():
    """告警占位图片"""
    from fastapi.responses import Response
    import base64
    
    # 简单的1x1像素透明PNG图片
    placeholder_data = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    
    return Response(content=placeholder_data, media_type="image/png")


def configure_logging():
    """配置日志和环境变量"""
    import logging
    import cv2
    import os

    # 判断环境
    is_production = os.getenv("ENV", "development").lower() == "production"

    # 设置OpenCV日志级别，屏蔽FFmpeg H264解码警告
    try:
        if hasattr(cv2, 'LOG_LEVEL_ERROR'):
            cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)
        elif hasattr(cv2, 'LOG_LEVEL_SILENT'):
            cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
        else:
            cv2.setLogLevel(2)  # ERROR级别
    except Exception as e:
        logger_ctx.warning(f"无法设置OpenCV日志级别: {e}")

    # 设置FFmpeg环境变量屏蔽详细日志
    os.environ['OPENCV_LOG_LEVEL'] = 'ERROR'
    os.environ['OPENCV_FFMPEG_LOGLEVEL'] = '-8'  # 静默模式

    if is_production:
        # 生产环境：禁用不必要的第三方库日志
        logging.getLogger("watchfiles.main").setLevel(logging.WARNING)
        logging.getLogger("watchfiles").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
    else:
        # 开发环境：屏蔽FFmpeg警告
        logging.getLogger("libav").setLevel(logging.ERROR)
        logging.getLogger("ffmpeg").setLevel(logging.ERROR)

    return is_production


def is_pycharm_debugger() -> bool:
    """检测是否在PyCharm调试器中运行"""
    return 'pydevd' in sys.modules or 'PYCHARM_HOSTED' in os.environ


def main():
    """
    主函数入口

    用于开发环境直接运行：python main.py
    生产环境应使用gunicorn: gunicorn -c gunicorn.conf.py main:app
    """
    try:
        import os

        # 配置日志
        is_production = configure_logging()
        logger_ctx.info(f"🚀 启动模式: {'生产' if is_production else '开发'}环境")

        # 开发环境：使用uvicorn with reload
        # 生产环境：给出提示（应使用gunicorn）
        if is_production:
            logger_ctx.warning(
                "⚠️ 检测到生产环境，建议使用Gunicorn启动:\n"
                "   gunicorn -c gunicorn.conf.py main:app"
            )

        logger_ctx.set_context(
            host=ServerConfig.HOST,
            port=ServerConfig.PORT
        ).info("启动Uvicorn服务器")

        # Uvicorn配置
        uvicorn_config = uvicorn.Config(
            app="main:app",
            host=ServerConfig.HOST,
            port=ServerConfig.PORT,
            reload=ServerConfig.DEBUG and not is_production,  # 开发环境启用reload
            log_level="info" if is_production else ("debug" if ServerConfig.DEBUG else "info"),
            loop=EVENT_LOOP_TYPE,  # 智能选择事件循环
        )

        server = uvicorn.Server(uvicorn_config)

        # ============ Windows + PyCharm调试器兼容性处理 ============
        if sys.platform == 'win32':
            # 确保Windows事件循环策略在asyncio.run之前生效
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

            # 检测PyCharm调试器
            if is_pycharm_debugger():
                logger_ctx.warning("🔧 检测到PyCharm调试器，使用兼容模式启动")
                # PyCharm调试器模式：手动创建事件循环（避免asyncio.run()冲突）
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(server.serve())
                finally:
                    try:
                        # 清理pending tasks
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    except Exception:
                        pass
                    loop.close()
            else:
                # 非调试模式：使用标准asyncio.run()
                asyncio.run(server.serve())
        else:
            # 非Windows平台：使用标准asyncio.run()
            asyncio.run(server.serve())

    except KeyboardInterrupt:
        logger_ctx.info("收到停止信号，正在关闭服务器...")
    except Exception as e:
        logger_ctx.error("服务器启动失败", exception=e)
        raise


# ==================== 应用启动配置 ====================
# 配置日志（import时执行，确保gunicorn worker也能正确配置）
configure_logging()


if __name__ == "__main__":
    # 直接运行：python main.py（开发模式）
    main()