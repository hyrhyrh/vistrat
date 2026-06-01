/**
 * v3 API TypeScript 类型定义
 * 对应后端 /api/v3/ 端点的请求和响应结构
 */

// === 视频流 ===
export interface VideoStream {
  id: string
  name: string
  stream_url: string
  stream_type: 'RTSP' | 'RTMP' | 'HLS' | 'WEBRTC' | 'HTTP_FLV' | 'LOCAL_CAMERA'
  location?: string
  group_name?: string
  description?: string
  tags: string[]
  status: 'ONLINE' | 'OFFLINE'
  project_id?: string
  created_at: string
  updated_at: string
  hls_url: string | null
}

export interface VideoStreamCreate {
  name: string
  stream_url: string
  stream_type?: string
  location?: string
  group_name?: string
  description?: string
  tags?: string[]
  project_id?: string
}

export interface VideoStreamUpdate {
  name?: string
  stream_url?: string
  stream_type?: string
  location?: string
  group_name?: string
  description?: string
  tags?: string[]
  status?: string
}

// === 告警 ===
export type AlertStatus = 'pending' | 'confirmed' | 'dismissed' | 'resolved'

export interface Alert {
  id: string
  stream_id: string
  task_id?: string
  level: string
  status: AlertStatus
  result?: Record<string, any>
  snapshot_path?: string
  message?: string
  project_id?: string
  created_at: string
  updated_at: string
}

export interface AlertListResponse {
  items: Alert[]
  total: number
}

export interface UpdateAlertStatusRequest {
  new_status: AlertStatus
  created_at: string
  feedback_by?: string
}

// === 分析任务 ===
export type TaskStatus = 'pending' | 'running' | 'paused' | 'stopped' | 'completed' | 'failed'

export interface AnalysisTask {
  id: string
  stream_id: string
  status: TaskStatus
  prompt?: string
  config?: Record<string, any>
  result?: Record<string, any>
  started_at?: string
  stopped_at?: string
  error_message?: string
  project_id?: string
  created_at: string
  updated_at: string
}

export interface StartAnalysisRequest {
  stream_id: string
  prompt?: string
  config?: Record<string, any>
  project_id?: string
}

export interface StartAnalysisResponse {
  task_id: string
  status: string
  stream_id: string
}
