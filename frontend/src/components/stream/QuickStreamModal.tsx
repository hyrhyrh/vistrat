import React, { useState, useEffect } from 'react'
import { 
  Modal, 
  Form, 
  Input, 
  Button, 
  Space, 
  message,
  Card,
  Typography,
  Alert
} from 'antd'
import { PlayCircleOutlined } from '@ant-design/icons'

const { Title } = Typography

interface QuickStreamModalProps {
  visible: boolean
  onCancel: () => void
  onSuccess?: () => void
}

const QuickStreamModal: React.FC<QuickStreamModalProps> = ({
  visible,
  onCancel,
  onSuccess
}) => {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (visible) {
      form.resetFields()
      // 设置默认值
      form.setFieldsValue({
        stream_name: `快速流_${new Date().getTime()}`,
        rtsp_url: 'rtsp://'
      })
    }
  }, [visible, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      // 使用默认算法配置创建实时流
      const streamConfig = {
        stream_name: values.stream_name,
        rtsp_url: values.rtsp_url,
        template_ids: ['template_1', 'template_2'], // 使用默认算法
        frame_interval: 3.0,
        auto_restart: true,
        max_reconnect_attempts: 5,
        analysis_enabled: true,
        alert_enabled: true,
        storage_enabled: true
      }

      // 创建流配置
      const response = await fetch('/api/realtime-streams/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(streamConfig)
      })

      const data = await response.json()
      if (data.success) {
        const streamId = data.data.stream_id
        message.success('实时流创建成功')
        
        // 自动启动分析
        await startAnalysis(streamId)
        
        // 关闭模态框
        handleCancel()
        if (onSuccess) {
          onSuccess()
        }
      } else {
        message.error(data.message || '创建失败')
      }
    } catch (error) {
      message.error('创建失败')
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
        message.success('实时分析已自动启动')
      }
    } catch (error) {
      console.error('启动分析失败:', error)
    }
  }

  const handleCancel = () => {
    form.resetFields()
    onCancel()
  }

  return (
    <Modal
      title="快速创建实时流"
      open={visible}
      onCancel={handleCancel}
      width={500}
      footer={
        <Space>
          <Button onClick={handleCancel}>取消</Button>
          <Button 
            type="primary" 
            icon={<PlayCircleOutlined />}
            onClick={handleSubmit}
            loading={loading}
          >
            创建并启动
          </Button>
        </Space>
      }
      destroyOnHidden
    >
      <Card>
        <Title level={4}>一键快速配置</Title>
        
        <Form form={form} layout="vertical">
          <Form.Item
            name="stream_name"
            label="流名称"
            rules={[{ required: true, message: '请输入流名称' }]}
          >
            <Input placeholder="为实时流起一个名称" />
          </Form.Item>
          
          <Form.Item
            name="rtsp_url"
            label="RTSP地址"
            rules={[
              { required: true, message: '请输入RTSP地址' },
              { pattern: /^(rtsp|rtmp|http):\/\/.+/, message: '请输入有效的RTSP地址' }
            ]}
          >
            <Input placeholder="rtsp://192.168.1.100:554/stream" />
          </Form.Item>
        </Form>

        <Alert
          message="自动配置"
          description="将使用默认算法模板进行智能分析，包含目标检测和行为分析，采样间隔3秒，自动启用告警和存储。"
          type="info"
          showIcon
          style={{ marginTop: 16 }}
        />
      </Card>
    </Modal>
  )
}

export default QuickStreamModal