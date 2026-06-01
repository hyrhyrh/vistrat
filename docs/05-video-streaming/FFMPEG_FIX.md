# FFmpeg 跨平台兼容性修复文档

## 问题描述

### 错误信息
```
/app/.venv/lib/python3.10/site-packages/pydub/utils.py:170: RuntimeWarning:
Couldn't find ffmpeg or avconv - defaulting to ffmpeg, but may not work
```

### 影响范围
- ❌ **Windows 平台**：容器启动报错
- ❌ **ARM 架构**（如 Apple Silicon M1/M2、ARM 服务器）：容器启动报错
- ✅ **AMD64 架构**：正常运行（本地可能已安装 ffmpeg）

### 根本原因
`pydub` 库用于音频格式转换（webm/mp3/m4a → WAV），依赖系统安装的 `ffmpeg` 或 `avconv`。
Docker 容器运行时环境缺少该依赖，导致语音识别功能无法正常工作。

## 解决方案

### 1. Dockerfile 修复

**文件**: `backend/Dockerfile:61-62`

在运行时阶段（runtime stage）添加 ffmpeg 依赖：

```dockerfile
# 音频处理依赖（pydub需要ffmpeg进行格式转换）
ffmpeg \
```

**完整上下文**:
```dockerfile
# 只安装运行时必需的系统库（不包含编译工具）
RUN apt-get update && apt-get install -y --no-install-recommends \
    # OpenCV运行时依赖
    libgl1 \
    libgl1-mesa-dri \
    libglib2.0-0 \
    # ... 其他依赖 ...
    # PostgreSQL客户端库（运行时）
    libpq5 \
    # 音频处理依赖（pydub需要ffmpeg进行格式转换）
    ffmpeg \
    # 健康检查工具
    curl \
    # ... 其他依赖 ...
```

### 2. 文档更新

**文件**: `README.md`

#### 技术栈说明（第138行）
```markdown
### 后端核心技术
- **FastAPI 0.104+** - 现代异步Web框架，自动API文档生成
- **OpenCV 4.8+** - 视频处理和计算机视觉库
- **FFmpeg** - 音频格式转换（pydub依赖）  ← 新增
- **WebSocket** - 实时双向通信协议
```

#### 系统依赖要求（第211-232行）
新增完整的 ffmpeg 安装说明：

```markdown
### 系统依赖要求

#### 本地开发环境
# Ubuntu/Debian
sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg

# Windows (使用 Chocolatey)
choco install ffmpeg

# 验证安装
ffmpeg -version

#### Docker环境
Docker镜像已内置 ffmpeg，无需额外安装。
```

### 3. 验证脚本

**文件**: `scripts/verify_ffmpeg.sh`

创建自动化验证脚本，用于检查 ffmpeg 是否正确安装：

```bash
#!/bin/bash
# 验证 ffmpeg 在容器中是否正确安装

# 检查 ffmpeg 命令
if command -v ffmpeg &> /dev/null; then
    echo "✅ ffmpeg 命令已安装"
    ffmpeg -version | head -5
else
    echo "❌ ffmpeg 命令未找到"
    exit 1
fi

# 测试 Python 中 pydub 是否能正确使用 ffmpeg
python3 -c "
from pydub import AudioSegment
from pydub.utils import which

ffmpeg_path = which('ffmpeg')
if ffmpeg_path:
    print(f'✅ pydub 可以找到 ffmpeg: {ffmpeg_path}')
else:
    print('❌ pydub 无法找到 ffmpeg')
    exit 1
"
```

## 验证方法

### Docker 环境验证

```bash
# 1. 重新构建镜像
docker-compose build backend

# 2. 启动容器
docker-compose up -d backend

# 3. 进入容器验证
docker exec -it vision_backend /bin/bash
ffmpeg -version
python -c "from pydub import AudioSegment; from pydub.utils import which; print(which('ffmpeg'))"

# 4. 运行验证脚本
docker exec -it vision_backend /app/scripts/verify_ffmpeg.sh
```

### 本地开发环境验证

```bash
# 1. 安装 ffmpeg（根据平台选择）
# Ubuntu/Debian
sudo apt-get install -y ffmpeg

# macOS
brew install ffmpeg

# Windows
choco install ffmpeg

# 2. 验证安装
ffmpeg -version

# 3. 测试 pydub
cd backend
source .venv/bin/activate
python -c "from pydub import AudioSegment; print('✅ pydub 工作正常')"
```

## 影响的功能

### 语音识别 API
**文件**: `backend/api/speech.py:68-106`

```python
def convert_audio_to_wav(audio_data: bytes, source_format: str = "webm") -> bytes:
    """
    将音频转换为WAV格式(百度AI要求)

    依赖: ffmpeg (通过 pydub 调用)
    """
    audio = AudioSegment.from_file(
        io.BytesIO(audio_data),
        format=source_format  # webm/mp3/m4a 等格式
    )

    # 转换为WAV格式
    audio = audio.set_frame_rate(16000)
    audio = audio.set_sample_width(2)  # 16bit
    audio = audio.set_channels(1)  # 单声道

    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")  # 需要 ffmpeg
    return wav_io.getvalue()
```

### API 端点
- `POST /speech/recognize` - 语音识别（webm/mp3/wav 音频上传）
- `GET /speech/health` - 语音服务健康检查

## 兼容性保证

### 多架构支持
Docker 镜像现在完全支持：
- ✅ **AMD64/x86_64** - Intel/AMD 处理器
- ✅ **ARM64/aarch64** - Apple Silicon M1/M2、ARM 服务器
- ✅ **Windows** - Docker Desktop on Windows

### Debian 包管理器兼容性
使用 `apt-get` 安装 ffmpeg，适用于所有基于 Debian/Ubuntu 的容器镜像。

## 依赖链分析

```
语音识别功能
    ↓
api/speech.py:convert_audio_to_wav()
    ↓
pydub.AudioSegment.export(format="wav")
    ↓
pydub.utils.which('ffmpeg')
    ↓
系统命令: ffmpeg
    ↓
apt-get install ffmpeg (Dockerfile)
```

## 相关文件清单

### 修改的文件
1. `backend/Dockerfile` - 添加 ffmpeg 依赖
2. `README.md` - 更新技术栈和配置说明

### 新增的文件
1. `scripts/verify_ffmpeg.sh` - 验证脚本
2. `docs/FFMPEG_FIX.md` - 本文档

### 受影响的文件
1. `backend/api/speech.py` - 使用 pydub 进行音频转换
2. `backend/pyproject.toml` - 声明 pydub 依赖

## 后续建议

### 1. CI/CD 集成
在构建流程中添加 ffmpeg 验证：

```yaml
# .github/workflows/build.yml
- name: Verify FFmpeg
  run: |
    docker-compose build backend
    docker-compose run backend /app/scripts/verify_ffmpeg.sh
```

### 2. 健康检查增强
在 `/health` 端点中添加 ffmpeg 检查：

```python
@router.get("/health")
async def health_check():
    from pydub.utils import which

    return {
        "status": "healthy",
        "ffmpeg_available": which('ffmpeg') is not None,
        "pydub_version": pydub.__version__
    }
```

### 3. 错误提示优化
当 ffmpeg 不可用时，提供友好的错误信息：

```python
if not which('ffmpeg'):
    raise HTTPException(
        status_code=503,
        detail="音频转换服务不可用：ffmpeg 未安装。请参考文档安装 ffmpeg。"
    )
```

## 参考资料

- [pydub 官方文档](https://github.com/jiaaro/pydub)
- [FFmpeg 官方网站](https://ffmpeg.org/)
- [Docker 多架构构建](https://docs.docker.com/build/building/multi-platform/)

---

**修复日期**: 2025-10-26
**影响版本**: v2.2.0+
**状态**: ✅ 已修复
