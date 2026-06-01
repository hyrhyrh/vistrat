import React, { useState, useEffect } from 'react'
import { 
  Modal, 
  Form, 
  Input,
  Select, 
  Button, 
  Space, 
  Card, 
  Typography,
  Descriptions,
  message,
  Spin,
  Badge,
  Steps,
  Result,
  Alert
} from 'antd'
import { SettingOutlined, CheckCircleOutlined, PlayCircleOutlined } from '@ant-design/icons'

const { Option } = Select
const { Title, Text } = Typography

interface AIAlgorithm {
  id: string
  name: string
  description: string
  category: string
  status: string
}

interface RealtimeStreamConfigModalProps {
  visible: boolean
  onCancel: () => void
  onSuccess?: (streamId: string) => void
  rtspUrl?: string
  streamName?: string
}

const RealtimeStreamConfigModal: React.FC<RealtimeStreamConfigModalProps> = ({
  visible,
  onCancel,
  onSuccess,
  rtspUrl,
  streamName
}) => {
  const [form] = Form.useForm()
  const [algorithms, setAlgorithms] = useState<AIAlgorithm[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedAlgorithms, setSelectedAlgorithms] = useState<string[]>([])
  const [isConfigured, setIsConfigured] = useState(false)
  const [currentStep, setCurrentStep] = useState<'config' | 'ready' | 'analyzing'>('config')

  useEffect(() => {
    if (visible) {
      // 重置状态
      setIsConfigured(false)
      setCurrentStep('config')
      setSelectedAlgorithms([])
      form.resetFields()
      
      // 设置默认值
      const defaultStreamName = streamName || `实时流_${Date.now()}`
      const defaultRtspUrl = rtspUrl || ''
      
      form.setFieldsValue({
        stream_name: defaultStreamName,
        rtsp_url: defaultRtspUrl
      })
      
      // 加载算法
      loadAIAlgorithms()
    }
  }, [visible, rtspUrl, streamName])

  const loadAIAlgorithms = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/ai-models/configs/')
      const data = await response.json()
      // 只显示激活状态的算法
      const activeAlgorithms = Array.isArray(data) ? data.filter(algo => algo.status === 'active') : []
      setAlgorithms(activeAlgorithms)
    } catch (error) {
      message.error('加载AI算法失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (!selectedAlgorithms.length) {
        message.warning('请选择至少一个分析算法')
        return
      }

      setLoading(true)
      setCurrentStep('ready')
      
      // 创建实时流配置
      const streamConfig = {
        stream_name: values.stream_name,
        rtsp_url: values.rtsp_url,
        template_ids: selectedAlgorithms,
        frame_interval: 3.0, // 默认3秒采样
        auto_restart: true,
        max_reconnect_attempts: 5,
        analysis_enabled: true,
        alert_enabled: true,
        storage_enabled: true
      }

      const response = await fetch('/api/realtime-streams/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(streamConfig)
      })

      const data = await response.json()
      if (data.success) {
        const streamId = data.data.stream_id
        message.success('实时流配置创建成功')
        
        // 自动启动分析
        setCurrentStep('analyzing')
        await startAnalysis(streamId)
        
        if (onSuccess) {
          onSuccess(streamId)
        }
        
        // 延时关闭模态框
        setTimeout(() => {
          handleCancel()
        }, 2000)
      } else {
        message.error(data.message || '创建失败')
        setCurrentStep('config')
      }
    } catch (error) {
      message.error('配置失败')
      setCurrentStep('config')
    } finally {
      setLoading(false)
    }
  }

  const startAnalysis = async (streamId: string) => {
    try {
      const response = await fetch(`/api/realtime-streams/${streamId}/analysis/start`, {
        method: 'POST'
      })
      const data = await response.json()
      if (data.success) {
        message.success('实时分析已启动')
      } else {
        message.error(data.message || '启动分析失败')
      }
    } catch (error) {
      message.error('启动分析失败')
    }
  }

  const handleCancel = () => {
    setCurrentStep('config')
    setIsConfigured(false)
    setSelectedAlgorithms([])
    form.resetFields()
    onCancel()
  }

  // 算法选择变化处理
  const handleAlgorithmChange = (algorithmIds: string[]) => {
    setSelectedAlgorithms(algorithmIds)
    setIsConfigured(algorithmIds.length > 0)
  }

  const getStepIcon = (step: string) => {
    switch (step) {
      case 'config':
        return <SettingOutlined />
      case 'ready':
        return <CheckCircleOutlined />
      case 'analyzing':
        return <PlayCircleOutlined />
      default:
        return <SettingOutlined />
    }
  }

  const getStepTitle = (step: string) => {
    switch (step) {
      case 'config':
        return '配置算法'
      case 'ready':
        return '准备就绪'
      case 'analyzing':
        return '分析中'
      default:
        return '配置算法'
    }
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 'config':
        return (
          <Spin spinning={loading}>
            <Card>
              <Title level={4}>实时流分析配置</Title>
              
              <Form form={form} layout="vertical">
                <Form.Item
                  name="stream_name"
                  label="流名称"
                  rules={[{ required: true, message: '请输入流名称' }]}
                >
                  <Input placeholder="为这个实时流起一个名称" />
                </Form.Item>
                
                <Form.Item
                  name="rtsp_url"
                  label="RTSP地址"
                  rules={[
                    { required: true, message: '请输入RTSP地址' },
                    { pattern: /^(rtsp|rtmp|http):\/\/.+/, message: '请输入有效的RTSP/RTMP/HTTP地址' }
                  ]}
                >
                  <Input placeholder="rtsp://192.168.1.100:554/stream" />
                </Form.Item>

                <Form.Item
                  label="AI分析算法"
                  required
                >
                  <Select
                    mode="multiple"
                    placeholder="选择要使用的AI分析算法"
                    value={selectedAlgorithms}
                    onChange={handleAlgorithmChange}
                    style={{ width: '100%' }}
                  >
                    {algorithms.map(algorithm => (
                      <Option key={algorithm.id} value={algorithm.id}>
                        <Space>
                          <span>{algorithm.name}</span>
                          <Badge
                            count={algorithm.category}
                            style={{ backgroundColor: algorithm.category === '目标检测' ? '#1890ff' : '#52c41a' }}
                          />
                        </Space>
                      </Option>
                    ))}
                  </Select>
                  
                  {selectedAlgorithms.length > 0 && (
                    <div style={{ marginTop: 8, color: '#52c41a' }}>
                      ✓ 已选择 {selectedAlgorithms.length} 个算法
                    </div>
                  )}
                </Form.Item>
              </Form>

              {selectedAlgorithms.length > 0 && (
                <Alert
                  message="算法将自动配置以下参数："
                  description="• 采样间隔: 3秒/帧 • 自动重启: 开启 • 告警通知: 开启 • 数据存储: 开启"
                  type="info"
                  showIcon
                  style={{ marginTop: 16 }}
                />
              )}
            </Card>
          </Spin>
        )

      case 'ready':
        return (
          <Card>
            <Result
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              title="配置完成"
              subTitle="正在创建实时流并启动分析..."
              extra={
                <Descriptions column={1} bordered size="small">
                  <Descriptions.Item label="流名称">{form.getFieldValue('stream_name')}</Descriptions.Item>
                  <Descriptions.Item label="RTSP地址">{form.getFieldValue('rtsp_url')}</Descriptions.Item>
                  <Descriptions.Item label="算法数量">{selectedAlgorithms.length} 个</Descriptions.Item>
                </Descriptions>
              }
            />
          </Card>
        )

      case 'analyzing':
        return (
          <Card>
            <Result
              status="success"
              title="实时分析已启动"
              subTitle="系统正在对实时流进行AI多模态分析，请前往流管理页面查看详细状态。"
              extra={
                <Space>
                  <Text type="secondary">🎯 智能分析 • 📊 实时监控 • 🚨 即时告警</Text>
                </Space>
              }
            />
          </Card>
        )

      default:
        return null
    }
  }

  return (
    <Modal
      title="配置实时流分析"
      open={visible}
      onCancel={handleCancel}
      width={600}
      footer={
        <Space>
          <Button onClick={handleCancel}>
            取消
          </Button>
          {currentStep === 'config' && (
            <Button
              type="primary"
              onClick={handleSubmit}
              loading={loading}
              disabled={!isConfigured}
            >
              开始分析
            </Button>
          )}
        </Space>
      }
      destroyOnHidden
    >
      <div style={{ marginBottom: 24 }}>
        <Steps
          current={currentStep === 'config' ? 0 : currentStep === 'ready' ? 1 : 2}
          size="small"
          items={[
            {
              title: '配置算法',
              icon: <SettingOutlined />
            },
            {
              title: '创建流配置',
              icon: <CheckCircleOutlined />
            },
            {
              title: '启动分析',
              icon: <PlayCircleOutlined />
            }
          ]}
        />
      </div>

      {renderStepContent()}
    </Modal>
  )
}

export default RealtimeStreamConfigModal