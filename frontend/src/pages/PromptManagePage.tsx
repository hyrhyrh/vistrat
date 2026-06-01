import React, { useState, useEffect } from 'react'
import { 
  Card, 
  Button, 
  Space, 
  message, 
  Form, 
  Input, 
  Table, 
  Tag, 
  Modal,
  Row,
  Col,
  Typography,
  Popconfirm,
  Tooltip,
  Layout
} from 'antd'
import { 
  PlusOutlined, 
  ReloadOutlined, 
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  RobotOutlined,
  ExclamationCircleOutlined,
  ClearOutlined
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'

const { Title, Text, Paragraph } = Typography
const { Search } = Input
const { Content } = Layout

interface AIAlgorithm {
  id: string
  name: string
  description: string
  provider: string
  model_name: string
  system_prompt: string
  user_prompt: string
  detection_capabilities: string[]  // 新增：检测能力列表
  tags: string[]
  status: string
  created_at: string
  updated_at: string
  temperature: number
  top_p: number
  max_tokens: number
  confidence_threshold: number
}

const PromptManagePage: React.FC = () => {
  const navigate = useNavigate()
  const [algorithms, setAlgorithms] = useState<AIAlgorithm[]>([])
  const [filteredAlgorithms, setFilteredAlgorithms] = useState<AIAlgorithm[]>([])
  const [loading, setLoading] = useState(false)
  const [searchForm] = Form.useForm()
  
  // 搜索条件
  const [searchName, setSearchName] = useState('')
  const [searchTags, setSearchTags] = useState('')

  useEffect(() => {
    loadAlgorithms()
  }, [])

  useEffect(() => {
    filterAlgorithms()
  }, [algorithms, searchName, searchTags])

  const loadAlgorithms = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/ai-models/configs/')
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      // 确保data是数组，如果不是则设置为空数组
      const algorithmsData = Array.isArray(data) ? data : []
      setAlgorithms(algorithmsData)
    } catch (error) {
      console.error('加载AI编排算法失败:', error)
      message.error('加载AI编排算法失败')
      // 发生错误时设置为空数组
      setAlgorithms([])
    } finally {
      setLoading(false)
    }
  }

  const filterAlgorithms = () => {
    // 确保algorithms是数组
    if (!Array.isArray(algorithms)) {
      setFilteredAlgorithms([])
      return
    }

    let filtered = algorithms

    // 按名称过滤
    if (searchName.trim()) {
      filtered = filtered.filter(algorithm => {
        const name = algorithm.name || ''
        const description = algorithm.description || ''
        return name.toLowerCase().includes(searchName.toLowerCase()) ||
               description.toLowerCase().includes(searchName.toLowerCase())
      })
    }

    // 按标签过滤
    if (searchTags.trim()) {
      const searchTagList = searchTags.split(',').map(tag => tag.trim().toLowerCase())
      filtered = filtered.filter(algorithm => {
        const tags = Array.isArray(algorithm.tags) ? algorithm.tags : []
        return tags.some(tag => 
          searchTagList.some(searchTag => 
            String(tag).toLowerCase().includes(searchTag)
          )
        )
      })
    }

    setFilteredAlgorithms(filtered)
  }

  const handleSearch = () => {
    filterAlgorithms()
  }

  const handleReset = () => {
    setSearchName('')
    setSearchTags('')
    searchForm.resetFields()
  }

  const handleCreate = () => {
    navigate('/ai-model')
  }

  const handleEdit = (algorithm: AIAlgorithm) => {
    // 跳转到AI模型编排页面并传递配置数据
    navigate('/ai-model', { 
      state: { 
        editMode: true,
        algorithmData: algorithm 
      }
    })
  }

  const handleDelete = async (algorithmId: string, algorithmName: string) => {
    try {
      const response = await fetch(`/api/ai-models/configs/${algorithmId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        message.success(`算法"${algorithmName}"已删除`)
        loadAlgorithms()
      } else {
        throw new Error('删除失败')
      }
    } catch (error) {
      message.error('删除算法失败')
    }
  }

  const columns = [
    {
      title: '算法名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: AIAlgorithm) => (
        <div>
          <Text strong>{text}</Text>
          <div style={{ fontSize: '12px', color: '#666', marginTop: 2 }}>
            {record.provider} · {record.model_name}
          </div>
        </div>
      )
    },
    {
      title: '算法描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Paragraph ellipsis={{ rows: 2 }} style={{ margin: 0 }}>
            {text || '暂无描述'}
          </Paragraph>
        </Tooltip>
      )
    },
    {
      title: '检测能力',
      dataIndex: 'detection_capabilities',
      key: 'detection_capabilities',
      width: 300,
      render: (capabilities: string[]) => {
        if (!capabilities || capabilities.length === 0) {
          return (
            <Tag color="orange" icon={<ExclamationCircleOutlined />}>
              传统模式（手动提示词）
            </Tag>
          )
        }

        // 显示检测能力标签（最多3个，超出显示数量）
        return (
          <div style={{ maxWidth: 280 }}>
            {capabilities.slice(0, 3).map((cap, index) => (
              <Tag key={index} color="blue" size="small" style={{ marginBottom: 2 }}>
                {cap}
              </Tag>
            ))}
            {capabilities.length > 3 && (
              <Tag size="small" color="geekblue" style={{ marginBottom: 2 }}>
                +{capabilities.length - 3} 种
              </Tag>
            )}
            <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
              复合检测 · {capabilities.length} 种能力
            </div>
          </div>
        )
      }
    },
    {
      title: '算法标签',
      dataIndex: 'tags',
      key: 'tags',
      width: 200,
      render: (tags: string[]) => (
        <div>
          {tags && tags.length > 0 ? (
            tags.slice(0, 3).map((tag, index) => (
              <Tag key={index} size="small" style={{ marginBottom: 2 }}>
                {tag}
              </Tag>
            ))
          ) : (
            <Text type="secondary" style={{ fontSize: '12px' }}>无标签</Text>
          )}
          {tags && tags.length > 3 && (
            <Tag size="small" style={{ marginBottom: 2 }}>
              +{tags.length - 3}
            </Tag>
          )}
        </div>
      )
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const statusConfig = {
          'active': { color: 'green', text: '激活' },
          'draft': { color: 'blue', text: '草稿' },
          'testing': { color: 'orange', text: '测试中' },
          'deprecated': { color: 'red', text: '已弃用' }
        }
        const config = statusConfig[status as keyof typeof statusConfig] || { color: 'default', text: status }
        return <Tag color={config.color}>{config.text}</Tag>
      }
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (dateString: string) => (
        <Text style={{ fontSize: '12px' }}>
          {new Date(dateString).toLocaleDateString()}
        </Text>
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record: AIAlgorithm) => (
        <Space size="small">
          <Tooltip title="编辑算法">
            <Button
              type="text"
              icon={<EditOutlined />}
              size="small"
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title={
              <div>
                <div style={{ fontWeight: 'bold', marginBottom: 8 }}>
                  确定要删除这个AI编排算法吗？
                </div>
                <div style={{ color: '#666', fontSize: '12px' }}>
                  算法名称：{record.name}
                </div>
                <div style={{ color: '#666', fontSize: '12px', marginTop: 4 }}>
                  此操作不可恢复，请谨慎操作。
                </div>
              </div>
            }
            onConfirm={() => handleDelete(record.id, record.name)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
            icon={<ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />}
          >
            <Tooltip title="删除算法">
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
                  <RobotOutlined />
                  AI编排算法
                </Space>
              </Title>
              <Text type="secondary" style={{ marginTop: 8 }}>
                管理和配置AI模型编排算法，支持多模态视觉分析
              </Text>
            </Col>
            <Col>
              <Space>
                <Button
                  icon={<ReloadOutlined />}
                  onClick={loadAlgorithms}
                  loading={loading}
                >
                  刷新
                </Button>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={handleCreate}
                >
                  新建编排算法
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        {/* 搜索区域 */}
        <Card style={{ marginBottom: '16px' }}>
          <Form
            form={searchForm}
            layout="inline"
            onFinish={handleSearch}
          >
            <Form.Item
              name="name"
              label="算法名称"
              style={{ marginRight: 16 }}
            >
              <Input
                placeholder="搜索算法名称或描述"
                value={searchName}
                onChange={(e) => setSearchName(e.target.value)}
                style={{ width: 200 }}
                allowClear
              />
            </Form.Item>
            <Form.Item
              name="tags"
              label="算法标签"
              style={{ marginRight: 16 }}
            >
              <Input
                placeholder="多个标签用逗号分隔"
                value={searchTags}
                onChange={(e) => setSearchTags(e.target.value)}
                style={{ width: 200 }}
                allowClear
              />
            </Form.Item>
            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  icon={<SearchOutlined />}
                  onClick={handleSearch}
                >
                  查询
                </Button>
                <Button
                  icon={<ClearOutlined />}
                  onClick={handleReset}
                >
                  重置
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Card>

        {/* 算法列表 */}
        <Card>
          <Table
            columns={columns}
            dataSource={Array.isArray(filteredAlgorithms) ? filteredAlgorithms : []}
            rowKey="id"
            loading={loading}
            pagination={{
              total: Array.isArray(filteredAlgorithms) ? filteredAlgorithms.length : 0,
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 个算法`
            }}
            scroll={{ x: 1200 }}
            size="middle"
          />
        </Card>
      </Content>
    </Layout>
  )
}

export default PromptManagePage