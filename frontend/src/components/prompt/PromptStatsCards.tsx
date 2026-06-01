import React from 'react'
import { Row, Col, Card, Statistic } from 'antd'
import {
  SafetyOutlined,
  UserOutlined, 
  EyeOutlined,
  EnvironmentOutlined,
  ToolOutlined,
  ExperimentOutlined
} from '@ant-design/icons'

interface PromptStatsCardsProps {
  categoryStats: Record<string, any>
}

const PromptStatsCards: React.FC<PromptStatsCardsProps> = ({ categoryStats }) => {
  const getCategoryIcon = (category: string) => {
    const icons: { [key: string]: React.ReactElement } = {
      'safety_detection': <SafetyOutlined />,
      'behavior_analysis': <UserOutlined />,
      'object_recognition': <EyeOutlined />,
      'environment_monitor': <EnvironmentOutlined />,
      'quality_control': <ToolOutlined />,
      'custom': <ExperimentOutlined />
    }
    return icons[category] || <ExperimentOutlined />
  }

  const getCategoryName = (category: string) => {
    const names: { [key: string]: string } = {
      'safety_detection': '安全检测',
      'behavior_analysis': '行为分析',
      'object_recognition': '目标识别',
      'environment_monitor': '环境监控',
      'quality_control': '质量控制',
      'custom': '自定义'
    }
    return names[category] || category
  }

  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
      {Object.entries(categoryStats).map(([category, stats]) => (
        <Col xs={24} sm={12} md={8} lg={6} key={category}>
          <Card size="small">
            <Statistic
              title={getCategoryName(category)}
              value={stats.count || 0}
              prefix={getCategoryIcon(category)}
              suffix="个模板"
            />
          </Card>
        </Col>
      ))}
    </Row>
  )
}

export default PromptStatsCards