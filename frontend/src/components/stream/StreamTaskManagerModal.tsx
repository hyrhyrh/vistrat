import React, { useState, useEffect } from 'react'
import {
  Modal,
  Table,
  Button,
  Space,
  Tag,
  message,
  Popconfirm,
  Tooltip,
  Switch,
  Badge,
  Card,
  Typography,
  Descriptions,
  Drawer,
  Alert,
  Divider,
} from 'antd'
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  SettingOutlined,
  DeleteOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  ReloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

const { Title, Text } = Typography

interface Task {
  id: string
  task_name: string
  status: string
  is_active: boolean
  is_running: boolean
  should_run_now: boolean
  algorithm_name: string
  time_config: any
  roi_config: any
  priority: number
  confidence_threshold: number
  last_run_at: string | null
  created_at: string
}

interface StreamTaskManagerModalProps {
  visible: boolean
  onCancel: () => void
  stream: any
  onTaskUpdate?: () => void
}

const StreamTaskManagerModal: React.FC<StreamTaskManagerModalProps> = ({
  visible,
  onCancel,
  stream,
  onTaskUpdate
}) => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(false)
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  // 加载任务列表
  const loadTasks = async () => {
    if (!stream?.id) return

    setLoading(true)
    try {
      const response = await fetch(`/api/stream-tasks/?stream_id=${stream.id}`)
      const data = await response.json()

      if (Array.isArray(data)) {
        setTasks(data)
      } else {
        console.error('获取任务列表返回格式错误:', data)
        setTasks([])
      }
    } catch (error) {
      console.error('加载任务列表失败:', error)
      message.error('加载任务列表失败')
      setTasks([])
    } finally {
      setLoading(false)
    }
  }

  // 启用/停用任务
  const toggleTaskActive = async (taskId: string, isActive: boolean) => {
    try {
      const action = isActive ? 'disable' : 'enable'
      const response = await fetch(`/api/stream-tasks/${taskId}/${action}`, {
        method: 'POST'
      })

      if (response.ok) {
        message.success(`任务已${isActive ? '停用' : '启用'}`)
        await loadTasks()
        onTaskUpdate?.()
      } else {
        throw new Error('操作失败')
      }
    } catch (error) {
      message.error(`${isActive ? '停用' : '启用'}任务失败`)
    }
  }

  // 启动/停止分析
  const toggleTaskAnalysis = async (taskId: string, isRunning: boolean) => {
    try {
      const action = isRunning ? 'stop' : 'start'
      const response = await fetch(`/api/stream-tasks/${taskId}/${action}`, {
        method: 'POST'
      })

      const result = await response.json()

      if (response.ok && result.success !== false) {
        message.success(`分析已${isRunning ? '停止' : '启动'}`)
        await loadTasks()
        onTaskUpdate?.()
      } else {
        throw new Error(result.message || '操作失败')
      }
    } catch (error: any) {
      message.error(error.message || `${isRunning ? '停止' : '启动'}分析失败`)
    }
  }

  // 删除任务
  const deleteTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/stream-tasks/${taskId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        message.success('任务已删除')
        await loadTasks()
        onTaskUpdate?.()
      } else {
        throw new Error('删除失败')
      }
    } catch (error) {
      message.error('删除任务失败')
    }
  }

  // 查看任务详情
  const showTaskDetail = (task: Task) => {
    console.log('显示任务详情:', task)
    
    // 使用回调函数确保状态正确设置
    setSelectedTask((prev) => {
      console.log('setSelectedTask callback:', { prev, new: task })
      return task
    })
    
    setDetailVisible((prev) => {
      console.log('setDetailVisible callback:', { prev, new: true })
      return true
    })
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

  // 获取状态颜色和图标
  const getStatusDisplay = (task: Task) => {
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

  const columns: ColumnsType<Task> = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
      width: 200,
      render: (text, record) => (
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
      render: (_, record) => getStatusDisplay(record)
    },
    {
      title: '时间配置',
      key: 'time_config',
      width: 150,
      render: (_, record) => formatTimeConfig(record.time_config)
    },
    {
      title: 'ROI配置',
      key: 'roi_config',
      width: 100,
      render: (_, record) => {
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
      render: (priority) => (
        <Tag color={priority >= 5 ? 'red' : priority >= 3 ? 'orange' : 'blue'}>
          {priority}
        </Tag>
      )
    },
    {
      title: '最后运行',
      dataIndex: 'last_run_at',
      key: 'last_run_at',
      width: 120,
      render: (time) => time ? (
        <Text style={{ fontSize: 12 }}>
          {new Date(time).toLocaleString()}
        </Text>
      ) : (
        <Text type="secondary">从未运行</Text>
      )
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title={record.is_active ? '停用任务' : '启用任务'}>
            <Switch
              size="small"
              checked={record.is_active}
              onChange={() => toggleTaskActive(record.id, record.is_active)}
            />
          </Tooltip>

          {record.is_active && (
            <Tooltip title={record.is_running ? '停止分析' : '启动分析'}>
              <Button
                size="small"
                type={record.is_running ? 'primary' : 'default'}
                danger={record.is_running}
                icon={record.is_running ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
                onClick={() => toggleTaskAnalysis(record.id, record.is_running)}
              />
            </Tooltip>
          )}

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
            onConfirm={() => deleteTask(record.id)}
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

  useEffect(() => {
    if (visible && stream) {
      loadTasks()
    }
  }, [visible, stream])

  // 监听抽屉状态变化
  useEffect(() => {
    console.log('抽屉状态变化:', { detailVisible, selectedTask })
  }, [detailVisible, selectedTask])

  const renderTaskDetail = () => {
    console.log('renderTaskDetail called:', { selectedTask, detailVisible })
    if (!selectedTask) return null

    const timeConfig = selectedTask.time_config || {}
    const roiConfig = selectedTask.roi_config || {}

    return (
      <Drawer
        title="任务详情"
        placement="right"
        width={600}
        open={detailVisible}
        onClose={() => {
          console.log('关闭抽屉')
          setDetailVisible(false)
        }}
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
    <>
      <Modal
        title={
          <Space>
            <SettingOutlined />
            任务管理 - {stream?.name}
          </Space>
        }
        open={visible}
        onCancel={onCancel}
        width={1200}
        footer={[
          <Button key="refresh" icon={<ReloadOutlined />} onClick={loadTasks}>
            刷新
          </Button>,
          <Button key="close" onClick={onCancel}>
            关闭
          </Button>
        ]}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          {/* 视频流信息 */}
          {stream && (
            <Card size="small">
              <Descriptions column={3} size="small">
                <Descriptions.Item label="视频流名称">{stream.name}</Descriptions.Item>
                <Descriptions.Item label="流类型">{stream.stream_type}</Descriptions.Item>
                <Descriptions.Item label="状态">
                  <Badge
                    status={stream.status === 'ONLINE' ? 'success' : 'error'}
                    text={stream.status === 'ONLINE' ? '在线' : '离线'}
                  />
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          {/* 统计信息 */}
          <Card size="small">
            <Space size="large">
              <div>
                <Text type="secondary">总任务</Text>
                <div><Text strong style={{ fontSize: 20 }}>{tasks.length}</Text></div>
              </div>
              <Divider type="vertical" />
              <div>
                <Text type="secondary">已启用</Text>
                <div><Text strong style={{ fontSize: 20, color: '#52c41a' }}>
                  {tasks.filter(t => t.is_active).length}
                </Text></div>
              </div>
              <Divider type="vertical" />
              <div>
                <Text type="secondary">运行中</Text>
                <div><Text strong style={{ fontSize: 20, color: '#1890ff' }}>
                  {tasks.filter(t => t.is_running).length}
                </Text></div>
              </div>
              <Divider type="vertical" />
              <div>
                <Text type="secondary">待运行</Text>
                <div><Text strong style={{ fontSize: 20, color: '#fa8c16' }}>
                  {tasks.filter(t => t.should_run_now && !t.is_running).length}
                </Text></div>
              </div>
            </Space>
          </Card>

          {/* 任务列表 */}
          <Card title="分析任务列表" size="small">
            {tasks.length === 0 ? (
              <Alert
                message="暂无分析任务"
                description="点击「新建任务」按钮为此视频流创建分析任务"
                type="info"
                showIcon
              />
            ) : (
              <Table
                columns={columns}
                dataSource={tasks}
                rowKey="id"
                loading={loading}
                pagination={false}
                size="small"
              />
            )}
          </Card>
        </Space>
      </Modal>

      {/* 调试信息 */}
      {detailVisible && (
        <div style={{ 
          position: 'fixed', 
          top: 10, 
          right: 10, 
          background: 'red', 
          color: 'white', 
          padding: '10px',
          zIndex: 9999 
        }}>
          抽屉应该显示: {detailVisible ? 'true' : 'false'}
          <br />
          选中任务: {selectedTask?.task_name || 'none'}
        </div>
      )}
      
      {/* 任务详情抽屉 */}
      {renderTaskDetail()}
    </>
  )
}

export default StreamTaskManagerModal