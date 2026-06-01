import { useEffect, useRef } from 'react'
import useSWR, { useSWRConfig } from 'swr'
import type {
  DetectionObject,
  ImageSize,
  ClipStatus,
  ClipEvent
} from '../types'

/**
 * 告警记录（对齐后端 /api/alerts/search 返回结构）
 *
 * 注：历史版本曾从 '../types/alert' 导入 Alert 类型，但该文件并不存在。
 * Week 4 统一就地定义，避免悬空引用，同时补齐 clip_* 字段。
 */
export interface Alert {
  id: string
  timestamp: string
  alert_type?: string
  algorithm_name?: string
  camera_name?: string
  video_name?: string
  image_path?: string
  confidence?: number
  detection_details?: unknown
  // 告警文字描述（后端 alert payload 中偶尔单独提供，用于详情页展示）
  description?: string
  detection_objects?: DetectionObject[]
  image_size?: ImageSize
  // Week 4：告警视频片段
  clip_url?: string
  clip_status?: ClipStatus
}

/**
 * useAlerts 的可选筛选参数，全部透传到 /api/alerts/search 查询串。
 * 纳入 SWR key 中，切换筛选条件时自动触发重新拉取并独立缓存。
 */
export interface AlertsFilters {
  algorithm_name?: string
  camera_name?: string
  start_time?: string
  end_time?: string
}

/**
 * 告警 API 响应接口（对齐后端分页结构）
 */
export interface AlertsResponse {
  data: Alert[]
  total: number
  page: number
  size: number
  // 某些接口用 success 标记，保留可选
  success?: boolean
}

/**
 * Fetcher 函数 - SWR 使用
 */
const fetcher = async (url: string): Promise<AlertsResponse> => {
  const token = localStorage.getItem('token')

  const response = await fetch(url, {
    headers: {
      Authorization: token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json'
    }
  })

  if (!response.ok) {
    throw new Error(`API请求失败: ${response.status}`)
  }

  return response.json()
}

// SWR 缓存 key 前缀，便于 mutate 批量匹配
const ALERTS_KEY_PREFIX = 'alerts-list:'

/**
 * 根据 VITE_API_URL 推导 WebSocket URL
 * - 有 VITE_API_URL：直接把 http(s) 替换成 ws(s)
 * - 否则基于 window.location（dev server 通过 Vite 代理转发 /alerts）
 */
function resolveAlertsWsUrl(): string {
  const apiUrl = import.meta.env.VITE_API_URL as string | undefined
  if (apiUrl) {
    return apiUrl.replace(/^http/i, 'ws').replace(/\/$/, '') + '/alerts'
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}/alerts`
}

/**
 * 订阅 /alerts WebSocket，专门处理 clip_ready / clip_failed 事件，
 * 并对所有 useAlerts 生成的 SWR 缓存做局部 patch（不触发重新拉接口）。
 *
 * 注：原 alert 实时推送由 useAlertWebSocket（useWebSocket.ts）处理，
 * 这里只订阅 clip 事件分支，两个监听并存；后端同一通道广播不冲突。
 */
function useClipEventsSubscription(): void {
  const { mutate } = useSWRConfig()
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let closedByUnmount = false
    let reconnectTimer: number | undefined

    const connect = () => {
      try {
        const ws = new WebSocket(resolveAlertsWsUrl())
        wsRef.current = ws

        ws.addEventListener('message', (evt) => {
          let msg: unknown
          try {
            msg = JSON.parse(evt.data)
          } catch {
            // 非 JSON 消息忽略（兼容其他广播格式）
            return
          }
          if (!msg || typeof msg !== 'object') return
          const event = msg as Partial<ClipEvent>
          if (event.type !== 'clip_ready' && event.type !== 'clip_failed') {
            return
          }
          const alertId = event.alert_id
          if (!alertId) return

          // 局部更新所有以 ALERTS_KEY_PREFIX 开头的分页缓存
          mutate(
            (key) => typeof key === 'string' && key.startsWith(ALERTS_KEY_PREFIX),
            (cached: AlertsResponse | undefined) => {
              if (!cached || !Array.isArray(cached.data)) return cached
              // 只在该页包含目标 alert 时才生成新对象，避免无谓渲染
              const hit = cached.data.some((a) => a.id === alertId)
              if (!hit) return cached
              return {
                ...cached,
                data: cached.data.map((a) => {
                  if (a.id !== alertId) return a
                  if (event.type === 'clip_ready') {
                    return {
                      ...a,
                      clip_url: event.clip_url,
                      clip_status: 'ready' as ClipStatus
                    }
                  }
                  return { ...a, clip_status: 'failed' as ClipStatus }
                })
              }
            },
            { revalidate: false }
          )
        })

        ws.addEventListener('close', () => {
          if (closedByUnmount) return
          // 简单退避重连，3s
          reconnectTimer = window.setTimeout(connect, 3000)
        })

        ws.addEventListener('error', () => {
          // 关闭事件会接着触发，统一走 close 分支重连
          try {
            ws.close()
          } catch {
            /* noop */
          }
        })
      } catch (err) {
        console.error('[useClipEventsSubscription] WS 连接失败', err)
        reconnectTimer = window.setTimeout(connect, 3000)
      }
    }

    connect()

    return () => {
      closedByUnmount = true
      if (reconnectTimer !== undefined) {
        window.clearTimeout(reconnectTimer)
      }
      if (wsRef.current) {
        try {
          wsRef.current.close()
        } catch {
          /* noop */
        }
        wsRef.current = null
      }
    }
  }, [mutate])
}

/**
 * useAlerts 的可选入参。兼容旧的位置参数用法（size, page, refreshInterval），
 * 新代码推荐使用对象形式以便传递筛选条件。
 */
export interface UseAlertsOptions extends AlertsFilters {
  size?: number
  page?: number
  refreshInterval?: number
}

/**
 * 使用 SWR 获取告警数据的 Hook
 *
 * 支持两种调用形式（保持向后兼容）：
 *   useAlerts(15, 1, 5000)
 *   useAlerts({ size: 15, page: 1, algorithm_name: 'xxx', start_time, end_time })
 */
export function useAlerts(
  sizeOrOptions: number | UseAlertsOptions = 15,
  page: number = 1,
  refreshInterval: number = 5000
) {
  // 归一化参数：对象形式 vs 位置参数形式
  const opts: UseAlertsOptions =
    typeof sizeOrOptions === 'number'
      ? { size: sizeOrOptions, page, refreshInterval }
      : {
          size: sizeOrOptions.size ?? 15,
          page: sizeOrOptions.page ?? 1,
          refreshInterval: sizeOrOptions.refreshInterval ?? 5000,
          algorithm_name: sizeOrOptions.algorithm_name,
          camera_name: sizeOrOptions.camera_name,
          start_time: sizeOrOptions.start_time,
          end_time: sizeOrOptions.end_time
        }

  const effectiveSize = opts.size ?? 15
  const effectivePage = opts.page ?? 1
  const effectiveRefresh = opts.refreshInterval ?? 5000

  const baseUrl = (import.meta.env.VITE_API_URL as string | undefined) || 'http://localhost:16532'

  // 构造查询串：仅拼接有值的筛选参数，避免把 undefined 发给后端
  const queryParams = new URLSearchParams()
  queryParams.set('size', String(effectiveSize))
  queryParams.set('page', String(effectivePage))
  if (opts.algorithm_name) queryParams.set('algorithm_name', opts.algorithm_name)
  if (opts.camera_name) queryParams.set('camera_name', opts.camera_name)
  if (opts.start_time) queryParams.set('start_time', opts.start_time)
  if (opts.end_time) queryParams.set('end_time', opts.end_time)
  const apiUrl = `${baseUrl}/api/alerts/search?${queryParams.toString()}`

  // 自定义 key：SWR 允许 key 与请求 URL 解耦，这里用前缀便于 WS 局部 mutate 匹配。
  // 筛选条件也参与 key 生成——不同筛选独立缓存。
  const filterKey = [
    opts.algorithm_name ?? '',
    opts.camera_name ?? '',
    opts.start_time ?? '',
    opts.end_time ?? ''
  ].join('|')
  const swrKey = `${ALERTS_KEY_PREFIX}${effectivePage}:${effectiveSize}:${filterKey}`

  const { data, error, isLoading, mutate } = useSWR<AlertsResponse>(
    swrKey,
    () => fetcher(apiUrl),
    {
      refreshInterval: effectiveRefresh,
      revalidateOnFocus: true,
      revalidateOnReconnect: true,
      shouldRetryOnError: true,
      errorRetryCount: 3,
      errorRetryInterval: 5000,
      dedupingInterval: 2000
    }
  )

  // 订阅 clip 事件，局部 patch 当前 hook 及其他分页缓存
  useClipEventsSubscription()

  return {
    alerts: data?.data || [],
    total: data?.total || 0,
    page: data?.page || effectivePage,
    size: data?.size || effectiveSize,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate
  }
}

/**
 * 使用 SWR 获取视频流列表的 Hook
 */
export function useVideoStreams(refreshInterval: number = 10000) {
  const baseUrl = (import.meta.env.VITE_API_URL as string | undefined) || 'http://localhost:16532'
  const apiUrl = `${baseUrl}/api/video-streams`

  const { data, error, isLoading, mutate } = useSWR(apiUrl, (url: string) => fetcher(url), {
    refreshInterval,
    revalidateOnFocus: false,
    dedupingInterval: 5000
  })

  return {
    streams: Array.isArray(data) ? data : [],
    isLoading,
    isError: !!error,
    error,
    refresh: mutate
  }
}
