// 告警严重程度枚举（与后端 annotation_service.py 保持一致）
export type AlertSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info'

// 检测框坐标（原始图像像素坐标系）
export interface BoundingBox {
  x: number
  y: number
  width: number
  height: number
}

// 单个检测对象
export interface DetectionObject {
  label: string
  confidence: number
  bbox: BoundingBox
  severity: AlertSeverity
}

// 图像原始尺寸（用于 canvas 坐标映射）
export interface ImageSize {
  width: number
  height: number
}

// 告警视频片段生成状态（与后端 ClipService 对齐）
// - pending:  后端正在生成中（告警触发后 T+11s 内的典型状态）
// - ready:    片段已上传 MinIO，clip_url 可播放
// - failed:   生成失败（FFmpeg 出错 / 上传失败等）
// - skipped:  未生成片段（录制未启用、降级路径等）
export type ClipStatus = 'pending' | 'ready' | 'failed' | 'skipped'

export interface AlertMessage {
  timestamp: string
  alert: string
  description?: string
  video_file_name?: string
  picture_file_name?: string
  // 后端新增：检测对象列表（用于前端绘制 bounding box）
  detection_objects?: DetectionObject[]
  // 后端新增：原图尺寸（用于 canvas 坐标映射）
  image_size?: ImageSize
  // Week 4：告警视频片段（告警前 5s + 后 10s）
  // 可能是 MinIO 预签名 URL（有过期时间）或公开直链
  clip_url?: string
  clip_status?: ClipStatus
}

// WebSocket clip 事件（与后端 broadcast 格式对齐）
export interface ClipReadyEvent {
  type: 'clip_ready'
  alert_id: string
  clip_url: string
  timestamp: string
}

export interface ClipFailedEvent {
  type: 'clip_failed'
  alert_id: string
  timestamp: string
}

export type ClipEvent = ClipReadyEvent | ClipFailedEvent

export interface VideoConfig {
  source: string
  type: 'local' | 'rtsp'
  analysis_interval?: number
  buffer_duration?: number
}

export interface PromptTemplate {
  id: string
  name: string
  description: string
  content: string
  type: 'video' | 'detect' | 'summary'
  created_at: string
  updated_at: string
}

export interface VideoStatus {
  is_running: boolean
  current_source: string
  fps: number
  resolution: {
    width: number
    height: number
  }
  last_analysis: string
}