import axios from 'axios'
import type { VideoConfig, PromptTemplate, VideoStatus } from '../types'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

// 请求拦截器：自动添加Authorization header
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token') || sessionStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器：处理401错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token过期或无效，清除本地存储
      console.warn('检测到401错误，清除登录状态并跳转到登录页')
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      sessionStorage.removeItem('token')
      sessionStorage.removeItem('user')

      // 跳转到登录页
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export const videoService = {
  startVideo: (config: VideoConfig) => 
    api.post('/video/start', config),
    
  stopVideo: () => 
    api.post('/video/stop'),
    
  getStatus: (): Promise<{ data: VideoStatus }> => 
    api.get('/video/status'),
    
  uploadVideo: (file: File) => {
    const formData = new FormData()
    formData.append('video', file)
    return api.post('/video/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  }
}

export const promptService = {
  getTemplates: (): Promise<{ data: PromptTemplate[] }> =>
    api.get('/prompts'),
    
  createTemplate: (template: Omit<PromptTemplate, 'id' | 'created_at' | 'updated_at'>) =>
    api.post('/prompts', template),
    
  updateTemplate: (id: string, template: Partial<PromptTemplate>) =>
    api.put(`/prompts/${id}`, template),
    
  deleteTemplate: (id: string) =>
    api.delete(`/prompts/${id}`),
    
  setActiveTemplate: (type: string, templateId: string) =>
    api.post(`/prompts/active/${type}/${templateId}`)
}

export const alertService = {
  getHistory: (limit = 50) =>
    api.get(`/alerts/history?limit=${limit}`),

  clearHistory: () =>
    api.delete('/alerts/history')
}

export default api