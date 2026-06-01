import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Row, Col, Card, Typography, Badge, Spin, Image, Progress, Modal, Descriptions, List, Button, Tooltip, Space } from 'antd';
import {
  WarningOutlined,
  SafetyOutlined,
  FireOutlined,
  EyeOutlined,
  AlertOutlined,
  VideoCameraOutlined,
  TeamOutlined,
  BarChartOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined
} from '@ant-design/icons';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import AIProcessFlow from '../components/dashboard/AIProcessFlow';
import AgentButton from '../components/agent/AgentButton';
import AgentDialog from '../components/agent/AgentDialog';
import FLVPlayer from '../components/stream/FLVPlayer';
import './SafetyMonitoringDashboard.css';

const { Title, Text } = Typography;

// 告警数据接口 - 与LivePreviewPage保持一致
interface Alert {
  id: string;
  video_name: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  algorithm_name: string;
  template_name?: string;
  confidence: number;
  created_at: string;
  image_url?: string;
  frame_index: number;
  video_time: string;
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

interface VideoStream {
  id: string;
  name: string;
  stream_url: string;
  stream_type: string;
  location?: string;
  group_name?: string;
  status: 'ONLINE' | 'OFFLINE';
}

const SafetyMonitoringDashboardWithAI: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [activeMonitorView, setActiveMonitorView] = useState<'main' | 'grid'>('main');
  const [agentDialogVisible, setAgentDialogVisible] = useState(false);
  const [statistics, setStatistics] = useState<StatisticsData>({
    today: 0,
    thisWeek: 0,
    thisMonth: 0,
    thisYear: 0
  });
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [alertModalVisible, setAlertModalVisible] = useState(false);
  const [trendData, setTrendData] = useState<TrendData[]>([]);
  const [alertTypeData, setAlertTypeData] = useState<AlertTypeData[]>([]);
  const [algorithmData, setAlgorithmData] = useState<AlgorithmData[]>([]);
  const [videoStreams, setVideoStreams] = useState<VideoStream[]>([]);

  // 新增：来自 LivePreviewPage 的视频流管理状态
  const [currentStreams, setCurrentStreams] = useState<VideoStream[]>([]);
  const [streamErrors, setStreamErrors] = useState<{[key: string]: boolean}>({});
  const [autoPlayEnabled, setAutoPlayEnabled] = useState(true);

  // 新增状态：全屏控制
  const [isFullscreen, setIsFullscreen] = useState(false);
  const videoContainerRef = useRef<HTMLDivElement>(null);

  // 视频流连接状态
  const [videoConnectionStatus, setVideoConnectionStatus] = useState<'connecting' | 'connected' | 'failed' | 'offline'>('connecting');
  const [retryCount, setRetryCount] = useState(0);
  const maxRetryCount = 3;

  // 模拟数据
  const mockTrendData = [
    { date: '10-06', count: 12 },
    { date: '10-07', count: 8 },
    { date: '10-08', count: 15 },
    { date: '10-09', count: 6 },
    { date: '10-10', count: 20 },
    { date: '10-11', count: 9 },
    { date: '10-12', count: 14 },
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

  // 获取最新告警数据（来自LivePreviewPage的完整逻辑）
  const fetchLatestAlerts = useCallback(async () => {
    try {
      const response = await fetch('/api/alerts/search?size=15&page=1');

      if (!response.ok) {
        console.warn('告警数据接口响应异常:', response.status);
        return;
      }

      const data = await response.json();

      // 处理数据响应 - 使用video_alerts索引的数据格式
      if (data.success && data.data) {
        const alertsData = data.data.map((alert: any) => ({
          id: alert.id || Math.random().toString(),
          video_name: alert.video_name || '未知位置',
          description: alert.description || alert.alert_type || '安全隐患',  // 使用video_alerts.description字段
          severity: 'medium', // video_alerts索引没有severity字段，设为默认值
          algorithm_name: alert.algorithm_name || 'AI检测',
          template_name: alert.algorithm_name, // 添加template_name字段
          confidence: alert.confidence || 0.8,
          created_at: alert.timestamp || new Date().toISOString(),
          image_url: alert.image_path || alert.image_url,
          frame_index: alert.detection_details?.frame_index || 0,
          video_time: alert.video_time || '00:00'
        }));
        setAlerts(alertsData);
      } else {
        // 暂无数据时使用模拟数据
        if (alerts.length === 0) {
          const mockAlerts = [
            {
              id: '1',
              video_name: '门口摄像头A1',
              description: '安全帽检测',
              severity: 'high' as const,
              algorithm_name: 'PPE检测',
              template_name: 'PPE检测',
              confidence: 0.92,
              created_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
              frame_index: 1250,
              video_time: '10:25',
              image_url: '/api/image-proxy/minio/images/analysis/demo1.jpg'
            },
            {
              id: '2',
              video_name: '车间摄像头B2',
              description: '反光衣检测',
              severity: 'medium' as const,
              algorithm_name: 'PPE检测',
              template_name: 'PPE检测',
              confidence: 0.85,
              created_at: new Date(Date.now() - 8 * 60 * 1000).toISOString(),
              frame_index: 890,
              video_time: '08:15',
              image_url: '/api/image-proxy/minio/images/analysis/demo2.jpg'
            }
          ];
          setAlerts(mockAlerts);
        }
      }
    } catch (error) {
      console.error('获取告警数据失败:', error);
      // 使用模拟数据作为后备
      if (alerts.length === 0) {
        setAlerts([
          {
            id: 'demo1',
            video_name: '模拟数据 - 门口',
            description: '系统检测模拟',
            severity: 'low' as const,
            algorithm_name: 'Demo',
            template_name: 'Demo',
            confidence: 0.75,
            created_at: new Date().toISOString(),
            frame_index: 100,
            video_time: '00:10',
            image_url: '/api/image-proxy/minio/images/analysis/demo.jpg'
          }
        ]);
      }
    }
  }, [alerts.length]);

  // 新增：获取视频流列表（来自 LivePreviewPage）
  const fetchVideoStreams = useCallback(async () => {
    try {
      const response = await fetch('/api/video-streams/');

      if (!response.ok) {
        console.warn('获取视频流失败:', response.status);
        setVideoConnectionStatus('failed');
        return;
      }

      const data = await response.json();

      // 过滤健康状态为online的流(优先使用health_status,其次使用status)
      const onlineStreams = data.filter((stream: VideoStream) => {
        const healthStatus = (stream as any).health_status;
        return healthStatus === 'online' || stream.status === 'ONLINE';
      });

      console.log('SafetyMonitoringDashboard: 获取到在线视频流', onlineStreams.length, '个');
      setVideoStreams(onlineStreams);

      // 初始化时设置第一个流
      if (onlineStreams.length > 0) {
        setCurrentStreams([onlineStreams[0]]);
        setVideoConnectionStatus('connected');
      } else {
        setVideoConnectionStatus('offline');
      }
    } catch (error) {
      console.error('获取视频流失败:', error);
      setVideoConnectionStatus('failed');
    }
  }, []); // 移除 activeMonitorView 依赖，只在初始化时调用一次

  // 新增：处理流错误状态（来自 LivePreviewPage）
  const handleStreamError = useCallback((streamId: string, hasError: boolean) => {
    setStreamErrors(prev => ({
      ...prev,
      [streamId]: hasError
    }));
  }, []);

  // 新增：创建稳定的错误处理函数映射，避免重复连接（来自 LivePreviewPage）
  const errorHandlers = useMemo(() => {
    const handlers = new Map();
    currentStreams.forEach(stream => {
      if (stream) {
        handlers.set(stream.id, (hasError: boolean) => handleStreamError(stream.id, hasError));
      }
    });
    return handlers;
  }, [currentStreams, handleStreamError]);

  // 实时时间更新
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // 处理告警点击 - 显示告警详情弹框（来自LivePreviewPage）
  const handleAlertClick = useCallback((alert: Alert) => {
    setSelectedAlert(alert);
    setAlertModalVisible(true);
  }, []);

  // 关闭告警详情弹框（来自LivePreviewPage）
  const handleAlertModalClose = useCallback(() => {
    setAlertModalVisible(false);
    setSelectedAlert(null);
  }, []);

  // 格式化时间显示（来自LivePreviewPage）
  const formatTime = (timestamp: string | number) => {
    const date = new Date(typeof timestamp === 'string' ? timestamp : timestamp);
    return date.toLocaleString('zh-CN');
  };

  // 全屏处理函数
  const handleFullscreen = useCallback(() => {
    if (!videoContainerRef.current) return;

    if (!isFullscreen) {
      // 进入全屏
      if (videoContainerRef.current.requestFullscreen) {
        videoContainerRef.current.requestFullscreen();
      } else if ((videoContainerRef.current as any).webkitRequestFullscreen) {
        (videoContainerRef.current as any).webkitRequestFullscreen();
      } else if ((videoContainerRef.current as any).mozRequestFullScreen) {
        (videoContainerRef.current as any).mozRequestFullScreen();
      } else if ((videoContainerRef.current as any).msRequestFullscreen) {
        (videoContainerRef.current as any).msRequestFullscreen();
      }
    } else {
      // 退出全屏
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if ((document as any).webkitExitFullscreen) {
        (document as any).webkitExitFullscreen();
      } else if ((document as any).mozCancelFullScreen) {
        (document as any).mozCancelFullScreen();
      } else if ((document as any).msExitFullscreen) {
        (document as any).msExitFullscreen();
      }
    }
  }, [isFullscreen]);

  // 监听全屏状态变化
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };

    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);

    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
      document.removeEventListener('mozfullscreenchange', handleFullscreenChange);
      document.removeEventListener('MSFullscreenChange', handleFullscreenChange);
    };
  }, []);

  // 处理视频流连接错误
  const handleVideoConnectionError = useCallback(() => {
    if (retryCount < maxRetryCount) {
      setVideoConnectionStatus('connecting');
      setRetryCount(prev => prev + 1);
      setTimeout(() => {
        // 重新获取视频流列表
        fetch('/api/video-streams/')
          .then(res => res.json())
          .then(data => {
            setVideoStreams(data);
            setVideoConnectionStatus('connected');
            setRetryCount(0);
          })
          .catch(() => {
            setVideoConnectionStatus('failed');
          });
      }, 2000 * retryCount); // 递增重试延迟
    } else {
      setVideoConnectionStatus('failed');
    }
  }, [retryCount, maxRetryCount]);

  // 手动重连
  const handleManualRetry = useCallback(() => {
    setRetryCount(0);
    setVideoConnectionStatus('connecting');
    setTimeout(() => {
      fetch('/api/video-streams/')
        .then(res => res.json())
        .then(data => {
          setVideoStreams(data);
          setVideoConnectionStatus('connected');
        })
        .catch(() => {
          setVideoConnectionStatus('failed');
        });
    }, 1000);
  }, []);

  // 监听网络状态
  useEffect(() => {
    const handleOnline = () => {
      setVideoConnectionStatus('connecting');
      handleManualRetry();
    };
    const handleOffline = () => {
      setVideoConnectionStatus('offline');
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [handleManualRetry]);

  // 初始数据加载（只加载一次）
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);

        const [statsRes, trendRes, typeRes, algoRes] = await Promise.allSettled([
          fetch('/api/safety/statistics').then(res => res.ok ? res.json() : mockStatistics),
          fetch('/api/safety/trend?days=7').then(res => res.ok ? res.json() : mockTrendData),
          fetch('/api/safety/alert-type-ranks').then(res => res.ok ? res.json() : mockAlertTypeData),
          fetch('/api/video-files/detection-types/templates').then(async res => {
            if (res.ok) {
              const data = await res.json();
              // 从detection_type_templates获取数据，映射为AlgorithmData格式
              // 只取前10个启用的检测类型
              const templates = data.templates || [];
              return templates
                .filter((t: any) => t.enabled)
                .slice(0, 10)
                .map((t: any, index: number) => ({
                  name: t.display_name, // 🐛 修复：使用display_name字段，与后端返回数据一致
                  count: 100 + index * 50, // 模拟使用次数
                  active: t.enabled
                }));
            }
            return mockAlgorithmData;
          })
        ]);

        if (statsRes.status === 'fulfilled') {
          setStatistics(statsRes.value);
        } else {
          setStatistics(mockStatistics);
        }

        if (trendRes.status === 'fulfilled') {
          // 格式化趋势数据的日期格式为 MM-DD
          const formattedTrendData = trendRes.value.map((item: TrendData) => ({
            ...item,
            date: item.date.includes('-') ? item.date.substring(5) : item.date // 转换 YYYY-MM-DD 为 MM-DD
          }));
          setTrendData(formattedTrendData);
        } else {
          setTrendData(mockTrendData);
        }

        if (typeRes.status === 'fulfilled') {
          // 计算百分比
          const typeData = typeRes.value;
          const totalCount = typeData.reduce((sum: number, item: any) => sum + item.count, 0);
          const dataWithPercentage = typeData.map((item: any) => ({
            ...item,
            percentage: totalCount > 0 ? (item.count / totalCount * 100) : 0
          }));
          setAlertTypeData(dataWithPercentage);
        } else {
          setAlertTypeData(mockAlertTypeData);
        }

        if (algoRes.status === 'fulfilled') {
          setAlgorithmData(algoRes.value);
        } else {
          setAlgorithmData(mockAlgorithmData);
        }

        // 使用新的 fetchVideoStreams 获取视频流（包含在线过滤）
        await fetchVideoStreams();

        // 首次加载告警数据
        await fetchLatestAlerts();

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

    fetchInitialData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // 只在组件挂载时执行一次

  // 新增：监听视图切换，更新显示的流
  useEffect(() => {
    if (videoStreams.length === 0) {
      console.log('SafetyMonitoringDashboard: 暂无视频流数据');
      return;
    }

    const streamCount = activeMonitorView === 'main' ? 1 : 4;
    const newStreams = videoStreams.slice(0, streamCount);
    console.log(`SafetyMonitoringDashboard: 切换到${activeMonitorView}视图，显示${newStreams.length}个流`);
    setCurrentStreams(newStreams);
  }, [activeMonitorView, videoStreams]);

  // 告警数据定时轮询 - 5秒间隔查询最新15条
  useEffect(() => {
    // 首次加载告警数据
    fetchLatestAlerts();

    // 设置5秒定时轮询
    const alertsInterval = setInterval(() => {
      fetchLatestAlerts();
    }, 5000); // 5秒轮询一次

    // 清理函数
    return () => {
      clearInterval(alertsInterval);
    };
  }, []); // 空依赖数组，只在组件挂载时执行一次

  // 组件卸载时清理视频流资源
  useEffect(() => {
    return () => {
      // 清理所有FLV视频流资源
      const videoElements = document.querySelectorAll('video[src^="blob:"]');
      videoElements.forEach((element) => {
        const videoElement = element as HTMLVideoElement;
        videoElement.pause();
        videoElement.src = '';
        videoElement.load();
      });

      // 清理状态
      setVideoStreams([]);
      setVideoConnectionStatus('offline');

      console.log('SafetyMonitoringDashboard: 视频流资源已清理');
    };
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
          <AgentButton onClick={() => setAgentDialogVisible(true)} />
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
            <Row gutter={[0, 16]} style={{ height: '100%' }}>
              {/* 上部分：告警分析 - 占2/3高度 */}
              <Col span={24} style={{ height: '66.67%' }}>
                <div style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* 告警趋势图 */}
                  <Card
                    className="panel-card"
                    title="告警趋势分析"
                    size="small"
                    style={{ flex: 1 }}
                    styles={{ body: { padding: '8px 8px 5px 8px', height: 'calc(100% - 40px)' } }}
                  >
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart
                        data={trendData}
                        margin={{ top: 5, right: 10, left: -15, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#1f4e79" opacity={0.3} />
                        <XAxis
                          dataKey="date"
                          axisLine={{ stroke: '#1f4e79' }}
                          tickLine={{ stroke: '#1f4e79' }}
                          tick={{ fill: '#87ceeb', fontSize: 9 }}
                          interval={0}
                          angle={-35}
                          textAnchor="end"
                          height={40}
                          dy={2}
                        />
                        <YAxis
                          axisLine={{ stroke: '#1f4e79' }}
                          tickLine={{ stroke: '#1f4e79' }}
                          tick={{ fill: '#87ceeb', fontSize: 9 }}
                          allowDecimals={false}
                          width={35}
                          domain={[0, 'auto']}
                          tickCount={6}
                        />
                        <RechartsTooltip
                          contentStyle={{
                            backgroundColor: 'rgba(15, 52, 96, 0.9)',
                            border: '1px solid #1890ff',
                            borderRadius: '6px',
                            color: '#fff',
                            fontSize: '12px'
                          }}
                          labelFormatter={(label) => `日期: ${label}`}
                          formatter={(value: any) => [`${value} 次`, '告警数量']}
                        />
                        <Line
                          type="monotone"
                          dataKey="count"
                          stroke="#1890ff"
                          strokeWidth={2}
                          dot={{ fill: '#1890ff', strokeWidth: 2, r: 3 }}
                          activeDot={{ r: 5 }}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </Card>

                  {/* 告警分类排行 */}
                  <Card className="panel-card" title="告警分类排行" size="small" style={{ flex: 1 }}>
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
                </div>
              </Col>
              
              {/* 下部分：AI编排算法 - 占1/3高度，与中间和右侧下半部分对齐 */}
              <Col span={24} style={{ height: '33.33%' }}>
                <Card className="panel-card" title="AI编排算法" size="small" style={{ height: '100%' }}>
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
                        {/* <span className="algo-count">({algo.count})</span> */}
                      </div>
                    ))}
                  </div>
                </Card>
              </Col>
            </Row>
          </Col>

          {/* 中间面板 */}
          <Col span={12} className="center-panel">
            <Row gutter={[0, 16]} style={{ height: '100%' }}>
              {/* 上部分：监控切换区域 - 占2/3高度 */}
              <Col span={24} style={{ height: '66.67%' }}>
                <div className="monitor-section" style={{ height: '100%' }}>
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
                      <Space size="middle">
                        {/* 全屏按钮 */}
                        <Tooltip title={isFullscreen ? "退出全屏" : "全屏显示"}>
                          <Button
                            size="small"
                            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                            onClick={handleFullscreen}
                          />
                        </Tooltip>

                        <Badge
                          status={
                            videoConnectionStatus === 'connected' ? 'processing' :
                            videoConnectionStatus === 'connecting' ? 'warning' :
                            videoConnectionStatus === 'offline' ? 'default' : 'error'
                          }
                          text={
                            videoConnectionStatus === 'connected' ? '实时监控中' :
                            videoConnectionStatus === 'connecting' ? `连接中${retryCount > 0 ? `(重试${retryCount}/${maxRetryCount})` : ''}` :
                            videoConnectionStatus === 'offline' ? '离线' : '连接失败'
                          }
                        />
                      </Space>
                    </div>
                  </div>
                  
                  {/* 监控内容区域 */}
                  <div className="monitor-content" ref={videoContainerRef}>
                    {activeMonitorView === 'main' ? (
                      <div className="main-monitor-view">
                        {currentStreams.length > 0 && currentStreams[0] && ((currentStreams[0] as any).health_status === 'online' || currentStreams[0].status === 'ONLINE') ? (
                          <FLVPlayer
                            rtspUrl={currentStreams[0].stream_url}
                            title={currentStreams[0].name}
                            autoPlay={autoPlayEnabled}
                            onError={errorHandlers.get(currentStreams[0].id)}
                            width="100%"
                            height="100%"
                          />
                        ) : (
                          <div className="monitor-placeholder">
                            <VideoCameraOutlined className="monitor-icon" />
                            <div className="monitor-text">主监控画面</div>
                            <div className="monitor-info">
                              {videoConnectionStatus === 'offline' ? '网络离线' :
                               videoConnectionStatus === 'failed' ? '连接失败' :
                               videoConnectionStatus === 'connecting' ? '正在连接...' :
                               '暂无在线视频流'}
                            </div>
                            {(videoConnectionStatus === 'failed' || videoConnectionStatus === 'offline') && (
                              <Button
                                type="primary"
                                onClick={handleManualRetry}
                                style={{ marginTop: 16 }}
                                loading={videoConnectionStatus === 'connecting'}
                              >
                                重新连接
                              </Button>
                            )}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="grid-monitor-view">
                        {[0, 1, 2, 3].map((index) => {
                          const stream = currentStreams[index];
                          return (
                            <div key={index} className="grid-monitor-item">
                              {stream && ((stream as any).health_status === 'online' || stream.status === 'ONLINE') ? (
                                <FLVPlayer
                                  rtspUrl={stream.stream_url}
                                  title={stream.name}
                                  autoPlay={autoPlayEnabled}
                                  onError={errorHandlers.get(stream.id)}
                                  width="100%"
                                  height="100%"
                                />
                              ) : (
                                <div className="grid-monitor-content">
                                  <VideoCameraOutlined className="grid-icon" />
                                  <div className="grid-label">
                                    {stream ? stream.location : '无信号'}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </Col>
              
              {/* 下部分：AI智能处理流程 - 占1/3高度，与左右侧下半部分对齐 */}
              <Col span={24} style={{ height: '33.33%' }}>
                <div className="ai-process-section" style={{ height: '100%', margin: 0 }}>
                  <AIProcessFlow />
                </div>
              </Col>
            </Row>
          </Col>

          {/* 右侧面板 */}
          <Col span={6} className="right-panel">
            <Row gutter={[0, 16]} style={{ height: '100%' }}>
              {/* 上部分：最新告警 - 占2/3高度 */}
              <Col span={24} style={{ height: '66.67%' }}>
                <Card className="panel-card" title="最新告警" size="small" style={{ height: '100%' }}>
                  <div className="alert-list">
                    {alerts.length === 0 ? (
                      <div className="no-alerts">
                        <SafetyOutlined className="no-alerts-icon" />
                        <Text className="no-alerts-text">暂无告警</Text>
                      </div>
                    ) : (
                      alerts.slice(0, 20).map((alert, index) => (
                        <div
                          key={alert.id}
                          className="alert-item-compact"
                          onClick={() => handleAlertClick(alert)}
                          style={{ cursor: 'pointer' }}
                        >
                          {/* 左侧告警图片 */}
                          <div className="alert-image-small">
                            {alert.image_url ? (
                              <img
                                src={alert.image_url}
                                alt="告警截图"
                                style={{
                                  width: '50px',
                                  height: '40px',
                                  objectFit: 'cover',
                                  borderRadius: '4px'
                                }}
                                onError={(e) => {
                                  e.currentTarget.style.display = 'none';
                                }}
                              />
                            ) : (
                              <div style={{
                                width: '50px',
                                height: '40px',
                                background: 'rgba(255,255,255,0.1)',
                                borderRadius: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '20px'
                              }}>
                                {alert.description?.includes('安全帽') && '⛑️'}
                                {alert.description?.includes('反光衣') && '🦸'}
                                {!alert.description?.includes('安全帽') && !alert.description?.includes('反光衣') && '⚠️'}
                              </div>
                            )}
                          </div>

                          {/* 右侧内容区域 */}
                          <div className="alert-content-compact">
                            {/* 算法名称 */}
                            <div className="alert-header-compact">
                              <Badge
                                status={
                                  alert.severity === 'critical' ? 'error' :
                                  alert.severity === 'high' ? 'error' :
                                  alert.severity === 'medium' ? 'warning' : 'processing'
                                }
                                size="small"
                              />
                              <span className="alert-type-compact">
                                {alert.template_name || alert.algorithm_name || '智能检测'}
                              </span>
                            </div>

                            {/* 详细信息：摄像头名称和置信度 */}
                            <div className="alert-details-compact">
                              <div className="alert-stream-compact">{alert.video_name}</div>
                              <div className="alert-confidence-compact">
                                {(alert.confidence * 100).toFixed(1)}%
                              </div>
                            </div>

                            {/* 告警时间 */}
                            <div className="alert-time-compact">
                              {new Date(alert.created_at).toLocaleString('zh-CN', {
                                month: '2-digit',
                                day: '2-digit',
                                hour: '2-digit',
                                minute: '2-digit',
                                second: '2-digit'
                              })}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </Card>
              </Col>
              
              {/* 下部分：告警统计 - 占1/3高度，与左侧和中间下半部分对齐 */}
              <Col span={24} style={{ height: '33.33%' }}>
                <Card className="panel-card" title="告警统计" size="small" style={{ height: '100%' }}>
                  <div className="alert-stats-compact">
                    <Row gutter={[8, 8]}>
                      <Col span={12}>
                        <div className="compact-metric-card today-card">
                          <div className="compact-metric-icon">
                            <AlertOutlined />
                          </div>
                          <div className="compact-metric-content">
                            <div className="compact-metric-value">{statistics.today}</div>
                            <div className="compact-metric-label">今日告警</div>
                          </div>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div className="compact-metric-card week-card">
                          <div className="compact-metric-icon">
                            <FireOutlined />
                          </div>
                          <div className="compact-metric-content">
                            <div className="compact-metric-value">{statistics.thisWeek}</div>
                            <div className="compact-metric-label">本周告警</div>
                          </div>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div className="compact-metric-card month-card">
                          <div className="compact-metric-icon">
                            <WarningOutlined />
                          </div>
                          <div className="compact-metric-content">
                            <div className="compact-metric-value">{statistics.thisMonth}</div>
                            <div className="compact-metric-label">本月告警</div>
                          </div>
                        </div>
                      </Col>
                      <Col span={12}>
                        <div className="compact-metric-card total-card">
                          <div className="compact-metric-icon">
                            <BarChartOutlined />
                          </div>
                          <div className="compact-metric-content">
                            <div className="compact-metric-value">{statistics.thisYear}</div>
                            <div className="compact-metric-label">累计告警</div>
                          </div>
                        </div>
                      </Col>
                    </Row>
                  </div>
                </Card>
              </Col>
            </Row>
          </Col>
        </Row>
      </div>

      {/* AI智能体对话框 */}
      <AgentDialog
        visible={agentDialogVisible}
        onClose={() => setAgentDialogVisible(false)}
      />

      {/* 告警详情弹框（来自LivePreviewPage） */}
      <Modal
        title="告警详情"
        open={alertModalVisible}
        onCancel={handleAlertModalClose}
        footer={null}
        width={800}
        centered
      >
        {selectedAlert && (
          <div className="alertDetailModal">
            {/* 告警图片 */}
            {selectedAlert.image_url && (
              <div className="alert-image-section" style={{ marginBottom: 20, textAlign: 'center' }}>
                <Image
                  src={selectedAlert.image_url}
                  alt="告警截图"
                  style={{ maxWidth: '100%', maxHeight: '400px' }}
                  placeholder={
                    <div style={{
                      width: '100%',
                      height: '200px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: '#f5f5f5',
                      color: '#999'
                    }}>
                      加载中...
                    </div>
                  }
                />
              </div>
            )}

            {/* 告警详细信息 */}
            <Descriptions
              column={2}
              bordered
              size="small"
              labelStyle={{ width: '120px', fontWeight: 600 }}
            >
              <Descriptions.Item label="算法名称" span={2}>
                <Badge
                  color="blue"
                  text={selectedAlert.template_name || selectedAlert.algorithm_name || '智能检测'}
                />
              </Descriptions.Item>

              <Descriptions.Item label="视频名称">
                {selectedAlert.video_name}
              </Descriptions.Item>

              <Descriptions.Item label="告警时间">
                {formatTime(selectedAlert.created_at)}
              </Descriptions.Item>

              <Descriptions.Item label="置信度">
                <Badge
                  color={selectedAlert.confidence > 0.8 ? 'green' : selectedAlert.confidence > 0.6 ? 'orange' : 'red'}
                  text={`${(selectedAlert.confidence * 100).toFixed(1)}%`}
                />
              </Descriptions.Item>

              <Descriptions.Item label="严重级别">
                <Badge
                  color={
                    selectedAlert.severity === 'critical' ? 'red' :
                    selectedAlert.severity === 'high' ? 'orange' :
                    selectedAlert.severity === 'medium' ? 'yellow' : 'blue'
                  }
                  text={
                    selectedAlert.severity === 'critical' ? '严重' :
                    selectedAlert.severity === 'high' ? '高' :
                    selectedAlert.severity === 'medium' ? '中' : '低'
                  }
                />
              </Descriptions.Item>

              <Descriptions.Item label="视频时间">
                {selectedAlert.video_time}
              </Descriptions.Item>

              <Descriptions.Item label="帧索引">
                #{selectedAlert.frame_index}
              </Descriptions.Item>

              {selectedAlert.description && (
                <Descriptions.Item label="详细描述" span={2}>
                  {selectedAlert.description}
                </Descriptions.Item>
              )}
            </Descriptions>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SafetyMonitoringDashboardWithAI;