import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Layout,
  Card,
  Form,
  Input,
  Button,
  Typography,
  Alert,
  Checkbox,
  Row,
  Col,
  Space,
  message
} from 'antd'
import { useAuth } from '../contexts/AuthContext'
import {
  UserOutlined,
  LockOutlined,
  EyeOutlined,
  SafetyCertificateOutlined,
  VideoCameraOutlined,
  AlertOutlined,
  RobotOutlined
} from '@ant-design/icons'

const { Title, Text, Paragraph } = Typography

interface LoginCredentials {
  username: string
  password: string
  remember?: boolean
}

const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 初始化时自动填充上次保存的用户名
  React.useEffect(() => {
    const rememberedUsername = localStorage.getItem('rememberedUsername')
    if (rememberedUsername) {
      form.setFieldsValue({ username: rememberedUsername, remember: true })
    }
  }, [form])

  // 添加CSS动画样式
  React.useEffect(() => {
    const style = document.createElement('style')
    style.textContent = `
      @keyframes scan {
        0% { transform: translateY(0); opacity: 0; }
        50% { transform: translateY(70px); opacity: 1; }
        100% { transform: translateY(140px); opacity: 0; }
      }

      @keyframes pulse {
        0%, 100% { opacity: 0.4; transform: scale(1); }
        50% { opacity: 1; transform: scale(1.2); }
      }

      @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
      }
    `
    document.head.appendChild(style)

    return () => {
      document.head.removeChild(style)
    }
  }, [])

  const handleSubmit = async (values: LoginCredentials) => {
    setLoading(true)
    setError('')

    try {
      // 传递 remember 参数到 login 函数
      await login(values.username, values.password, values.remember || false)
      message.success('登录成功')
      navigate('/')
    } catch (error) {
      setError('登录失败，请检查用户名和密码')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #1e293b 0%, #334155 25%, #475569 50%, #64748b 75%, #334155 100%)',
    }}>
      <Row style={{ minHeight: '100vh' }}>
        {/* 左侧 - AI监控系统展示区域 */}
        <Col span={14} style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          position: 'relative',
          overflow: 'hidden'
        }}>
          {/* 背景装饰 */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'radial-gradient(circle at 30% 70%, rgba(255,255,255,0.1) 0%, transparent 50%)',
            pointerEvents: 'none',
          }} />

          <div style={{
            textAlign: 'center',
            zIndex: 2,
            maxWidth: 500,
            position: 'relative',
          }}>
            {/* AI监控设备图标组 */}
            <div style={{
              position: 'relative',
              display: 'inline-block',
              marginBottom: 48,
            }}>
              {/* 主要监控设备 */}
              <div style={{
                width: 220,
                height: 180,
                backgroundColor: 'rgba(0,0,0,0.25)',
                borderRadius: 20,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                position: 'relative',
                border: '3px solid rgba(255,255,255,0.25)',
                backdropFilter: 'blur(15px)',
                boxShadow: '0 12px 40px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.2)',
                background: 'linear-gradient(145deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%)',
              }}>
                <div style={{
                  width: 190,
                  height: 140,
                  backgroundColor: 'rgba(0,0,0,0.6)',
                  borderRadius: 16,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  border: '2px solid rgba(96, 165, 250, 0.3)',
                  position: 'relative',
                  overflow: 'hidden',
                }}>
                  {/* 扫描线动画效果 */}
                  <div style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    height: '2px',
                    background: 'linear-gradient(90deg, transparent, #60a5fa, transparent)',
                    animation: 'scan 2s ease-in-out infinite',
                  }} />

                  {/* 监控摄像头图标 */}
                  <div style={{ position: 'relative', zIndex: 2 }}>
                    <VideoCameraOutlined style={{
                      fontSize: 64,
                      color: '#60a5fa',
                      filter: 'drop-shadow(0 0 10px rgba(96, 165, 250, 0.5))',
                    }} />

                    {/* AI标识 */}
                    <div style={{
                      position: 'absolute',
                      top: -8,
                      right: -8,
                      width: 24,
                      height: 24,
                      borderRadius: '50%',
                      backgroundColor: '#10b981',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: 12,
                      fontWeight: 'bold',
                      color: 'white',
                      boxShadow: '0 0 15px rgba(16, 185, 129, 0.6)',
                    }}>
                      AI
                    </div>
                  </div>

                  {/* 角落状态指示器 */}
                  <div style={{
                    position: 'absolute',
                    bottom: 8,
                    left: 8,
                    display: 'flex',
                    gap: 4,
                  }}>
                    <div style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: '#10b981',
                      boxShadow: '0 0 8px rgba(16, 185, 129, 0.6)',
                      animation: 'pulse 1.5s ease-in-out infinite',
                    }} />
                    <div style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: '#f59e0b',
                      boxShadow: '0 0 8px rgba(245, 158, 11, 0.6)',
                      animation: 'pulse 1.5s ease-in-out infinite 0.3s',
                    }} />
                    <div style={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: '#ef4444',
                      boxShadow: '0 0 8px rgba(239, 68, 68, 0.6)',
                      animation: 'pulse 1.5s ease-in-out infinite 0.6s',
                    }} />
                  </div>
                </div>
              </div>

              {/* 装饰元素 - AI分析效果 */}
              <div style={{
                position: 'absolute',
                top: -15,
                left: -15,
                width: 12,
                height: 12,
                borderRadius: '50%',
                backgroundColor: '#fbbf24',
                boxShadow: '0 0 20px rgba(251, 191, 36, 0.6)',
              }} />
              <div style={{
                position: 'absolute',
                top: 30,
                right: -25,
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: '#f472b6',
                boxShadow: '0 0 15px rgba(244, 114, 182, 0.5)',
              }} />
              <div style={{
                position: 'absolute',
                bottom: -12,
                left: 50,
                width: 10,
                height: 10,
                borderRadius: '50%',
                backgroundColor: '#34d399',
                boxShadow: '0 0 18px rgba(52, 211, 153, 0.5)',
              }} />
              <div style={{
                position: 'absolute',
                bottom: 20,
                right: 15,
                width: 6,
                height: 6,
                borderRadius: '50%',
                backgroundColor: '#a78bfa',
                boxShadow: '0 0 12px rgba(167, 139, 250, 0.4)',
              }} />
            </div>

            {/* 功能图标组 */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 40, marginTop: 36 }}>
              <div style={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                backgroundColor: 'rgba(255,255,255,0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backdropFilter: 'blur(15px)',
                border: '2px solid rgba(16, 185, 129, 0.3)',
                boxShadow: '0 6px 20px rgba(0,0,0,0.25), 0 0 20px rgba(16, 185, 129, 0.15)',
                animation: 'float 3s ease-in-out infinite',
                position: 'relative',
              }}>
                <RobotOutlined style={{ color: '#10b981', fontSize: 36, filter: 'drop-shadow(0 0 8px rgba(16, 185, 129, 0.5))' }} />
                <div style={{
                  position: 'absolute',
                  bottom: -2,
                  right: -2,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: '#10b981',
                  boxShadow: '0 0 10px rgba(16, 185, 129, 0.7)',
                  animation: 'pulse 2s ease-in-out infinite',
                }} />
              </div>

              <div style={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                backgroundColor: 'rgba(255,255,255,0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backdropFilter: 'blur(15px)',
                border: '2px solid rgba(96, 165, 250, 0.3)',
                boxShadow: '0 6px 20px rgba(0,0,0,0.25), 0 0 20px rgba(96, 165, 250, 0.15)',
                animation: 'float 3s ease-in-out infinite 0.5s',
                position: 'relative',
              }}>
                <EyeOutlined style={{ color: '#60a5fa', fontSize: 36, filter: 'drop-shadow(0 0 8px rgba(96, 165, 250, 0.5))' }} />
                <div style={{
                  position: 'absolute',
                  bottom: -2,
                  right: -2,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: '#60a5fa',
                  boxShadow: '0 0 10px rgba(96, 165, 250, 0.7)',
                  animation: 'pulse 2s ease-in-out infinite 0.3s',
                }} />
              </div>

              <div style={{
                width: 72,
                height: 72,
                borderRadius: '50%',
                backgroundColor: 'rgba(255,255,255,0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backdropFilter: 'blur(15px)',
                border: '2px solid rgba(239, 68, 68, 0.3)',
                boxShadow: '0 6px 20px rgba(0,0,0,0.25), 0 0 20px rgba(239, 68, 68, 0.15)',
                animation: 'float 3s ease-in-out infinite 1s',
                position: 'relative',
              }}>
                <AlertOutlined style={{ color: '#ef4444', fontSize: 36, filter: 'drop-shadow(0 0 8px rgba(239, 68, 68, 0.5))' }} />
                <div style={{
                  position: 'absolute',
                  bottom: -2,
                  right: -2,
                  width: 12,
                  height: 12,
                  borderRadius: '50%',
                  backgroundColor: '#ef4444',
                  boxShadow: '0 0 10px rgba(239, 68, 68, 0.7)',
                  animation: 'pulse 2s ease-in-out infinite 0.6s',
                }} />
              </div>
            </div>

            {/* 系统名称 */}
            <Title level={1} style={{
              color: 'white',
              fontWeight: 700,
              textAlign: 'center',
              marginTop: 32,
              marginBottom: 16,
              textShadow: '0 2px 4px rgba(0,0,0,0.3)',
              fontSize: '2.8rem',
              letterSpacing: '0.02em',
              background: 'linear-gradient(135deg, #ffffff 0%, #e0f2fe 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}>
              Vistrat
            </Title>

            <Title level={4} style={{
              color: 'rgba(255,255,255,0.95)',
              fontWeight: 500,
              textAlign: 'center',
              textShadow: '0 1px 2px rgba(0,0,0,0.2)',
              letterSpacing: '0.08em',
              marginTop: 0,
              fontSize: '1.1rem'
            }}>
              观策 — 观察与决策的数字大脑
            </Title>

            <Paragraph style={{
              color: 'rgba(255,255,255,0.85)',
              textAlign: 'center',
              fontSize: '17px',
              marginTop: 28,
              lineHeight: '1.7',
              fontWeight: 400
            }}>
              Vision + Strategy · 基于先进多模态视觉AI技术的智能监控分析平台
              <br />
              实时检测异常行为 • 智能预警防护 • 全域安全保障
            </Paragraph>
          </div>
        </Col>

        {/* 右侧 - 登录表单 */}
        <Col span={10} style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#fff',
          padding: 32,
        }}>
          <Card style={{
            width: '100%',
            maxWidth: 400,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
            borderRadius: 16,
            border: 'none'
          }}>
            <div style={{ textAlign: 'center', marginBottom: 32 }}>
              <div style={{
                width: 80,
                height: 80,
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #3b82f6 0%, #1e40af 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px auto',
                boxShadow: '0 8px 24px rgba(59, 130, 246, 0.3)',
              }}>
                <SafetyCertificateOutlined style={{
                  fontSize: 40,
                  color: 'white',
                }} />
              </div>
              <Title level={2} style={{
                fontWeight: 700,
                color: '#1f2937',
                margin: 0,
                marginBottom: 8,
                fontSize: '1.8rem'
              }}>
                系统登录
              </Title>
              <Text type="secondary" style={{ fontSize: 16, color: '#6b7280' }}>
                Vistrat · 观策 • 安全认证
              </Text>
            </div>

            {error && (
              <Alert
                message={error}
                type="error"
                showIcon
                style={{
                  marginBottom: 24,
                  borderRadius: 8
                }}
              />
            )}

            <Form
              form={form}
              name="login"
              onFinish={handleSubmit}
              size="large"
              layout="vertical"
            >
              <Form.Item
                name="username"
                label="用户名"
                rules={[{ required: true, message: '请输入用户名!' }]}
              >
                <Input
                  prefix={<UserOutlined style={{ color: '#bfbfbf' }} />}
                  placeholder="请输入用户名"
                  style={{ borderRadius: 8 }}
                />
              </Form.Item>

              <Form.Item
                name="password"
                label="密码"
                rules={[{ required: true, message: '请输入密码!' }]}
              >
                <Input.Password
                  prefix={<LockOutlined style={{ color: '#bfbfbf' }} />}
                  placeholder="请输入密码"
                  style={{ borderRadius: 8 }}
                />
              </Form.Item>

              <Form.Item style={{ marginBottom: 16 }}>
                <Row justify="space-between" align="middle">
                  <Col>
                    <Form.Item name="remember" valuePropName="checked" noStyle>
                      <Checkbox>记住我</Checkbox>
                    </Form.Item>
                  </Col>
                  <Col>
                    <Button type="link" style={{ padding: 0 }}>
                      忘记密码？
                    </Button>
                  </Col>
                </Row>
              </Form.Item>

              <Form.Item style={{ marginBottom: 16 }}>
                <Button
                  type="primary"
                  htmlType="submit"
                  loading={loading}
                  block
                  style={{
                    height: 48,
                    borderRadius: 8,
                    fontSize: 16,
                    fontWeight: 600,
                    background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                    border: 'none'
                  }}
                >
                  {loading ? '登录中...' : '登录'}
                </Button>
              </Form.Item>

              <div style={{ textAlign: 'center' }}>
                <Text type="secondary" style={{ fontSize: 14 }}>
                  还没有账号？
                  <Button type="link" style={{ padding: '0 4px', fontWeight: 500 }}>
                    立即注册
                  </Button>
                </Text>
              </div>
            </Form>
          </Card>
        </Col>
      </Row>

      {/* 底部版权 */}
      <div style={{
        position: 'absolute',
        bottom: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        color: 'rgba(255,255,255,0.8)',
        fontSize: 14,
        textAlign: 'center',
        display: 'flex',
        alignItems: 'center',
        gap: 8,
      }}>
        <SafetyCertificateOutlined style={{ color: 'rgba(255,255,255,0.8)' }} />
        Copyright © 2025 Vistrat（观策） | 基于多模态视觉AI技术
      </div>
    </Layout>
  )
}

export default LoginPage
