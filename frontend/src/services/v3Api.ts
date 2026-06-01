/**
 * v3 API 服务客户端
 * 封装所有 /api/v3/ 端点调用，复用现有 axios 实例（含 auth 拦截器）
 */

import api from './api'
import type {
  VideoStream,
  VideoStreamCreate,
  VideoStreamUpdate,
  Alert,
  AlertListResponse,
  UpdateAlertStatusRequest,
  AnalysisTask,
  StartAnalysisRequest,
  StartAnalysisResponse,
} from '../types/v3'

// 现有 api 实例 baseURL 是 /api，所以 v3 路径从 /v3 开始
const V3 = '/v3'

export const v3StreamService = {
  list: (params?: { skip?: number; limit?: number }) =>
    api.get<VideoStream[]>(`${V3}/streams/`, { params }),
  create: (data: VideoStreamCreate) =>
    api.post<VideoStream>(`${V3}/streams/`, data),
  get: (id: string) =>
    api.get<VideoStream>(`${V3}/streams/${id}`),
  update: (id: string, data: VideoStreamUpdate) =>
    api.put<VideoStream>(`${V3}/streams/${id}`, data),
  delete: (id: string) =>
    api.delete(`${V3}/streams/${id}`),
}

export const v3AlertService = {
  list: (params?: {
    stream_id?: string
    status?: string
    limit?: number
    offset?: number
  }) => api.get<AlertListResponse>(`${V3}/alerts/`, { params }),
  get: (id: string) => api.get<Alert>(`${V3}/alerts/${id}`),
  updateStatus: (alertId: string, data: UpdateAlertStatusRequest) =>
    api.patch<{ status: string; new_status: string }>(
      `${V3}/alerts/${alertId}/status`,
      data
    ),
  feedbackStats: () => api.get(`${V3}/alerts/statistics/feedback`),
}

export const v3AnalysisService = {
  start: (data: StartAnalysisRequest) =>
    api.post<StartAnalysisResponse>(`${V3}/analysis/tasks/start`, data),
  stop: (taskId: string) =>
    api.post(`${V3}/analysis/tasks/${taskId}/stop`),
  list: (params?: { status?: string; stream_id?: string }) =>
    api.get<AnalysisTask[]>(`${V3}/analysis/tasks`, { params }),
  listActive: () => api.get(`${V3}/analysis/tasks/active`),
}
