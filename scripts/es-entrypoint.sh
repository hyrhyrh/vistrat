#!/bin/bash
#
# Elasticsearch容器EntryPoint包装脚本
# 自动修复挂载目录权限,然后启动Elasticsearch
#

set -e

echo "🚀 Elasticsearch容器启动中..."

# 数据目录
DATA_DIR="/usr/share/elasticsearch/data"

# 检查并修复权限
if [ -d "$DATA_DIR" ]; then
    echo "🔧 检查数据目录权限: $DATA_DIR"

    # 获取当前目录所有者
    CURRENT_OWNER=$(stat -c '%u:%g' "$DATA_DIR" 2>/dev/null || echo "unknown")
    echo "   当前所有者: $CURRENT_OWNER"

    # 检查是否需要修复权限
    if [ "$CURRENT_OWNER" != "1000:0" ]; then
        echo "   ⚠️  权限不正确,尝试修复..."
        # 尝试修复权限(如果有权限的话)
        chown -R elasticsearch:root "$DATA_DIR" 2>/dev/null || {
            echo "   ⚠️  无法修复权限(这是正常的,如果已经是正确的用户)"
        }
    fi

    echo "✅ 权限检查完成"
else
    echo "📁 创建数据目录: $DATA_DIR"
    mkdir -p "$DATA_DIR"
    chown -R elasticsearch:root "$DATA_DIR"
fi

echo "🚀 启动Elasticsearch..."
echo ""

# 执行原始的Elasticsearch启动命令
exec /bin/tini -- /usr/local/bin/docker-entrypoint.sh "$@"
