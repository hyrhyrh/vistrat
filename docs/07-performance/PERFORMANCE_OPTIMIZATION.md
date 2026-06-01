# 性能优化方案

## 🎯 优化目标
- 降低CPU使用率（从100%降到50-70%）
- 提升GPU利用率（从7%提升到30-50%）
- 优化系统吞吐量和响应速度

## 📊 系统资源分析

### 硬件配置
- **CPU**: 12核心
- **GPU**: NVIDIA RTX 3060 12GB
- **内存**: 32GB

### 优化前状态
| 指标 | 数值 | 状态 |
|------|------|------|
| CPU负载 | 56.48 | 🔴 严重过载 |
| CPU使用率 | 100% | 🔴 饱和 |
| Gunicorn Workers | 25个 | 🔴 过多 |
| GPU显存占用 | 7GB/12GB (58%) | 🟡 偏高 |
| GPU计算利用率 | 7% | 🔴 闲置 |
| 视频解码方式 | CPU软解码 | 🔴 低效 |

---

## ✅ 已实施优化（阶段1）

### 1. Worker数量优化
```env
# .env配置
GUNICORN_WORKERS=6  # 从25降到6（CPU核心数/2）
```

**效果预期**：
- CPU负载：56 → 6-12
- CPU使用率：100% → 50-70%
- Worker进程数：25 → 6

### 2. vLLM显存优化
```yaml
# docker-compose.yml
--gpu-memory-utilization 0.65  # 从0.85降到0.65
```

**效果预期**：
- GPU显存占用：7GB → 5GB
- 释放显存：2GB（可用于其他GPU任务）

### 3. 并发控制优化
```env
# .env配置
MAX_CONCURRENT_STREAMS=12      # 从50降到12
MAX_CONCURRENT_AI_CALLS=36     # 从150降到36
STREAM_FRAME_INTERVAL=10       # 从5增到10秒
```

**效果预期**：
- 降低系统负载峰值
- 减少资源争抢
- 提升单流处理质量

---

## 🚀 待实施优化（阶段2）

### 方案A：GPU视频解码加速

#### 当前状态
- OpenCV使用CPU软解码
- 12个并发流全部占用CPU资源

#### 优化方案
使用FFmpeg + NVDEC硬件解码器：

```python
# 修改video_analysis_service.py和stream_abstraction.py
import subprocess

def decode_with_nvdec(video_path: str, frame_index: int) -> np.ndarray:
    """使用NVDEC硬件解码"""
    cmd = [
        'ffmpeg',
        '-hwaccel', 'cuda',           # 启用CUDA加速
        '-hwaccel_output_format', 'cuda',
        '-i', video_path,
        '-vf', f'select=eq(n\\,{frame_index}),hwdownload,format=bgr24',
        '-vframes', '1',
        '-f', 'rawvideo',
        'pipe:1'
    ]
    # ...解码逻辑
```

**效果预期**：
- CPU占用降低：每流节省20-30% CPU
- GPU利用率提升：7% → 30-40%
- 解码速度提升：2-3倍

#### 实施步骤
1. backend Dockerfile添加FFmpeg：
   ```dockerfile
   RUN apt-get update && apt-get install -y ffmpeg
   ```
2. 修改视频解码逻辑
3. 测试RTSP流和本地视频

---

### 方案B：多GPU环境扩展（可选）

如果未来添加第二块GPU：

```yaml
# docker-compose.yml
services:
  vllm:
    environment:
      - CUDA_VISIBLE_DEVICES=0  # vLLM独占GPU0

  backend:
    environment:
      - CUDA_VISIBLE_DEVICES=1  # 视频解码使用GPU1
```

**效果**：
- GPU0：专用AI推理（vLLM）
- GPU1：专用视频处理（解码、预处理）

---

## 📈 性能监控指标

### 关键指标
```bash
# CPU负载监控
watch -n 2 "top -b -n 1 | head -20"

# GPU监控
watch -n 2 "nvidia-smi"

# Worker数量
ps aux | grep gunicorn | grep -v grep | wc -l

# 实时告警监控
tail -f storage/logs/$(date +%Y-%m-%d)-aiwatch.log | grep "性能告警"
```

### 预期优化效果

| 指标 | 优化前 | 阶段1后 | 阶段2后 |
|------|--------|---------|---------|
| CPU负载 | 56 | 8-12 | 6-8 |
| CPU使用率 | 100% | 60-70% | 40-50% |
| GPU利用率 | 7% | 10-15% | 30-50% |
| Worker进程 | 25 | 6 | 6 |
| 并发流数 | 50 | 12 | 12-20 |
| 帧处理延迟 | 高 | 中 | 低 |

---

## 🔄 应用优化

### 立即生效（阶段1）
```bash
# 1. 重启vLLM（应用显存优化）
docker-compose restart vllm

# 2. 重启backend（应用worker和并发优化）
docker-compose restart backend

# 3. 验证
ps aux | grep gunicorn | wc -l  # 应显示6-7
nvidia-smi                        # 查看GPU显存占用
top                               # 查看CPU负载
```

### 后续实施（阶段2）
1. 修改Dockerfile添加FFmpeg
2. 修改视频解码代码
3. 测试验证
4. 逐步灰度发布

---

## 📝 配置文件清单

### 已修改文件
- ✅ `.env` - Worker数量和并发控制
- ✅ `docker-compose.yml` - vLLM显存配置

### 待修改文件（阶段2）
- ⏳ `backend/Dockerfile` - 添加FFmpeg
- ⏳ `backend/services/video_analysis_service.py` - GPU解码
- ⏳ `backend/services/stream_abstraction.py` - GPU解码

---

## 🎓 最佳实践建议

### CPU密集型任务
- Worker数 = CPU核心数 / 2（避免过度上下文切换）
- 单worker处理1-2个并发流

### GPU资源分配
- AI模型显存占用 < 70%（留余地给其他GPU任务）
- 优先使用GPU硬件加速（解码、预处理）

### 并发控制
- 最大并发流数 = Worker数量 * 2
- 最大AI调用数 = 并发流数 * 3
- 帧采样间隔 ≥ 10秒（降低处理压力）

---

## 📞 问题排查

### CPU仍然100%
```bash
# 检查worker数量
ps aux | grep gunicorn | wc -l

# 检查是否重启生效
docker-compose ps backend

# 查看日志
docker-compose logs backend | grep "配置:"
```

### GPU利用率低
```bash
# 检查vLLM是否正常
docker exec vision_vllm nvidia-smi

# 检查AI调用日志
tail -f storage/logs/$(date +%Y-%m-%d)-aiwatch.log | grep "vllm"
```

---

**更新时间**: 2025-11-21
**优化版本**: v1.0
