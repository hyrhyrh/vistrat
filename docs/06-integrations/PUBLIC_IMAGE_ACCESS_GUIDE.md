# 告警图片公网访问配置指南

## 📋 概述

本文档说明如何配置系统，使得video_alerts索引中的告警图片可以从公网访问。

## 🎯 问题背景

**原问题**：
- video_alerts索引中的图片URL格式：`http://minio:9000/images/streams/xxx/frame_001.jpg`
- 这是Docker内网地址，公网无法直接访问
- 导致外部系统或用户无法查看告警图片

**解决方案**：
- 自动将MinIO内网URL转换为代理URL
- 代理URL格式：`http://公网IP:端口/api/image-proxy/minio/images/streams/xxx/frame_001.jpg`
- 通过后端图片代理服务提供公网访问能力

## 🔧 技术架构

### URL转换流程

```
1. 图片上传到MinIO
   ↓
2. 生成MinIO内网URL: http://minio:9000/images/streams/xxx/frame_001.jpg
   ↓
3. 转换为代理URL: http://<INTERNAL_HOST>:16532/api/image-proxy/minio/images/streams/xxx/frame_001.jpg
   ↓
4. 存储到Elasticsearch (video_alerts索引)
   ↓
5. 前端/外部系统通过代理URL访问图片
```

### 核心组件

1. **图片代理服务** (`backend/api/image_proxy.py`)
   - 端点：`GET /api/image-proxy/minio/{bucket_name}/{object_path}`
   - 功能：从MinIO下载图片并返回给客户端
   - 特性：支持缓存、内容类型识别

2. **URL转换函数** (`backend/services/storage.py`)
   - `convert_to_proxy_url()`: 将MinIO URL转换为代理URL
   - 自动识别开发/生产环境
   - 支持相对路径和完整URL

3. **图片上传服务** (`backend/services/storage.py`)
   - `upload_stream_frame_image()`: 实时流图片上传
   - `upload_frame_image()`: 离线视频图片上传
   - 自动生成代理URL

## 🚀 部署步骤

### 1. 配置环境变量

编辑 `backend/.env` 文件，添加公网基础URL配置：

```bash
# 方式1: 使用公网IP
PUBLIC_BASE_URL=http://<INTERNAL_HOST>:16532

# 方式2: 使用域名（推荐）
PUBLIC_BASE_URL=https://watchdog.your-company.com

# 方式3: 使用HTTPS + 自定义端口
PUBLIC_BASE_URL=https://watchdog.your-company.com:8443
```

**重要说明**：
- 开发环境可不配置，默认使用 `http://localhost:16532`
- 生产环境**必须**配置为实际的公网地址
- 配置时不要在末尾添加斜杠 `/`

### 2. 重启后端服务

```bash
# Docker环境
docker-compose restart backend

# 或完全重启
docker-compose down
docker-compose up -d

# 本地开发环境
cd backend
python main.py
```

### 3. 验证配置

运行测试脚本验证URL转换功能：

```bash
cd backend
python scripts/test_url_conversion.py
```

**预期输出**：
```
================================================================================
URL转换功能测试
================================================================================

【当前配置】
PUBLIC_BASE_URL: http://<INTERNAL_HOST>:16532
PORT: 16532

【测试用例】

测试 1: 实时流图片URL - Docker内网地址
输入URL: http://minio:9000/images/streams/d40dad17-6109-4e2d-a201-376347ca20da/frame_000666.jpg
输出URL: http://<INTERNAL_HOST>:16532/api/image-proxy/minio/images/streams/d40dad17-6109-4e2d-a201-376347ca20da/frame_000666.jpg
✅ 测试通过（生产环境完整URL）

...

测试结果: 3/3 通过
✅ 所有测试通过！
```

### 4. 测试图片访问

使用curl或浏览器测试图片代理服务：

```bash
# 测试代理服务健康状态
curl http://<INTERNAL_HOST>:16532/api/image-proxy/test

# 测试实际图片访问（替换为实际的URL）
curl -I http://<INTERNAL_HOST>:16532/api/image-proxy/minio/images/streams/xxx/frame_001.jpg
```

**预期响应**：
```
HTTP/1.1 200 OK
content-type: image/jpeg
cache-control: public, max-age=3600
content-disposition: inline; filename=frame_001.jpg
```

## 🔍 URL格式说明

### 开发环境（localhost）

配置：
```bash
PUBLIC_BASE_URL=http://localhost:16532  # 默认值
```

生成的URL（相对路径）：
```
/api/image-proxy/minio/images/streams/xxx/frame_001.jpg
```

**优点**：
- 简洁，不包含域名
- 适合本地开发和前端代理

### 生产环境（公网IP）

配置：
```bash
PUBLIC_BASE_URL=http://<INTERNAL_HOST>:16532
```

生成的URL（完整URL）：
```
http://<INTERNAL_HOST>:16532/api/image-proxy/minio/images/streams/xxx/frame_001.jpg
```

**优点**：
- 可直接从任何网络访问
- 适合外部系统集成、微信推送等场景

### 生产环境（域名）

配置：
```bash
PUBLIC_BASE_URL=https://watchdog.your-company.com
```

生成的URL：
```
https://watchdog.your-company.com/api/image-proxy/minio/images/streams/xxx/frame_001.jpg
```

**优点**：
- 安全（HTTPS）
- 易记、专业
- 推荐用于生产环境

## 📊 效果验证

### 查询Elasticsearch验证

连接到Elasticsearch查看video_alerts索引中的image_url字段：

```bash
# 查询最近的告警
curl -X GET "http://localhost:9200/video_alerts/_search?size=1&sort=created_at:desc" | jq '.hits.hits[0]._source.image_url'
```

**配置前**（内网地址，公网无法访问）：
```json
"http://minio:9000/images/streams/d40dad17-6109-4e2d-a201-376347ca20da/frame_000666.jpg"
```

**配置后**（代理URL，公网可访问）：
```json
"http://<INTERNAL_HOST>:16532/api/image-proxy/minio/images/streams/d40dad17-6109-4e2d-a201-376347ca20da/frame_000666.jpg"
```

### 前端验证

1. 打开安全监控大屏：`http://<INTERNAL_HOST>:3000`
2. 查看告警列表
3. 点击告警查看详情
4. 确认图片能正常显示

## 🛡️ 安全考虑

### 1. 访问控制

当前图片代理服务**没有**访问控制，任何人知道URL都可以访问。如需增强安全性，可以考虑：

- 添加JWT认证
- 添加IP白名单
- 添加URL签名验证
- 设置图片访问有效期

### 2. 缓存策略

图片代理服务默认设置1小时浏览器缓存：
```
Cache-Control: public, max-age=3600
```

可以根据需要调整缓存时间（修改 `backend/api/image_proxy.py:64`）。

### 3. 带宽优化

建议配置CDN或对象存储的公网访问能力，减轻后端服务器压力：

- 使用MinIO的公网访问功能（需要配置MINIO_SERVER_URL）
- 配置Nginx反向代理和缓存
- 使用CDN加速图片访问

## 🐛 常见问题

### Q1: 配置后图片仍无法访问

**检查清单**：
1. 确认 `PUBLIC_BASE_URL` 已正确配置
2. 确认已重启后端服务
3. 检查防火墙是否开放端口16532
4. 验证后端服务是否正常运行
5. 测试图片代理服务健康状态

```bash
# 检查服务状态
docker-compose ps backend

# 查看服务日志
docker-compose logs -f backend | grep "image-proxy"

# 测试代理服务
curl http://<INTERNAL_HOST>:16532/api/image-proxy/test
```

### Q2: 历史告警图片URL仍是旧格式

**说明**：
- 配置只影响**新生成**的告警
- 历史告警的image_url不会自动更新

**解决方案**：
如需更新历史数据，可以运行批量更新脚本（需要开发）：
```python
# 伪代码示例
for alert in es.search(index="video_alerts"):
    old_url = alert["image_url"]
    new_url = convert_to_proxy_url(old_url)
    es.update(index="video_alerts", id=alert["id"], body={"image_url": new_url})
```

### Q3: 使用域名时出现404错误

**原因**：
- 域名解析未配置
- Nginx反向代理配置不正确
- 证书问题（HTTPS）

**解决方案**：
1. 检查域名A记录是否指向正确的服务器IP
2. 配置Nginx反向代理：
```nginx
server {
    listen 80;
    server_name watchdog.your-company.com;

    location /api/image-proxy/ {
        proxy_pass http://localhost:16532/api/image-proxy/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Q4: 图片加载很慢

**原因**：
- MinIO存储性能问题
- 网络带宽不足
- 图片文件过大

**优化建议**：
1. 启用图片压缩（调整JPEG_QUALITY配置）
2. 配置CDN加速
3. 使用对象存储的预签名URL直接访问
4. 增加后端服务器数量，做负载均衡

## 📚 相关文档

- [图片代理API文档](../backend/api/image_proxy.py)
- [存储服务文档](../backend/services/storage.py)
- [环境变量配置](../backend/.env.README.md)
- [系统架构文档](../CLAUDE.md)

## 🔗 相关API端点

- `GET /api/image-proxy/minio/{bucket_name}/{object_path}` - 获取MinIO图片
- `GET /api/image-proxy/presigned` - 生成预签名URL
- `GET /api/image-proxy/url-convert` - 转换MinIO URL
- `GET /api/image-proxy/test` - 测试图片代理服务

## ✅ 部署检查清单

- [ ] 已配置 `PUBLIC_BASE_URL` 环境变量
- [ ] 已重启后端服务
- [ ] 运行测试脚本验证URL转换
- [ ] 测试图片代理服务健康状态
- [ ] 创建新的告警测试图片访问
- [ ] 确认前端能正常显示告警图片
- [ ] 检查服务器防火墙配置
- [ ] （可选）配置域名和SSL证书
- [ ] （可选）配置CDN加速
- [ ] 文档已更新并通知团队

---

**版本**: v1.0
**更新日期**: 2025-12-17
**维护者**: AI视频监控系统团队
