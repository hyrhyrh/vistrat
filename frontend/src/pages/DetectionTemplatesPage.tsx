import React, { useState, useEffect } from 'react'
import {
  Layout,
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  message,
  Popconfirm,
  Tag,
  Tooltip,
  Upload,
  Typography,
  Row,
  Col,
  Badge,
  Divider
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined,
  InfoCircleOutlined,
  SafetyOutlined,
  ExclamationCircleOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { UploadFile } from 'antd/lib/upload/interface'

const { Content } = Layout
const { TextArea } = Input
const { Option } = Select
const { Title, Text, Paragraph } = Typography

// 类别和严重程度映射
const CATEGORY_MAP: Record<string, { text: string; color: string; icon: string }> = {
  'safety': { text: '安全装备', color: 'red', icon: '🛡️' },
  'behavior': { text: '违规行为', color: 'orange', icon: '⚠️' },
  'environment': { text: '环境风险', color: 'green', icon: '🌍' },
  'security': { text: '安保威胁', color: 'purple', icon: '🔒' }
}

const SEVERITY_MAP: Record<string, { text: string; color: string }> = {
  'critical': { text: '严重', color: 'error' },
  'high': { text: '高', color: 'warning' },
  'medium': { text: '中', color: 'processing' },
  'low': { text: '低', color: 'default' }
}

interface DetectionTemplate {
  type_code: string
  name: string
  category: string
  severity: string
  description: string
  prompt_template: string
  json_schema: string
  sort_order: number
  enabled: boolean
  created_at: string
  updated_at: string
}

const DetectionTemplatesPage: React.FC = () => {
  const [templates, setTemplates] = useState<DetectionTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [modalVisible, setModalVisible] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<DetectionTemplate | null>(null)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [uploadFileList, setUploadFileList] = useState<UploadFile[]>([])
  const [form] = Form.useForm()

  useEffect(() => {
    loadTemplates()
  }, [])

  const loadTemplates = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/video-files/detection-types/templates')
      const data = await response.json()
      setTemplates(data.templates || [])
    } catch (error) {
      message.error('加载检测类型模板失败')
      console.error('加载失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingTemplate(null)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (template: DetectionTemplate) => {
    setEditingTemplate(template)
    form.setFieldsValue({
      type_code: template.type_code,
      display_name: template.name,
      category: template.category,
      severity: template.severity,
      description: template.description,
      prompt_template: template.prompt_template,
      json_field_name: template.json_schema,
      sort_order: template.sort_order,
      enabled: template.enabled
    })
    setModalVisible(true)
  }

  const handleDelete = async (type_code: string) => {
    try {
      const response = await fetch(`/api/video-files/detection-types/${type_code}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        message.success('删除成功')
        loadTemplates()
      } else {
        const data = await response.json()
        message.error(data.detail || '删除失败')
      }
    } catch (error) {
      message.error('删除失败')
      console.error('删除失败:', error)
    }
  }

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields()

      const templateData = {
        type_code: values.type_code,
        display_name: values.display_name,
        category: values.category,
        severity: values.severity,
        description: values.description || '',
        prompt_template: values.prompt_template || '',
        json_field_name: values.json_field_name || values.type_code,
        sort_order: values.sort_order || 0,
        enabled: values.enabled !== false
      }

      let response
      if (editingTemplate) {
        // 更新
        response = await fetch(`/api/video-files/detection-types/${editingTemplate.type_code}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(templateData)
        })
      } else {
        // 新建
        response = await fetch('/api/video-files/detection-types', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(templateData)
        })
      }

      if (response.ok) {
        message.success(editingTemplate ? '更新成功' : '创建成功')
        setModalVisible(false)
        loadTemplates()
      } else {
        const data = await response.json()
        message.error(data.detail || (editingTemplate ? '更新失败' : '创建失败'))
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请填写必填字段')
      } else {
        message.error('操作失败')
        console.error('操作失败:', error)
      }
    }
  }

  const handleExport = () => {
    const dataStr = JSON.stringify(templates, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = `detection_templates_${new Date().getTime()}.json`
    link.click()
    URL.revokeObjectURL(url)
    message.success('导出成功')
  }

  const handleUploadFile = (info: any) => {
    setUploadFileList(info.fileList.slice(-1))
  }

  const handleBatchImport = async () => {
    if (uploadFileList.length === 0) {
      message.warning('请选择JSON文件')
      return
    }

    try {
      const file = uploadFileList[0].originFileObj
      if (!file) {
        message.error('文件读取失败')
        return
      }

      const reader = new FileReader()
      reader.onload = async (e) => {
        try {
          const content = e.target?.result as string
          const templates = JSON.parse(content)

          if (!Array.isArray(templates)) {
            message.error('JSON格式错误：应为数组格式')
            return
          }

          const response = await fetch('/api/video-files/detection-types/batch-import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(templates)
          })

          const data = await response.json()
          if (response.ok) {
            message.success(data.message)
            setUploadModalVisible(false)
            setUploadFileList([])
            loadTemplates()
          } else {
            message.error(data.detail || '批量导入失败')
          }
        } catch (error) {
          message.error('JSON解析失败，请检查文件格式')
          console.error('解析失败:', error)
        }
      }
      reader.readAsText(file)
    } catch (error) {
      message.error('文件读取失败')
      console.error('读取失败:', error)
    }
  }

  const columns: ColumnsType<DetectionTemplate> = [
    {
      title: '类型编码',
      dataIndex: 'type_code',
      key: 'type_code',
      width: 150,
      render: (text: string) => (
        <Text code style={{ fontSize: '12px' }}>{text}</Text>
      )
    },
    {
      title: '检测类型',
      dataIndex: 'name',
      key: 'name',
      width: 150,
      render: (text: string) => (
        <Text strong>{text}</Text>
      )
    },
    {
      title: '类别',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string) => {
        const config = CATEGORY_MAP[category] || { text: category, color: 'default', icon: '📋' }
        return (
          <Tag color={config.color}>
            <span>{config.icon} {config.text}</span>
          </Tag>
        )
      }
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => {
        const config = SEVERITY_MAP[severity] || { text: severity, color: 'default' }
        return (
          <Badge status={config.color as any} text={config.text} />
        )
      }
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text} placement="topLeft">
          <Paragraph ellipsis={{ rows: 2 }} style={{ margin: 0, maxWidth: 300 }}>
            {text || '暂无描述'}
          </Paragraph>
        </Tooltip>
      )
    },
    {
      title: '排序',
      dataIndex: 'sort_order',
      key: 'sort_order',
      width: 80,
      align: 'center',
      render: (order: number) => <Text type="secondary">{order}</Text>
    },
    {
      title: '状态',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      align: 'center',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? '启用' : '禁用'}
        </Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              size="small"
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定要删除这个检测类型模板吗？"
            description={
              <div style={{ maxWidth: 300 }}>
                <div>类型：{record.name}</div>
                <div style={{ color: '#ff4d4f', marginTop: 4 }}>
                  此操作将软删除该模板，相关算法配置可能受影响
                </div>
              </div>
            }
            onConfirm={() => handleDelete(record.type_code)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            icon={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
          >
            <Tooltip title="删除">
              <Button
                type="text"
                icon={<DeleteOutlined />}
                size="small"
                danger
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      )
    }
  ]

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <div style={{ marginBottom: '24px' }}>
          <Row justify="space-between" align="middle">
            <Col>
              <Title level={2} style={{ margin: 0 }}>
                <Space>
                  <SafetyOutlined />
                  检测类型模板管理
                </Space>
              </Title>
              <Text type="secondary" style={{ marginTop: 8 }}>
                管理AI检测类型模板，用于复合检测算法配置
              </Text>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadTemplates}
                  loading={loading}
                >
                  刷新
                </Button>
                <Button
                  icon={<DownloadOutlined />}
                  onClick={handleExport}
                  disabled={templates.length === 0}
                >
                  导出JSON
                </Button>
                <Button
                  icon={<UploadOutlined />}
                  onClick={() => setUploadModalVisible(true)}
                >
                  批量导入
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreate}
                >
                  新建模板
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        <Card>
          <Table
            columns={columns}
            dataSource={templates}
            rowKey="type_code"
            loading={loading}
            pagination={{
              total: templates.length,
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 个模板`
            }}
            scroll={{ x: 1200 }}
            size="middle"
          />
        </Card>

        {/* 新建/编辑模态框 */}
        <Modal
          title={
            <Space>
              {editingTemplate ? <EditOutlined /> : <PlusOutlined />}
              <span>{editingTemplate ? '编辑检测类型模板' : '新建检测类型模板'}</span>
            </Space>
          }
          open={modalVisible}
          onOk={handleModalOk}
          onCancel={() => setModalVisible(false)}
          width={800}
          okText="确定"
          cancelText="取消"
        >
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              category: 'safety',
              severity: 'medium',
              sort_order: 0,
              enabled: true
            }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="type_code"
                  label="类型编码"
                  rules={[
                    { required: true, message: '请输入类型编码' },
                    { pattern: /^[a-z_]+$/, message: '只能包含小写字母和下划线' }
                  ]}
                  tooltip="唯一标识，如: safety_helmet, smoking"
                >
                  <Input
                    placeholder="如: safety_helmet"
                    disabled={!!editingTemplate}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="display_name"
                  label="显示名称"
                  rules={[{ required: true, message: '请输入显示名称' }]}
                >
                  <Input placeholder="如: 未佩戴安全帽" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item
                  name="category"
                  label="类别"
                  rules={[{ required: true, message: '请选择类别' }]}
                >
                  <Select placeholder="选择类别">
                    {Object.entries(CATEGORY_MAP).map(([key, value]) => (
                      <Option key={key} value={key}>
                        <Space>
                          <span>{value.icon}</span>
                          <span>{value.text}</span>
                        </Space>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="severity"
                  label="严重程度"
                  rules={[{ required: true, message: '请选择严重程度' }]}
                >
                  <Select placeholder="选择严重程度">
                    {Object.entries(SEVERITY_MAP).map(([key, value]) => (
                      <Option key={key} value={key}>
                        {value.text}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="sort_order"
                  label="排序顺序"
                  tooltip="数字越小越靠前"
                >
                  <InputNumber
                    min={0}
                    max={999}
                    style={{ width: '100%' }}
                    placeholder="0"
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="description"
              label="描述"
            >
              <TextArea
                rows={2}
                placeholder="描述该检测类型的用途和场景"
              />
            </Form.Item>

            <Form.Item
              name="prompt_template"
              label={
                <Space>
                  <span>提示词模板</span>
                  <Tooltip title="用于AI检测的提示词内容，会自动组装到复合提示词中">
                    <InfoCircleOutlined />
                  </Tooltip>
                </Space>
              }
            >
              <TextArea
                rows={4}
                placeholder="请输入AI检测提示词..."
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={16}>
                <Form.Item
                  name="json_field_name"
                  label="JSON字段名"
                  tooltip="AI返回结果中的字段名，默认与type_code相同"
                >
                  <Input placeholder="如: safety_helmet" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="enabled"
                  label="启用状态"
                  valuePropName="checked"
                >
                  <Switch checkedChildren="启用" unCheckedChildren="禁用" />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Modal>

        {/* 批量导入模态框 */}
        <Modal
          title={
            <Space>
              <UploadOutlined />
              <span>批量导入检测类型模板</span>
            </Space>
          }
          open={uploadModalVisible}
          onOk={handleBatchImport}
          onCancel={() => {
            setUploadModalVisible(false)
            setUploadFileList([])
          }}
          okText="开始导入"
          cancelText="取消"
        >
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            <div>
              <Paragraph>
                请上传JSON格式的模板文件，格式示例：
              </Paragraph>
              <pre style={{
                background: '#f5f5f5',
                padding: '12px',
                borderRadius: '4px',
                fontSize: '12px',
                overflow: 'auto'
              }}>
{`[
  {
    "type_code": "safety_helmet",
    "display_name": "未佩戴安全帽",
    "category": "safety",
    "severity": "high",
    "description": "检测人员是否佩戴安全帽",
    "prompt_template": "请检测...",
    "json_field_name": "safety_helmet",
    "sort_order": 1,
    "enabled": true
  }
]`}
              </pre>
            </div>

            <Upload
              fileList={uploadFileList}
              onChange={handleUploadFile}
              beforeUpload={() => false}
              accept=".json"
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>
                选择JSON文件
              </Button>
            </Upload>

            <div style={{ color: '#666', fontSize: '12px' }}>
              <div>• 文件格式：JSON</div>
              <div>• 重复的type_code将被跳过</div>
              <div>• 导入后会自动刷新列表</div>
            </div>
          </Space>
        </Modal>
      </Content>
    </Layout>
  )
}

export default DetectionTemplatesPage
