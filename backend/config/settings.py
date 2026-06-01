"""
系统配置管理
统一管理所有配置项，支持环境变量覆盖
"""

import os
import logging
from typing import Dict, Any
from pathlib import Path
from core.secrets import read_secret

from core.constants import (
    DEFAULT_VIDEO_INTERVAL, DEFAULT_ANALYSIS_INTERVAL, DEFAULT_BUFFER_DURATION,
    DEFAULT_WS_RETRY_INTERVAL, DEFAULT_MAX_WS_QUEUE, DEFAULT_JPEG_QUALITY,
    DEFAULT_FRAME_SAMPLE_INTERVAL, DEFAULT_STREAM_FRAME_INTERVAL,
    DEFAULT_MAX_CONCURRENT_STREAMS, DEFAULT_MAX_CONCURRENT_AI_CALLS,
    DEFAULT_STREAM_BUFFER_BATCH_SIZE, DEFAULT_STREAM_BUFFER_FLUSH_INTERVAL,
    DEFAULT_FRAME_WARMUP_COUNT, DEFAULT_FRAME_QUALITY_MIN_SCORE, DEFAULT_FRAME_SHARPNESS_MIN,
    DEFAULT_TASK_HEALTH_CHECK_INTERVAL, DEFAULT_STREAM_HEALTH_CHECK_INTERVAL,
    DEFAULT_RETRY_DELAY_BASE, DEFAULT_MAX_RETRY_DELAY, DEFAULT_MAX_CONSECUTIVE_FAILURES,
    DEFAULT_REQUEST_TIMEOUT, DEFAULT_DB_POOL_SIZE, DEFAULT_DB_MAX_OVERFLOW,
    DEFAULT_DB_POOL_TIMEOUT, DEFAULT_DB_POOL_RECYCLE,
    DEFAULT_MAX_FILE_SIZE_MB, DEFAULT_CLEANUP_INTERVAL_HOURS, DEFAULT_FILE_RETENTION_DAYS,
)


class VideoConfig:
    """视频处理配置"""
    VIDEO_INTERVAL = int(os.getenv("VIDEO_INTERVAL", str(DEFAULT_VIDEO_INTERVAL)))  # 视频分段时长(秒)
    ANALYSIS_INTERVAL = int(os.getenv("ANALYSIS_INTERVAL", str(DEFAULT_ANALYSIS_INTERVAL)))  # 分析间隔(秒)
    BUFFER_DURATION = int(os.getenv("BUFFER_DURATION", str(DEFAULT_BUFFER_DURATION)))  # 滑窗分析时长
    WS_RETRY_INTERVAL = int(os.getenv("WS_RETRY_INTERVAL", str(DEFAULT_WS_RETRY_INTERVAL)))  # WebSocket重连间隔
    MAX_WS_QUEUE = int(os.getenv("MAX_WS_QUEUE", str(DEFAULT_MAX_WS_QUEUE)))  # 消息队列最大容量
    JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", str(DEFAULT_JPEG_QUALITY)))  # JPEG压缩质量
    FRAME_SAMPLE_INTERVAL = int(os.getenv("FRAME_SAMPLE_INTERVAL", str(DEFAULT_FRAME_SAMPLE_INTERVAL)))  # 帧采样间隔(秒)
    STREAM_FRAME_INTERVAL = int(os.getenv("STREAM_FRAME_INTERVAL", str(DEFAULT_STREAM_FRAME_INTERVAL)))  # 视频流抽帧间隔(秒)
    ENABLE_STREAM_AI_LOGGING = os.getenv("ENABLE_STREAM_AI_LOGGING", "true").lower() == "true"  # 是否启用实时流AI调用日志记录

    # 并发性能优化配置
    MAX_CONCURRENT_STREAMS = int(os.getenv("MAX_CONCURRENT_STREAMS", str(DEFAULT_MAX_CONCURRENT_STREAMS)))  # 最大并发流数
    MAX_CONCURRENT_AI_CALLS = int(os.getenv("MAX_CONCURRENT_AI_CALLS", str(DEFAULT_MAX_CONCURRENT_AI_CALLS)))  # 最大并发AI调用数
    STREAM_BUFFER_BATCH_SIZE = int(os.getenv("STREAM_BUFFER_BATCH_SIZE", str(DEFAULT_STREAM_BUFFER_BATCH_SIZE)))  # 流数据批量处理大小
    STREAM_BUFFER_FLUSH_INTERVAL = int(os.getenv("STREAM_BUFFER_FLUSH_INTERVAL", str(DEFAULT_STREAM_BUFFER_FLUSH_INTERVAL)))  # 流缓冲区刷新间隔(秒)

    # ✨ 企业级解码器配置（100%保证图片质量）
    USE_FFMPEG_DECODER = os.getenv("USE_FFMPEG_DECODER", "true").lower() == "true"  # 使用FFmpeg专业解码器
    FFMPEG_ONLY_KEYFRAMES = os.getenv("FFMPEG_ONLY_KEYFRAMES", "true").lower() == "true"  # 🔧 修复：只解码I帧（关键帧），100%清晰
    FRAME_WARMUP_COUNT = int(os.getenv("FRAME_WARMUP_COUNT", str(DEFAULT_FRAME_WARMUP_COUNT)))  # 预热帧数：丢弃前N帧
    FRAME_QUALITY_MIN_SCORE = float(os.getenv("FRAME_QUALITY_MIN_SCORE", str(DEFAULT_FRAME_QUALITY_MIN_SCORE)))  # 最低质量分数
    FRAME_SHARPNESS_MIN = float(os.getenv("FRAME_SHARPNESS_MIN", str(DEFAULT_FRAME_SHARPNESS_MIN)))  # 最低清晰度


class HealthMonitorConfig:
    """任务健康监控配置"""
    # 任务健康检查间隔（秒），默认5分钟
    TASK_HEALTH_CHECK_INTERVAL = int(os.getenv("TASK_HEALTH_CHECK_INTERVAL", str(DEFAULT_TASK_HEALTH_CHECK_INTERVAL)))

    # 视频流健康检查间隔（秒），默认10分钟
    STREAM_HEALTH_CHECK_INTERVAL = int(os.getenv("STREAM_HEALTH_CHECK_INTERVAL", str(DEFAULT_STREAM_HEALTH_CHECK_INTERVAL)))

    # 基础重试延迟（秒），默认5分钟
    RETRY_DELAY_BASE = int(os.getenv("RETRY_DELAY_BASE", str(DEFAULT_RETRY_DELAY_BASE)))

    # 最大重试延迟（秒），默认1小时
    MAX_RETRY_DELAY = int(os.getenv("MAX_RETRY_DELAY", str(DEFAULT_MAX_RETRY_DELAY)))

    # 最大连续失败次数，超过后延长重试间隔
    MAX_CONSECUTIVE_FAILURES = int(os.getenv("MAX_CONSECUTIVE_FAILURES", str(DEFAULT_MAX_CONSECUTIVE_FAILURES)))

    # 是否启用任务健康监控
    ENABLE_HEALTH_MONITOR = os.getenv("ENABLE_HEALTH_MONITOR", "true").lower() == "true"


class APIConfig:
    """
    API配置 - 安全增强版

    ⚠️ 安全注意事项:
    1. 所有API密钥必须通过环境变量配置，不提供默认值
    2. 请在 .env 文件中配置实际密钥（参考 .env.example）
    3. 确保 .env 文件已在 .gitignore 中，不会被提交到代码仓库
    """

    # Claude API配置 (OpenAI兼容格式)
    CLAUDE_API_KEY = read_secret("CLAUDE_API_KEY", "")  # 优先从 /run/secrets/ 读取
    CLAUDE_API_URL = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")

    # 通义千问API配置
    QWEN_API_KEY = read_secret("QWEN_API_KEY", "")  # 优先从 /run/secrets/ 读取
    QWEN_API_URL = os.getenv("QWEN_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-max")

    # Moonshot API配置
    MOONSHOT_API_KEY = read_secret("MOONSHOT_API_KEY", "")  # 优先从 /run/secrets/ 读取
    MOONSHOT_API_URL = os.getenv("MOONSHOT_API_URL", "https://api.moonshot.cn/v1/chat/completions")
    MOONSHOT_MODEL = os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k")

    # DeepSeek API配置
    DEEPSEEK_API_KEY = read_secret("DEEPSEEK_API_KEY", "")  # 优先从 /run/secrets/ 读取
    DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

    # API请求配置
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", str(DEFAULT_REQUEST_TIMEOUT)))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.5"))
    TOP_P = float(os.getenv("TOP_P", "0.01"))
    TOP_K = int(os.getenv("TOP_K", "20"))
    REPETITION_PENALTY = float(os.getenv("REPETITION_PENALTY", "1.05"))


class RAGConfig:
    """RAG系统配置"""
    ENABLE_RAG = os.getenv("ENABLE_RAG", "false").lower() == "true"
    VECTOR_API_URL = os.getenv("VECTOR_API_URL", "")
    HISTORY_FILE = os.getenv("HISTORY_FILE", "video_histroy_info.txt")


class StorageConfig:
    """MinIO存储配置"""
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    # Docker容器内网访问端点（供本地AI模型使用）
    # 使用MinIO容器IP而非hostname，避免MinIO的hostname验证限制
    # MinIO要求配置MINIO_SERVER_URL才能正确处理自定义hostname
    MINIO_INTERNAL_ENDPOINT = os.getenv("MINIO_INTERNAL_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY = read_secret("MINIO_ACCESS_KEY", "")  # 优先从 /run/secrets/ 读取
    MINIO_SECRET_KEY = read_secret("MINIO_SECRET_KEY", "")  # 优先从 /run/secrets/ 读取
    MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
    MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")
    
    # 存储桶配置（使用multi前缀区分）
    VIDEO_BUCKET = os.getenv("VIDEO_BUCKET", "multi-videos")
    IMAGE_BUCKET = os.getenv("IMAGE_BUCKET", "multi-images")
    THUMBNAIL_BUCKET = os.getenv("THUMBNAIL_BUCKET", "multi-thumbnails")
    ANNOTATION_BUCKET = os.getenv("ANNOTATION_BUCKET", "multi-annotations")
    
    # 文件管理
    MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", str(DEFAULT_MAX_FILE_SIZE_MB)))
    CLEANUP_INTERVAL_HOURS = int(os.getenv("CLEANUP_INTERVAL_HOURS", str(DEFAULT_CLEANUP_INTERVAL_HOURS)))
    FILE_RETENTION_DAYS = int(os.getenv("FILE_RETENTION_DAYS", str(DEFAULT_FILE_RETENTION_DAYS)))


class ServerConfig:
    """服务器配置"""
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "16532"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    RELOAD = os.getenv("RELOAD", "false").lower() == "true"
    WORKERS = int(os.getenv("WORKERS", "1"))

    # 公网访问配置
    # 用于生成可公网访问的图片代理URL
    # 格式: http://公网IP:端口 或 https://域名
    # 示例: http://<INTERNAL_HOST>:16532 或 https://your-domain.com
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://localhost:{PORT}")


class PathConfig:
    """路径配置"""
    ROOT_DIR = Path(__file__).parent.parent  # /app (容器中的工作目录)
    BACKEND_DIR = ROOT_DIR  # 在容器中，backend就是/app目录
    
    # 应用数据目录
    UPLOAD_DIR = BACKEND_DIR / "uploads"
    WARNING_DIR = BACKEND_DIR / "video_warning"
    ARCHIVE_DIR = BACKEND_DIR / "archive"
    TEMP_DIR = BACKEND_DIR / "temp"
    LOGS_DIR = BACKEND_DIR / "logs"
    DATA_DIR = BACKEND_DIR / "data"

    # HLS流媒体临时目录（跨平台兼容）
    HLS_STREAMS_DIR = TEMP_DIR / "hls_streams"
    
    # 数据子目录
    DATA_PROMPTS_DIR = DATA_DIR / "prompts"
    DATA_VIDEOS_DIR = DATA_DIR / "videos"
    
    # 配置文件
    TEMPLATES_FILE = BACKEND_DIR / "templates.json"
    
    @classmethod
    def ensure_directories(cls):
        """确保所有必需目录存在"""
        # 创建所有以_DIR结尾的目录
        for attr_name in dir(cls):
            if attr_name.endswith('_DIR'):
                attr = getattr(cls, attr_name)
                if isinstance(attr, Path):
                    attr.mkdir(parents=True, exist_ok=True)
                    print(f"✅ 目录已创建: {attr}")
        
        # 确保日志文件存在
        log_files = [
            cls.LOGS_DIR / "aiwatch.log",
            cls.LOGS_DIR / "error.log"
        ]
        for log_file in log_files:
            log_file.touch(exist_ok=True)
            print(f"✅ 日志文件已创建: {log_file}")


class DatabaseConfig:
    """数据库配置"""
    # PostgreSQL配置（使用multi_前缀区分）
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "vision_db")
    DB_USER = os.getenv("DB_USER", "vision")
    DB_PASSWORD = read_secret("DB_PASSWORD", "vision123")  # 优先从 /run/secrets/ 读取
    
    # 连接池配置 - 性能优化: 提升连接池容量支持更高并发
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", str(DEFAULT_DB_POOL_SIZE)))  # 核心连接池大小
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", str(DEFAULT_DB_MAX_OVERFLOW)))  # 最大溢出连接数
    DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", str(DEFAULT_DB_POOL_TIMEOUT)))  # 获取连接超时（秒）
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", str(DEFAULT_DB_POOL_RECYCLE)))  # 连接回收时间（秒）
    DB_POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"  # 启用连接健康检查
    
    @classmethod
    def get_database_url(cls) -> str:
        """获取数据库连接URL（asyncpg驱动）"""
        return f"postgresql+asyncpg://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"

    @classmethod
    def get_sync_database_url(cls) -> str:
        """获取同步数据库连接URL（psycopg 3驱动，用于数据库初始化）"""
        return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"


class RedisConfig:
    """Redis缓存配置"""
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD = read_secret("REDIS_PASSWORD", "")  # 优先从 /run/secrets/ 读取
    REDIS_DB = int(os.getenv("REDIS_DB", "2"))  # 使用数据库2区分
    REDIS_PREFIX = os.getenv("REDIS_PREFIX", "multi_watchdog:")  # 使用前缀区分

    @classmethod
    def get_redis_url(cls) -> str:
        """获取Redis连接URL"""
        if cls.REDIS_PASSWORD:
            return f"redis://:{cls.REDIS_PASSWORD}@{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"
        return f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/{cls.REDIS_DB}"


class ElasticsearchConfig:
    """Elasticsearch配置"""
    ES_HOST = os.getenv("ES_HOST", "localhost")
    ES_PORT = int(os.getenv("ES_PORT", "9200"))
    ES_USERNAME = os.getenv("ES_USERNAME", "")
    ES_PASSWORD = read_secret("ES_PASSWORD", "")  # 优先从 /run/secrets/ 读取
    ES_SSL = os.getenv("ES_SSL", "false").lower() == "true"

    # 索引配置
    ANALYSIS_RESULTS_INDEX = os.getenv("ES_ANALYSIS_INDEX", "video_analysis_results")
    FRAME_RESULTS_INDEX = os.getenv("ES_FRAME_INDEX", "video_frame_results")
    ALERTS_INDEX = os.getenv("ES_ALERTS_INDEX", "video_alerts")

    @classmethod
    def get_es_url(cls) -> str:
        """获取Elasticsearch连接URL"""
        protocol = "https" if cls.ES_SSL else "http"
        return f"{protocol}://{cls.ES_HOST}:{cls.ES_PORT}"


class MediaMTXConfig:
    """mediamtx 流媒体服务配置

    mediamtx 以 Docker sidecar 形式运行，负责 RTSP 拉流 + HLS 分发 + 滚动录制。
    仅定义实际被引用的字段，避免无用配置膨胀。
    """
    HOST: str = os.getenv("MEDIAMTX_HOST", "localhost")
    API_PORT: int = int(os.getenv("MEDIAMTX_API_PORT", "9997"))
    HLS_PORT: int = int(os.getenv("MEDIAMTX_HLS_PORT", "8888"))

    # 容器内录制根目录（与 docker-compose 挂载点一致）
    RECORDING_ROOT: str = os.getenv("MEDIAMTX_RECORDING_ROOT", "/recordings")
    # 单 segment 时长（秒），需与 mediamtx.yml recordSegmentDuration 对齐
    RECORD_SEGMENT_DURATION: int = int(os.getenv("MEDIAMTX_SEGMENT_DURATION", "10"))

    # 片段裁剪窗口
    CLIP_PRE_SECONDS: int = int(os.getenv("CLIP_PRE_SECONDS", "5"))
    CLIP_POST_SECONDS: int = int(os.getenv("CLIP_POST_SECONDS", "10"))

    @classmethod
    def get_api_url(cls) -> str:
        """mediamtx Control API 基地址"""
        return os.getenv("MEDIAMTX_API_URL", f"http://{cls.HOST}:{cls.API_PORT}")

    @classmethod
    def get_hls_url(cls, path_name: str) -> str:
        """HLS 播放地址（路径名对应 add_path 注册时的 name）"""
        base = os.getenv("MEDIAMTX_HLS_BASE_URL", f"http://{cls.HOST}:{cls.HLS_PORT}")
        return f"{base}/{path_name}/index.m3u8"


class InferenceConfig:
    """Vistrat 推理服务（A100 中台）配置

    主后端作为 CPU 服务器，通过 HTTP 调用 A100 推理服务完成 VLM+DINO 检测。
    当推理服务不可达时，走降级路径（本地 ai_client 仅文字解析）。
    """
    ENABLED: bool = os.getenv("INFERENCE_ENABLED", "true").lower() == "true"
    BASE_URL: str = os.getenv("INFERENCE_BASE_URL", "http://localhost:8100")
    API_KEY: str = os.getenv("INFERENCE_API_KEY", "")
    TIMEOUT: int = int(os.getenv("INFERENCE_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("INFERENCE_MAX_RETRIES", "2"))

    # 熔断参数：30 秒窗口内失败 >= 5 次 → 开启熔断 60 秒
    BREAKER_WINDOW_SECONDS: int = int(os.getenv("INFERENCE_BREAKER_WINDOW", "30"))
    BREAKER_FAIL_THRESHOLD: int = int(os.getenv("INFERENCE_BREAKER_THRESHOLD", "5"))
    BREAKER_COOLDOWN_SECONDS: int = int(os.getenv("INFERENCE_BREAKER_COOLDOWN", "60"))

    # MinIO 预签名 URL 过期时间（秒），供 A100 拉取帧图片
    PRESIGNED_EXPIRES_SECONDS: int = int(os.getenv("INFERENCE_PRESIGNED_EXPIRES", "900"))


class LogConfig:
    """日志配置"""
    LEVEL = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
    FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    @classmethod
    def get_handlers(cls):
        """获取日志处理器"""
        handlers = [logging.StreamHandler()]
        
        log_file = os.getenv("LOG_FILE")
        if log_file:
            handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
            
        return handlers


def update_config(args: Dict[str, Any]) -> None:
    """动态更新配置"""
    for key, value in args.items():
        if hasattr(VideoConfig, key.upper()):
            setattr(VideoConfig, key.upper(), value)
        elif hasattr(ServerConfig, key.upper()):
            setattr(ServerConfig, key.upper(), value)


# 注意：目录初始化由main.py的lifespan函数负责
# 避免在模块导入时自动执行，导致重复创建日志