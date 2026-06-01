import React, { useState, useEffect, useRef } from 'react';
import { Card, Badge, Tooltip, Progress } from 'antd';
import {
  VideoCameraOutlined,
  ScissorOutlined,
  SettingOutlined,
  ExperimentOutlined,
  BarChartOutlined,
  AlertOutlined,
  SendOutlined,
  ThunderboltOutlined
} from '@ant-design/icons';
import './AIProcessFlow.css';

interface ProcessStep {
  id: string;
  name: string;
  icon: React.ReactNode;
  status: 'idle' | 'processing' | 'completed' | 'error';
  progress: number;
  metrics: {
    fps?: number;
    latency?: number;
    accuracy?: number;
    confidence?: number;
  };
  description: string;
}

interface FlowConnection {
  from: string;
  to: string;
  particles: Array<{
    id: string;
    progress: number;
    active: boolean;
  }>;
}

const AIProcessFlow: React.FC = () => {
  const [processSteps, setProcessSteps] = useState<ProcessStep[]>([
    {
      id: 'video_input',
      name: '视频输入',
      icon: <VideoCameraOutlined />,
      status: 'processing',
      progress: 100,
      metrics: { fps: 25 },
      description: 'RTSP视频流接入'
    },
    {
      id: 'frame_extract',
      name: '智能抽帧',
      icon: <ScissorOutlined />,
      status: 'processing',
      progress: 85,
      metrics: { fps: 15, latency: 45 },
      description: '关键帧提取与预处理'
    },
    {
      id: 'preprocessing',
      name: '预处理',
      icon: <SettingOutlined />,
      status: 'processing',
      progress: 78,
      metrics: { latency: 25 },
      description: '图像增强与归一化'
    },
    {
      id: 'ai_model',
      name: 'AI大模型',
      icon: <ExperimentOutlined />,
      status: 'processing',
      progress: 92,
      metrics: { accuracy: 94.2, confidence: 0.89 },
      description: '多模态大语言模型推理'
    },
    {
      id: 'result_analysis',
      name: '结果分析',
      icon: <BarChartOutlined />,
      status: 'processing',
      progress: 88,
      metrics: { confidence: 0.91 },
      description: '语义理解与场景分析'
    },
    {
      id: 'alert_judge',
      name: '告警判断',
      icon: <AlertOutlined />,
      status: 'completed',
      progress: 100,
      metrics: { accuracy: 96.8 },
      description: '风险等级评估与决策'
    },
    {
      id: 'output',
      name: '结果输出',
      icon: <SendOutlined />,
      status: 'completed',
      progress: 100,
      metrics: { latency: 120 },
      description: '告警推送与存储'
    }
  ]);

  const [connections, setConnections] = useState<FlowConnection[]>([
    { from: 'video_input', to: 'frame_extract', particles: [] },
    { from: 'frame_extract', to: 'preprocessing', particles: [] },
    { from: 'preprocessing', to: 'ai_model', particles: [] },
    { from: 'ai_model', to: 'result_analysis', particles: [] },
    { from: 'result_analysis', to: 'alert_judge', particles: [] },
    { from: 'alert_judge', to: 'output', particles: [] }
  ]);

  const flowContainerRef = useRef<HTMLDivElement>(null);

  // 模拟实时数据更新
  useEffect(() => {
    const interval = setInterval(() => {
      setProcessSteps(prev => prev.map(step => ({
        ...step,
        progress: Math.max(60, Math.min(100, step.progress + (Math.random() - 0.5) * 10)),
        metrics: {
          ...step.metrics,
          fps: step.metrics.fps ? step.metrics.fps + (Math.random() - 0.5) * 2 : undefined,
          latency: step.metrics.latency ? Math.max(10, step.metrics.latency + (Math.random() - 0.5) * 10) : undefined,
          accuracy: step.metrics.accuracy ? Math.max(85, Math.min(99, step.metrics.accuracy + (Math.random() - 0.5) * 2)) : undefined,
          confidence: step.metrics.confidence ? Math.max(0.7, Math.min(0.99, step.metrics.confidence + (Math.random() - 0.5) * 0.05)) : undefined
        }
      })));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // 粒子动画
  useEffect(() => {
    const particleInterval = setInterval(() => {
      setConnections(prev => prev.map(conn => {
        // 添加新粒子
        const newParticles = [...conn.particles];
        if (Math.random() > 0.7) {
          newParticles.push({
            id: `particle_${Date.now()}_${Math.random()}`,
            progress: 0,
            active: true
          });
        }

        // 更新粒子位置
        const updatedParticles = newParticles
          .map(particle => ({
            ...particle,
            progress: particle.progress + 0.05
          }))
          .filter(particle => particle.progress < 1);

        return {
          ...conn,
          particles: updatedParticles
        };
      }));
    }, 100);

    return () => clearInterval(particleInterval);
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'processing': return '#1890ff';
      case 'completed': return '#52c41a';
      case 'error': return '#ff4d4f';
      default: return '#8c8c8c';
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'processing': return 'processing';
      case 'completed': return 'success';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  const formatMetric = (key: string, value: number | undefined) => {
    if (value === undefined) return null;
    
    switch (key) {
      case 'fps':
        return `${Math.round(value)} FPS`;
      case 'latency':
        return `${Math.round(value)}ms`;
      case 'accuracy':
        return `${value.toFixed(1)}%`;
      case 'confidence':
        return `${(value * 100).toFixed(1)}%`;
      default:
        return value.toString();
    }
  };

  return (
    <Card 
      className="ai-process-flow-card" 
      title={
        <div className="flow-title">
          <ThunderboltOutlined className="flow-title-icon" />
          <span>AI智能处理流程</span>
          <Badge status="processing" text="实时运行中" className="flow-status" />
        </div>
      }
      size="small"
    >
      <div className="ai-flow-container" ref={flowContainerRef}>
        {/* 背景网格 */}
        <div className="flow-background">
          <div className="neural-grid"></div>
        </div>

        {/* 处理节点 */}
        <div className="flow-nodes">
          {processSteps.map((step, index) => (
            <div key={step.id} className="flow-node-wrapper" style={{ '--node-index': index } as React.CSSProperties}>
              <Tooltip
                title={
                  <div className="node-tooltip">
                    <div className="tooltip-title">{step.name}</div>
                    <div className="tooltip-desc">{step.description}</div>
                    <div className="tooltip-metrics">
                      {Object.entries(step.metrics).map(([key, value]) => (
                        <div key={key} className="metric-item">
                          <span className="metric-key">{key}:</span>
                          <span className="metric-value">{formatMetric(key, value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                }
                placement="top"
              >
                <div 
                  className={`flow-node ${step.id === 'ai_model' ? 'ai-core-node' : ''} ${step.status}`}
                  style={{ 
                    borderColor: getStatusColor(step.status),
                    boxShadow: `0 0 20px ${getStatusColor(step.status)}33`
                  }}
                >
                  {/* 节点图标 */}
                  <div className="node-icon" style={{ color: getStatusColor(step.status) }}>
                    {step.icon}
                  </div>
                  
                  {/* 节点标题 */}
                  <div className="node-title">{step.name}</div>
                  
                  {/* 进度条 */}
                  <div className="node-progress">
                    <Progress
                      percent={step.progress}
                      size="small"
                      strokeColor={getStatusColor(step.status)}
                      trailColor="rgba(255,255,255,0.1)"
                      showInfo={false}
                    />
                  </div>
                  
                  {/* 状态指示 */}
                  <div className="node-status">
                    <Badge status={getStatusBadge(step.status) as any} size="small" />
                  </div>

                  {/* AI核心节点特效 */}
                  {step.id === 'ai_model' && (
                    <div className="ai-core-effects">
                      <div className="pulse-ring"></div>
                      <div className="pulse-ring delay-1"></div>
                      <div className="pulse-ring delay-2"></div>
                    </div>
                  )}

                  {/* 神经元连接动画 */}
                  <div className="neural-connections">
                    {[...Array(3)].map((_, i) => (
                      <div key={i} className={`neural-line neural-line-${i + 1}`}></div>
                    ))}
                  </div>
                </div>
              </Tooltip>
            </div>
          ))}
        </div>

        {/* 连接线和粒子 */}
        <div className="flow-connections">
          {connections.map((conn, index) => (
            <div key={`${conn.from}-${conn.to}`} className="connection-line">
              <div className={`connection-path connection-${index}`}>
                {conn.particles.map(particle => (
                  <div
                    key={particle.id}
                    className="flow-particle"
                    style={{
                      left: `${particle.progress * 100}%`,
                      animationDelay: `${Math.random() * 2}s`
                    }}
                  ></div>
                ))}
              </div>
            </div>
          ))}
        </div>

      </div>
    </Card>
  );
};

export default AIProcessFlow;