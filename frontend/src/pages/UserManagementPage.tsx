import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Table,
  Tag,
  Popconfirm,
  Row,
  Col,
  Statistic,
  Avatar,
  Tooltip,
  Badge
} from 'antd'
import {
  UserOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  KeyOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  UserAddOutlined,
  TeamOutlined,
  CrownOutlined,
  SafetyOutlined
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'

const { Option } = Select

interface User {
  id: string
  username: string
  email?: string
  role: string
  created_at: string
  last_login?: string
  is_active: boolean
}

interface CreateUserRequest {
  username: string
  email?: string
  password: string
  role: string
}

interface UpdateUserRequest {
  username?: string
  email?: string
  role?: string
  is_active?: boolean
}

interface ChangePasswordRequest {
  user_id: string
  new_password: string
}

const UserManagementPage: React.FC = () => {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [passwordModalVisible, setPasswordModalVisible] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [showPassword, setShowPassword] = useState(false)
  
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()
  const [passwordForm] = Form.useForm()

  // 统计数据
  const [statistics, setStatistics] = useState({
    total: 0,
    active: 0,
    inactive: 0,
    admins: 0
  })

  useEffect(() => {
    fetchUsers()
  }, [])

  useEffect(() => {
    updateStatistics()
  }, [users])

  const updateStatistics = () => {
    const stats = {
      total: users.length,
      active: users.filter(user => user.is_active).length,
      inactive: users.filter(user => !user.is_active).length,
      admins: users.filter(user => user.role === 'admin').length
    }
    setStatistics(stats)
  }

  const fetchUsers = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/users', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      } else {
        message.error('获取用户列表失败')
      }
    } catch (error) {
      console.error('获取用户失败:', error)
      message.error('网络错误')
    } finally {
      setLoading(false)
    }
  }

  const handleCreateUser = async (values: CreateUserRequest) => {
    try {
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(values)
      })

      if (response.ok) {
        message.success('用户创建成功')
        setCreateModalVisible(false)
        createForm.resetFields()
        fetchUsers()
      } else {
        const error = await response.json()
        message.error(error.detail || '创建用户失败')
      }
    } catch (error) {
      console.error('创建用户失败:', error)
      message.error('网络错误')
    }
  }

  const handleUpdateUser = async (values: UpdateUserRequest) => {
    if (!selectedUser) return

    try {
      const response = await fetch(`/api/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(values)
      })

      if (response.ok) {
        message.success('用户更新成功')
        setEditModalVisible(false)
        editForm.resetFields()
        setSelectedUser(null)
        fetchUsers()
      } else {
        const error = await response.json()
        message.error(error.detail || '更新用户失败')
      }
    } catch (error) {
      console.error('更新用户失败:', error)
      message.error('网络错误')
    }
  }

  const handleChangePassword = async (values: { new_password: string }) => {
    if (!selectedUser) return

    try {
      const response = await fetch(`/api/users/${selectedUser.id}/password`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: selectedUser.id,
          new_password: values.new_password
        })
      })

      if (response.ok) {
        message.success('密码修改成功')
        setPasswordModalVisible(false)
        passwordForm.resetFields()
        setSelectedUser(null)
      } else {
        const error = await response.json()
        message.error(error.detail || '修改密码失败')
      }
    } catch (error) {
      console.error('修改密码失败:', error)
      message.error('网络错误')
    }
  }

  const handleDeleteUser = async (userId: string) => {
    try {
      const response = await fetch(`/api/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      })

      if (response.ok) {
        message.success('用户删除成功')
        fetchUsers()
      } else {
        const error = await response.json()
        message.error(error.detail || '删除用户失败')
      }
    } catch (error) {
      console.error('删除用户失败:', error)
      message.error('网络错误')
    }
  }

  const handleEditUser = (user: User) => {
    setSelectedUser(user)
    editForm.setFieldsValue({
      username: user.username,
      email: user.email,
      role: user.role,
      is_active: user.is_active
    })
    setEditModalVisible(true)
  }

  const handleChangeUserPassword = (user: User) => {
    setSelectedUser(user)
    setPasswordModalVisible(true)
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'red'
      case 'user': return 'blue'
      default: return 'default'
    }
  }

  const getRoleIcon = (role: string) => {
    switch (role) {
      case 'admin': return <CrownOutlined />
      case 'user': return <UserOutlined />
      default: return <SafetyOutlined />
    }
  }

  const columns: ColumnsType<User> = [
    {
      title: '用户',
      key: 'user',
      render: (_, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} />
          <div>
            <div style={{ fontWeight: 500 }}>{record.username}</div>
            {record.email && <div style={{ color: '#666', fontSize: '12px' }}>{record.email}</div>}
          </div>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={getRoleColor(role)} icon={getRoleIcon(role)}>
          {role === 'admin' ? '管理员' : '普通用户'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (is_active: boolean) => (
        <Badge 
          status={is_active ? 'success' : 'default'} 
          text={is_active ? '活跃' : '禁用'} 
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (created_at: string) => new Date(created_at).toLocaleString('zh-CN'),
    },
    {
      title: '最后登录',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (last_login?: string) => 
        last_login ? new Date(last_login).toLocaleString('zh-CN') : '从未登录',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Tooltip title="编辑用户">
            <Button 
              type="text" 
              icon={<EditOutlined />} 
              onClick={() => handleEditUser(record)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="修改密码">
            <Button 
              type="text" 
              icon={<KeyOutlined />} 
              onClick={() => handleChangeUserPassword(record)}
              size="small"
            />
          </Tooltip>
          {/* 系统管理员用户不显示删除按钮 */}
          {record.username !== 'admin' && (
            <Popconfirm
              title="确定要删除这个用户吗？"
              description="此操作不可恢复"
              onConfirm={() => handleDeleteUser(record.id)}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="删除用户">
                <Button 
                  type="text" 
                  icon={<DeleteOutlined />} 
                  danger
                  size="small"
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16}>
          <Col span={6}>
            <Statistic
              title="总用户数"
              value={statistics.total}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="活跃用户"
              value={statistics.active}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="禁用用户"
              value={statistics.inactive}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Col>
          <Col span={6}>
            <Statistic
              title="管理员"
              value={statistics.admins}
              prefix={<CrownOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Col>
        </Row>
      </Card>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <h3>用户管理</h3>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setCreateModalVisible(true)}
          >
            新增用户
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={users}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
          }}
        />
      </Card>

      {/* 创建用户模态框 */}
      <Modal
        title={<><UserAddOutlined style={{ marginRight: 8 }} />新增用户</>}
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false)
          createForm.resetFields()
        }}
        footer={null}
        width={600}
      >
        <Form
          form={createForm}
          layout="vertical"
          onFinish={handleCreateUser}
          requiredMark={false}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="用户名"
                name="username"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { min: 3, message: '用户名至少3个字符' }
                ]}
              >
                <Input placeholder="请输入用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[
                  { type: 'email', message: '请输入有效的邮箱地址' }
                ]}
              >
                <Input placeholder="请输入邮箱（可选）" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="密码"
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' }
            ]}
          >
            <Input.Password 
              placeholder="请输入密码"
              iconRender={visible => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
            />
          </Form.Item>

          <Form.Item
            label="角色"
            name="role"
            initialValue="user"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            <Select placeholder="请选择用户角色">
              <Option value="admin">
                <Space>
                  <CrownOutlined />
                  管理员
                </Space>
              </Option>
              <Option value="user">
                <Space>
                  <UserOutlined />
                  普通用户
                </Space>
              </Option>
            </Select>
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setCreateModalVisible(false)
                createForm.resetFields()
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                创建用户
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑用户模态框 */}
      <Modal
        title={<><EditOutlined style={{ marginRight: 8 }} />编辑用户</>}
        open={editModalVisible}
        onCancel={() => {
          setEditModalVisible(false)
          editForm.resetFields()
          setSelectedUser(null)
        }}
        footer={null}
        width={600}
      >
        <Form
          form={editForm}
          layout="vertical"
          onFinish={handleUpdateUser}
          requiredMark={false}
        >
          {/* 系统管理员用户的提示信息 */}
          {selectedUser?.username === 'admin' && (
            <div style={{ 
              backgroundColor: '#fff7e6', 
              border: '1px solid #ffd591', 
              borderRadius: '6px', 
              padding: '12px', 
              marginBottom: '16px',
              fontSize: '14px',
              color: '#d46b08'
            }}>
              <CrownOutlined style={{ marginRight: '8px' }} />
              系统管理员用户的角色和状态不可修改，以确保系统安全。
            </div>
          )}
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="用户名"
                name="username"
                rules={[
                  { required: true, message: '请输入用户名' },
                  { min: 3, message: '用户名至少3个字符' }
                ]}
              >
                <Input placeholder="请输入用户名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="邮箱"
                name="email"
                rules={[
                  { type: 'email', message: '请输入有效的邮箱地址' }
                ]}
              >
                <Input placeholder="请输入邮箱（可选）" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="角色"
                name="role"
                rules={[{ required: true, message: '请选择角色' }]}
              >
                <Select 
                  placeholder="请选择用户角色" 
                  disabled={selectedUser?.username === 'admin'}
                >
                  <Option value="admin">
                    <Space>
                      <CrownOutlined />
                      管理员
                    </Space>
                  </Option>
                  <Option value="user">
                    <Space>
                      <UserOutlined />
                      普通用户
                    </Space>
                  </Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="状态"
                name="is_active"
                rules={[{ required: true, message: '请选择状态' }]}
              >
                <Select 
                  placeholder="请选择用户状态"
                  disabled={selectedUser?.username === 'admin'}
                >
                  <Option value={true}>
                    <Badge status="success" text="活跃" />
                  </Option>
                  <Option value={false}>
                    <Badge status="default" text="禁用" />
                  </Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setEditModalVisible(false)
                editForm.resetFields()
                setSelectedUser(null)
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                更新用户
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改密码模态框 */}
      <Modal
        title={<><KeyOutlined style={{ marginRight: 8 }} />修改密码</>}
        open={passwordModalVisible}
        onCancel={() => {
          setPasswordModalVisible(false)
          passwordForm.resetFields()
          setSelectedUser(null)
        }}
        footer={null}
        width={500}
      >
        <Form
          form={passwordForm}
          layout="vertical"
          onFinish={handleChangePassword}
          requiredMark={false}
        >
          <Form.Item
            label={`为用户 "${selectedUser?.username}" 设置新密码`}
            name="new_password"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '密码至少6个字符' }
            ]}
          >
            <Input.Password 
              placeholder="请输入新密码"
              iconRender={visible => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
            />
          </Form.Item>

          <Form.Item
            label="确认新密码"
            name="confirm_password"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请确认新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password 
              placeholder="请再次输入新密码"
              iconRender={visible => (visible ? <EyeOutlined /> : <EyeInvisibleOutlined />)}
            />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => {
                setPasswordModalVisible(false)
                passwordForm.resetFields()
                setSelectedUser(null)
              }}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                修改密码
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default UserManagementPage