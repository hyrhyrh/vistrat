import React, { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Layout, Spin, Result, Button, Card } from 'antd'
import { LoadingOutlined, CloseCircleOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { useAuth } from '../contexts/AuthContext'
import axios from 'axios'

const { Content } = Layout

/**
 * SSO单点登录页面
 *
 * 通过URL参数中的加密token进行自动登录
 * URL格式: /sso-login?token=<encrypted_credentials>
 */
const SSOLoginPage: React.FC = () => {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { loginWithToken } = useAuth()

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const [loadingMessage, setLoadingMessage] = useState('请稍候，系统正在验证您的身份')

  useEffect(() => {
    let cancelled = false
    let retryTimer: number | undefined
    const maxRetries = 12
    const retryDelayMs = 5000

    const shouldRetry = (error: any) => {
      if (!error) {
        return false
      }
      if (error.response) {
        const statusCode = Number(error.response.status)
        return statusCode >= 500
      }
      return Boolean(error.request)
    }

    const performSSOLogin = async (attempt: number) => {
      try {
        // 获取URL参数中的token
        const token = searchParams.get('token')

        if (!token) {
          if (cancelled) {
            return
          }
          setStatus('error')
          setErrorMessage('缺少登录凭证参数')
          return
        }

        // 调用后端SSO登录API（使用相对路径，支持局域网访问）
        const response = await axios.get('/api/auth/sso-login', {
          params: { token }
        })

        if (response.data && response.data.token && response.data.user) {
          if (cancelled) {
            return
          }
          // 登录成功，保存token和用户信息
          const { token: jwtToken, user } = response.data

          // 使用AuthContext的loginWithToken方法保存认证信息
          loginWithToken(jwtToken, user)

          setStatus('success')

          // 延迟跳转到实时预览页面
          setTimeout(() => {
            navigate('/live-preview', { replace: true })
          }, 1000)
        } else {
          setStatus('error')
          setErrorMessage('登录响应格式不正确')
        }
      } catch (error: any) {
        console.error('[SSO Login] 登录失败:', error)
        if (!cancelled && shouldRetry(error) && attempt < maxRetries) {
          const nextAttempt = attempt + 1
          setStatus('loading')
          setLoadingMessage(`系统启动中，正在重试 (${nextAttempt}/${maxRetries})`)
          retryTimer = window.setTimeout(() => {
            performSSOLogin(nextAttempt)
          }, retryDelayMs)
          return
        }

        if (cancelled) {
          return
        }
        setStatus('error')

        if (error.response) {
          // 服务器返回错误
          setErrorMessage(error.response.data?.detail || '登录失败，请检查凭证是否正确')
        } else if (error.request) {
          // 请求发送了但没有收到响应
          setErrorMessage('无法连接到服务器，请检查网络连接')
        } else {
          // 其他错误
          setErrorMessage(error.message || '登录失败')
        }
      }
    }

    setLoadingMessage('请稍候，系统正在验证您的身份')
    performSSOLogin(0)

    return () => {
      cancelled = true
      if (retryTimer) {
        window.clearTimeout(retryTimer)
      }
    }
  }, [searchParams, loginWithToken, navigate])

  const handleRetry = () => {
    setStatus('loading')
    window.location.reload()
  }

  const handleBackToLogin = () => {
    navigate('/login', { replace: true })
  }

  return (
    <Layout style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <Content style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', padding: '20px' }}>
        <Card style={{ maxWidth: 500, width: '100%', textAlign: 'center' }}>
          {status === 'loading' && (
            <Result
              icon={<Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />}
              title="正在登录..."
              subTitle={loadingMessage}
            />
          )}

          {status === 'success' && (
            <Result
              status="success"
              icon={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
              title="登录成功！"
              subTitle="正在跳转到实时预览页面..."
            />
          )}

          {status === 'error' && (
            <Result
              status="error"
              icon={<CloseCircleOutlined style={{ color: '#ff4d4f' }} />}
              title="登录失败"
              subTitle={errorMessage}
              extra={[
                <Button type="primary" key="retry" onClick={handleRetry}>
                  重试
                </Button>,
                <Button key="login" onClick={handleBackToLogin}>
                  返回登录页
                </Button>
              ]}
            />
          )}
        </Card>
      </Content>
    </Layout>
  )
}

export default SSOLoginPage
