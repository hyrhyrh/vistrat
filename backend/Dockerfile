# ================== 多阶段构建 ==================
# 第一阶段：构建环境（包含编译工具）
FROM python:3.10-slim AS builder

# 设置工作目录
WORKDIR /app

# 安装构建依赖（编译工具和库）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 编译工具（仅构建阶段需要）
    gcc \
    g++ \
    make \
    pkg-config \
    # OpenCV编译依赖
    libgl1-mesa-dev \
    libglib2.0-dev \
    # PostgreSQL客户端库开发包
    libpq-dev \
    # 网络工具
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 安装uv包管理器（优化网络连接）
RUN curl -fsSL https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 复制依赖文件
COPY pyproject.toml ./

# 创建虚拟环境并安装依赖（使用完整路径）
RUN /root/.local/bin/uv venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# 安装生产依赖（排除开发依赖）
RUN /root/.local/bin/uv pip install --no-cache-dir -e .

# ================== 第二阶段：运行环境（最小化） ==================
FROM python:3.10-slim AS runtime

# 设置工作目录
WORKDIR /app

# 只安装运行时必需的系统库（不包含编译工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV运行时依赖
    libgl1 \
    libgl1-mesa-dri \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgthread-2.0-0 \
    libfontconfig1 \
    libfreetype6 \
    libgtk-3-0 \
    # PostgreSQL客户端库（运行时）
    libpq5 \
    # 健康检查工具
    curl \
    # 进程管理
    procps \
    # gosu - 用于安全降权(替代su)
    gosu \
    # ✨ FFmpeg - RTSP流处理和FLV转换核心依赖
    ffmpeg \
    # RTSP流处理依赖
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# 从构建阶段复制已安装的Python包
COPY --from=builder /app/.venv /app/.venv

# 设置Python环境变量
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 设置生产环境变量
ENV ENV=production
ENV DEBUG=false
ENV RELOAD=false

# 修复OpenBLAS线程创建问题（Docker容器安全限制）
# 限制为1个线程避免pthread_create权限错误
ENV OPENBLAS_NUM_THREADS=1
ENV OMP_NUM_THREADS=1

# 复制应用源代码（.dockerignore会过滤不需要的文件）
COPY . .

# 复制entrypoint脚本
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

# 创建非root用户（gosu会用到）并设置脚本权限
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && chmod +x /usr/local/bin/entrypoint.sh \
    && chown -R appuser:appuser /app

# 暴露应用端口
EXPOSE 16532

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:16532/health || exit 1

# 设置entrypoint(以root运行,处理卷挂载权限)
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# 🔧 设置默认命令：生产环境使用gunicorn
# 由entrypoint以appuser身份执行
CMD ["gunicorn", "-c", "gunicorn.conf.py", "main:app"]