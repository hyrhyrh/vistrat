import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Progress, 
  Table, 
  Alert, 
  Tabs, 
  Tag,
  Space,
  Button,
  Typography,
  Descriptions,
  notification
} from 'antd'
import { 
  DashboardOutlined,
  DatabaseOutlined,
  CloudServerOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons'

const { Title, Text } = Typography

interface SystemStats {
  success: boolean
  timestamp: string
  system: {
    cpu_percent: number
    memory: {
      total: number
      available: number
      percent: number
      used: number
    }
    disk: {
      total: number
      free: number
      used: number
      percent: number
    }
    process: {
      memory_rss: number
      memory_vms: number
      cpu_percent: number
      num_threads: number
    }
  }
  application: {
    buffer_manager: any
    circuit_breakers: any
    database_pool: any
  }
}

interface HealthCheck {
  overall_status: string
  timestamp: string
  checks: {
    [key: string]: {
      status: string
      message: string
    }
  }
}

const PerformanceMonitorPage: React.FC = () => {
  const [systemStats, setSystemStats] = useState<SystemStats | null>(null)
  const [healthCheck, setHealthCheck] = useState<HealthCheck | null>(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchSystemStats = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/performance/system/overview')
      const data = await response.json()
      setSystemStats(data)
    } catch (error) {
      notification.error({
        message: '获取系统统计失败',
        description: String(error)
      })
    } finally {
      setLoading(false)
    }
  }

  const fetchHealthCheck = async () => {
    try {
      const response = await fetch('/api/performance/health/comprehensive')
      const data = await response.json()
      setHealthCheck(data)
    } catch (error) {
      notification.error({
        message: '获取健康检查失败',
        description: String(error)
      })
    }
  }

  useEffect(() => {
    fetchSystemStats()
    fetchHealthCheck()

    if (autoRefresh) {
      const interval = setInterval(() => {
        fetchSystemStats()
        fetchHealthCheck()
      }, 5000) // 每5秒刷新

      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'green'
      case 'warning': return 'orange'
      case 'critical': return 'red'
      case 'error': return 'red'
      default: return 'default'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircleOutlined />
      case 'warning': 
      case 'critical': 
      case 'error': return <ExclamationCircleOutlined />
      default: return null
    }
  }

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2}>
          <DashboardOutlined /> 系统性能监控
        </Title>
        <Space>
          <Button 
            type={autoRefresh ? 'primary' : 'default'}
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? '停止自动刷新' : '开启自动刷新'}
          </Button>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => {
              fetchSystemStats()
              fetchHealthCheck()
            }}
            loading={loading}
          >
            手动刷新
          </Button>
        </Space>
      </div>

      {/* 系统健康状态总览 */}
      {healthCheck && (
        <Alert
          message={`系统整体状态: ${healthCheck.overall_status}`}
          type={healthCheck.overall_status === 'healthy' ? 'success' : 'warning'}
          showIcon
          style={{ marginBottom: '24px' }}
        />
      )}

      <Tabs
        defaultActiveKey="overview"
        type="card"
        items={[
          {
            key: 'overview',
            label: '系统概览',
            children: systemStats && (
              <Row gutter={[16, 16]}>
                {/* CPU 使用率 */}
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="CPU 使用率"
                      value={systemStats.system.cpu_percent}
                      precision={1}
                      suffix="%"
                      valueStyle={{
                        color: systemStats.system.cpu_percent > 80 ? '#cf1322' :
                               systemStats.system.cpu_percent > 60 ? '#fa8c16' : '#3f8600'
                      }}
                    />
                    <Progress
                      percent={systemStats.system.cpu_percent}
                      status={systemStats.system.cpu_percent > 80 ? 'exception' : 'active'}
                      size="small"
                    />
                  </Card>
                </Col>

                {/* 内存使用率 */}
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="内存使用率"
                      value={systemStats.system.memory.percent}
                      precision={1}
                      suffix="%"
                      valueStyle={{
                        color: systemStats.system.memory.percent > 85 ? '#cf1322' :
                               systemStats.system.memory.percent > 70 ? '#fa8c16' : '#3f8600'
                      }}
                    />
                    <Progress
                      percent={systemStats.system.memory.percent}
                      status={systemStats.system.memory.percent > 85 ? 'exception' : 'active'}
                      size="small"
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {formatBytes(systemStats.system.memory.used)} / {formatBytes(systemStats.system.memory.total)}
                    </Text>
                  </Card>
                </Col>

                {/* 磁盘使用率 */}
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="磁盘使用率"
                      value={systemStats.system.disk.percent}
                      precision={1}
                      suffix="%"
                      valueStyle={{
                        color: systemStats.system.disk.percent > 90 ? '#cf1322' :
                               systemStats.system.disk.percent > 75 ? '#fa8c16' : '#3f8600'
                      }}
                    />
                    <Progress
                      percent={systemStats.system.disk.percent}
                      status={systemStats.system.disk.percent > 90 ? 'exception' : 'active'}
                      size="small"
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {formatBytes(systemStats.system.disk.used)} / {formatBytes(systemStats.system.disk.total)}
                    </Text>
                  </Card>
                </Col>

                {/* 进程线程数 */}
                <Col span={6}>
                  <Card>
                    <Statistic
                      title="进程线程数"
                      value={systemStats.system.process.num_threads}
                      suffix="个"
                    />
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      进程内存: {formatBytes(systemStats.system.process.memory_rss)}
                    </Text>
                  </Card>
                </Col>
              </Row>
            )
          },
          {
            key: 'application',
            label: '应用状态',
            children: systemStats && (
              <Row gutter={[16, 16]}>
                {/* 数据库连接池 */}
                <Col span={12}>
                  <Card title={<><DatabaseOutlined /> 数据库连接池</>}>
                    <Descriptions column={2} size="small">
                      <Descriptions.Item label="连接池大小">
                        {systemStats.application.database_pool.pool_size}
                      </Descriptions.Item>
                      <Descriptions.Item label="最大溢出">
                        {systemStats.application.database_pool.max_overflow}
                      </Descriptions.Item>
                      <Descriptions.Item label="已签入连接">
                        {systemStats.application.database_pool.current_checked_in}
                      </Descriptions.Item>
                      <Descriptions.Item label="已签出连接">
                        {systemStats.application.database_pool.current_checked_out}
                      </Descriptions.Item>
                      <Descriptions.Item label="连接状态">
                        <Tag color={systemStats.application.database_pool.status === 'healthy' ? 'green' : 'red'}>
                          {systemStats.application.database_pool.status}
                        </Tag>
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                </Col>

                {/* 缓冲区管理器 */}
                <Col span={12}>
                  <Card title={<><CloudServerOutlined /> 缓冲区管理</>}>
                    <Descriptions column={2} size="small">
                      <Descriptions.Item label="活跃缓冲区">
                        {systemStats.application.buffer_manager.adaptive_buffer_manager.total_buffers}
                      </Descriptions.Item>
                      <Descriptions.Item label="已处理条目">
                        {systemStats.application.buffer_manager.adaptive_buffer_manager.total_items_processed}
                      </Descriptions.Item>
                      <Descriptions.Item label="刷新次数">
                        {systemStats.application.buffer_manager.adaptive_buffer_manager.total_flushes}
                      </Descriptions.Item>
                      <Descriptions.Item label="活跃流数">
                        {systemStats.application.buffer_manager.adaptive_buffer_manager.active_streams}
                      </Descriptions.Item>
                      <Descriptions.Item label="运行任务">
                        {systemStats.application.buffer_manager.running_tasks_count}
                      </Descriptions.Item>
                    </Descriptions>
                  </Card>
                </Col>
              </Row>
            )
          },
          {
            key: 'health',
            label: '健康检查',
            children: healthCheck && (
              <Card>
                <Row gutter={[16, 16]}>
                  {Object.entries(healthCheck.checks).map(([key, check]) => (
                    <Col span={8} key={key}>
                      <Card size="small" title={key}>
                        <Space>
                          {getStatusIcon(check.status)}
                          <Tag color={getStatusColor(check.status)}>
                            {check.status}
                          </Tag>
                        </Space>
                        <div style={{ marginTop: '8px' }}>
                          <Text type="secondary">{check.message}</Text>
                        </div>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Card>
            )
          }
        ]}
      />
    </div>
  )
}

export default PerformanceMonitorPage