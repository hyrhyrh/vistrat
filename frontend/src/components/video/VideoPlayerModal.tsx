import React, { useRef, useEffect, useState } from 'react'
import { Modal, Card, Space, Typography, Spin, Alert } from 'antd'
import {
  ExclamationCircleOutlined
} from '@ant-design/icons'

const { Text } = Typography

interface VideoPlayerModalProps {
  open: boolean
  onCancel: () => void
  video: any
}

const VideoPlayerModal: React.FC<VideoPlayerModalProps> = ({
  open,
  onCancel,
  video
}) => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [duration, setDuration] = useState(0)
  const [videoUrl, setVideoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 获取视频URL
  useEffect(() => {
    if (!open || !video) {
      setVideoUrl('')
      setError('')
      return
    }

    const fetchVideo = async () => {
      setLoading(true)
      setError('')
      
      try {
        // 方案1：通过后端代理流API直接获取视频（推荐）
        const apiUrl = `/api/video/files/${video.original_filename}`
        
        try {
          const testResponse = await fetch(apiUrl, { method: 'HEAD' })
          if (testResponse.ok) {
            console.log('使用后端代理API:', apiUrl)
            setVideoUrl(apiUrl)
            setLoading(false)
            return
          }
        } catch (e) {
          console.warn('后端代理API不可访问，尝试视频ID流播方法')
        }

        // 方案2：通过视频ID流播接口
        if (video.id) {
          const streamUrl = `/api/video-files/stream/${video.id}`
          try {
            const testResponse = await fetch(streamUrl, { method: 'HEAD' })
            if (testResponse.ok) {
              console.log('使用视频流播接口:', streamUrl)
              setVideoUrl(streamUrl)
              setLoading(false)
              return
            }
          } catch (e) {
            console.warn('视频流播接口不可访问')
          }
        }

        throw new Error('所有视频访问方法都失败了')
      } catch (error) {
        console.error('视频加载失败:', error)
        setError('视频加载失败，请检查文件是否存在或网络连接')
      } finally {
        setLoading(false)
      }
    }

    fetchVideo()

    // 清理函数
    return () => {
      if (videoUrl && videoUrl.startsWith('blob:')) {
        URL.revokeObjectURL(videoUrl)
      }
    }
  }, [open, video])

  useEffect(() => {
    if (open && videoRef.current && videoUrl) {
      // 视频已加载，可以播放
    }
  }, [open, videoUrl])



  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration)
    }
  }

  const formatTime = (time: number): string => {
    const minutes = Math.floor(time / 60)
    const seconds = Math.floor(time % 60)
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  }


  // 清理blob URL的函数
  const handleClose = () => {
    if (videoUrl && videoUrl.startsWith('blob:')) {
      URL.revokeObjectURL(videoUrl)
    }
    setVideoUrl('')
    setError('')
    onCancel()
  }

  return (
    <Modal
      title={`播放视频: ${video?.name || '未知视频'}`}
      open={open}
      onCancel={handleClose}
      width="60vw"
      footer={null}
      destroyOnHidden
      style={{
        minWidth: 800,
        maxWidth: 1400
      }}
    >
      {video && (
        <div>
          {/* 视频信息卡片 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space split={<span style={{ color: '#d9d9d9' }}>|</span>}>
              <Text type="secondary">文件名: {video.original_filename}</Text>
              <Text type="secondary">时长: {formatTime(video.duration || 0)}</Text>
              <Text type="secondary">分辨率: {video.width}x{video.height}</Text>
              <Text type="secondary">帧率: {video.fps}fps</Text>
            </Space>
          </Card>

          {/* 视频播放器 */}
          <div style={{ 
            position: 'relative', 
            background: '#000', 
            borderRadius: 8,
            overflow: 'hidden',
            minHeight: '400px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            {loading ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                color: 'white'
              }}>
                <Spin size="large" />
                <Text style={{ color: 'white', marginTop: 16 }}>视频加载中...</Text>
              </div>
            ) : error ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                padding: 32
              }}>
                <ExclamationCircleOutlined style={{ fontSize: 48, color: '#ff4d4f', marginBottom: 16 }} />
                <Alert
                  message="视频加载失败"
                  description={error}
                  type="error"
                  showIcon={false}
                  style={{ backgroundColor: 'transparent', border: 'none' }}
                />
              </div>
            ) : videoUrl ? (
              <video
                ref={videoRef}
                controls
                style={{ 
                  width: '100%', 
                  height: 'auto',
                  maxHeight: '500px',
                  objectFit: 'contain'
                }}
                onLoadedMetadata={handleLoadedMetadata}
                onError={(e) => {
                  console.error('视频播放错误:', e)
                  setError('视频播放失败，请检查文件格式')
                }}
                preload="metadata"
                src={videoUrl}
              >
                您的浏览器不支持视频播放
              </video>
            ) : (
              <Text style={{ color: 'white' }}>无法加载视频</Text>
            )}
          </div>

        </div>
      )}
    </Modal>
  )
}

export default VideoPlayerModal