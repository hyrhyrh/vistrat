import { useState, useEffect, useRef, useCallback } from 'react'
import type { AlertMessage } from '../types'

export const useAlertWebSocket = () => {
  const [alerts, setAlerts] = useState<AlertMessage[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const connect = useCallback(() => {
    try {
      wsRef.current = new WebSocket('ws://localhost:16532/alerts')
      
      wsRef.current.onopen = () => {
        setIsConnected(true)
        console.log('Alert WebSocket connected')
      }
      
      wsRef.current.onmessage = (event) => {
        const alert = JSON.parse(event.data) as AlertMessage
        setAlerts(prev => [alert, ...prev].slice(0, 100))
      }
      
      wsRef.current.onclose = () => {
        setIsConnected(false)
        console.log('Alert WebSocket disconnected')
        setTimeout(connect, 3000)
      }
      
      wsRef.current.onerror = (error) => {
        console.error('Alert WebSocket error:', error)
        setIsConnected(false)
      }
    } catch (error) {
      console.error('Failed to connect to alert WebSocket:', error)
    }
  }, [])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  useEffect(() => {
    connect()
    return disconnect
  }, [connect, disconnect])

  return { alerts, isConnected, connect, disconnect }
}

export const useVideoWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  const connect = useCallback(() => {
    try {
      wsRef.current = new WebSocket('ws://localhost:16532/video_feed')
      
      wsRef.current.onopen = () => {
        setIsConnected(true)
        console.log('Video WebSocket connected')
      }
      
      wsRef.current.onmessage = (event) => {
        if (canvasRef.current && event.data instanceof Blob) {
          const img = new Image()
          img.onload = () => {
            const canvas = canvasRef.current
            if (canvas) {
              const ctx = canvas.getContext('2d')
              if (ctx) {
                canvas.width = img.width
                canvas.height = img.height
                ctx.drawImage(img, 0, 0)
              }
            }
            URL.revokeObjectURL(img.src)
          }
          img.src = URL.createObjectURL(event.data)
        }
      }
      
      wsRef.current.onclose = () => {
        setIsConnected(false)
        console.log('Video WebSocket disconnected')
      }
      
      wsRef.current.onerror = (error) => {
        console.error('Video WebSocket error:', error)
        setIsConnected(false)
      }
    } catch (error) {
      console.error('Failed to connect to video WebSocket:', error)
    }
  }, [])

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  return { isConnected, connect, disconnect, canvasRef }
}