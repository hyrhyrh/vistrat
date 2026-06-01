import React, { useState, useEffect } from 'react'
import { 
  Modal, 
  Form, 
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
  provider: string
  model_name: string
  status: string
  tags: string[]
}

interface AlgorithmConfigModalProps {
  open: boolean
  onCancel: () => void
  video: any
  onConfirm: (algorithmIds: string[]) => void
}

const AlgorithmConfigModal: React.FC<AlgorithmConfigModalProps> = ({
  open,
  onCancel,
  video,
  onConfirm
}) => {
  const [form] = Form.useForm()
  const [algorithms, setAlgorithms] = useState<AIAlgorithm[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedAlgorithms, setSelectedAlgorithms] = useState<string[]>([])
  const [isConfigured, setIsConfigured] = useState(false)
  const [currentStep, setCurrentStep] = useState<'config' | 'ready' | 'analyzing'>('config')

  useEffect(() => {
    if (open) {
      // 重置状态
      setIsConfigured(false)
      setCurrentStep('config')
      setSelectedAlgorithms([])
      form.resetFields()

      // 加载数据
      loadAIAlgorithms()
      loadCurrentConfig()
    }
  }, [open, video?.id])

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

  const loadCurrentConfig = async () => {
    if (!video?.id) return
    
    try {
      const response = await fetch(`/api/video-files/${video.id}/analysis/templates`)
      const data = await response.json()
      const currentAlgorithmIds = data.templates?.map(t => t.template_id) || []
      setSelectedAlgorithms(currentAlgorithmIds)
      form.setFieldsValue({ algorithm_ids: currentAlgorithmIds })
      
      // 如果已有配置，则显示为ready状态
      if (currentAlgorithmIds.length > 0) {
        setIsConfigured(true)
        setCurrentStep('ready')
      }
    } catch (error) {
      console.error('加载当前配置失败:', error)
    }
  }

  const handleSaveConfig = async () => {
    try {
      const values = await form.validateFields()
      const algorithmIds = values.algorithm_ids || []
      
      setLoading(true)
      
      // 配置分析算法
      const response = await fetch(`/api/video-files/${video.id}/analysis/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: video.id,
          template_ids: algorithmIds
        })
      })
      
      if (!response.ok) {
        throw new Error('配置失败')
      }
      
      message.success(`已配置 ${algorithmIds.length} 个AI分析算法`)
      setIsConfigured(true)
      setCurrentStep('ready')
      onConfirm(algorithmIds)
      
    } catch (error) {
      message.error('配置算法失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveAndStart = async () => {
    try {
      const values = await form.validateFields()
      const algorithmIds = values.algorithm_ids || []
      
      setLoading(true)
      setCurrentStep('analyzing')
      
      // 先配置分析算法
      const configResponse = await fetch(`/api/video-files/${video.id}/analysis/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          video_id: video.id,
          template_ids: algorithmIds
        })
      })
      
      if (!configResponse.ok) {
        throw new Error('配置失败')
      }
      
      // 然后启动分析
      const startResponse = await fetch(`/api/video-files/${video.id}/analysis/start`, {
        method: 'POST'
      })
      
      if (!startResponse.ok) {
        throw new Error('启动分析失败')
      }
      
      message.success('分析任务已启动')
      onConfirm(algorithmIds)
      onCancel()
      
    } catch (error) {
      message.error(error.message || '操作失败')
      setCurrentStep('config')
    } finally {
      setLoading(false)
    }
  }

  const handleStartAnalysis = async () => {
    try {
      setLoading(true)
      
      const response = await fetch(`/api/video-files/${video.id}/analysis/start`, {
        method: 'POST'
      })
      
      if (!response.ok) {
        throw new Error('启动分析失败')
      }
      
      message.success('分析任务已启动')
      onCancel()
      
    } catch (error) {
      message.error('启动分析失败')
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status: string) => {
    const colors = {
      'active': '#52c41a',
      'draft': '#1890ff',
      'testing': '#fa8c16',
      'deprecated': '#ff4d4f'
    }
    return colors[status] || '#666666'
  }

  const getStatusName = (status: string) => {
    const names = {
      'active': '激活',
      'draft': '草稿',
      'testing': '测试中',
      'deprecated': '已弃用'
    }
    return names[status] || status
  }

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          配置分析算法
        </Space>
      }
      open={open}
      onCancel={onCancel}
      width={800}
      footer={null}
    >
      <Spin spinning={loading}>
        {/* 步骤指示器 */}
        <Steps 
          current={currentStep === 'config' ? 0 : currentStep === 'ready' ? 1 : 2} 
          style={{ marginBottom: 24 }}
          items={[
            {
              title: '配置算法',
              description: '选择AI分析算法',
              icon: <SettingOutlined />
            },
            {
              title: '准备就绪',
              description: '配置已保存',
              icon: <CheckCircleOutlined />
            },
            {
              title: '启动分析',
              description: '开始视频分析',
              icon: <PlayCircleOutlined />
            }
          ]}
        />

        {video && (
          <Card size="small" style={{ marginBottom: 16 }}>
            <Descriptions column={3} size="small">
              <Descriptions.Item label="视频名称">{video.name}</Descriptions.Item>
              <Descriptions.Item label="状态">{video.status}</Descriptions.Item>
              <Descriptions.Item label="分析进度">{video.analysis_progress}%</Descriptions.Item>
            </Descriptions>
          </Card>
        )}

        {/* 配置成功提示 */}
        {currentStep === 'ready' && (
          <Alert
            message="配置已保存"
            description={`已成功配置 ${selectedAlgorithms.length} 个AI分析算法，您可以立即启动分析或继续修改配置。`}
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}

        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="algorithm_ids"
            label={<Title level={5}>选择AI分析算法</Title>}
            rules={[{ required: true, message: '请至少选择一个AI分析算法' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择要使用的AI分析算法（可多选）"
              style={{ width: '100%' }}
              onChange={setSelectedAlgorithms}
            >
              {algorithms.map(algorithm => (
                <Option key={algorithm.id} value={algorithm.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ fontWeight: 'bold' }}>{algorithm.name}</div>
                      <div style={{ fontSize: 12, color: '#666' }}>
                        {algorithm.description}
                      </div>
                      <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                        {algorithm.provider} · {algorithm.model_name}
                      </div>
                    </div>
                    <Space>
                      {algorithm.tags.slice(0, 2).map((tag, index) => (
                        <span key={index} style={{ fontSize: 11, color: '#666', backgroundColor: '#f0f0f0', padding: '2px 6px', borderRadius: 2 }}>
                          {tag}
                        </span>
                      ))}
                      <Badge status="success" text={getStatusName(algorithm.status)} />
                    </Space>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>

          {selectedAlgorithms.length > 0 && (
            <Card size="small" title="已选择的AI算法" style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {selectedAlgorithms.map(algorithmId => {
                  const algorithm = algorithms.find(a => a.id === algorithmId)
                  return algorithm ? (
                    <div key={algorithmId} style={{ 
                      padding: 8, 
                      border: '1px solid #f0f0f0', 
                      borderRadius: 4 
                    }}>
                      <Space>
                        <Text strong>{algorithm.name}</Text>
                        <Text type="secondary">({algorithm.provider} · {algorithm.model_name})</Text>
                      </Space>
                      <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                        {algorithm.description}
                      </div>
                      <div style={{ marginTop: 4 }}>
                        {algorithm.tags.map((tag, index) => (
                          <span key={index} style={{ 
                            fontSize: 11, 
                            color: '#666', 
                            backgroundColor: '#f0f0f0', 
                            padding: '2px 6px', 
                            borderRadius: 2, 
                            marginRight: 4 
                          }}>
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null
                })}
              </Space>
            </Card>
          )}
        </Form>

        {/* 智能按钮区域 */}
        <div style={{ 
          marginTop: 24, 
          borderTop: '1px solid #f0f0f0',
          paddingTop: 16
        }}>
          {currentStep === 'config' && (
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button onClick={onCancel}>取消</Button>
                {selectedAlgorithms.length > 0 && (
                  <>
                    <Button onClick={handleSaveConfig}>
                      仅保存配置
                    </Button>
                    <Button 
                      type="primary" 
                      onClick={handleSaveAndStart}
                      style={{ background: '#52c41a', borderColor: '#52c41a' }}
                      icon={<PlayCircleOutlined />}
                    >
                      保存并启动分析
                    </Button>
                  </>
                )}
              </Space>
            </div>
          )}

          {currentStep === 'ready' && (
            <div>
              <div style={{ textAlign: 'left', marginBottom: 12 }}>
                <Text type="secondary">
                  💡 提示：您可以继续修改配置，或者立即启动分析任务。
                </Text>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Space>
                  <Button onClick={onCancel}>完成并关闭</Button>
                  <Button 
                    onClick={() => setCurrentStep('config')}
                    icon={<SettingOutlined />}
                  >
                    修改配置
                  </Button>
                  <Button 
                    type="primary" 
                    onClick={handleStartAnalysis}
                    style={{ background: '#52c41a', borderColor: '#52c41a' }}
                    icon={<PlayCircleOutlined />}
                  >
                    启动分析
                  </Button>
                </Space>
              </div>
            </div>
          )}

          {currentStep === 'analyzing' && (
            <div style={{ textAlign: 'center' }}>
              <Spin size="small" style={{ marginRight: 8 }} />
              <Text>正在启动分析任务，请稍候...</Text>
            </div>
          )}
        </div>
      </Spin>
    </Modal>
  )
}

export default AlgorithmConfigModal