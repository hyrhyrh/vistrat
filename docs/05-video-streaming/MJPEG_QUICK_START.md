# MJPEG流媒体快速使用指南

## 快速开始

### 1. 启动服务

```bash
# 使用Docker (推荐)
docker-compose up -d

# 或者手动启动
cd backend && python main.py
cd frontend && npm run dev
```

### 2. 访问系统

- 前端界面: http://localhost:3010
- 后端API: http://localhost:16532
- MJPEG健康检查: http://localhost:16532/api/mjpeg/health

## 主要功能

### 实时视频流预览 (LivePreviewPage)

访问实时预览页面，查看所有在线视频流的MJPEG实时画面：

- **多分屏模式**: 1分屏、4分屏、9分屏、16分屏
- **轮播控制**: 单分屏模式下的视频流轮播
- **实时数据**: 告警信息实时显示
- **统计指标**: 视频总数、在线数、告警数等

### 视频流管理 (VideoStreamPage)

管理和监控所有视频流：

- **流列表**: 查看所有RTSP视频流状态
- **播放器**: 点击播放按钮打开MJPEG流播放器
- **统计数据**: 流总数、在线率、状态分布
- **流控制**: 播放/暂停、刷新、全屏等功能

## API使用示例

### 获取MJPEG视频流

```bash
# 直接访问MJPEG流
curl "http://localhost:16532/api/mjpeg/stream/rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream"

# 通过前端代理访问 (推荐)
curl "http://localhost:3010/api/mjpeg/stream/rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream"
```

### 检查服务状态

```bash
# MJPEG服务健康检查
curl "http://localhost:16532/api/mjpeg/health" | jq .

# 视频流统计信息
curl "http://localhost:16532/api/video-streams/statistics/summary" | jq .
```

## 组件使用

### 在React中使用MJPEGPlayer

```typescript
import MJPEGPlayer from '../components/stream/MJPEGPlayer';

function VideoPreview() {
  return (
    <MJPEGPlayer
      rtspUrl="rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream"
      width="100%"
      height="400px"
      autoPlay={true}
      onError={(hasError) => {
        console.log('播放错误:', hasError);
      }}
      onConnectionStateChange={(state) => {
        console.log('连接状态:', state);
      }}
    />
  );
}
```

### 使用StreamPlayerModal

```typescript
import StreamPlayerModal from '../components/stream/StreamPlayerModal';

function StreamManager() {
  const [visible, setVisible] = useState(false);
  const [selectedStream, setSelectedStream] = useState(null);

  return (
    <>
      <Button onClick={() => setVisible(true)}>
        播放视频流
      </Button>

      <StreamPlayerModal
        visible={visible}
        onCancel={() => setVisible(false)}
        stream={selectedStream}
      />
    </>
  );
}
```

## 常见问题

### Q: MJPEG流无法播放
**A**: 检查以下项目：
1. RTSP流地址是否可访问
2. 后端MJPEG服务是否启动 (`/api/mjpeg/health`)
3. 网络防火墙设置
4. 浏览器控制台是否有错误信息

### Q: 视频延迟较高
**A**: 可以调整以下参数：
1. 后端FPS设置 (默认15FPS)
2. JPEG压缩质量 (默认85%)
3. 队列缓冲大小 (默认3帧)

### Q: 内存使用过高
**A**: 系统已内置内存管理：
1. 自动队列清理 (5分钟周期)
2. 帧大小限制 (50MB)
3. 客户端断开时自动释放资源

## 性能优化建议

### 生产环境配置

1. **Nginx反向代理**:
```nginx
location /api/mjpeg/ {
    proxy_pass http://backend:16532;
    proxy_buffering off;
    proxy_cache off;
    proxy_request_buffering off;
}
```

2. **Docker资源限制**:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

3. **监控指标**:
- 活跃流数量
- 客户端连接数
- 内存使用情况
- 帧处理速度

### 开发调试

1. **启用详细日志**:
```python
logging.basicConfig(level=logging.INFO)
```

2. **前端开发模式**:
```typescript
// MJPEGPlayer.tsx 中的调试信息
{process.env.NODE_ENV === 'development' && (
  <div className={styles.debugInfo}>
    <span>尺寸: {imgRef.current?.naturalWidth}x{imgRef.current?.naturalHeight}</span>
    <span>完整: {imgRef.current?.complete ? '是' : '否'}</span>
  </div>
)}
```

## 更多信息

- 详细架构文档: [MJPEG流媒体架构文档](./MJPEG_STREAMING_ARCHITECTURE.md)
- 项目配置: [CLAUDE.md](../CLAUDE.md)
- API文档: http://localhost:16532/docs (服务启动后访问)