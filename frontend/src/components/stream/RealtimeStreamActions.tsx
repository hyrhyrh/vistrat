import React from 'react'
import { Space, Button, Tooltip, Popconfirm, Tag } from 'antd'
import {
  PlayCircleOutlined,
  StopOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  EyeOutlined,
  ReloadOutlined,
  InfoCircleOutlined
} from '@ant-design/icons'

interface RealtimeStream {
  stream_id: string
  config: {
    stream_name: string
    rtsp_url: string
    template_ids: string[]
    frame_interval: number
    auto_restart: boolean
    analysis_enabled: boolean
    alert_enabled: boolean
    storage_enabled: boolean
  }
  status: {
    status: string // 'stopped', 'starting', 'running', 'error', 'reconnecting'
    task_id?: string
    frames_processed: number
    alerts_generated: number
    connection_uptime: number
    error_message?: string
  }
}

interface RealtimeStreamActionsProps {
  stream: RealtimeStream
  onPlay: (stream: RealtimeStream) => void
  onStop: (stream: RealtimeStream) => void
  onEdit: (stream: RealtimeStream) => void
  onDelete: (streamId: string) => void
  onConfigure: (stream: RealtimeStream) => void
  onPreview?: (stream: RealtimeStream) => void
  onRestart?: (stream: RealtimeStream) => void
  onViewDetails?: (stream: RealtimeStream) => void
}

const RealtimeStreamActions: React.FC<RealtimeStreamActionsProps> = ({
  stream,
  onPlay,
  onStop,
  onEdit,
  onDelete,
  onConfigure,
  onPreview,
  onRestart,
  onViewDetails
}) => {
  const getStatusTag = (status: string) => {
    const statusMap = {
      'stopped': { color: 'default', text: '已停止' },
      'starting': { color: 'processing', text: '启动中' },
      'running': { color: 'success', text: '运行中' },
      'error': { color: 'error', text: '错误' },
      'reconnecting': { color: 'warning', text: '重连中' }
    }
    const config = statusMap[status as keyof typeof statusMap] || { color: 'default', text: '未知' }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const isRunning = stream.status.status === 'running'
  const isStopped = stream.status.status === 'stopped'
  const hasError = stream.status.status === 'error'

  return (
    <Space size="small" direction="vertical">
      {/* 状态显示 */}
      <div style={{ marginBottom: 8 }}>
        {getStatusTag(stream.status.status)}
        {stream.status.frames_processed > 0 && (
          <Tag color="blue">已处理 {stream.status.frames_processed} 帧</Tag>
        )}
        {stream.status.alerts_generated > 0 && (
          <Tag color="orange">告警 {stream.status.alerts_generated}</Tag>
        )}
      </div>

      {/* 操作按钮 */}
      <Space size="small">
        {onPreview && (
          <Tooltip title="预览流">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => onPreview(stream)}
            />
          </Tooltip>
        )}

        {/* 启动/停止按钮 */}
        {isStopped || hasError ? (
          <Tooltip title="启动分析">
            <Button
              type="text"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => onPlay(stream)}
              style={{ color: '#52c41a' }}
            />
          </Tooltip>
        ) : isRunning ? (
          <Tooltip title="停止分析">
            <Button
              type="text"
              size="small"
              icon={<StopOutlined />}
              onClick={() => onStop(stream)}
              style={{ color: '#ff4d4f' }}
            />
          </Tooltip>
        ) : (
          <Tooltip title="处理中...">
            <Button
              type="text"
              size="small"
              icon={<StopOutlined />}
              disabled
            />
          </Tooltip>
        )}

        {/* 重启按钮 */}
        {onRestart && isRunning && (
          <Tooltip title="重启分析">
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => onRestart(stream)}
            />
          </Tooltip>
        )}

        {/* 配置算法 */}
        <Tooltip title="配置算法">
          <Button
            type="text"
            size="small"
            icon={<SettingOutlined />}
            onClick={() => onConfigure(stream)}
          />
        </Tooltip>

        {/* 编辑流 */}
        <Tooltip title="编辑流配置">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => onEdit(stream)}
          />
        </Tooltip>

        {/* 查看详情 */}
        {onViewDetails && (
          <Tooltip title="查看详情">
            <Button
              type="text"
              size="small"
              icon={<InfoCircleOutlined />}
              onClick={() => onViewDetails(stream)}
            />
          </Tooltip>
        )}

        {/* 删除流 */}
        <Popconfirm
          title="确定要删除这个实时流吗？"
          description={
            isRunning 
              ? "流正在运行中，删除将停止分析。此操作无法恢复，请谨慎操作"
              : "删除后无法恢复，请谨慎操作"
          }
          onConfirm={() => onDelete(stream.stream_id)}
          okText="确定删除"
          cancelText="取消"
          okType="danger"
        >
          <Tooltip title="删除流">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            />
          </Tooltip>
        </Popconfirm>
      </Space>

      {/* 错误信息显示 */}
      {hasError && stream.status.error_message && (
        <div style={{ marginTop: 8 }}>
          <Tag color="error" style={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            错误: {stream.status.error_message}
          </Tag>
        </div>
      )}
    </Space>
  )
}

export default RealtimeStreamActions