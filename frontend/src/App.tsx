import React from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom'
import { Layout, Menu, Typography, Dropdown, Avatar, Space } from 'antd'
import {
  BellOutlined,
  SettingOutlined,
  DatabaseOutlined,
  MonitorOutlined,
  ExperimentOutlined,
  UserOutlined,
  LogoutOutlined,
  BarChartOutlined,
  VideoCameraOutlined,
  TeamOutlined,
  DashboardOutlined,
  LineChartOutlined,
  SwapOutlined,
  SafetyOutlined
} from '@ant-design/icons'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import SSOLoginPage from './pages/SSOLoginPage'
import AlertsPage from './pages/AlertsPage'
import PromptManagePage from './pages/PromptManagePage'
import VideoManagementPage from './pages/VideoManagementPage'
import VideoStreamPage from './pages/VideoStreamPage'
import AIModelPage from './pages/AIModelPage'
import AIProviderConfigPage from './pages/AIProviderConfigPage'
import AnalysisResultsPage from './pages/AnalysisResultsPage'
import LivePreviewPage from './pages/LivePreviewPage'
import UserManagementPage from './pages/UserManagementPage'
import SafetyMonitoringDashboard from './pages/SafetyMonitoringDashboard'
import SafetyMonitoringDashboardWithAI from './pages/SafetyMonitoringDashboardWithAI'
import PerformanceMonitorPage from './pages/PerformanceMonitorPage'
import VideoComparisonPage from './pages/VideoComparisonPage'
import DetectionTemplatesPage from './pages/DetectionTemplatesPage'
import DailyAlertsReportPage from './pages/DailyAlertsReportPage'
import './App.css'

const { Header, Sider, Content } = Layout
const { Title } = Typography

const AppContent: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    }
  ]

  const menuItems = [
    {
      key: '/live-preview',
      icon: <VideoCameraOutlined />,
      label: '实时预览监控',
      onClick: () => navigate('/live-preview')
    },
    {
      key: '/stream-management',
      icon: <MonitorOutlined />,
      label: '实时流管理',
      onClick: () => navigate('/stream-management')
    },
    {
      key: '/video-comparison',
      icon: <SwapOutlined />,
      label: '视频播放方案对比',
      onClick: () => navigate('/video-comparison')
    },
    {
      key: '/video-management',
      icon: <DatabaseOutlined />,
      label: '离线视频管理',
      onClick: () => navigate('/video-management')
    },
    {
      key: '/alerts',
      icon: <BellOutlined />,
      label: '实时告警',
      onClick: () => navigate('/alerts')
    },
    {
      key: '/analysis-results',
      icon: <BarChartOutlined />,
      label: '分析结果查询',
      onClick: () => navigate('/analysis-results')
    },
    {
      key: '/prompts',
      icon: <SettingOutlined />,
      label: 'AI编排算法',
      onClick: () => navigate('/prompts')
    },
    {
      key: '/detection-templates',
      icon: <SafetyOutlined />,
      label: '检测类型模板',
      onClick: () => navigate('/detection-templates')
    },
    {
      key: '/ai-model',
      icon: <ExperimentOutlined />,
      label: 'AI模型编排',
      onClick: () => navigate('/ai-model')
    },
    {
      key: '/ai-provider-config',
      icon: <SettingOutlined />,
      label: 'AI供应商配置',
      onClick: () => navigate('/ai-provider-config')
    },
    {
      key: '/safety-dashboard-ai',
      icon: <ExperimentOutlined />,
      label: '安全生产监测大屏',
      onClick: () => {
        window.open('/safety-dashboard-ai', '_blank');
      }
    },
    {
      key: '/performance',
      icon: <LineChartOutlined />,
      label: '性能监控',
      onClick: () => navigate('/performance')
    },
    {
      key: '/user-management',
      icon: <TeamOutlined />,
      label: '用户管理',
      onClick: () => navigate('/user-management')
    }
  ]

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider theme="dark" width={240}>
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: 'white',
          fontSize: '18px',
          fontWeight: 'bold',
          borderBottom: '1px solid #303030'
        }}>
          {/* AI视频监控系统 */}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Sider>
      
      <Layout>
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: '0 1px 4px rgba(0,21,41,.08)'
        }}>
          <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
            Vistrat <span style={{ fontSize: 14, color: '#888', fontWeight: 400, marginLeft: 8 }}>观策 · 智能视频监控</span>
          </Title>
          
          <Space>
            <span style={{ marginRight: 16, color: '#666' }}>
              欢迎，{user?.username}
            </span>
            <Dropdown
              menu={{ items: userMenuItems }}
              placement="bottomRight"
            >
              <Avatar 
                icon={<UserOutlined />} 
                style={{ backgroundColor: '#1890ff', cursor: 'pointer' }}
              />
            </Dropdown>
          </Space>
        </Header>
        
        <Content style={{ margin: '24px', background: '#f0f2f5' }}>
          <ProtectedRoute>
            <Routes>
              <Route path="/" element={<Navigate to="/live-preview" replace />} />
              <Route path="/live-preview" element={<LivePreviewPage />} />
              <Route path="/video-management" element={<VideoManagementPage />} />
              <Route path="/stream-management" element={<VideoStreamPage />} />
              <Route path="/video-comparison" element={<VideoComparisonPage />} />
              <Route path="/alerts" element={<AlertsPage />} />
              <Route path="/analysis-results" element={<AnalysisResultsPage />} />
              <Route path="/prompts" element={<PromptManagePage />} />
              <Route path="/detection-templates" element={<DetectionTemplatesPage />} />
              <Route path="/ai-model" element={<AIModelPage />} />
              <Route path="/ai-provider-config" element={<AIProviderConfigPage />} />
              <Route path="/performance" element={<PerformanceMonitorPage />} />
              {/* 大屏页面已移到独立路由 */}
              <Route path="/user-management" element={<UserManagementPage />} />
            </Routes>
          </ProtectedRoute>
        </Content>
      </Layout>
    </Layout>
  )
}

const App: React.FC = () => {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/sso-login" element={<SSOLoginPage />} />
        <Route path="/safety-dashboard" element={<SafetyMonitoringDashboard />} />
        <Route path="/safety-dashboard-ai" element={<SafetyMonitoringDashboardWithAI />} />
        <Route path="/daily-alerts-report" element={<DailyAlertsReportPage />} />
        <Route path="/*" element={<AppContent />} />
      </Routes>
    </AuthProvider>
  )
}

export default App