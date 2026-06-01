#!/bin/bash
#
# 存储目录初始化脚本
# 用于在首次部署或重新部署时自动创建和配置存储目录权限
#

set -e

echo "======================================"
echo "📂 初始化存储目录结构和权限"
echo "======================================"

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STORAGE_DIR="${PROJECT_ROOT}/storage"

echo "项目根目录: ${PROJECT_ROOT}"
echo "存储目录: ${STORAGE_DIR}"

# 创建所有必需的存储目录
echo ""
echo "🔧 创建存储目录..."
mkdir -p "${STORAGE_DIR}/postgres"
mkdir -p "${STORAGE_DIR}/elasticsearch"
mkdir -p "${STORAGE_DIR}/redis"
mkdir -p "${STORAGE_DIR}/minio"
mkdir -p "${STORAGE_DIR}/uploads"
mkdir -p "${STORAGE_DIR}/data/prompts"
mkdir -p "${STORAGE_DIR}/logs"
mkdir -p "${STORAGE_DIR}/video_warning"
mkdir -p "${STORAGE_DIR}/archive"

echo "✅ 目录创建完成"

# 设置Elasticsearch目录权限 (UID:GID = 1000:1000)
echo ""
echo "🔧 配置Elasticsearch目录权限..."
if [ -d "${STORAGE_DIR}/elasticsearch" ]; then
    sudo chown -R 1000:1000 "${STORAGE_DIR}/elasticsearch"
    chmod -R 755 "${STORAGE_DIR}/elasticsearch"
    echo "✅ Elasticsearch权限设置完成 (1000:1000)"
fi

# 设置PostgreSQL目录权限 (UID:GID = 999:999)
echo ""
echo "🔧 配置PostgreSQL目录权限..."
if [ -d "${STORAGE_DIR}/postgres" ]; then
    sudo chown -R 999:999 "${STORAGE_DIR}/postgres"
    chmod -R 700 "${STORAGE_DIR}/postgres"
    echo "✅ PostgreSQL权限设置完成 (999:999)"
fi

# 设置Redis目录权限 (UID:GID = 999:999)
echo ""
echo "🔧 配置Redis目录权限..."
if [ -d "${STORAGE_DIR}/redis" ]; then
    sudo chown -R 999:999 "${STORAGE_DIR}/redis"
    chmod -R 755 "${STORAGE_DIR}/redis"
    echo "✅ Redis权限设置完成 (999:999)"
fi

# 设置MinIO目录权限 (UID:GID = 1000:1000)
echo ""
echo "🔧 配置MinIO目录权限..."
if [ -d "${STORAGE_DIR}/minio" ]; then
    sudo chown -R 1000:1000 "${STORAGE_DIR}/minio"
    chmod -R 755 "${STORAGE_DIR}/minio"
    echo "✅ MinIO权限设置完成 (1000:1000)"
fi

# 设置后端应用目录权限 (确保可读写)
echo ""
echo "🔧 配置后端应用目录权限..."
for dir in uploads data logs video_warning archive; do
    if [ -d "${STORAGE_DIR}/${dir}" ]; then
        sudo chown -R 1000:1000 "${STORAGE_DIR}/${dir}"
        chmod -R 755 "${STORAGE_DIR}/${dir}"
    fi
done
echo "✅ 后端应用目录权限设置完成"

# 显示目录权限摘要
echo ""
echo "======================================"
echo "📊 权限配置摘要"
echo "======================================"
ls -la "${STORAGE_DIR}/" | grep -E "postgres|elasticsearch|redis|minio|uploads|data|logs"

echo ""
echo "======================================"
echo "✅ 存储目录初始化完成!"
echo "======================================"
echo ""
echo "💡 提示:"
echo "   - Elasticsearch: UID 1000 (非root用户)"
echo "   - PostgreSQL:    UID 999 (postgres用户)"
echo "   - Redis:         UID 999 (redis用户)"
echo "   - MinIO:         UID 1000 (minio用户)"
echo "   - Backend:       UID 1000 (应用用户)"
echo ""
echo "现在可以安全启动服务: docker-compose up -d"
echo ""
