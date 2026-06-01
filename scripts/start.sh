#!/bin/bash
#
# AI视频监控系统 - 一键启动脚本
# 自动处理存储目录初始化和服务启动
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${PROJECT_ROOT}"

echo -e "${BLUE}======================================"
echo "🚀 AI视频监控系统启动脚本"
echo "======================================${NC}"
echo ""

# 检查Docker和Docker Compose
echo -e "${YELLOW}📋 检查环境依赖...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ 错误: Docker未安装${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ 错误: Docker Compose未安装${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker: $(docker --version)${NC}"
echo -e "${GREEN}✅ Docker Compose: $(docker-compose --version)${NC}"
echo ""

# 检查.env文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  警告: .env文件不存在${NC}"
    if [ -f ".env.example" ]; then
        echo -e "${BLUE}📝 从.env.example创建.env文件...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠️  请编辑.env文件配置必要的环境变量!${NC}"
        echo -e "${YELLOW}   特别是: POSTGRES_PASSWORD, MINIO密码, AI API密钥${NC}"
        echo ""
        read -p "是否现在编辑.env文件? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-vim} .env
        fi
    else
        echo -e "${RED}❌ 错误: .env.example也不存在${NC}"
        exit 1
    fi
fi

# 初始化存储目录
echo -e "${BLUE}======================================"
echo "📂 初始化存储目录权限"
echo "======================================${NC}"

STORAGE_DIR="${PROJECT_ROOT}/storage"

echo -e "${YELLOW}🔧 创建存储目录...${NC}"
mkdir -p "${STORAGE_DIR}/elasticsearch"
mkdir -p "${STORAGE_DIR}/postgres"
mkdir -p "${STORAGE_DIR}/redis"
mkdir -p "${STORAGE_DIR}/minio"
mkdir -p "${STORAGE_DIR}/uploads"
mkdir -p "${STORAGE_DIR}/data/prompts"
mkdir -p "${STORAGE_DIR}/logs"
mkdir -p "${STORAGE_DIR}/video_warning"
mkdir -p "${STORAGE_DIR}/archive"
echo -e "${GREEN}✅ 目录创建完成${NC}"

# 使用Docker容器设置权限(避免sudo)
echo -e "${YELLOW}🔧 配置目录权限...${NC}"
docker run --rm \
    -v "${STORAGE_DIR}:/storage" \
    alpine:latest \
    sh -c "
        chown -R 1000:1000 /storage/elasticsearch &&
        chmod -R 755 /storage/elasticsearch &&
        echo '✅ Elasticsearch: 1000:1000' &&

        chown -R 999:999 /storage/postgres &&
        chmod -R 700 /storage/postgres &&
        echo '✅ PostgreSQL: 999:999' &&

        chown -R 999:999 /storage/redis &&
        chmod -R 755 /storage/redis &&
        echo '✅ Redis: 999:999' &&

        chown -R 1000:1000 /storage/minio &&
        chmod -R 755 /storage/minio &&
        echo '✅ MinIO: 1000:1000' &&

        chown -R 1000:1000 /storage/uploads /storage/data /storage/logs /storage/video_warning /storage/archive &&
        chmod -R 755 /storage/uploads /storage/data /storage/logs /storage/video_warning /storage/archive &&
        echo '✅ Backend: 1000:1000'
    "

echo -e "${GREEN}✅ 权限配置完成${NC}"
echo ""

# 启动服务
echo -e "${BLUE}======================================"
echo "🚀 启动Docker服务"
echo "======================================${NC}"

# 检查是否已有运行的容器
if docker ps -a | grep -q vision_; then
    echo -e "${YELLOW}⚠️  检测到已存在的容器${NC}"
    read -p "是否停止并重新启动? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🛑 停止现有容器...${NC}"
        docker-compose down
    else
        echo -e "${YELLOW}⏭️  跳过停止,尝试直接启动${NC}"
    fi
fi

echo -e "${YELLOW}🚀 启动所有服务...${NC}"
docker-compose up -d

# 等待服务启动
echo ""
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 5

# 检查服务状态
echo ""
echo -e "${BLUE}======================================"
echo "📊 服务状态检查"
echo "======================================${NC}"

docker-compose ps

echo ""
echo -e "${BLUE}======================================"
echo "🔍 健康检查"
echo "======================================${NC}"

# 检查PostgreSQL
echo -n "PostgreSQL: "
if docker exec vision_postgres pg_isready -U ${POSTGRES_USER:-vision} &>/dev/null; then
    echo -e "${GREEN}✅ 运行中${NC}"
else
    echo -e "${RED}❌ 未就绪${NC}"
fi

# 检查Elasticsearch
echo -n "Elasticsearch: "
if curl -s http://localhost:9200/_cluster/health &>/dev/null; then
    STATUS=$(curl -s http://localhost:9200/_cluster/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    if [ "$STATUS" = "green" ] || [ "$STATUS" = "yellow" ]; then
        echo -e "${GREEN}✅ 运行中 (status: $STATUS)${NC}"
    else
        echo -e "${RED}❌ 状态异常 (status: $STATUS)${NC}"
    fi
else
    echo -e "${YELLOW}⏳ 启动中...${NC}"
fi

# 检查Redis
echo -n "Redis: "
if docker exec vision_redis redis-cli ping &>/dev/null | grep -q PONG; then
    echo -e "${GREEN}✅ 运行中${NC}"
else
    echo -e "${RED}❌ 未就绪${NC}"
fi

# 检查MinIO
echo -n "MinIO: "
if curl -s http://localhost:9010/minio/health/live &>/dev/null; then
    echo -e "${GREEN}✅ 运行中${NC}"
else
    echo -e "${YELLOW}⏳ 启动中...${NC}"
fi

# 检查Backend
echo -n "Backend API: "
if curl -s http://localhost:16532/health &>/dev/null; then
    echo -e "${GREEN}✅ 运行中${NC}"
else
    echo -e "${YELLOW}⏳ 启动中...${NC}"
fi

# 检查Frontend
echo -n "Frontend: "
if curl -s http://localhost:3009 &>/dev/null; then
    echo -e "${GREEN}✅ 运行中${NC}"
else
    echo -e "${YELLOW}⏳ 启动中...${NC}"
fi

echo ""
echo -e "${BLUE}======================================"
echo "✅ 启动完成!"
echo "======================================${NC}"
echo ""
echo -e "${GREEN}📱 访问地址:${NC}"
echo -e "  前端界面: ${BLUE}http://localhost:3009${NC}"
echo -e "  后端API:  ${BLUE}http://localhost:16532${NC}"
echo -e "  MinIO控制台: ${BLUE}http://localhost:9011${NC}"
echo ""
echo -e "${YELLOW}💡 常用命令:${NC}"
echo "  查看日志: docker-compose logs -f [service]"
echo "  停止服务: docker-compose down"
echo "  重启服务: docker-compose restart [service]"
echo "  查看状态: docker-compose ps"
echo ""
echo -e "${YELLOW}⚠️  提示:${NC}"
echo "  某些服务可能需要额外时间完成初始化"
echo "  如果服务未就绪,请等待1-2分钟后再次检查"
echo "  查看服务日志: docker-compose logs -f"
echo ""
