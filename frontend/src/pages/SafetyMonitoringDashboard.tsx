import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Typography, Badge, Spin, Image, Progress } from 'antd';
import {
  WarningOutlined,
  SafetyOutlined,
  FireOutlined,
  EyeOutlined,
  AlertOutlined,
  VideoCameraOutlined,
  TeamOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import './SafetyMonitoringDashboard.css';

const { Title, Text } = Typography;

interface AlertRecord {
  id: string;
  type: string;
  typeName: string;
  image: string;
  timestamp: string;
  streamName: string;
  confidence: number;
}

interface TrendData {
  date: string;
  count: number;
}

interface StatisticsData {
  today: number;
  thisWeek: number;
  thisMonth: number;
  thisYear: number;
}

interface AlertTypeData {
  type: string;
  typeName: string;
  count: number;
  percentage: number;
}

interface AlgorithmData {
  name: string;
  count: number;
  active: boolean;
}

const SafetyMonitoringDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeMonitorView, setActiveMonitorView] = useState<'main' | 'grid'>('main');
  const [statistics, setStatistics] = useState<StatisticsData>({
    today: 0,
    thisWeek: 0,
    thisMonth: 0,
    thisYear: 0
  });
  const [recentAlerts, setRecentAlerts] = useState<AlertRecord[]>([]);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [alertTypeData, setAlertTypeData] = useState<AlertTypeData[]>([]);
  const [algorithmData, setAlgorithmData] = useState<AlgorithmData[]>([]);

  // 模拟数据
  const mockTrendData = [
    { date: '20日', count: 12 },
    { date: '21日', count: 8 },
    { date: '22日', count: 15 },
    { date: '23日', count: 6 },
    { date: '24日', count: 20 },
    { date: '25日', count: 9 },
    { date: '26日', count: 14 },
  ];

  const mockStatistics = {
    today: 14,
    thisWeek: 84,
    thisMonth: 312,
    thisYear: 2847
  };

  const mockAlertTypeData = [
    { type: 'no_helmet', typeName: '未戴安全帽', count: 45, percentage: 35.2 },
    { type: 'smoking', typeName: '吸烟行为', count: 32, percentage: 25.0 },
    { type: 'unauthorized_person', typeName: '无关人员', count: 28, percentage: 21.9 },
    { type: 'unsafe_behavior', typeName: '违规操作', count: 23, percentage: 17.9 }
  ];

  const mockAlgorithmData = [
    { name: '安全帽检测', count: 1250, active: true },
    { name: '吸烟行为识别', count: 890, active: true },
    { name: '人员闯入检测', count: 760, active: true },
    { name: '违规操作监控', count: 650, active: true },
    { name: '火灾风险识别', count: 420, active: false },
    { name: '设备异常检测', count: 380, active: true }
  ];

  const pieColors = ['#ff4d4f', '#faad14', '#1890ff', '#52c41a'];

  // 实时时间更新
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // 数据获取和定时刷新
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        const [statsRes, alertsRes, trendRes, typeRes, algoRes] = await Promise.allSettled([
          fetch('/api/safety/statistics').then(res => res.ok ? res.json() : mockStatistics),
          fetch('/api/safety/recent-alerts?limit=8').then(res => res.ok ? res.json() : []),
          fetch('/api/safety/trend?days=7').then(res => res.ok ? res.json() : mockTrendData),
          fetch('/api/safety/alert-type-ranks').then(res => res.ok ? res.json() : mockAlertTypeData),
          fetch('/api/safety/algorithm-stats').then(res => res.ok ? res.json() : mockAlgorithmData)
        ]);

        if (statsRes.status === 'fulfilled') {
          setStatistics(statsRes.value);
        } else {
          setStatistics(mockStatistics);
        }

        if (alertsRes.status === 'fulfilled') {
          setRecentAlerts(alertsRes.value);
        }

        if (trendRes.status === 'fulfilled') {
          setTrendData(trendRes.value);
        } else {
          setTrendData(mockTrendData);
        }

        if (typeRes.status === 'fulfilled') {
          setAlertTypeData(typeRes.value);
        } else {
          setAlertTypeData(mockAlertTypeData);
        }

        if (algoRes.status === 'fulfilled') {
          setAlgorithmData(algoRes.value);
        } else {
          setAlgorithmData(mockAlgorithmData);
        }

      } catch (error) {
        console.error('获取数据失败:', error);
        setStatistics(mockStatistics);
        setTrendData(mockTrendData);
        setAlertTypeData(mockAlertTypeData);
        setAlgorithmData(mockAlgorithmData);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="safety-dashboard">
        <div className="loading-container">
          <Spin size="large" />
          <Text className="loading-text">正在加载安全监控数据...</Text>
        </div>
      </div>
    );
  }

  return (
    <div className="safety-dashboard">
      {/* 顶部标题栏 */}
      <div className="dashboard-header">
        <div className="header-left">
          <SafetyOutlined className="header-icon" />
          <Title level={1} className="dashboard-title">
            安全生产监测大屏系统
          </Title>
        </div>
        <div className="header-center">
          <div className="main-title">智能安全监控平台</div>
        </div>
        <div className="header-right">
          <div className="system-info">
            <span className="online-count">在线监控: 8/12</span>
            <span className="fps-info">15 FPS</span>
          </div>
          <div className="status-indicator">
            <Badge status="processing" />
            <Text className="status-text">系统运行正常</Text>
          </div>
          <div className="current-time">
            {currentTime.toLocaleString('zh-CN', {
              year: 'numeric',
              month: '2-digit', 
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit'
            })}
          </div>
        </div>
      </div>

      {/* 主要内容区域 - 左中右布局 */}
      <div className="dashboard-content">
        <Row gutter={16} style={{ height: '100%' }}>
          {/* 左侧面板 */}
          <Col span={6} className="left-panel">
            {/* 告警趋势图 */}
            <Card className="panel-card" title="告警趋势分析" size="small">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f4e79" opacity={0.3} />
                  <XAxis 
                    dataKey="date" 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#87ceeb', fontSize: 12 }}
                  />
                  <YAxis 
                    axisLine={false}
                    tickLine={false}
                    tick={{ fill: '#87ceeb', fontSize: 12 }}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: 'rgba(15, 52, 96, 0.9)',
                      border: '1px solid #1890ff',
                      borderRadius: '6px',
                      color: '#fff'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="count" 
                    stroke="#1890ff"
                    strokeWidth={3}
                    dot={{ fill: '#1890ff', strokeWidth: 2, r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Card>

            {/* 告警分类排行 */}
            <Card className="panel-card" title="告警分类排行" size="small">
              {alertTypeData.map((item, index) => (
                <div key={item.type} className="alert-type-item">
                  <div className="type-info">
                    <div 
                      className="type-color" 
                      style={{ backgroundColor: pieColors[index % pieColors.length] }}
                    ></div>
                    <span className="type-name">{item.typeName}</span>
                  </div>
                  <div className="type-progress">
                    <Progress 
                      percent={item.percentage} 
                      size="small" 
                      strokeColor={pieColors[index % pieColors.length]}
                      trailColor="rgba(255,255,255,0.1)"
                      showInfo={false}
                    />
                  </div>
                  <span className="type-count">{item.count}</span>
                </div>
              ))}
            </Card>

            {/* AI算法词云 */}
            <Card className="panel-card" title="AI编排算法" size="small">
              <div className="algorithm-cloud">
                {algorithmData.map((algo, index) => (
                  <div 
                    key={algo.name} 
                    className={`algorithm-tag ${algo.active ? 'active' : 'inactive'}`}
                    style={{ 
                      fontSize: `${Math.min(16, Math.max(10, algo.count / 100 + 10))}px`,
                      animationDelay: `${index * 0.1}s`
                    }}
                  >
                    <span className="algo-name">{algo.name}</span>
                    <span className="algo-count">({algo.count})</span>
                  </div>
                ))}
              </div>
            </Card>
          </Col>

          {/* 中间面板 */}
          <Col span={12} className="center-panel">
            {/* 监控切换区域 */}
            <div className="monitor-section">
              {/* 监控切换按钮 */}
              <div className="monitor-switch-bar">
                <div className="switch-buttons">
                  <button 
                    className={`switch-btn ${activeMonitorView === 'main' ? 'active' : ''}`}
                    onClick={() => setActiveMonitorView('main')}
                  >
                    <VideoCameraOutlined /> 主监控画面
                  </button>
                  <button 
                    className={`switch-btn ${activeMonitorView === 'grid' ? 'active' : ''}`}
                    onClick={() => setActiveMonitorView('grid')}
                  >
                    <EyeOutlined /> 分屏监控
                  </button>
                </div>
                <div className="monitor-status">
                  <Badge status="processing" text="实时监控中" />
                </div>
              </div>
              
              {/* 监控内容区域 */}
              <div className="monitor-content">
                {activeMonitorView === 'main' ? (
                  <div className="main-monitor-view">
                    <div className="monitor-placeholder">
                      <VideoCameraOutlined className="monitor-icon" />
                      <div className="monitor-text">主监控画面</div>
                      <div className="monitor-info">摄像头 #001 - 生产区域A</div>
                    </div>
                  </div>
                ) : (
                  <div className="grid-monitor-view">
                    {[1, 2, 3, 4].map((item) => (
                      <div key={item} className="grid-monitor-item">
                        <div className="grid-monitor-header">
                          <span className="camera-name">摄像头 #{item.toString().padStart(3, '0')}</span>
                          <Badge status={item <= 2 ? "processing" : "default"} size="small" />
                        </div>
                        <div className="grid-monitor-content">
                          <VideoCameraOutlined className="grid-icon" />
                          <div className="grid-label">{['生产区域A', '仓储区域B', '入口通道', '办公区域'][item-1]}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* 告警统计模块 */}
            <div className="alert-statistics-section">
              <div className="statistics-header">
                <div className="section-title">
                  <BarChartOutlined className="title-icon" />
                  <span>告警统计</span>
                </div>
              </div>
              <Row gutter={12} className="center-metrics">
                <Col span={6}>
                  <div className="metric-card today-card">
                    <div className="metric-icon">
                      <AlertOutlined />
                    </div>
                    <div className="metric-content">
                      <div className="metric-value">{statistics.today}</div>
                      <div className="metric-label">今日告警</div>
                    </div>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="metric-card week-card">
                    <div className="metric-icon">
                      <FireOutlined />
                    </div>
                    <div className="metric-content">
                      <div className="metric-value">{statistics.thisWeek}</div>
                      <div className="metric-label">本周告警</div>
                    </div>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="metric-card month-card">
                    <div className="metric-icon">
                      <WarningOutlined />
                    </div>
                    <div className="metric-content">
                      <div className="metric-value">{statistics.thisMonth}</div>
                      <div className="metric-label">本月告警</div>
                    </div>
                  </div>
                </Col>
                <Col span={6}>
                  <div className="metric-card total-card">
                    <div className="metric-icon">
                      <BarChartOutlined />
                    </div>
                    <div className="metric-content">
                      <div className="metric-value">{statistics.thisYear}</div>
                      <div className="metric-label">累计告警</div>
                    </div>
                  </div>
                </Col>
              </Row>
            </div>
          </Col>

          {/* 右侧面板 */}
          <Col span={6} className="right-panel">
            {/* 最新告警 */}
            <Card className="panel-card" title="最新告警" size="small">
              <div className="alert-list">
                {recentAlerts.length === 0 ? (
                  <div className="no-alerts">
                    <SafetyOutlined className="no-alerts-icon" />
                    <Text className="no-alerts-text">暂无告警</Text>
                  </div>
                ) : (
                  recentAlerts.slice(0, 8).map((alert, index) => (
                    <div key={alert.id} className="alert-item-compact">
                      <div className="alert-image-small">
                        <Image
                          src={alert.image}
                          alt={alert.typeName}
                          width={50}
                          height={40}
                          style={{ objectFit: 'cover', borderRadius: '4px' }}
                          fallback="/api/placeholder-alert.jpg"
                        />
                      </div>
                      <div className="alert-content-compact">
                        <div className="alert-header-compact">
                          <Badge 
                            status={index < 2 ? "error" : index < 4 ? "warning" : "processing"}
                            size="small"
                          />
                          <span className="alert-type-compact">{alert.typeName}</span>
                        </div>
                        <div className="alert-details-compact">
                          <div className="alert-stream-compact">{alert.streamName}</div>
                          <div className="alert-time-compact">
                            {new Date(alert.timestamp).toLocaleTimeString('zh-CN', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </Card>

            {/* 监控统计 */}
            <Card className="panel-card" title="监控统计" size="small">
              <div className="monitor-stats">
                <div className="stats-grid">
                  <div className="stat-item-small">
                    <span className="stat-label-small">活跃摄像头</span>
                    <span className="stat-value-small">8/12</span>
                  </div>
                  <div className="stat-item-small">
                    <span className="stat-label-small">检测精度</span>
                    <span className="stat-value-small">94.2%</span>
                  </div>
                  <div className="stat-item-small">
                    <span className="stat-label-small">处理帧率</span>
                    <span className="stat-value-small">15 FPS</span>
                  </div>
                  <div className="stat-item-small">
                    <span className="stat-label-small">响应时间</span>
                    <span className="stat-value-small">120ms</span>
                  </div>
                  <div className="stat-item-small">
                    <span className="stat-label-small">在线算法</span>
                    <span className="stat-value-small">5/6</span>
                  </div>
                  <div className="stat-item-small">
                    <span className="stat-label-small">系统负载</span>
                    <span className="stat-value-small">68%</span>
                  </div>
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </div>
    </div>
  );
};

export default SafetyMonitoringDashboard;