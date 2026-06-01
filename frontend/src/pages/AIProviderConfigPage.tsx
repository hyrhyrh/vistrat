import React, { useState, useEffect } from 'react'
import {
  Layout,
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Switch,
  InputNumber,
  Tag,
  Space,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Divider,
  Alert
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SettingOutlined,
  CheckCircleOutlined,
  StopOutlined,
  ReloadOutlined,
  ExperimentOutlined
} from '@ant-design/icons'

const { Content } = Layout
const { TextArea } = Input
const { Title } = Typography

interface AIProvider {
  id: string
  provider_name: string
  display_name: string
  icon: string
  description: string
  api_base_url: string
  api_key: string
  api_version: string
  available_models: string[]
  default_model: string
  is_active: boolean
  sort_order: number
  created_at: string
  updated_at: string
}

const AIProviderConfigPage: React.FC = () => {
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingProvider, setEditingProvider] = useState<AIProvider | null>(null)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<any>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    loadProviders()
  }, [])

  const loadProviders = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/ai-provider-configs/')
      const data = await response.json()
      setProviders(data)
    } catch (error) {
      message.error('加载AI供应商配置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingProvider(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (provider: AIProvider) => {
    setEditingProvider(provider)
    form.setFieldsValue({
      ...provider,
      available_models: provider.available_models.join(', ')
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: string) => {
    try {
      const response = await fetch(`/api/ai-provider-configs/${id}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        message.success('供应商配置删除成功')
        loadProviders()
      } else {
        throw new Error('删除失败')
      }
    } catch (error) {
      message.error('删除供应商配置失败')
    }
  }

  const handleToggleStatus = async (id: string) => {
    try {
      const response = await fetch(`/api/ai-provider-configs/${id}/toggle-status`, {
        method: 'POST'
      })
      
      if (response.ok) {
        message.success('供应商状态切换成功')
        loadProviders()
      } else {
        throw new Error('状态切换失败')
      }
    } catch (error) {
      message.error('切换供应商状态失败')
    }
  }

  const handleTest = async () => {
    try {
      const values = await form.validateFields(['api_base_url', 'default_model', 'api_key'])
      
      setTesting(true)
      setTestResult(null)

      // 处理available_models字段
      const processedValues = {
        ...values,
        available_models: values.available_models?.split(',').map((model: string) => model.trim()).filter(Boolean) || []
      }

      const response = await fetch('/api/ai-provider-configs/test-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(processedValues)
      })

      const result = await response.json()
      setTestResult(result)
      
      if (result.status === 'ok') {
        message.success('连接测试成功！')
      } else {
        message.error('连接测试失败')
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请先填写必需字段：API地址、API密钥、默认模型')
      } else {
        message.error('测试失败：' + (error.message || '未知错误'))
        setTestResult({
          status: 'error',
          message: '测试失败',
          details: { error: error.message || '未知错误' }
        })
      }
    } finally {
      setTesting(false)
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      
      // 处理available_models字段
      const processedValues = {
        ...values,
        available_models: values.available_models?.split(',').map((model: string) => model.trim()).filter(Boolean) || []
      }

      const url = editingProvider 
        ? `/api/ai-provider-configs/${editingProvider.id}`
        : '/api/ai-provider-configs/'
      
      const method = editingProvider ? 'PUT' : 'POST'

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(processedValues)
      })

      if (response.ok) {
        message.success(editingProvider ? '更新成功' : '创建成功')
        setModalVisible(false)
        setTestResult(null)
        loadProviders()
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || '保存失败')
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请检查表单输入')
      } else {
        message.error(error.message || '保存失败')
      }
    }
  }

  const columns = [
    {
      title: '供应商',
      dataIndex: 'display_name',
      key: 'display_name',
      render: (text: string, record: AIProvider) => (
        <Space>
          <span style={{ fontSize: '18px' }}>{record.icon}</span>
          <span>{text}</span>
          <Tag color={record.is_active ? 'green' : 'red'}>
            {record.is_active ? '活跃' : '禁用'}
          </Tag>
        </Space>
      )
    },
    {
      title: '供应商名称',
      dataIndex: 'provider_name',
      key: 'provider_name',
      render: (text: string) => <code>{text}</code>
    },
    {
      title: 'API地址',
      dataIndex: 'api_base_url',
      key: 'api_base_url',
      ellipsis: true
    },
    {
      title: '可用模型',
      dataIndex: 'available_models',
      key: 'available_models',
      render: (models: string[]) => (
        <span>
          {models?.slice(0, 2).map(model => (
            <Tag key={model} size="small">{model}</Tag>
          ))}
          {models?.length > 2 && <Tag size="small">+{models.length - 2}</Tag>}
        </span>
      )
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
      align: 'center' as const
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record: AIProvider) => (
        <Space size="small">
          <Button
            type="text"
            icon={record.is_active ? <StopOutlined /> : <CheckCircleOutlined />}
            onClick={() => handleToggleStatus(record.id)}
            title={record.is_active ? '禁用' : '启用'}
          />
          <Button
            type="text"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            title="编辑"
          />
          <Popconfirm
            title="确定删除这个供应商配置吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              title="删除"
            />
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <Row justify="space-between" align="middle" style={{ marginBottom: '24px' }}>
          <Col>
            <Title level={2}>
              <SettingOutlined style={{ marginRight: '8px' }} />
              AI供应商配置
            </Title>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadProviders}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                添加供应商
              </Button>
            </Space>
          </Col>
        </Row>

        <Alert
          message="AI供应商配置管理"
          description="在这里管理各AI模型供应商的配置信息，包括API地址、密钥、可用模型等。只有激活的供应商才会在AI模型编排页面中显示。"
          type="info"
          style={{ marginBottom: '24px' }}
          showIcon
        />

        <Card>
          <Table
            columns={columns}
            dataSource={providers}
            rowKey="id"
            loading={loading}
            pagination={{
              total: providers.length,
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条记录`
            }}
          />
        </Card>

        <Modal
          title={editingProvider ? '编辑AI供应商' : '添加AI供应商'}
          open={modalVisible}
          onOk={handleSave}
          onCancel={() => {
            setModalVisible(false)
            setTestResult(null)
          }}
          width={900}
          okText="保存"
          cancelText="取消"
          footer={[
            <Button key="cancel" onClick={() => {
              setModalVisible(false)
              setTestResult(null)
            }}>
              取消
            </Button>,
            <Button 
              key="test" 
              icon={<ExperimentOutlined />}
              onClick={handleTest}
              loading={testing}
            >
              {testing ? '测试中...' : '测试连接'}
            </Button>,
            <Button 
              key="save" 
              type="primary" 
              onClick={handleSave}
            >
              保存
            </Button>
          ]}
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              is_active: true,
              sort_order: 0,
              api_version: 'v1',
              icon: '🤖'
            }}
          >
            {/* 测试结果显示 */}
            {testResult && (
              <Alert
                message={testResult.message}
                description={
                  <div>
                    <p><strong>供应商:</strong> {testResult.provider}</p>
                    {testResult.details && (
                      <>
                        <p><strong>状态码:</strong> {testResult.details.status_code}</p>
                        <p><strong>响应时间:</strong> {testResult.details.response_time}秒</p>
                        {testResult.details.success ? (
                          <>
                            <p><strong>AI响应:</strong> {testResult.details.ai_response}</p>
                            {testResult.details.model_used && (
                              <p><strong>使用模型:</strong> {testResult.details.model_used}</p>
                            )}
                            {testResult.details.tokens_used > 0 && (
                              <p><strong>Token消耗:</strong> {testResult.details.tokens_used}</p>
                            )}
                          </>
                        ) : (
                          <>
                            <p><strong>错误信息:</strong> {testResult.details.error}</p>
                            {testResult.details.raw_response && (
                              <p><strong>原始响应:</strong> {testResult.details.raw_response}</p>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </div>
                }
                type={testResult.status === 'ok' ? 'success' : 'error'}
                style={{ marginBottom: '16px' }}
                closable
                onClose={() => setTestResult(null)}
              />
            )}

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="provider_name"
                  label="供应商名称"
                  rules={[{ required: true, message: '请输入供应商名称' }]}
                >
                  <Input placeholder="如: qwen, gpt, claude" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="display_name"
                  label="显示名称"
                  rules={[{ required: true, message: '请输入显示名称' }]}
                >
                  <Input placeholder="如: 通义千问, OpenAI GPT" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="icon" label="图标">
                  <Input placeholder="🤖" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="api_version" label="API版本">
                  <Input placeholder="v1" />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="sort_order" label="排序">
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="is_active" label="是否启用" valuePropName="checked">
                  <Switch />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="description" label="描述">
              <TextArea rows={2} placeholder="供应商描述信息" />
            </Form.Item>

            <Form.Item
              name="api_base_url"
              label="API基础地址"
              rules={[{ required: true, message: '请输入API基础地址' }]}
            >
              <Input placeholder="https://api.example.com/v1/chat/completions" />
            </Form.Item>

            <Form.Item name="api_key" label="API密钥">
              <Input.Password placeholder="输入API密钥" />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="available_models" label="可用模型">
                  <TextArea
                    rows={3}
                    placeholder="用逗号分隔多个模型，如: gpt-4, gpt-3.5-turbo"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="default_model" label="默认模型">
                  <Input placeholder="默认使用的模型名称" />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Modal>
      </Content>
    </Layout>
  )
}

export default AIProviderConfigPage