import React, { useState, useEffect } from 'react'
import { 
  Modal, 
  Form, 
  Select, 
  Button, 
  Space, 
  message,
  Table,
  Tag,
  InputNumber,
  Switch,
  Descriptions,
  Alert,
  Badge,
  Row,
  Col
} from 'antd'
import { CheckCircleOutlined, ExclamationCircleOutlined } from '@ant-design/icons'

const { Option } = Select

interface StreamAlgorithmModalProps {
  visible: boolean
  onCancel: () => void
  stream: any
  onConfirm: () => void
}

interface PromptTemplate {
  id: string
  name: string
  type: string
  description?: string
  enabled: boolean
}

interface StreamTemplate {
  id: string
  template_id: string
  template_name: string
  analysis_status: string
  enabled: boolean
  confidence_threshold: number
  priority: number
  alerts_count: number
  detection_count: number
}

const StreamAlgorithmModal: React.FC<StreamAlgorithmModalProps> = ({
  visible,
  onCancel,
  stream,
  onConfirm
}) => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [availableTemplates, setAvailableTemplates] = useState<PromptTemplate[]>([])
  const [currentTemplates, setCurrentTemplates] = useState<StreamTemplate[]>([])
  
  useEffect(() => {
    if (visible && stream) {
      loadAvailableTemplates()
      loadCurrentTemplates()
    }
  }, [visible, stream])

  const loadAvailableTemplates = async () => {
    try {
      const response = await fetch('/api/prompts/')
      const data = await response.json()
      setAvailableTemplates(data.templates || [])
    } catch (error) {
      message.error('加载AI模板列表失败')
    }
  }

  const loadCurrentTemplates = async () => {
    if (!stream?.id) return
    
    try {
      const response = await fetch(`/api/video-streams/${stream.id}/analysis/templates`)
      const data = await response.json()
      setCurrentTemplates(data.templates || [])
    } catch (error) {
      console.error('加载当前配置失败:', error)
    }
  }

  const handleSubmit = async (values: any) => {
    if (!stream?.id) return
    
    setLoading(true)
    try {
      const response = await fetch(`/api/video-streams/${stream.id}/analysis/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stream_id: stream.id,
          template_ids: values.template_ids || [],
          priority: values.priority || 1,
          confidence_threshold: values.confidence_threshold || 0.7
        })
      })
      
      if (response.ok) {
        message.success('算法配置成功')
        onCancel()
        onConfirm()
      } else {
        const error = await response.json()
        throw new Error(error.detail || '配置失败')
      }
    } catch (error: any) {
      message.error(error.message || '配置算法失败')
    } finally {
      setLoading(false)
    }
  }

  const handleStartAnalysis = async () => {
    if (!stream?.id) return

    try {
      const response = await fetch(`/api/video-streams/${stream.id}/analysis/start`, {
        method: 'POST'
      })

      if (response.ok) {
        message.success('分析任务已启动')
        onConfirm()
      } else {
        // 读取响应体获取详细错误信息
        const errorData = await response.json()
        const errorMsg = errorData.error?.message || errorData.message || '启动分析失败'
        throw new Error(errorMsg)
      }
    } catch (error: any) {
      // 显示详细的错误信息
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        message.error('网络连接失败，请检查网络后重试')
      } else {
        // 如果错误信息太长，使用Modal显示
        const errorMsg = error.message || '启动分析失败'
        if (errorMsg.length > 100) {
          Modal.error({
            title: '启动分析失败',
            content: (
              <div style={{ maxHeight: '400px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                {errorMsg}
              </div>
            ),
            width: 600
          })
        } else {
          message.error(errorMsg)
        }
      }
    }
  }

  const handleStopAnalysis = async () => {
    if (!stream?.id) return
    
    try {
      const response = await fetch(`/api/video-streams/${stream.id}/analysis/stop`, {
        method: 'POST'
      })
      
      if (response.ok) {
        message.success('分析任务已停止')
        onConfirm()
      } else {
        throw new Error('停止分析失败')
      }
    } catch (error) {
      message.error('停止分析失败')
    }
  }

  const templateColumns = [
    {
      title: '模板名称',
      dataIndex: 'template_name',
      key: 'template_name'
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority'
    },
    {
      title: '置信度',
      dataIndex: 'confidence_threshold',
      key: 'confidence_threshold',
      render: (value: number) => `${(value * 100).toFixed(1)}%`
    },
    {
      title: '检测/告警',
      key: 'stats',
      render: (record: StreamTemplate) => (
        <div>
          <div>检测: {record.detection_count}</div>
          <div>告警: {record.alerts_count}</div>
        </div>
      )
    }
  ]

  return (
    <Modal
      title={`配置算法 - ${stream?.name}`}
      open={visible}
      onCancel={onCancel}
      width={800}
      footer={null}
    >
      <div>
        {/* 视频流信息 */}
        <Descriptions size="small" column={2} style={{ marginBottom: 16 }}>
          <Descriptions.Item label="摄像头">{stream?.name}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Badge 
              status={stream?.status === 'ONLINE' ? 'success' : 'error'} 
              text={stream?.status === 'ONLINE' ? '在线' : '离线'} 
            />
          </Descriptions.Item>
          <Descriptions.Item label="流地址">{stream?.stream_url}</Descriptions.Item>
        </Descriptions>

        {/* 当前配置的模板 */}
        {currentTemplates.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <h4>当前配置的算法模板</h4>
            <Table
              columns={templateColumns}
              dataSource={currentTemplates}
              size="small"
              pagination={false}
              rowKey="id"
            />
          </div>
        )}

        {/* 分析控制 */}
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button 
              type="primary" 
              icon={<CheckCircleOutlined />}
              onClick={handleStartAnalysis}
              disabled={currentTemplates.length === 0}
            >
              启动分析
            </Button>
            <Button 
              danger
              onClick={handleStopAnalysis}
            >
              停止分析
            </Button>
          </Space>
        </div>

        {/* 配置新算法 */}
        <Alert 
          message="算法配置" 
          description="选择AI提示词模板来配置视频分析算法" 
          type="info" 
          style={{ marginBottom: 16 }} 
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="template_ids"
            label="选择AI算法模板"
            rules={[{ required: true, message: '请选择至少一个算法模板' }]}
          >
            <Select
              mode="multiple"
              placeholder="选择算法模板（可多选）"
              style={{ width: '100%' }}
              optionFilterProp="label"
            >
              {availableTemplates.map(template => (
                <Option 
                  key={template.id} 
                  value={template.id}
                  label={template.name}
                  disabled={!template.enabled}
                >
                  <div>
                    <div>{template.name}</div>
                    <div style={{ fontSize: '12px', color: '#666' }}>
                      {template.type} - {template.description}
                    </div>
                  </div>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label="优先级"
                initialValue={1}
              >
                <InputNumber min={1} max={5} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="confidence_threshold"
                label="置信度阈值"
                initialValue={0.7}
              >
                <InputNumber 
                  min={0.1} 
                  max={1.0} 
                  step={0.1} 
                  formatter={value => `${(value * 100).toFixed(0)}%`}
                  parser={value => parseFloat(value?.replace('%', '')) / 100}
                  style={{ width: '100%' }} 
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading}>
                应用配置
              </Button>
              <Button onClick={onCancel}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </div>
    </Modal>
  )
}

export default StreamAlgorithmModal