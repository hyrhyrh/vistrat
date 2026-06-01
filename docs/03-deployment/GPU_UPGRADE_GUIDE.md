# RTX 4060 GPU 升级指南

本指南说明如何将系统从CPU转码升级到GPU硬件加速。

---

## 🎯 升级目标

**从：** CPU软件转码 (libx264)
**到：** GPU硬件加速 (h264_nvenc)

**性能提升：**
- 转码速度：提升 **10倍**
- CPU占用：从 60-80% → **<10%**
- 首帧延迟：从 2-3秒 → **<1秒**
- 并发能力：从 1-2路 → **10-20路视频流**

---

## 📋 升级步骤

### 步骤1：安装NVIDIA驱动（宿主机）

**Ubuntu/Debian:**

```bash
# 1. 添加NVIDIA官方源
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# 2. 安装推荐驱动（自动选择最佳版本）
sudo ubuntu-drivers autoinstall

# 或者手动安装指定版本（推荐535或更高）
sudo apt install nvidia-driver-535

# 3. 重启系统
sudo reboot

# 4. 验证驱动安装
nvidia-smi
```

**预期输出示例：**
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03   Driver Version: 535.129.03   CUDA Version: 12.2   |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  NVIDIA GeForce ...  Off  | 00000000:01:00.0 Off |                  N/A |
| 30%   40C    P0    25W / 115W |      0MiB /  8192MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

---

### 步骤2：安装nvidia-docker2

```bash
# 1. 配置NVIDIA Docker仓库
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# 2. 更新并安装
sudo apt-get update
sudo apt-get install -y nvidia-docker2

# 3. 重启Docker服务
sudo systemctl restart docker

# 4. 验证NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

**成功标志：** 能在Docker容器内看到nvidia-smi输出

---

### 步骤3：修改docker-compose.yml

**编辑项目根目录的 `docker-compose.yml`：**

找到backend服务的GPU配置部分（约145-153行），**取消注释**：

```yaml
# 【可选】NVIDIA GPU硬件加速配置（需要安装nvidia-docker2和NVIDIA驱动）
# 安装RTX 4060后取消下方注释即可自动启用GPU加速
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1  # 使用1块GPU（如有多块GPU可调整）
          capabilities: [gpu, video]  # GPU计算 + 视频编解码加速
```

**修改后效果：**
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu, video]
```

---

### 步骤4：重启服务并验证

```bash
# 1. 进入项目目录
cd /www/wwwroot/system/video-multi

# 2. 拉取最新代码（包含GPU自动检测功能）
git pull origin main

# 3. 重新创建容器（应用GPU配置）
docker-compose up -d --force-recreate backend

# 4. 查看后端日志（验证GPU已启用）
docker-compose logs -f backend | grep -E "GPU|FLV流服务|编码"
```

**预期日志输出（成功）：**
```
✅ 检测到NVIDIA GPU: GPU 0: NVIDIA GeForce RTX 4060
✅ FFmpeg支持h264_nvenc硬件加速编码器
🚀 FLV流服务启用GPU加速: GPU加速可用: GPU 0: NVIDIA GeForce RTX 4060
🚀 使用GPU加速编码: h264_nvenc (预计速度提升10倍)
```

**如果看到以下日志（失败）：**
```
ℹ️ 未检测到NVIDIA GPU，将使用CPU转码
💻 FLV流服务使用CPU转码: 未检测到NVIDIA GPU
```

**故障排查：**
1. 检查宿主机GPU：`nvidia-smi`
2. 检查Docker GPU访问：`docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi`
3. 检查docker-compose.yml配置是否取消注释
4. 查看完整日志：`docker-compose logs backend | grep -i error`

---

## 🧪 性能测试

### 测试1：查看GPU使用率

```bash
# 在宿主机执行（每秒刷新）
watch -n 1 nvidia-smi
```

**播放视频流时：**
- GPU使用率应该在 **20-40%**
- 视频编码器引擎（Encoder）使用率应该 **>0%**

### 测试2：对比CPU占用

**CPU模式：**
```bash
docker stats vision_backend
# CPU占用：60-80%
```

**GPU模式：**
```bash
docker stats vision_backend
# CPU占用：<10%
```

### 测试3：并发压力测试

**CPU模式：** 同时播放2路视频流
**GPU模式：** 同时播放10-20路视频流

---

## 📊 技术细节

### FFmpeg编码参数对比

| 参数 | CPU (libx264) | GPU (h264_nvenc) |
|------|---------------|------------------|
| 编码器 | libx264 | h264_nvenc |
| 预设 | ultrafast | p2 (NVENC专用) |
| 延迟优化 | zerolatency | ull (超低延迟) |
| 质量控制 | CRF 28 | CQ 28 |
| 比特率 | 固定质量 | VBR 2M-4M |
| B帧 | 自动 | 禁用 (bf=0) |
| 线程 | 2线程 | GPU并行 |

### GPU编码器特性

**h264_nvenc优势：**
1. **专用硬件**：独立编码单元，不占用GPU核心
2. **低功耗**：RTX 4060编码功耗 <10W
3. **高并发**：单GPU可同时处理多路流
4. **质量保证**：与CPU编码质量相当

**适用场景：**
- ✅ 多路视频流实时转码
- ✅ 低延迟直播推流
- ✅ 2K/4K高分辨率转码
- ✅ 服务器CPU资源紧张

---

## ⚠️ 注意事项

### 1. FFmpeg版本要求

**后端Docker镜像已包含：**
- FFmpeg 4.4+ (支持h264_nvenc)
- 已编译NVENC支持

**无需额外安装**

### 2. CUDA版本兼容性

| NVIDIA驱动 | CUDA版本 | 支持GPU |
|-----------|----------|---------|
| 535+ | 12.2 | RTX 4060 ✅ |
| 470+ | 11.4 | RTX 3060 ✅ |
| 450+ | 11.0 | GTX 1660 ✅ |

### 3. Docker版本要求

- Docker: 19.03+
- Docker Compose: 1.28+（支持`deploy`语法）

### 4. 内存建议

- GPU显存：最少4GB（RTX 4060 8GB ✅）
- 系统内存：建议16GB+

---

## 🔧 故障排除

### 问题1：容器无法访问GPU

**症状：**
```
Could not initialize CUDA
CUDA driver version is insufficient
```

**解决：**
1. 检查驱动版本：`nvidia-smi`（应>=535）
2. 重启Docker：`sudo systemctl restart docker`
3. 重建容器：`docker-compose up -d --force-recreate backend`

### 问题2：FFmpeg不支持h264_nvenc

**症状：**
```
Unknown encoder 'h264_nvenc'
```

**解决：**
1. 检查FFmpeg编译选项：
   ```bash
   docker exec vision_backend ffmpeg -encoders | grep nvenc
   ```
2. 如果没有输出，需要重新构建支持NVENC的FFmpeg镜像

### 问题3：编码质量下降

**症状：** 视频出现马赛克、卡顿

**解决：**
调整docker-compose.yml中的GPU编码参数：

```yaml
# 提升质量（降低速度）
- '-cq', '23'        # 从28调整到23（更高质量）
- '-preset', 'p4'    # 从p2调整到p4（更慢但更好）
- '-rc', 'cbr'       # 固定比特率模式
- '-b:v', '4M'       # 提高比特率到4Mbps
```

---

## 📚 参考资料

- [NVIDIA Video Codec SDK](https://developer.nvidia.com/nvidia-video-codec-sdk)
- [FFmpeg h264_nvenc文档](https://trac.ffmpeg.org/wiki/HWAccelIntro)
- [Docker GPU支持文档](https://docs.docker.com/config/containers/resource_constraints/#gpu)
- [RTX 4060规格表](https://www.nvidia.com/en-us/geforce/graphics-cards/40-series/rtx-4060-family/)

---

## ✅ 验收标准

升级成功的标志：

1. ✅ 后端日志显示：`🚀 使用GPU加速编码: h264_nvenc`
2. ✅ `nvidia-smi`显示视频编码器使用率 >0%
3. ✅ 容器CPU占用 <10%
4. ✅ 视频流首帧延迟 <1秒
5. ✅ 可同时播放10路以上视频流

**如果全部满足，恭喜你升级成功！🎉**
