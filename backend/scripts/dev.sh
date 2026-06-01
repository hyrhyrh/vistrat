#!/bin/bash
#
# 开发环境启动脚本
# 使用uvicorn with reload模式
#

set -e

# 脚本目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${BACKEND_DIR}"

echo "🚀 启动开发环境..."
echo "📂 工作目录: ${BACKEND_DIR}"
echo "⚙️  模式: Uvicorn with reload"
echo ""

# 设置开发环境变量
export ENV=development
export DEBUG=true

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: uv venv"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装/更新依赖
echo "📦 检查依赖..."
uv pip install -e .

echo ""
echo "✅ 依赖检查完成"
echo "🔄 启动Uvicorn服务器（reload模式）..."
echo ""

# 使用uvicorn启动，启用reload
uvicorn main:app \
    --host 0.0.0.0 \
    --port 16532 \
    --reload \
    --log-level debug \
    --reload-dir . \
    --reload-exclude "*.pyc" \
    --reload-exclude "__pycache__" \
    --reload-exclude ".git"
