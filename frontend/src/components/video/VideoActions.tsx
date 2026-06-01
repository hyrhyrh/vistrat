import React from 'react'
import { Space, Button, Tooltip, Popconfirm } from 'antd'
import {
  PlayCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  EyeOutlined,
  BellOutlined
} from '@ant-design/icons'

interface VideoActionsProps {
  video: any
  isPlaying?: boolean
  onPlay: (video: any) => void
  onEdit: (video: any) => void
  onDelete: (videoId: string) => void
  onConfigure: (video: any) => void
  onPreview?: (video: any) => void
  onViewAlerts?: (video: any) => void
}

const VideoActions: React.FC<VideoActionsProps> = ({
  video,
  isPlaying = false,
  onPlay,
  onEdit,
  onDelete,
  onConfigure,
  onPreview,
  onViewAlerts
}) => {
  return (
    <Space size="small">
      {onPreview && (
        <Tooltip title="预览">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onPreview(video)}
          />
        </Tooltip>
      )}
      
      {onViewAlerts && (
        <Tooltip title={`查看告警 (${video.total_alerts || 0})`}>
          <Button
            type="text"
            size="small"
            icon={<BellOutlined />}
            onClick={() => onViewAlerts(video)}
            style={{ 
              color: video.total_alerts > 0 ? '#ff4d4f' : undefined 
            }}
          />
        </Tooltip>
      )}
      
      <Tooltip title={isPlaying ? "加载中..." : "播放视频"}>
        <Button
          type="text"
          size="small"
          icon={<PlayCircleOutlined />}
          onClick={() => onPlay(video)}
          loading={isPlaying}
          disabled={isPlaying}
          //disabled={video.status !== 'READY' && video.status !== 'COMPLETED'}
        />
      </Tooltip>
      
      <Tooltip title="配置算法">
        <Button
          type="text"
          size="small"
          icon={<SettingOutlined />}
          onClick={() => onConfigure(video)}
          disabled={video.status === 'DELETED'}
        />
      </Tooltip>
      
      <Tooltip title="编辑视频">
        <Button
          type="text"
          size="small"
          icon={<EditOutlined />}
          onClick={() => onEdit(video)}
        />
      </Tooltip>
      
      <Popconfirm
        title="确定要删除这个视频吗？"
        description="删除后无法恢复，请谨慎操作"
        onConfirm={() => onDelete(video.id)}
        okText="确定删除"
        cancelText="取消"
        okType="danger"
      >
        <Tooltip title="删除视频">
          <Button
            type="text"
            size="small"
            danger
            icon={<DeleteOutlined />}
          />
        </Tooltip>
      </Popconfirm>
    </Space>
  )
}

export default VideoActions