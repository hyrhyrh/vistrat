# FFmpeg 跨平台测试指南

## 测试目标

验证 ffmpeg 在不同平台（Windows、ARM、AMD64）的 Docker 容器中正确安装并可被 pydub 使用。

## 快速测试（推荐）

### 方法1：使用验证脚本

```bash
# 1. 重新构建后端镜像
docker-compose build backend

# 2. 启动后端容器
docker-compose up -d backend

# 3. 运行验证脚本
docker exec -it vision_backend /app/scripts/verify_ffmpeg.sh

# 期望输出：
# =========================================
# 验证 ffmpeg 安装
# =========================================
# ✅ ffmpeg 命令已安装
#
# 版本信息：
# ffmpeg version 4.x.x-xxx
# ...
#
# ✅ ffprobe 命令已安装
#
# =========================================
# 测试 pydub 是否能找到 ffmpeg
# =========================================
# ✅ pydub 可以找到 ffmpeg: /usr/bin/ffmpeg
#
# =========================================
# ✅ 所有检查通过！
# =========================================
```

### 方法2：手动验证

```bash
# 1. 进入容器
docker exec -it vision_backend /bin/bash

# 2. 检查 ffmpeg 版本
ffmpeg -version

# 3. 检查 ffmpeg 路径
which ffmpeg
# 期望输出: /usr/bin/ffmpeg

# 4. 测试 pydub
python -c "
from pydub import AudioSegment
from pydub.utils import which
print('ffmpeg 路径:', which('ffmpeg'))
"

# 5. 退出容器
exit
```

## 完整功能测试

### 测试语音识别 API

```bash
# 1. 准备测试音频文件（webm 格式）
# 可以使用浏览器录制一段语音保存为 test.webm

# 2. 调用语音识别 API
curl -X POST "http://localhost:16532/speech/recognize" \
  -H "Content-Type: multipart/form-data" \
  -F "audio=@test.webm"

# 期望响应（成功）：
# {
#   "text": "识别的文本内容",
#   "confidence": 1.0,
#   "message": "识别成功"
# }

# 如果 ffmpeg 缺失，将返回错误：
# {
#   "detail": "音频格式转换失败: ..."
# }
```

### 测试健康检查

```bash
# 检查语音服务状态
curl http://localhost:16532/speech/health

# 期望响应：
# {
#   "status": "healthy",
#   "service": "baidu_speech_recognition",
#   "configured": true/false,
#   "message": "语音识别服务正常"
# }
```

## 多架构平台测试

### AMD64 平台（Intel/AMD）

```bash
# 构建 AMD64 镜像
docker buildx build \
  --platform linux/amd64 \
  -t vision-backend-amd64 \
  -f backend/Dockerfile \
  backend/

# 运行测试
docker run --rm vision-backend-amd64 ffmpeg -version
docker run --rm vision-backend-amd64 python -c "from pydub.utils import which; print(which('ffmpeg'))"
```

### ARM64 平台（Apple Silicon、ARM 服务器）

```bash
# 构建 ARM64 镜像
docker buildx build \
  --platform linux/arm64 \
  -t vision-backend-arm64 \
  -f backend/Dockerfile \
  backend/

# 运行测试
docker run --rm vision-backend-arm64 ffmpeg -version
docker run --rm vision-backend-arm64 python -c "from pydub.utils import which; print(which('ffmpeg'))"
```

### 多架构同时构建

```bash
# 创建 buildx 构建器（如果还没有）
docker buildx create --name multiarch --use

# 构建多架构镜像
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t your-registry/vision-backend:latest \
  --push \
  -f backend/Dockerfile \
  backend/
```

## 常见问题排查

### 问题1：pydub 仍然报警告

**症状**:
```
RuntimeWarning: Couldn't find ffmpeg or avconv
```

**排查步骤**:

```bash
# 1. 确认使用了最新镜像
docker-compose pull backend
# 或
docker-compose build --no-cache backend

# 2. 检查容器中 ffmpeg 是否存在
docker exec -it vision_backend which ffmpeg

# 3. 检查 Python 环境
docker exec -it vision_backend python -c "import sys; print(sys.path)"

# 4. 重新安装 pydub
docker exec -it vision_backend pip install --force-reinstall pydub
```

### 问题2：音频转换失败

**症状**:
```
HTTPException: 音频格式转换失败
```

**排查步骤**:

```bash
# 1. 手动测试 ffmpeg
docker exec -it vision_backend ffmpeg -version

# 2. 测试简单的格式转换
docker exec -it vision_backend bash -c "
echo 'Testing ffmpeg...'
ffmpeg -f lavfi -i sine=frequency=1000:duration=1 -ar 16000 /tmp/test.wav -y
ls -lh /tmp/test.wav
"

# 3. 查看详细错误日志
docker logs vision_backend | grep -i "ffmpeg\|pydub\|audio"
```

### 问题3：不同平台行为不一致

**症状**: AMD64 正常，ARM64 报错

**排查步骤**:

```bash
# 1. 检查平台架构
docker exec -it vision_backend uname -m
# AMD64: x86_64
# ARM64: aarch64

# 2. 检查 ffmpeg 版本差异
docker exec -it vision_backend ffmpeg -version

# 3. 检查依赖库
docker exec -it vision_backend ldd $(which ffmpeg)

# 4. 检查 apt 包列表
docker exec -it vision_backend dpkg -l | grep ffmpeg
```

## 性能测试

### 音频转换性能

```python
# 创建测试脚本 test_audio_performance.py
import time
import io
from pydub import AudioSegment

def test_conversion_performance():
    """测试音频转换性能"""
    # 生成测试音频（1秒，1000Hz正弦波）
    audio = AudioSegment.silent(duration=1000)  # 1秒静音

    start_time = time.time()

    # 执行转换
    wav_io = io.BytesIO()
    audio.set_frame_rate(16000).set_channels(1).export(
        wav_io, format="wav"
    )

    duration = time.time() - start_time
    print(f"转换耗时: {duration:.3f}秒")
    print(f"输出大小: {len(wav_io.getvalue())} bytes")

if __name__ == "__main__":
    test_conversion_performance()
```

```bash
# 运行性能测试
docker exec -it vision_backend python /app/test_audio_performance.py
```

## 回归测试清单

在部署到生产环境前，请确认以下检查项：

- [ ] Dockerfile 包含 `ffmpeg` 依赖（第62行）
- [ ] 容器启动无 pydub 警告
- [ ] `ffmpeg -version` 命令正常输出
- [ ] `which ffmpeg` 返回 `/usr/bin/ffmpeg`
- [ ] pydub 可以找到 ffmpeg（Python 测试）
- [ ] 语音识别 API 可以正常转换 webm 格式
- [ ] 语音识别 API 可以正常转换 mp3 格式
- [ ] 语音识别 API 健康检查通过
- [ ] AMD64 平台测试通过
- [ ] ARM64 平台测试通过（如适用）
- [ ] Windows Docker Desktop 测试通过（如适用）

## 自动化测试脚本

```bash
#!/bin/bash
# 文件: scripts/test_ffmpeg_integration.sh

set -e

echo "========================================="
echo "FFmpeg 集成测试"
echo "========================================="

# 1. 构建镜像
echo "📦 构建 Docker 镜像..."
docker-compose build backend

# 2. 启动容器
echo "🚀 启动容器..."
docker-compose up -d backend

# 等待容器就绪
echo "⏳ 等待服务启动..."
sleep 10

# 3. 运行验证脚本
echo "🔍 运行 ffmpeg 验证..."
docker exec vision_backend /app/scripts/verify_ffmpeg.sh

# 4. 测试健康检查
echo "🏥 测试健康检查端点..."
curl -f http://localhost:16532/speech/health || {
    echo "❌ 健康检查失败"
    exit 1
}

echo ""
echo "========================================="
echo "✅ 所有测试通过！"
echo "========================================="
```

## 环境信息收集

如果遇到问题，请收集以下信息：

```bash
# 运行诊断脚本
cat > /tmp/ffmpeg_diagnostics.sh << 'EOF'
#!/bin/bash
echo "=== 系统信息 ==="
uname -a
echo ""

echo "=== Docker 信息 ==="
docker version
echo ""

echo "=== 容器架构 ==="
docker exec vision_backend uname -m
echo ""

echo "=== FFmpeg 版本 ==="
docker exec vision_backend ffmpeg -version | head -5
echo ""

echo "=== FFmpeg 路径 ==="
docker exec vision_backend which ffmpeg
echo ""

echo "=== Python 环境 ==="
docker exec vision_backend python --version
echo ""

echo "=== pydub 测试 ==="
docker exec vision_backend python -c "from pydub.utils import which; print('ffmpeg:', which('ffmpeg'))"
echo ""

echo "=== 容器日志（最后50行）==="
docker logs --tail 50 vision_backend
EOF

chmod +x /tmp/ffmpeg_diagnostics.sh
bash /tmp/ffmpeg_diagnostics.sh > /tmp/ffmpeg_diagnostics.log 2>&1
cat /tmp/ffmpeg_diagnostics.log
```

---

**最后更新**: 2025-10-26
**适用版本**: v2.2.0+
