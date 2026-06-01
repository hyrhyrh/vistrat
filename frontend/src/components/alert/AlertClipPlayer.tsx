import React, { useState, useEffect, useRef } from 'react'
import { Spin, Empty, Button } from 'antd'
import {
  LoadingOutlined,
  WarningOutlined,
  StopOutlined,
  ReloadOutlined
} from '@ant-design/icons'
import type { ClipStatus } from '../../types'

export interface AlertClipPlayerProps {
  clipUrl?: string
  clipStatus?: ClipStatus
  /** 可选封面图（通常用告警静态帧 URL） */
  poster?: string
  width?: number | string
  height?: number | string
  /** 默认 false；Modal 首次打开通常不自动播放，避免打扰用户 */
  autoPlay?: boolean
  onPlayError?: (e: Error) => void
}

/**
 * 告警视频片段播放器
 * - ready + clipUrl：原生 <video> 控件，浏览器原生 MP4 播放
 * - pending / clipUrl 为空：灰色占位 + Spin，提示"生成中"
 * - failed：灰色占位 + 警告图标 + 重试按钮（本期占位，不实装）
 * - skipped：提示"未生成片段"
 */
const AlertClipPlayer: React.FC<AlertClipPlayerProps> = ({
  clipUrl,
  clipStatus,
  poster,
  width = '100%',
  height = 400,
  autoPlay = false,
  onPlayError
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  // 播放失败本地 state，优先级高于 clipStatus（运行时 URL 过期等情况）
  const [playbackError, setPlaybackError] = useState<string | null>(null)

  // clipUrl 变化时重置播放错误（新片段）
  useEffect(() => {
    setPlaybackError(null)
  }, [clipUrl])

  // 容器基础样式
  const baseBoxStyle: React.CSSProperties = {
    width,
    height,
    background: '#f5f5f5',
    border: '1px dashed #d9d9d9',
    borderRadius: 4,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    color: '#8c8c8c',
    boxSizing: 'border-box',
    padding: 16
  }

  // 决议最终状态：有播放错误 → failed 视觉；无 clipUrl 且 status=ready → 降级为 pending
  const effectiveStatus: ClipStatus = (() => {
    if (playbackError) return 'failed'
    if (clipStatus === 'ready' && !clipUrl) return 'pending'
    if (!clipStatus && !clipUrl) return 'pending'
    return clipStatus ?? 'pending'
  })()

  // failed 占位（含重试按钮占位）
  if (effectiveStatus === 'failed') {
    return (
      <div style={baseBoxStyle} data-testid="clip-player-failed">
        <WarningOutlined style={{ fontSize: 32, color: '#faad14' }} />
        <div>{playbackError ?? '视频片段生成失败'}</div>
        <Button
          size="small"
          icon={<ReloadOutlined />}
          onClick={() => {
            // 本期暂不实装重试（等后端提供 /clips/{alert_id}/retry）
            // 先打 console，保留 UI 入口
            console.warn('[AlertClipPlayer] 重试生成片段暂未实装')
          }}
        >
          重试
        </Button>
      </div>
    )
  }

  // skipped 占位
  if (effectiveStatus === 'skipped') {
    return (
      <div style={baseBoxStyle} data-testid="clip-player-skipped">
        <Empty
          image={<StopOutlined style={{ fontSize: 32, color: '#bfbfbf' }} />}
          styles={{ image: { height: 40 } }}
          description="该告警未生成视频片段"
        />
      </div>
    )
  }

  // pending 占位（含无 clipUrl 降级）
  if (effectiveStatus === 'pending') {
    return (
      <div style={baseBoxStyle} data-testid="clip-player-pending">
        <Spin indicator={<LoadingOutlined style={{ fontSize: 28 }} spin />} />
        <div>视频片段生成中…</div>
        <div style={{ fontSize: 12, color: '#bfbfbf' }}>
          后端需约 10 秒完成生成，请稍候
        </div>
      </div>
    )
  }

  // ready + clipUrl：渲染 <video>
  return (
    <video
      ref={videoRef}
      data-testid="clip-player-video"
      src={clipUrl}
      poster={poster}
      controls
      preload="metadata"
      autoPlay={autoPlay}
      style={{
        width,
        height,
        background: '#000',
        borderRadius: 4,
        display: 'block',
        objectFit: 'contain'
      }}
      onError={() => {
        const err = new Error('视频片段播放失败（URL 可能已过期或文件损坏）')
        setPlaybackError(err.message)
        onPlayError?.(err)
      }}
    >
      您的浏览器不支持 HTML5 video 标签
    </video>
  )
}

export { AlertClipPlayer }
export default AlertClipPlayer
