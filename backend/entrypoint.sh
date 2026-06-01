#!/bin/bash
set -e

echo "🚀 初始化容器环境..."

# 创建所有必需的数据目录(支持卷挂载)
echo "📁 创建数据目录..."
mkdir -p /app/data/prompts \
         /app/uploads \
         /app/logs \
         /app/video_warning \
         /app/archive

# 修复挂载卷的权限(确保appuser可写)
echo "🔧 修复目录权限..."
chown -R appuser:appuser \
    /app/data \
    /app/uploads \
    /app/logs \
    /app/video_warning \
    /app/archive

echo "✅ 环境初始化完成,切换到appuser运行应用..."

# 🔧 修复ARM边缘设备线程限制问题
# 设置资源限制(解决"can't start new thread"错误)
echo "🔧 配置用户资源限制..."
ulimit -u 65535  # 最大进程数(包含线程)
ulimit -n 65535  # 最大文件描述符数
echo "   - 最大进程数: $(ulimit -u)"
echo "   - 最大文件描述符: $(ulimit -n)"

# 使用gosu切换到非root用户运行应用(安全最佳实践)
exec gosu appuser "$@"
