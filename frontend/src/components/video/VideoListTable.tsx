import React, { useState } from 'react'
import { Table, Image, Tag, Progress, Badge, Tooltip } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import VideoActions from './VideoActions'
import AlertDrawer from '../alert/AlertDrawer'

interface VideoFile {
  id: string
  name: string
  original_filename: string
  thumbnail_path?: string
  status: string
  tags: string[]
  analysis_progress: number
  duration?: number
  file_size?: number
  created_at: string
  total_alerts: number
}

interface VideoListTableProps {
  videos: VideoFile[]
  loading: boolean
  playingVideoId?: string | null
  onPlay: (video: VideoFile) => void
  onEdit: (video: VideoFile) => void
  onDelete: (videoId: string) => void
  onConfigure: (video: VideoFile) => void
}

const VideoListTable: React.FC<VideoListTableProps> = ({
  videos,
  loading,
  playingVideoId,
  onPlay,
  onEdit,
  onDelete,
  onConfigure
}) => {
  const [alertDrawerVisible, setAlertDrawerVisible] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null)

  const handleViewAlerts = (video: VideoFile) => {
    console.log('🔔 点击查看告警按钮:', {
      videoId: video.id,
      videoName: video.name,
      totalAlerts: video.total_alerts
    })
    setSelectedVideo(video)
    setAlertDrawerVisible(true)
    console.log('✅ 告警抽屉状态已设置为true')
  }

  const handleCloseAlertDrawer = () => {
    setAlertDrawerVisible(false)
    setSelectedVideo(null)
  }
  const getStatusBadge = (status: string) => {
    const statusConfig = {
      'pending': { status: 'default', text: '待处理' },
      'PENDING': { status: 'default', text: '待处理' },
      'uploading': { status: 'processing', text: '上传中' },
      'UPLOADING': { status: 'processing', text: '上传中' },
      'ready': { status: 'success', text: '就绪' },
      'READY': { status: 'success', text: '就绪' },
      'analyzing': { status: 'processing', text: '分析中' },
      'ANALYZING': { status: 'processing', text: '分析中' },
      'completed': { status: 'success', text: '已完成' },
      'COMPLETED': { status: 'success', text: '已完成' },
      'error': { status: 'error', text: '错误' },
      'ERROR': { status: 'error', text: '错误' },
      'deleted': { status: 'default', text: '已删除' },
      'DELETED': { status: 'default', text: '已删除' }
    }
    
    const config = statusConfig[status] || statusConfig['pending']
    return <Badge status={config.status as any} text={config.text} />
  }

  const formatFileSize = (bytes: number): string => {
    if (!bytes) return '-'
    const units = ['B', 'KB', 'MB', 'GB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
      size /= 1024
      unitIndex++
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`
  }

  const formatDuration = (seconds: number): string => {
    if (!seconds) return '-'
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`
  }

  const columns: ColumnsType<VideoFile> = [
    {
      title: '视频信息',
      width: 300,
      render: (_, record) => (
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{ marginRight: 12 }}>
            {record.thumbnail_path ? (
              <Image
                width={80}
                height={45}
                src={`/api/files/${record.thumbnail_path}`}
                fallback="/placeholder-video.jpg"
                style={{ borderRadius: 4 }}
              />
            ) : (
              <div style={{
                width: 80,
                height: 45,
                background: '#f0f0f0',
                borderRadius: 4,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 12,
                color: '#999'
              }}>
                暂无缩略图
              </div>
            )}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ 
              fontWeight: 'bold', 
              marginBottom: 4,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {record.name}
            </div>
            <div style={{ 
              fontSize: 12, 
              color: '#666',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap'
            }}>
              {record.original_filename}
            </div>
            <div style={{ fontSize: 12, color: '#999', marginTop: 2 }}>
              {formatFileSize(record.file_size)} • {formatDuration(record.duration)}
            </div>
          </div>
        </div>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status) => getStatusBadge(status)
    },
    {
      title: '标签',
      dataIndex: 'tags',
      width: 150,
      render: (tags: string[]) => (
        <div style={{ maxHeight: 60, overflow: 'auto' }}>
          {tags.map(tag => (
            <Tag key={tag} size="small" style={{ marginBottom: 2 }}>
              {tag}
            </Tag>
          ))}
        </div>
      )
    },
    {
      title: '分析进度',
      width: 150,
      render: (_, record) => (
        <div>
          <Progress 
            percent={record.analysis_progress} 
            size="small"
            status={record.status === 'ERROR' ? 'exception' : 
                   record.analysis_progress === 100 ? 'success' : 'active'}
          />
          {record.total_alerts > 0 && (
            <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>
              {record.total_alerts} 条告警
            </div>
          )}
        </div>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 120,
      render: (date) => new Date(date).toLocaleDateString('zh-CN')
    },
    {
      title: '操作',
      width: 180,
      render: (_, record) => (
        <VideoActions
          video={record}
          isPlaying={playingVideoId === record.id}
          onPlay={onPlay}
          onEdit={onEdit}
          onDelete={onDelete}
          onConfigure={onConfigure}
          onViewAlerts={handleViewAlerts}
        />
      )
    }
  ]

  return (
    <>
      <Table
        columns={columns}
        dataSource={videos}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => 
            `第 ${range[0]}-${range[1]} 条，共 ${total} 个视频`,
          pageSizeOptions: ['10', '20', '50']
        }}
        scroll={{ x: 1000 }}
      />
      
      {/* 告警抽屉 */}
      <AlertDrawer
        open={alertDrawerVisible}
        onClose={handleCloseAlertDrawer}
        sourceId={selectedVideo?.id}
        sourceName={selectedVideo?.name}
        sourceType="video"
      />
    </>
  )
}

export default VideoListTable