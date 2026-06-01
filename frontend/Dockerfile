# ================== 多阶段构建 ==================
# 第一阶段：构建环境（包含编译工具和依赖）
FROM node:18-alpine AS builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖（仅构建阶段需要）
RUN apk add --no-cache \
    git \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# 复制依赖文件（优化Docker缓存层）
COPY package*.json ./

# 安装依赖（包括开发依赖，用于构建）
RUN npm ci --prefer-offline --no-audit --no-fund \
    && npm cache clean --force

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# ================== 第二阶段：运行环境（最小化） ==================
FROM nginx:alpine AS production

# 只安装运行时必需的工具
RUN apk add --no-cache \
    curl \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# 从构建阶段复制静态文件
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制nginx配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 创建非root用户（安全最佳实践）
RUN addgroup -g 1001 -S appuser && \
    adduser -S appuser -u 1001 -G appuser

# 修改nginx主配置 - 移除user指令(非root运行时不需要)
RUN sed -i 's/^user /#user /' /etc/nginx/nginx.conf

# 设置权限
RUN chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appuser /var/run/nginx.pid

# 切换到非root用户
USER appuser

# 暴露应用端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# 启动nginx
CMD ["nginx", "-g", "daemon off;"]

# ================== 开发阶段（可选） ==================
FROM node:18-alpine AS development

# 设置工作目录
WORKDIR /app

# 安装开发依赖
RUN apk add --no-cache \
    git \
    ca-certificates \
    && rm -rf /var/cache/apk/*

# 复制依赖文件
COPY package*.json ./

# 安装全部依赖（包括开发依赖）
RUN npm install --prefer-offline --no-audit --no-fund \
    && npm cache clean --force

# 复制源代码
COPY . .

# 暴露开发端口
EXPOSE 3000

# 启动开发服务器
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]