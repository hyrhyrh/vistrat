"""
Gunicorn生产环境配置文件
使用Uvicorn Worker提供异步支持
"""

import multiprocessing
import os

# ==================== 服务器套接字 ====================
bind = f"0.0.0.0:{os.getenv('PORT', '16532')}"
backlog = 2048

# ==================== Worker进程 ====================
# Worker类型：使用uvicorn的异步worker
worker_class = "uvicorn.workers.UvicornWorker"

# Worker数量：CPU核心数 * 2 + 1（推荐公式）
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# 每个Worker的线程数（异步worker不需要threads，设置为1）
threads = 1

# Worker超时时间（秒）
timeout = 120  # 2分钟（AI分析可能较慢）
keepalive = 5

# ==================== 进程管理 ====================
# 最大请求数（防止内存泄漏）
max_requests = 1000
max_requests_jitter = 50

# 优雅重启超时
graceful_timeout = 30

# ==================== 日志配置 ====================
# 访问日志格式
accesslog = "-"  # 输出到stdout
errorlog = "-"   # 输出到stderr

# 日志级别
loglevel = os.getenv("LOG_LEVEL", "info")

# 访问日志格式（包含响应时间）
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ==================== 服务器机制 ====================
# 守护进程
daemon = False  # Docker环境不需要daemon

# PID文件
pidfile = None  # Docker环境不需要pidfile

# 用户和组（Docker中由entrypoint处理）
user = None
group = None

# umask
umask = 0

# 临时目录
tmp_upload_dir = None

# ==================== SSL配置 ====================
# keyfile = '/path/to/keyfile'
# certfile = '/path/to/certfile'

# ==================== 预加载 ====================
# 预加载应用代码（提高启动速度，但会增加内存）
preload_app = True

# ==================== Worker连接 ====================
# Worker重启前的最大客户端连接数
worker_connections = 1000

# ==================== 事件循环 ====================
# Uvicorn worker配置
uvicorn_loop = os.getenv("UVICORN_LOOP", "auto")  # auto会自动选择最优循环（uvloop或asyncio）

# ==================== 钩子函数 ====================
def on_starting(server):
    """服务器启动时调用"""
    print("🚀 Gunicorn服务器启动中...")
    print(f"📊 配置: {workers} workers, {worker_class}")
    print(f"🌐 监听: {bind}")


def when_ready(server):
    """服务器就绪时调用"""
    print("✅ Gunicorn服务器已就绪")


def on_reload(server):
    """代码重载时调用"""
    print("🔄 Gunicorn服务器重载中...")


def worker_int(worker):
    """Worker被中断时调用"""
    print(f"⚠️ Worker {worker.pid} 被中断")


def pre_fork(server, worker):
    """Worker fork之前调用"""
    pass


def post_fork(server, worker):
    """Worker fork之后调用"""
    print(f"👷 Worker {worker.pid} 已启动")


def post_worker_init(worker):
    """Worker初始化完成后调用"""
    pass


def worker_exit(server, worker):
    """Worker退出时调用"""
    print(f"👋 Worker {worker.pid} 已退出")


def pre_exec(server):
    """exec新进程之前调用"""
    pass


def pre_request(worker, req):
    """处理请求之前调用"""
    pass


def post_request(worker, req, environ, resp):
    """处理请求之后调用"""
    pass


def child_exit(server, worker):
    """子进程退出时调用"""
    pass


def nworkers_changed(server, new_value, old_value):
    """Worker数量变化时调用"""
    print(f"📊 Worker数量变化: {old_value} -> {new_value}")


def on_exit(server):
    """服务器退出时调用"""
    print("🛑 Gunicorn服务器已关闭")
