import React from 'react'
import { Modal, Form, Input, Select, Switch, Space, Button, Tag, Descriptions } from 'antd'
import { PromptTemplate } from '../../types/prompt'

const { TextArea } = Input
const { Option } = Select

interface PromptModalsProps {
  // 创建模态框
  createModalVisible: boolean
  setCreateModalVisible: (visible: boolean) => void
  createForm: any
  onCreateSubmit: (values: any) => void
  
  // 编辑模态框
  editModalVisible: boolean
  setEditModalVisible: (visible: boolean) => void
  editForm: any
  selectedTemplate: PromptTemplate | null
  onEditSubmit: (values: any) => void
  
  // 预览模态框
  previewModalVisible: boolean
  setPreviewModalVisible: (visible: boolean) => void
}

const PromptModals: React.FC<PromptModalsProps> = ({
  createModalVisible,
  setCreateModalVisible,
  createForm,
  onCreateSubmit,
  editModalVisible,
  setEditModalVisible,
  editForm,
  selectedTemplate,
  onEditSubmit,
  previewModalVisible,
  setPreviewModalVisible
}) => {
  const categoryOptions = [
    { value: 'safety_detection', label: '安全检测' },
    { value: 'behavior_analysis', label: '行为分析' },
    { value: 'object_recognition', label: '目标识别' },
    { value: 'environment_monitor', label: '环境监控' },
    { value: 'quality_control', label: '质量控制' },
    { value: 'custom', label: '自定义' }
  ]

  const priorityOptions = [
    { value: 'critical', label: '危险' },
    { value: 'high', label: '高' },
    { value: 'medium', label: '中' },
    { value: 'low', label: '低' }
  ]

  return (
    <>
      {/* 创建模板模态框 */}
      <Modal
        title="创建提示词模板"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        width={800}
        footer={null}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={onCreateSubmit}
        >
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="输入模板名称" />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item
              name="category"
              label="分类"
              rules={[{ required: true, message: '请选择分类' }]}
            >
              <Select placeholder="选择分类" style={{ width: 150 }}>
                {categoryOptions.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="priority"
              label="优先级"
              rules={[{ required: true, message: '请选择优先级' }]}
            >
              <Select placeholder="选择优先级" style={{ width: 120 }}>
                {priorityOptions.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Space>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="输入模板描述" />
          </Form.Item>

          <Form.Item
            name="system_prompt"
            label="系统提示词"
            rules={[{ required: true, message: '请输入系统提示词' }]}
          >
            <TextArea rows={4} placeholder="输入系统提示词" />
          </Form.Item>

          <Form.Item
            name="user_prompt"
            label="用户提示词"
            rules={[{ required: true, message: '请输入用户提示词' }]}
          >
            <TextArea rows={4} placeholder="输入用户提示词" />
          </Form.Item>

          <Form.Item name="tags" label="标签">
            <Select
              mode="tags"
              placeholder="输入标签（回车确认）"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item name="is_active" label="立即激活" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                创建模板
              </Button>
              <Button onClick={() => setCreateModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑模板模态框 */}
      <Modal
        title="编辑提示词模板"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        width={800}
        footer={null}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={onEditSubmit}
        >
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="输入模板名称" />
          </Form.Item>

          <Space style={{ width: '100%' }} size="large">
            <Form.Item
              name="category"
              label="分类"
              rules={[{ required: true, message: '请选择分类' }]}
            >
              <Select placeholder="选择分类" style={{ width: 150 }}>
                {categoryOptions.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item
              name="priority"
              label="优先级"
              rules={[{ required: true, message: '请选择优先级' }]}
            >
              <Select placeholder="选择优先级" style={{ width: 120 }}>
                {priorityOptions.map(option => (
                  <Option key={option.value} value={option.value}>
                    {option.label}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Space>

          <Form.Item name="description" label="描述">
            <TextArea rows={2} placeholder="输入模板描述" />
          </Form.Item>

          <Form.Item
            name="system_prompt"
            label="系统提示词"
            rules={[{ required: true, message: '请输入系统提示词' }]}
          >
            <TextArea rows={4} placeholder="输入系统提示词" />
          </Form.Item>

          <Form.Item
            name="user_prompt"
            label="用户提示词"
            rules={[{ required: true, message: '请输入用户提示词' }]}
          >
            <TextArea rows={4} placeholder="输入用户提示词" />
          </Form.Item>

          <Form.Item name="tags" label="标签">
            <Select
              mode="tags"
              placeholder="输入标签（回车确认）"
              style={{ width: '100%' }}
            />
          </Form.Item>

          <Form.Item name="is_active" label="激活状态" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                更新模板
              </Button>
              <Button onClick={() => setEditModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 预览模态框 */}
      <Modal
        title="模板预览"
        open={previewModalVisible}
        onCancel={() => setPreviewModalVisible(false)}
        width={800}
        footer={[
          <Button key="close" onClick={() => setPreviewModalVisible(false)}>
            关闭
          </Button>
        ]}
      >
        {selectedTemplate && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="模板名称">
              {selectedTemplate.name}
            </Descriptions.Item>
            <Descriptions.Item label="分类">
              {selectedTemplate.category}
            </Descriptions.Item>
            <Descriptions.Item label="优先级">
              {selectedTemplate.priority}
            </Descriptions.Item>
            <Descriptions.Item label="描述">
              {selectedTemplate.description}
            </Descriptions.Item>
            <Descriptions.Item label="系统提示词">
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                {selectedTemplate.system_prompt}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="用户提示词">
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit' }}>
                {selectedTemplate.user_prompt}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label="标签">
              <Space>
                {selectedTemplate.tags.map(tag => (
                  <Tag key={tag}>{tag}</Tag>
                ))}
              </Space>
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </>
  )
}

export default PromptModals