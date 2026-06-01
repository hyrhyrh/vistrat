#!/bin/bash
#
# 生产环境启动脚本
# 使用gunicorn + uvicorn worker
#

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

echo "🚀 启动生产环境..."
echo "📂 工作目录: ${BACKEND_DIR}"
echo "⚙️  模式: Gunicorn + Uvicorn Worker"
echo ""

# 设置生产环境变量
export ENV=production
export DEBUG=false

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: uv venv"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查gunicorn是否安装
if ! command -v gunicorn &> /dev/null; then
    echo "❌ gunicorn未安装，请先运行: uv pip install -e ."
    exit 1
fi

# 计算Worker数量（CPU核心数 * 2 + 1）
WORKERS=${GUNICORN_WORKERS:-$(($(nproc) * 2 + 1))}
export GUNICORN_WORKERS=${WORKERS}

echo "📊 配置信息:"
echo "   Workers: ${WORKERS}"
echo "   端口: 16532"
echo "   日志级别: info"
echo ""
echo "✅ 启动Gunicorn服务器..."
echo ""

# 使用gunicorn启动
gunicorn -c gunicorn.conf.py main:app
