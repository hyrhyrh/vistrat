import React from 'react'
import { Input, Select, Space, Button, Form } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'

const { Option } = Select

interface VideoSearchBarProps {
  onSearch: (params: any) => void
  onReset: () => void
  loading?: boolean
}

const VideoSearchBar: React.FC<VideoSearchBarProps> = ({ 
  onSearch, 
  onReset, 
  loading = false 
}) => {
  const [form] = Form.useForm()

  const handleSearch = () => {
    const values = form.getFieldsValue()
    onSearch(values)
  }

  const handleReset = () => {
    form.resetFields()
    onReset()
  }

  const statusOptions = [
    { value: 'PENDING', label: '待处理' },
    { value: 'UPLOADING', label: '上传中' },
    { value: 'READY', label: '就绪' },
    { value: 'ANALYZING', label: '分析中' },
    { value: 'COMPLETED', label: '已完成' },
    { value: 'ERROR', label: '错误' }
  ]

  return (
    <div style={{ 
      padding: '16px', 
      background: '#fafafa', 
      borderRadius: '6px', 
      marginBottom: '16px' 
    }}>
      <Form form={form} layout="inline">
        <Form.Item name="search_name" style={{ minWidth: 200 }}>
          <Input 
            placeholder="搜索视频名称..." 
            prefix={<SearchOutlined />}
            onPressEnter={handleSearch}
          />
        </Form.Item>
        
        <Form.Item name="status" style={{ minWidth: 120 }}>
          <Select 
            placeholder="选择状态" 
            allowClear
          >
            {statusOptions.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </Form.Item>
        
        <Form.Item name="tags" style={{ minWidth: 150 }}>
          <Input placeholder="标签(逗号分隔)" />
        </Form.Item>
        
        <Form.Item>
          <Space>
            <Button 
              type="primary" 
              icon={<SearchOutlined />} 
              onClick={handleSearch}
              loading={loading}
            >
              搜索
            </Button>
            <Button 
              icon={<ReloadOutlined />} 
              onClick={handleReset}
            >
              重置
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </div>
  )
}

export default VideoSearchBar