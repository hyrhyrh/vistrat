import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Tooltip,
  Badge,
  Switch,
  Popconfirm,
  List,
  Typography,
  Drawer,
  Alert,
  Descriptions,
  Divider
} from 'antd'
import {
  VideoCameraOutlined,
  PlusOutlined,
  PlayCircleOutlined,
  SettingOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ThunderboltOutlined,
  BellOutlined,
  DownOutlined,
  EyeOutlined,
  PauseCircleOutlined,
  UpOutlined,
  ClockCircleOutlined
} from '@ant-design/icons'

import StreamAlgorithmModal from '../components/stream/StreamAlgorithmModal'
import SimpleStreamAlgorithmModal from '../components/stream/SimpleStreamAlgorithmModal'
import StreamPlayerModal from '../components/stream/StreamPlayerModal'
import QuickStreamModal from '../components/stream/QuickStreamModal'
import AlertDrawer from '../components/alert/AlertDrawer'

const { TextArea } = Input
const { Option } = Select

interface VideoStream {
  id: string
  name: string
  stream_url: string
  stream_type: string
  status: string
  location?: string
  group_name?: string
  description?: string
  tags: string[]
  thumbnail_path?: string
  analysis_status: string
  total_analysis_count: number
  total_alerts_count: number  // 修正: 与后端返回字段一致
  created_at: string
  last_online_at?: string
  fps?: number
  width?: number
  height?: number
}

const VideoStreamPage: React.FC = () => {
  const [streams, setStreams] = useState<VideoStream[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [configModalVisible, setConfigModalVisible] = useState(false)
  const [playerModalVisible, setPlayerModalVisible] = useState(false)
  const [selectedStream, setSelectedStream] = useState<VideoStream | null>(null)
  const [alertDrawerVisible, setAlertDrawerVisible] = useState(false)
  const [alertSelectedStream, setAlertSelectedStream] = useState<VideoStream | null>(null)
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([])
  const [streamTasks, setStreamTasks] = useState<{ [streamId: string]: any[] }>({})
  const [taskDetailVisible, setTaskDetailVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<any | null>(null)
  
  const [statistics, setStatistics] = useState({
    total_streams: 0,
    by_status: {},
    by_group: {},
    online_rate: 0
  })
  
  const [searchParams, setSearchParams] = useState({})
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()
  const [searchForm] = Form.useForm()

  // WebSocket 引用（按需连接）
  const [wsRef, setWsRef] = useState<WebSocket | null>(null)
  const [healthCheckInProgress, setHealthCheckInProgress] = useState(false)

  useEffect(() => {
    loadStreams()
    loadStatistics()
  }, [])

  // 建立临时 WebSocket 连接接收健康状态更新
  const connectTemporaryWebSocket = () => {
    // 如果已有连接在进行中，不重复建立
    if (wsRef || healthCheckInProgress) {
      console.log('健康检查正在进行中，跳过重复连接')
      return
    }

    setHealthCheckInProgress(true)

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.hostname
    // 开发环境直接连接后端16532端口，生产环境使用当前端口
    const wsPort = import.meta.env.DEV ? '16532' : (window.location.port || '80')
    const wsUrl = `${wsProtocol}//${wsHost}:${wsPort}/video-streams/ws/health-status`

    try {
      const ws = new WebSocket(wsUrl)
      setWsRef(ws)

      // 接收到的更新数量（用于判断是否完成）
      let receivedUpdates = 0
      let closeTimer: NodeJS.Timeout | null = null

      ws.onopen = () => {
        console.log('WebSocket 临时连接已建立')

        // 设置超时自动关闭（30秒后）
        closeTimer = setTimeout(() => {
          console.log('健康检查超时，关闭连接')
          ws.close()
          setHealthCheckInProgress(false)
          setWsRef(null)
        }, 30000)
      }

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)

          if (message.type === 'health_update') {
            receivedUpdates++

            // 更新对应流的健康状态
            setStreams(prevStreams =>
              prevStreams.map(stream => {
                if (stream.id === message.stream_id) {
                  return {
                    ...stream,
                    status: message.data.health_status?.toUpperCase() || stream.status
                  }
                }
                return stream
              })
            )

            // 如果接收到足够的更新（流数量），5秒后关闭连接
            if (closeTimer && receivedUpdates >= streams.length) {
              clearTimeout(closeTimer)
              closeTimer = setTimeout(() => {
                console.log(`已接收 ${receivedUpdates} 个状态更新，关闭连接`)
                ws.close()
              }, 5000)
            }
          }
        } catch (error) {
          console.error('解析 WebSocket 消息失败:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket 错误:', error)
        if (closeTimer) clearTimeout(closeTimer)
      }

      ws.onclose = () => {
        console.log('WebSocket 临时连接已关闭')
        if (closeTimer) clearTimeout(closeTimer)
        setHealthCheckInProgress(false)
        setWsRef(null)
      }
    } catch (error) {
      console.error('WebSocket 连接失败:', error)
      setHealthCheckInProgress(false)
      setWsRef(null)
    }
  }

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      if (wsRef) {
        wsRef.close()
      }
    }
  }, [wsRef])

  // 加载指定视频流的任务列表
  const loadStreamTasks = async (streamId: string) => {
    try {
      const response = await fetch(`/api/stream-tasks/?stream_id=${streamId}`)
      const data = await response.json()

      if (Array.isArray(data)) {
        setStreamTasks(prev => ({
          ...prev,
          [streamId]: data
        }))
      }
    } catch (error) {
      console.error('加载任务列表失败:', error)
      message.error('加载任务列表失败')
    }
  }

  // 启用/停用任务
  const toggleTaskActive = async (taskId: string, isActive: boolean, streamId: string) => {
    try {
      const action = isActive ? 'disable' : 'enable'
      const response = await fetch(`/api/stream-tasks/${taskId}/${action}`, {
        method: 'POST'
      })

      if (response.ok) {
        message.success(`任务已${isActive ? '停用' : '启用'}`)
        await loadStreamTasks(streamId)
      } else {
        throw new Error('操作失败')
      }
    } catch (error) {
      message.error(`${isActive ? '停用' : '启用'}任务失败`)
    }
  }

  // 启动/停止分析
  const toggleTaskAnalysis = async (taskId: string, isRunning: boolean, streamId: string) => {
    try {
      const action = isRunning ? 'stop' : 'start'
      const response = await fetch(`/api/stream-tasks/${taskId}/${action}`, {
        method: 'POST'
      })

      const result = await response.json()

      if (response.ok && result.success !== false) {
        message.success(`分析已${isRunning ? '停止' : '启动'}`)
        await loadStreamTasks(streamId)
      } else {
        throw new Error(result.message || '操作失败')
      }
    } catch (error: any) {
      message.error(error.message || `${isRunning ? '停止' : '启动'}分析失败`)
    }
  }

  // 删除任务
  const deleteTask = async (taskId: string, streamId: string) => {
    try {
      const response = await fetch(`/api/stream-tasks/${taskId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        message.success('任务已删除')
        await loadStreamTasks(streamId)
      } else {
        throw new Error('删除失败')
      }
    } catch (error) {
      message.error('删除任务失败')
    }
  }

  // 查看任务详情
  const showTaskDetail = (task: any) => {
    console.log('显示任务详情:', task)
    setSelectedTask(task)
    setTaskDetailVisible(true)
  }

  // 格式化时间配置显示
  const formatTimeConfig = (timeConfig: any) => {
    if (!timeConfig?.enabled) {
      return <Tag color="default">全天运行</Tag>
    }

    const ranges = timeConfig.time_ranges || []
    if (ranges.length === 0) {
      return <Tag color="default">全天运行</Tag>
    }

    return (
      <div>
        {ranges.map((range: any, index: number) => (
          <Tag key={index} color="blue" style={{ marginBottom: 4 }}>
            {range.start_time}-{range.end_time}
            {range.days?.length < 7 && (
              <span style={{ marginLeft: 4 }}>
                ({range.days?.length || 0}天)
              </span>
            )}
          </Tag>
        ))}
      </div>
    )
  }

  const { Text } = Typography

  // 获取任务状态显示（简化版：只显示运行中/已停用/未知状态）
  const getTaskStatusDisplay = (task: any) => {
    // 已停用
    if (!task.is_active) {
      return <Badge status="default" text="已停用" />
    }

    // 运行中
    if (task.is_active) {
      return <Badge status="processing" text="运行中" />
    }

    // 其他情况统一显示为未知状态
    return <Badge status="warning" text="未知状态" />
  }

  const loadStreams = async (params: any = {}) => {
    setLoading(true)
    try {
      const filteredParams = Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null && value !== '')
        .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})

      const queryParams = new URLSearchParams(filteredParams).toString()
      const response = await fetch(`/api/video-streams/${queryParams ? '?' + queryParams : ''}`)
      const data = await response.json()
      setStreams(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载视频流列表失败')
      setStreams([])
    } finally {
      setLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      const response = await fetch('/api/video-streams/statistics/summary')
      const result = await response.json()

      if (result.success && result.data) {
        // 将API返回的数据格式转换为组件期望的格式
        setStatistics({
          total_streams: result.data.total_count,
          online_rate: result.data.online_rate,
          by_status: {
            ONLINE: result.data.online_count,
            OFFLINE: result.data.offline_count
          },
          by_group: result.data.group_statistics || {}
        })
      }
    } catch (error) {
      console.error('加载统计信息失败:', error)
    }
  }

  const handleSearch = (params: any) => {
    setSearchParams(params)
    // 搜索时触发健康检查并建立临时 WebSocket 连接接收更新
    loadStreams({ ...params, trigger_health_check: true })
    connectTemporaryWebSocket()
  }

  const handleReset = () => {
    setSearchParams({})
    searchForm.resetFields()
    // 重置时触发健康检查并建立临时 WebSocket 连接接收更新
    loadStreams({ trigger_health_check: true })
    connectTemporaryWebSocket()
  }

  const handlePlay = (stream: VideoStream) => {
    setSelectedStream(stream)
    setPlayerModalVisible(true)
  }

  const handleEdit = (stream: VideoStream) => {
    setSelectedStream(stream)
    editForm.setFieldsValue({
      name: stream.name,
      stream_url: stream.stream_url,
      stream_type: stream.stream_type,
      description: stream.description,
      location: stream.location,
      group_name: stream.group_name,
      tags: stream.tags
    })
    setEditModalVisible(true)
  }

  const handleDelete = async (streamId: string) => {
    try {
      const response = await fetch(`/api/video-streams/${streamId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        message.success('视频流删除成功')
        loadStreams(searchParams)
        loadStatistics()
      } else {
        throw new Error('删除失败')
      }
    } catch (error) {
      message.error('删除视频流失败')
    }
  }

  const handleConfigure = (stream: VideoStream) => {
    setSelectedStream(stream)
    setConfigModalVisible(true)
  }


  const handleConfigConfirm = () => {
    loadStreams(searchParams)
    loadStatistics()
  }


  const handleViewAlerts = (stream: VideoStream) => {
    setAlertSelectedStream(stream)
    setAlertDrawerVisible(true)
  }

  const handleCloseAlertDrawer = () => {
    setAlertDrawerVisible(false)
    setAlertSelectedStream(null)
  }

  const handleCreateSubmit = async (values: any) => {
    try {
      const response = await fetch('/api/video-streams/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      
      if (response.ok) {
        message.success('视频流创建成功')
        setCreateModalVisible(false)
        createForm.resetFields()
        loadStreams(searchParams)
        loadStatistics()
      } else {
        const error = await response.json()
        throw new Error(error.detail || '创建失败')
      }
    } catch (error: any) {
      message.error(error.message || '创建视频流失败')
    }
  }

  const handleEditSubmit = async (values: any) => {
    if (!selectedStream) return
    
    try {
      const response = await fetch(`/api/video-streams/${selectedStream.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      
      if (response.ok) {
        message.success('视频流信息更新成功')
        setEditModalVisible(false)
        editForm.resetFields()
        loadStreams(searchParams)
      } else {
        const error = await response.json()
        throw new Error(error.detail || '更新失败')
      }
    } catch (error: any) {
      message.error(error.message || '更新视频流信息失败')
    }
  }

  const handleTestConnection = async (streamId: string) => {
    try {
      const response = await fetch(`/api/video-streams/${streamId}/test-connection`, {
        method: 'POST'
      })
      
      if (response.ok) {
        message.success('连接测试成功')
        loadStreams(searchParams)
      } else {
        throw new Error('连接测试失败')
      }
    } catch (error) {
      message.error('连接测试失败')
    }
  }

  const statusCounts = statistics.by_status || {}

  // 渲染任务列表（完整表格版本）
  const renderTaskList = (streamId: string) => {
    const tasks = streamTasks[streamId] || []
    
    if (tasks.length === 0) {
      return (
        <div style={{ padding: 16, textAlign: 'center', color: '#999' }}>
          暂无分析任务，可通过"快速配置"创建任务
        </div>
      )
    }

    const taskColumns = [
      {
        title: '任务名称',
        dataIndex: 'task_name',
        key: 'task_name',
        width: 200,
        render: (text: string, record: any) => (
          <div>
            <Text strong>{text}</Text>
            <br />
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.algorithm_name || '未知算法'}
            </Text>
          </div>
        )
      },
      {
        title: '状态',
        key: 'status',
        width: 100,
        render: (_: any, record: any) => getTaskStatusDisplay(record)
      },
      {
        title: '时间配置',
        key: 'time_config',
        width: 150,
        render: (_: any, record: any) => formatTimeConfig(record.time_config)
      },
      {
        title: 'ROI配置',
        key: 'roi_config',
        width: 100,
        render: (_: any, record: any) => {
          const roiEnabled = record.roi_config?.enabled
          const regionCount = record.roi_config?.regions?.length || 0
          
          return roiEnabled ? (
            <Tag color="green">{regionCount} 个区域</Tag>
          ) : (
            <Tag color="default">全画面</Tag>
          )
        }
      },
      {
        title: '优先级',
        dataIndex: 'priority',
        key: 'priority',
        width: 80,
        render: (priority: number) => (
          <Tag color={priority >= 5 ? 'red' : priority >= 3 ? 'orange' : 'blue'}>
            {priority}
          </Tag>
        )
      },
      {
        title: '操作',
        key: 'actions',
        width: 180,
        render: (_: any, record: any) => (
          <Space size="small">
            <Tooltip title={record.is_active ? '停用任务' : '启用任务'}>
              <Switch
                size="small"
                checked={record.is_active}
                onChange={() => toggleTaskActive(record.id, record.is_active, streamId)}
              />
            </Tooltip>

            <Tooltip title="查看详情">
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => showTaskDetail(record)}
              />
            </Tooltip>

            <Popconfirm
              title="确定要删除这个任务吗？"
              description="删除后将无法恢复，正在运行的分析也会被停止。"
              onConfirm={() => deleteTask(record.id, streamId)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="删除任务">
                <Button
                  size="small"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        )
      }
    ]

    return (
      <Table
        columns={taskColumns}
        dataSource={tasks}
        rowKey="id"
        pagination={false}
        size="small"
        scroll={{ x: 800 }}
      />
    )
  }

  const streamColumns = [
    {
      title: '摄像头名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: VideoStream) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          {record.location && (
            <div style={{ fontSize: '12px', color: '#666' }}>{record.location}</div>
          )}
        </div>
      )
    },
    {
      title: '流地址',
      dataIndex: 'stream_url',
      key: 'stream_url',
      width: 300,
      render: (text: string, record: VideoStream) => (
        <div>
          <div style={{ fontSize: '12px', fontFamily: 'monospace' }}>{text}</div>
          <Tag color="blue" style={{ marginTop: 4 }}>{record.stream_type?.toUpperCase()}</Tag>
        </div>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const statusConfig = {
          ONLINE: { color: 'success', icon: <CheckCircleOutlined />, text: '在线' },
          OFFLINE: { color: 'default', icon: <CloseCircleOutlined />, text: '离线' },
          CONNECTING: { color: 'processing', icon: <SyncOutlined spin />, text: '连接中' },
          ERROR: { color: 'error', icon: <CloseCircleOutlined />, text: '错误' },
          MAINTENANCE: { color: 'warning', icon: <SyncOutlined />, text: '维护中' }
        }
        const config = statusConfig[status] || statusConfig.OFFLINE
        return (
          <Badge status={config.color} text={config.text} />
        )
      }
    },
    {
      title: '统计信息',
      key: 'stats',
      width: 150,
      render: (record: VideoStream) => (
        <div style={{ fontSize: '12px' }}>
          <div>分析: {record.total_analysis_count || 0}</div>
          <div style={{ color: record.total_alerts_count > 0 ? '#ff4d4f' : undefined }}>
            告警: {record.total_alerts_count || 0}
          </div>
        </div>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 300,
      render: (record: VideoStream) => {
        // 统计已配置的任务数量
        const taskCount = streamTasks[record.id]?.length || 0
        const hasConfig = taskCount > 0

        return (
          <Space size={4}>
            <Tooltip title="直播流">
              <Button
                type="link"
                size="small"
                icon={<PlayCircleOutlined />}
                onClick={() => handlePlay(record)}
              />
            </Tooltip>
            <Tooltip title={hasConfig ? `快速配置 (已配置${taskCount}个任务)` : "快速配置"}>
              <Button
                type="link"
                size="small"
                icon={<ThunderboltOutlined />}
                onClick={() => handleConfigure(record)}
                style={{
                  color: hasConfig ? '#52c41a' : undefined
                }}
              />
            </Tooltip>
            <Tooltip title="编辑流信息">
              <Button
                type="link"
                size="small"
                icon={<EditOutlined />}
                onClick={() => handleEdit(record)}
              />
            </Tooltip>
            <Tooltip title={`查看告警 (${record.total_alerts_count || 0})`}>
              <Button
                type="link"
                size="small"
                icon={<BellOutlined />}
                onClick={() => handleViewAlerts(record)}
                style={{
                  color: record.total_alerts_count > 0 ? '#ff4d4f' : undefined
                }}
              />
            </Tooltip>
            <Tooltip title="删除">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={() => handleDelete(record.id)}
              />
            </Tooltip>
          </Space>
        )
      }
    }
  ]

  // 获取状态显示（与StreamTaskManagerModal保持一致）
  const getStatusDisplay = (task: any) => {
    if (!task.is_active) {
      return <Badge status="default" text="已停用" />
    }

    if (task.is_running) {
      return <Badge status="processing" text="运行中" />
    }

    if (task.should_run_now) {
      return <Badge status="warning" text="待运行" />
    }

    if (task.status === 'enabled') {
      return <Badge status="success" text="已启用" />
    }

    return <Badge status="error" text={task.status} />
  }

  // 渲染任务详情抽屉
  const renderTaskDetail = () => {
    if (!selectedTask) return null

    const timeConfig = selectedTask.time_config || {}
    const roiConfig = selectedTask.roi_config || {}

    return (
      <Drawer
        title="任务详情"
        placement="right"
        width={600}
        open={taskDetailVisible}
        onClose={() => setTaskDetailVisible(false)}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 基本信息 */}
          <Card title="基本信息" size="small">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="任务名称">
                {selectedTask.task_name}
              </Descriptions.Item>
              <Descriptions.Item label="算法">
                {selectedTask.algorithm_name || '未知算法'}
              </Descriptions.Item>
              <Descriptions.Item label="当前状态">
                {getStatusDisplay(selectedTask)}
              </Descriptions.Item>
              <Descriptions.Item label="优先级">
                <Tag color={selectedTask.priority >= 5 ? 'red' : selectedTask.priority >= 3 ? 'orange' : 'blue'}>
                  {selectedTask.priority}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="置信度阈值">
                {selectedTask.confidence_threshold}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {selectedTask.created_at ? new Date(selectedTask.created_at).toLocaleString() : '未知'}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          {/* 时间配置 */}
          <Card title="时间配置" size="small">
            {timeConfig.enabled ? (
              <div>
                <Alert
                  message="已启用时间控制"
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                {timeConfig.time_ranges?.map((range: any, index: number) => (
                  <Card key={index} size="small" style={{ marginBottom: 8 }}>
                    <div>
                      <ClockCircleOutlined style={{ marginRight: 8 }} />
                      <Text strong>{range.start_time} - {range.end_time}</Text>
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <Text type="secondary">运行日期：</Text>
                      {['日', '一', '二', '三', '四', '五', '六'].map((day, dayIndex) => (
                        <Tag
                          key={dayIndex}
                          color={range.days?.includes(dayIndex) ? 'blue' : 'default'}
                          style={{ margin: 2 }}
                        >
                          {day}
                        </Tag>
                      ))}
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <Alert message="未启用时间控制，全天运行" type="default" />
            )}
          </Card>

          {/* ROI配置 */}
          <Card title="ROI配置" size="small">
            {roiConfig.enabled ? (
              <div>
                <Alert
                  message={`已设置 ${roiConfig.regions?.length || 0} 个感兴趣区域`}
                  type="success"
                  showIcon
                  style={{ marginBottom: 16 }}
                />
                {roiConfig.regions?.map((region: any, index: number) => (
                  <Card key={index} size="small" style={{ marginBottom: 8 }}>
                    <div>
                      <Text strong>{region.name}</Text>
                      <Tag color="green" style={{ marginLeft: 8 }}>
                        {region.type === 'rectangle' ? '矩形' : '多边形'}
                      </Tag>
                    </div>
                    {region.type === 'rectangle' && (
                      <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                        位置: ({region.data?.x}, {region.data?.y})<br />
                        尺寸: {region.data?.width} × {region.data?.height}
                      </div>
                    )}
                  </Card>
                ))}
              </div>
            ) : (
              <Alert message="未设置ROI区域，全画面分析" type="default" />
            )}
          </Card>
        </Space>
      </Drawer>
    )
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="总流数"
              value={statistics.total_streams}
              prefix={<VideoCameraOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="在线率"
              value={statistics.online_rate}
              suffix="%"
              valueStyle={{ color: statistics.online_rate > 80 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="在线流"
              value={statusCounts.ONLINE || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="离线流"
              value={statusCounts.OFFLINE || 0}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 搜索和操作栏 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => setCreateModalVisible(true)}
            >
              添加视频流
            </Button>
          </Space>
        </div>

        {/* 搜索框 */}
        <Form 
          form={searchForm} 
          layout="inline" 
          style={{ 
            padding: '16px', 
            background: '#fafafa', 
            borderRadius: '6px', 
            marginBottom: '16px' 
          }}
        >
          <Form.Item name="search_name" style={{ minWidth: 200 }}>
            <Input 
              placeholder="搜索摄像头名称..." 
              prefix={<SearchOutlined />}
              onPressEnter={() => handleSearch(searchForm.getFieldsValue())}
            />
          </Form.Item>
          
          <Form.Item name="status" style={{ minWidth: 120 }}>
            <Select placeholder="连接状态" allowClear>
              <Option value="ONLINE">在线</Option>
              <Option value="OFFLINE">离线</Option>
              <Option value="CONNECTING">连接中</Option>
              <Option value="ERROR">错误</Option>
              <Option value="MAINTENANCE">维护中</Option>
            </Select>
          </Form.Item>
          
          <Form.Item name="group_name" style={{ minWidth: 120 }}>
            <Input placeholder="分组名称" />
          </Form.Item>
          
          <Form.Item name="location" style={{ minWidth: 120 }}>
            <Input placeholder="位置" />
          </Form.Item>
          
          <Form.Item>
            <Space>
              <Button 
                type="primary" 
                icon={<SearchOutlined />} 
                onClick={() => handleSearch(searchForm.getFieldsValue())}
                loading={loading}
              >
                搜索
              </Button>
              <Button 
                icon={<ReloadOutlined />} 
                onClick={handleReset}
              >
                重置
              </Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 视频流列表表格 */}
        <Table
          columns={streamColumns}
          dataSource={streams}
          loading={loading}
          rowKey="id"
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
          scroll={{ x: 1000 }}
          expandable={{
            expandedRowKeys,
            onExpand: (expanded, record) => {
              if (expanded) {
                setExpandedRowKeys([...expandedRowKeys, record.id])
                loadStreamTasks(record.id)
              } else {
                setExpandedRowKeys(expandedRowKeys.filter(key => key !== record.id))
              }
            },
            expandedRowRender: (record) => (
              <Card size="small" title="分析任务列表" style={{ margin: '0 24px' }}>
                {renderTaskList(record.id)}
              </Card>
            ),
            expandIcon: ({ expanded, onExpand, record }) => (
              <Button
                type="link"
                size="small"
                icon={expanded ? <UpOutlined /> : <DownOutlined />}
                onClick={(e) => onExpand(record, e)}
              >
                {expanded ? '收起任务' : '查看任务'}
              </Button>
            )
          }}
        />
      </Card>

      {/* 创建视频流模态框 */}
      <Modal
        title="添加视频流"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateSubmit}
        >
          <Form.Item
            name="name"
            label="摄像头名称"
            rules={[{ required: true, message: '请输入摄像头名称' }]}
          >
            <Input placeholder="输入摄像头名称" />
          </Form.Item>

          <Form.Item
            name="stream_url"
            label="流地址"
            rules={[{ required: true, message: '请输入流地址' }]}
          >
            <Input placeholder="rtsp://192.168.1.100:554/stream1" />
          </Form.Item>

          <Form.Item
            name="stream_type"
            label="流类型"
            rules={[{ required: true, message: '请选择流类型' }]}
          >
            <Select placeholder="选择流类型">
              <Option value="RTSP">RTSP</Option>
              <Option value="RTMP">RTMP</Option>
              <Option value="HLS">HLS</Option>
              <Option value="WEBRTC">WebRTC</Option>
              <Option value="HTTP_FLV">HTTP-FLV</Option>
              <Option value="LOCAL_CAMERA">本地摄像头</Option>
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="location" label="位置">
                <Input placeholder="摄像头位置" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="group_name" label="分组">
                <Input placeholder="分组名称" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="摄像头描述" />
          </Form.Item>

          <Form.Item name="tags" label="标签">
            <Select
              mode="tags"
              placeholder="输入标签（回车确认）"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="username" label="用户名">
                <Input placeholder="认证用户名（可选）" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="password" label="密码">
                <Input.Password placeholder="认证密码（可选）" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建视频流
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑视频流模态框 */}
      <Modal
        title="编辑视频流"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleEditSubmit}
        >
          <Form.Item
            name="name"
            label="摄像头名称"
            rules={[{ required: true, message: '请输入摄像头名称' }]}
          >
            <Input placeholder="输入摄像头名称" />
          </Form.Item>

          <Form.Item
            name="stream_url"
            label="流地址"
            rules={[{ required: true, message: '请输入流地址' }]}
          >
            <Input placeholder="rtsp://192.168.1.100:554/stream1" />
          </Form.Item>

          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="摄像头描述" />
          </Form.Item>

          <Form.Item name="tags" label="标签">
            <Select
              mode="tags"
              placeholder="输入标签（回车确认）"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                更新视频流
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 算法配置模态框 - 简化版本 */}
      <SimpleStreamAlgorithmModal
        open={configModalVisible}
        onCancel={() => setConfigModalVisible(false)}
        stream={selectedStream}
        onConfirm={handleConfigConfirm}
      />


      {/* 直播流播放模态框 */}
      <StreamPlayerModal
        open={playerModalVisible}
        onCancel={() => setPlayerModalVisible(false)}
        stream={selectedStream}
      />

      {/* 告警抽屉 */}
      <AlertDrawer
        open={alertDrawerVisible}
        onClose={handleCloseAlertDrawer}
        sourceId={alertSelectedStream?.id}
        sourceName={alertSelectedStream?.name}
        sourceType="stream"
      />
      
      {/* 任务详情抽屉 */}
      {renderTaskDetail()}
    </div>
  )
}

export default VideoStreamPage