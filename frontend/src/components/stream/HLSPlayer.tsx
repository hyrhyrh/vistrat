/**
 * HLS 视频播放器组件
 * 基于 hls.js 实现，替代 MJPEGPlayer，支持 mediamtx HLS 流播放
 */

import React, { useRef, useEffect, useState, useCallback } from 'react'
import Hls from 'hls.js'
import { Spin, Alert, Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

interface HLSPlayerProps {
  url: string
  autoPlay?: boolean
  muted?: boolean
  style?: React.CSSProperties
}

const MAX_RETRIES = 3

const HLSPlayer: React.FC<HLSPlayerProps> = ({
  url,
  autoPlay = true,
  muted = true,
  style,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const hlsRef = useRef<Hls | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const retryCountRef = useRef(0)

  const initHls = useCallback(() => {
    if (!videoRef.current) return

    // 清理上一个实例
    if (hlsRef.current) {
      hlsRef.current.destroy()
      hlsRef.current = null
    }
    setLoading(true)
    setError(null)

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
      })
      hlsRef.current = hls
      hls.loadSource(url)
      hls.attachMedia(videoRef.current)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setLoading(false)
        setError(null)
        retryCountRef.current = 0
        if (autoPlay) {
          videoRef.current?.play().catch(() => {})
        }
      })

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          if (retryCountRef.current < MAX_RETRIES) {
            const delay = Math.pow(2, retryCountRef.current) * 1000
            retryCountRef.current++
            setTimeout(() => {
              if (data.type === Hls.ErrorTypes.NETWORK_ERROR) {
                hls.startLoad()
              } else if (data.type === Hls.ErrorTypes.MEDIA_ERROR) {
                hls.recoverMediaError()
              } else {
                initHls()
              }
            }, delay)
          } else {
            setError(`视频流加载失败: ${data.details}`)
            setLoading(false)
          }
        }
      })
    } else if (
      videoRef.current.canPlayType('application/vnd.apple.mpegurl')
    ) {
      // Safari 原生 HLS 支持
      const video = videoRef.current
      video.src = url

      const handleLoaded = () => {
        setLoading(false)
        if (autoPlay) {
          video.play().catch(() => {})
        }
      }
      const handleError = () => {
        setError('视频流加载失败')
        setLoading(false)
      }

      video.addEventListener('loadedmetadata', handleLoaded)
      video.addEventListener('error', handleError)
    } else {
      setError('浏览器不支持 HLS 播放')
      setLoading(false)
    }
  }, [url, autoPlay])

  useEffect(() => {
    initHls()
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy()
        hlsRef.current = null
      }
    }
  }, [initHls])

  const handleRetry = () => {
    retryCountRef.current = 0
    initHls()
  }

  const containerStyle: React.CSSProperties = {
    position: 'relative',
    width: '100%',
    aspectRatio: '16 / 9',
    backgroundColor: '#000',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    ...style,
  }

  return (
    <div style={containerStyle}>
      <video
        ref={videoRef}
        muted={muted}
        playsInline
        style={{
          width: '100%',
          height: '100%',
          display: error ? 'none' : 'block',
        }}
      />
      {loading && !error && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'rgba(0,0,0,0.5)',
          }}
        >
          <Spin tip="正在连接视频流..." size="large" />
        </div>
      )}
      {error && (
        <div style={{ padding: 24, textAlign: 'center' }}>
          <Alert
            type="error"
            message="视频流加载失败"
            description={error}
            showIcon
            style={{ marginBottom: 16 }}
          />
          <Button icon={<ReloadOutlined />} onClick={handleRetry}>
            重试
          </Button>
        </div>
      )}
    </div>
  )
}

export default HLSPlayer
