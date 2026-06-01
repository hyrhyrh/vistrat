import React from 'react'
import { Table, Tag, Badge, Button, Space, Tooltip, Popconfirm } from 'antd'
import {
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CopyOutlined,
  SafetyOutlined,
  UserOutlined,
  EnvironmentOutlined,
  ToolOutlined,
  ExperimentOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { PromptTemplate } from '../../types/prompt'

interface PromptTableProps {
  templates: PromptTemplate[]
  loading: boolean
  onEdit: (template: PromptTemplate) => void
  onPreview: (template: PromptTemplate) => void
  onDelete: (templateId: string) => void
  onActivate: (templateId: string, category: string) => void
}

const PromptTable: React.FC<PromptTableProps> = ({
  templates,
  loading,
  onEdit,
  onPreview,
  onDelete,
  onActivate
}) => {
  const getCategoryIcon = (category: string) => {
    const icons = {
      'safety_detection': <SafetyOutlined />,
      'behavior_analysis': <UserOutlined />,
      'object_recognition': <EyeOutlined />,
      'environment_monitor': <EnvironmentOutlined />,
      'quality_control': <ToolOutlined />,
      'custom': <ExperimentOutlined />
    }
    return icons[category] || <ExperimentOutlined />
  }

  const getPriorityBadge = (priority: string) => {
    const config = {
      'critical': { status: 'error', text: '危险' },
      'high': { status: 'warning', text: '高' },
      'medium': { status: 'processing', text: '中' },
      'low': { status: 'default', text: '低' }
    }
    
    const item = config[priority] || config['medium']
    return <Badge status={item.status as any} text={item.text} />
  }

  const columns: ColumnsType<PromptTemplate> = [
    {
      title: '模板信息',
      dataIndex: 'name',
      width: 300,
      render: (name, record) => (
        <div>
          <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
            {getCategoryIcon(record.category)} {name}
            {record.is_system_template && <Tag size="small" color="blue">系统</Tag>}
            {record.is_active && <Tag size="small" color="green">激活</Tag>}
          </div>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: 4 }}>
            {record.description}
          </div>
          <div>
            {record.tags.map(tag => (
              <Tag key={tag} size="small">{tag}</Tag>
            ))}
          </div>
        </div>
      )
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 100,
      render: (priority) => getPriorityBadge(priority)
    },
    {
      title: '使用统计',
      width: 150,
      render: (_, record) => (
        <div>
          <div>使用次数: {record.usage_count || 0}</div>
          <div>成功率: {((record.success_rate || 0) * 100).toFixed(1)}%</div>
        </div>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 150,
      render: (date) => new Date(date).toLocaleDateString()
    },
    {
      title: '操作',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="预览">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => onPreview(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => onEdit(record)}
            />
          </Tooltip>
          <Tooltip title="复制">
            <Button type="text" icon={<CopyOutlined />} />
          </Tooltip>
          {!record.is_active && (
            <Tooltip title="激活">
              <Button
                type="text"
                onClick={() => onActivate(record.id, record.category)}
              >
                激活
              </Button>
            </Tooltip>
          )}
          {!record.is_system_template && (
            <Popconfirm
              title="确定要删除这个模板吗？"
              onConfirm={() => onDelete(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="删除">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      )
    }
  ]

  return (
    <Table
      columns={columns}
      dataSource={templates}
      rowKey="id"
      loading={loading}
      pagination={{
        pageSize: 10,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total) => `共 ${total} 个模板`
      }}
    />
  )
}

export default PromptTable