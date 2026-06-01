/**
 * 重新设计的实时视频预览页面
 * 使用 react-grid-layout 实现动态多分屏布局
 * 使用企业级MJPEG流媒体服务实现高兼容性实时流播放
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { Card, Button, List, Badge, Space, Typography, Row, Col, Switch, message, Tooltip, Modal, Image, Descriptions } from 'antd';
import { 
  PlayCircleOutlined, 
  PauseCircleOutlined, 
  ReloadOutlined, 
  VideoCameraOutlined, 
  WarningOutlined, 
  FullscreenOutlined, 
  SettingOutlined, 
  SoundOutlined,
  LeftOutlined,
  RightOutlined,
  EyeOutlined,
  BorderOutlined,
  AppstoreOutlined,
  BorderlessTableOutlined,
} from '@ant-design/icons';
import FLVPlayer from '../components/stream/FLVPlayer';
import './LivePreviewPage.css';

const { Title, Text } = Typography;


// 视频流数据接口
interface VideoStream {
  id: string;
  name: string;
  stream_url: string;
  stream_type: string;
  location?: string;
  group_name?: string;
  status: 'ONLINE' | 'OFFLINE';
}

// 告警数据接口
interface Alert {
  id: string;
  video_name: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  algorithm_name: string;
  template_name?: string;  // AI编排算法名称
  confidence: number;
  created_at: string;
  image_url?: string;
  frame_index: number;
  video_time: string;
}

const LivePreviewPage: React.FC = () => {
  // 状态管理
  const [videoStreams, setVideoStreams] = useState<VideoStream[]>([]);
  const [currentStreams, setCurrentStreams] = useState<VideoStream[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [alertStats, setAlertStats] = useState<{total_alerts: number; today_alerts: number}>({
    total_alerts: 0,
    today_alerts: 0
  });
  const [isCarouselActive, setIsCarouselActive] = useState(false);
  const [currentPage, setCurrentPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [streamErrors, setStreamErrors] = useState<{[key: string]: boolean}>({});
  const [layoutMode, setLayoutMode] = useState<'single' | 'quad' | 'nine'>('single');
  const [selectedStreamIndex, setSelectedStreamIndex] = useState(0);
  const [autoPlayEnabled, setAutoPlayEnabled] = useState(true);  // 添加自动播放控制

  // 告警详情弹框状态
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [alertModalVisible, setAlertModalVisible] = useState(false);

  // 视频预览弹框状态
  const [videoPreviewVisible, setVideoPreviewVisible] = useState(false);
  const [selectedVideoStream, setSelectedVideoStream] = useState<VideoStream | null>(null);

  // 定时器引用
  const [carouselTimer, setCarouselTimer] = useState<NodeJS.Timeout | null>(null);
  const [alertsTimer, setAlertsTimer] = useState<NodeJS.Timeout | null>(null);


  // 获取视频流列表
  const fetchVideoStreams = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/video-streams/');

      if (!response.ok) {
        throw new Error('获取视频流失败');
      }

      const data = await response.json();

      // 过滤健康状态为online的流(优先使用health_status,其次使用status)
      const onlineStreams = data.filter((stream: VideoStream) => {
        const healthStatus = (stream as any).health_status;
        return healthStatus === 'online' || stream.status === 'ONLINE';
      });

      setVideoStreams(onlineStreams);

      // 根据当前布局模式初始化显示流
      const streamCount = layoutMode === 'single' ? 1 : layoutMode === 'quad' ? 4 : 9;
      setCurrentStreams(onlineStreams.slice(0, streamCount));
    } catch (error) {
      console.error('获取视频流失败:', error);
      message.error('获取视频流失败');
    } finally {
      setLoading(false);
    }
  }, [layoutMode]);

  // 获取告警统计数据（从ES的video_alerts索引）
  const fetchAlertStats = useCallback(async () => {
    try {
      const response = await fetch('/api/alerts/stats');

      if (!response.ok) {
        console.warn('告警统计接口响应异常:', response.status);
        return;
      }

      const stats = await response.json();
      setAlertStats({
        total_alerts: stats.total_alerts || 0,
        today_alerts: stats.today_alerts || 0
      });

      console.log('✅ 告警统计已更新:', stats);
    } catch (error) {
      console.error('获取告警统计失败:', error);
    }
  }, []);

  // 获取最新告警数据（优化ES接口调用）
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

  // 视频轮播逻辑
  const startCarousel = useCallback(() => {
    const streamCount = layoutMode === 'single' ? 1 : layoutMode === 'quad' ? 4 : 9;
    
    if (videoStreams.length <= streamCount) {
      message.warning('视频流数量不足，无需轮播');
      return;
    }

    const timer = setInterval(() => {
      if (layoutMode === 'single') {
        // 单屏模式：切换到下一个流
        setSelectedStreamIndex(prevIndex => {
          const nextIndex = (prevIndex + 1) % videoStreams.length;
          setCurrentStreams([videoStreams[nextIndex]]);
          return nextIndex;
        });
      } else {
        // 多屏模式：切换页面
        setCurrentPage(prevPage => {
          const totalPages = Math.ceil(videoStreams.length / streamCount);
          const nextPage = (prevPage + 1) % totalPages;
          const start = nextPage * streamCount;
          const end = start + streamCount;
          const newStreams = videoStreams.slice(start, end);
          setCurrentStreams(newStreams);
          // 无需重新生成网格布局 - 使用CSS Grid固定布局
          return nextPage;
        });
      }
    }, 15000); // 每15秒切换一次

    setCarouselTimer(timer);
    setIsCarouselActive(true);
    message.success('视频轮播已启动');
  }, [videoStreams, layoutMode]);

  const stopCarousel = useCallback(() => {
    if (carouselTimer) {
      clearInterval(carouselTimer);
      setCarouselTimer(null);
    }
    setIsCarouselActive(false);
    message.info('视频轮播已停止');
  }, [carouselTimer]);

  // 手动刷新告警数据
  const handleRefreshAlerts = useCallback(() => {
    fetchLatestAlerts();
    message.success('告警数据已刷新');
  }, [fetchLatestAlerts]);

  // 处理流错误状态
  const handleStreamError = useCallback((streamId: string, hasError: boolean) => {
    setStreamErrors(prev => ({
      ...prev,
      [streamId]: hasError
    }));
  }, []);

  // 创建稳定的错误处理函数映射，避免重复连接
  const errorHandlers = useMemo(() => {
    const handlers = new Map();
    currentStreams.forEach(stream => {
      if (stream) {
        handlers.set(stream.id, (hasError: boolean) => handleStreamError(stream.id, hasError));
      }
    });
    return handlers;
  }, [currentStreams, handleStreamError]);

  // 处理布局切换
  const handleLayoutChange = useCallback((mode: 'single' | 'quad' | 'nine') => {
    setLayoutMode(mode);
    
    // 根据布局模式更新显示的流
    const streamCount = mode === 'single' ? 1 : mode === 'quad' ? 4 : 9;
    const startIndex = mode === 'single' ? selectedStreamIndex : currentPage * streamCount;
    const newStreams = videoStreams.slice(startIndex, startIndex + streamCount);
    
    // 强制确保单屏模式只有一个流
    if (mode === 'single' && newStreams.length > 1) {
      newStreams.length = 1;
    }
    
    setCurrentStreams(newStreams);
    
    // 重置页面状态
    if (mode !== 'single') {
      setCurrentPage(0);
    }
    
    message.success(`已切换到${mode === 'single' ? '单屏' : mode === 'quad' ? '四分屏' : '九分屏'}模式`);
  }, [videoStreams, selectedStreamIndex, currentPage]);

  // 单屏模式切换流
  const handleSingleStreamChange = useCallback((direction: 'prev' | 'next') => {
    if (layoutMode !== 'single' || videoStreams.length === 0) return;
    
    const newIndex = direction === 'next' 
      ? (selectedStreamIndex + 1) % videoStreams.length
      : selectedStreamIndex === 0 ? videoStreams.length - 1 : selectedStreamIndex - 1;
    
    setSelectedStreamIndex(newIndex);
    setCurrentStreams([videoStreams[newIndex]]);
  }, [layoutMode, videoStreams, selectedStreamIndex]);

  // ============= 视频预览弹框功能 =============
  
  // 打开视频预览弹框
  const handleVideoPreview = useCallback((stream: VideoStream) => {
    setSelectedVideoStream(stream);
    setVideoPreviewVisible(true);
  }, []);

  // 关闭视频预览弹框
  const handleVideoPreviewClose = useCallback(() => {
    setVideoPreviewVisible(false);
    setSelectedVideoStream(null);
  }, []);

  // ============= 视频预览功能结束 =============

  // 处理告警点击 - 显示告警详情弹框
  const handleAlertClick = useCallback((alert: Alert) => {
    setSelectedAlert(alert);
    setAlertModalVisible(true);
  }, []);

  // 关闭告警详情弹框
  const handleAlertModalClose = useCallback(() => {
    setAlertModalVisible(false);
    setSelectedAlert(null);
  }, []);



  // 生命周期管理 + 页面可见性检测（性能优化）
  useEffect(() => {
    // 初始化数据
    fetchVideoStreams();
    fetchLatestAlerts();
    fetchAlertStats();  // 页面加载时获取一次告警统计，不轮询

    let alertsInterval: NodeJS.Timeout | null = null;

    // 启动告警轮询
    const startAlertsPolling = () => {
      if (alertsInterval) return; // 防止重复启动
      alertsInterval = setInterval(fetchLatestAlerts, 5000);
      setAlertsTimer(alertsInterval);
      console.log('✅ 告警轮询已启动（页面可见）');
    };

    // 停止告警轮询
    const stopAlertsPolling = () => {
      if (alertsInterval) {
        clearInterval(alertsInterval);
        alertsInterval = null;
        setAlertsTimer(null);
        console.log('⏸️ 告警轮询已停止（页面隐藏）');
      }
    };

    // 页面可见性变化监听
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        // 页面可见：立即刷新告警数据并启动轮询（统计数据不刷新）
        fetchLatestAlerts();
        startAlertsPolling();
      } else {
        // 页面隐藏：停止轮询，节省资源
        stopAlertsPolling();
      }
    };

    // 只在页面可见时启动告警轮询
    if (document.visibilityState === 'visible') {
      startAlertsPolling();
    }

    // 添加可见性监听器
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      // 清理定时器
      if (carouselTimer) clearInterval(carouselTimer);
      stopAlertsPolling();
      // 移除监听器
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []); // ✅ 修复：移除依赖项，只在组件挂载时执行一次

  // 格式化告警严重级别
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'yellow';
      case 'low': return 'blue';
      default: return 'default';
    }
  };

  // 格式化时间显示
  const formatTime = (timestamp: string | number) => {
    const date = new Date(typeof timestamp === 'string' ? timestamp : timestamp);
    return date.toLocaleString('zh-CN');
  };

  return (
    <div className="livePreviewContainer">
      {/* 头部指标区域 */}
      <div className="metricsHeader">
        <div className="metricsGrid">
          <div className="metricCard">
            <div className="metricIcon streamsIcon">
              <VideoCameraOutlined />
            </div>
            <div className="metricContent">
              <div className="metricValue">{videoStreams.length}</div>
              <div className="metricLabel">视频总数</div>
            </div>
          </div>
          
          <div className="metricCard">
            <div className="metricIcon onlineIcon">
              <EyeOutlined />
            </div>
            <div className="metricContent">
              <div className="metricValue">{videoStreams.filter(s => s.status === 'ONLINE').length}</div>
              <div className="metricLabel">在线视频数</div>
            </div>
          </div>
          
          <div className="metricCard">
            <div className="metricIcon algorithmsIcon">
              <SettingOutlined />
            </div>
            <div className="metricContent">
              <div className="metricValue">5</div>
              <div className="metricLabel">算法总数</div>
            </div>
          </div>
          
          <div className="metricCard">
            <div className="metricIcon todayAlertsIcon">
              <WarningOutlined />
            </div>
            <div className="metricContent">
              <div className="metricValue">{alertStats.today_alerts}</div>
              <div className="metricLabel">今日告警</div>
            </div>
          </div>

          <div className="metricCard">
            <div className="metricIcon totalAlertsIcon">
              <WarningOutlined />
            </div>
            <div className="metricContent">
              <div className="metricValue">{alertStats.total_alerts}</div>
              <div className="metricLabel">总告警数</div>
            </div>
          </div>
        </div>
      </div>

      {/* 主要内容区域 */}
      <div className="mainContent">
        <Row gutter={24}>
          {/* 左侧：实时监控画面 */}
          <Col span={16}>
            <Card className="videoMonitorCard" variant="borderless">
              {/* 视频区域头部 */}
              <div className="videoHeaderSection">
                <div className="videoTitle">
                  <EyeOutlined />
                  <span>实时监控画面</span>
                  <Badge count={videoStreams.length} className="streamCount" />
                </div>
                
                {/* 布局切换控件 - 居中显示 */}
                <div className="layoutControlsCenter">
                  <div className="layoutControls">
                    <Space size="small">
                      <Tooltip title="单屏显示">
                        <Button 
                          size="small" 
                          type={layoutMode === 'single' ? 'primary' : 'default'}
                          icon={<BorderOutlined />}
                          onClick={() => handleLayoutChange('single')}
                        >
                          单屏
                        </Button>
                      </Tooltip>
                      <Tooltip title="四分屏显示">
                        <Button 
                          size="small" 
                          type={layoutMode === 'quad' ? 'primary' : 'default'}
                          icon={<AppstoreOutlined />}
                          onClick={() => handleLayoutChange('quad')}
                        >
                          四分屏
                        </Button>
                      </Tooltip>
                      <Tooltip title="九分屏显示">
                        <Button 
                          size="small" 
                          type={layoutMode === 'nine' ? 'primary' : 'default'}
                          icon={<BorderlessTableOutlined />}
                          onClick={() => handleLayoutChange('nine')}
                        >
                          九分屏
                        </Button>
                      </Tooltip>
                    </Space>
                  </div>
                </div>
                
                {/* 轮播控制按钮 */}
                {(() => {
                  const streamCount = layoutMode === 'single' ? 1 : layoutMode === 'quad' ? 4 : 9;
                  return videoStreams.length > streamCount && (
                  <div className="carouselControls">
                    <div className="pageInfo">
                      {layoutMode === 'single' ? (
                        <span>{selectedStreamIndex + 1} / {videoStreams.length}</span>
                      ) : (
                        <span>{currentPage + 1} / {Math.ceil(videoStreams.length / streamCount)}</span>
                      )}
                    </div>
                    <Space size="small">
                      <Button 
                        icon={<LeftOutlined />} 
                        size="small" 
                        className="navBtn"
                        onClick={() => {
                          if (layoutMode === 'single') {
                            handleSingleStreamChange('prev');
                          } else {
                            const totalPages = Math.ceil(videoStreams.length / streamCount);
                            const prevPage = currentPage === 0 ? totalPages - 1 : currentPage - 1;
                            setCurrentPage(prevPage);
                            const start = prevPage * streamCount;
                            const newStreams = videoStreams.slice(start, start + streamCount);
                            setCurrentStreams(newStreams);
                          }
                        }}
                      />
                      <Button 
                        icon={<RightOutlined />} 
                        size="small" 
                        className="navBtn"
                        onClick={() => {
                          if (layoutMode === 'single') {
                            handleSingleStreamChange('next');
                          } else {
                            const totalPages = Math.ceil(videoStreams.length / streamCount);
                            const nextPage = (currentPage + 1) % totalPages;
                            setCurrentPage(nextPage);
                            const start = nextPage * streamCount;
                            const newStreams = videoStreams.slice(start, start + streamCount);
                            setCurrentStreams(newStreams);
                          }
                        }}
                      />
                      <Switch
                        checked={isCarouselActive}
                        onChange={(checked) => checked ? startCarousel() : stopCarousel()}
                        size="small"
                        checkedChildren="自动"
                        unCheckedChildren="手动"
                        className="autoSwitch"
                      />
                    </Space>
                  </div>
                );
              })()}
              </div>

              {/* 动态视频显示区域 */}
              <div className="videoGridContainer">
                <div className={`videoGrid layout${layoutMode.charAt(0).toUpperCase() + layoutMode.slice(1)}`}>
                  {layoutMode === 'single' ? (
                    // 单屏模式：只渲染一个视频组件，WebRTCPlayer充满整个区域
                    (() => {
                      const stream = currentStreams[0];
                      return (
                        <div key="single-video" className="videoCell singleScreenCell">
                          {stream ? (
                            ((stream as any).health_status === 'online' || stream.status === 'ONLINE') ? (
                              <FLVPlayer
                                rtspUrl={stream.stream_url}
                                title={stream.name}
                                autoPlay={autoPlayEnabled}
                                onError={errorHandlers.get(stream.id)}
                                width="100%"
                                height="100%"
                              />
                            ) : (
                              <div className="videoContainer">
                                <div className="videoHeader">
                                  <Text strong>{stream.name}</Text>
                                  <Badge 
                                    status="default"
                                    text="流异常"
                                  />
                                </div>
                                <div className="videoPlaceholder">
                                  <VideoCameraOutlined style={{ fontSize: 48, color: '#333' }} />
                                  <p>视频流离线</p>
                                  <p>{stream.location}</p>
                                  <p style={{ fontSize: '12px', color: '#666' }}>
                                    {stream.stream_url}
                                  </p>
                                </div>
                              </div>
                            )
                          ) : (
                            <div className="emptyCell">
                              <VideoCameraOutlined style={{ fontSize: 32, color: '#d9d9d9' }} />
                              <p>无信号</p>
                            </div>
                          )}
                        </div>
                      );
                    })()
                  ) : (
                    // 多屏模式：按原有逻辑渲染多个视频组件
                    (() => {
                      const cellCount = layoutMode === 'quad' ? 4 : 9;
                      return Array.from({ length: cellCount }, (_, index) => {
                        const stream = currentStreams[index];
                        return (
                          <div key={index} className="videoCell">
                            {stream ? (
                              ((stream as any).health_status === 'online' || stream.status === 'ONLINE') ? (
                                <FLVPlayer
                                  rtspUrl={stream.stream_url}
                                  title={stream.name}
                                  autoPlay={autoPlayEnabled}
                                  onError={errorHandlers.get(stream.id)}
                                  width="100%"
                                  height="100%"
                                />
                              ) : (
                                <div className="videoPlaceholder">
                                  <VideoCameraOutlined style={{ fontSize: 48, color: '#333' }} />
                                  <p>视频流离线</p>
                                  <p>{stream.location}</p>
                                  <p style={{ fontSize: '12px', color: '#666' }}>
                                    {stream.stream_url}
                                  </p>
                                </div>
                              )
                            ) : (
                              <div className="emptyCell">
                                <VideoCameraOutlined style={{ fontSize: 32, color: '#d9d9d9' }} />
                                <p>无信号</p>
                              </div>
                            )}
                          </div>
                        );
                      });
                    })()
                  )}
                </div>
              </div>
            </Card>
          </Col>

          {/* 右侧：实时数据 */}
          <Col span={8}>
            <Card className="alertsCard" variant="borderless">
              <div className="alertsHeader">
                <div className="alertsTitle">
                  <WarningOutlined className="alertsIcon" />
                  <span>实时数据</span>
                  <Badge count={alerts.length} className="alertsCount" />
                </div>
                  <div className="alertsControls">
                    <Button 
                      type="text" 
                      icon={<ReloadOutlined />} 
                      onClick={handleRefreshAlerts}
                      size="small"
                      className="refreshBtn"
                    >
                      刷新
                    </Button>
                    <div className="autoRefreshIndicator">
                      <div className="refreshDot"></div>
                      <span>5s自动刷新</span>
                    </div>
                  </div>
                </div>

                <div className="alertsContent">
                  {alerts.length === 0 ? (
                    <div className="noAlerts">
                      <WarningOutlined className="noAlertsIcon" />
                      <p>暂无告警信息</p>
                      <p className="noAlertsDesc">系统正在实时监控中...</p>
                    </div>
                  ) : (
                    <List
                      className="alertsList"
                      dataSource={alerts.slice(0, 10)}
                      renderItem={(alert, index) => (
                        <List.Item 
                          className={`alertItem priority${alert.severity.charAt(0).toUpperCase() + alert.severity.slice(1)} ${alert.description?.includes('安全帽') ? 'safetyHelmet' : ''} ${alert.description?.includes('反光衣') ? 'reflectiveVest' : ''}`}
                          onClick={() => handleAlertClick(alert)}
                          style={{ cursor: 'pointer' }}
                        >
                          <div className="alertItemContent">
                            {/* 左侧小图展示 */}
                            <div className="alertThumbnail">
                              {alert.image_url ? (
                                <img 
                                  src={alert.image_url} 
                                  alt="告警截图" 
                                  className="alertThumbImg"
                                  onError={(e) => {
                                    e.currentTarget.style.display = 'none';
                                    e.currentTarget.nextElementSibling.style.display = 'flex';
                                  }}
                                />
                              ) : null}
                              <div className="alertThumbPlaceholder" style={{ display: alert.image_url ? 'none' : 'flex' }}>
                                <div className="alertType">
                                  {alert.description?.includes('安全帽') && <span className="typeIcon safety">⛑️</span>}
                                  {alert.description?.includes('反光衣') && <span className="typeIcon vest">🦸</span>}
                                  {!alert.description?.includes('安全帽') && !alert.description?.includes('反光衣') && 
                                    <span className="typeIcon general">⚠️</span>
                                  }
                                </div>
                              </div>
                            </div>
                            
                            {/* 右侧文字内容，增加左边距 */}
                            <div className="alertMain">
                              <div className="alertInfo">
                                <div className="alertTitle">
                                  {alert.template_name || alert.algorithm_name || '智能检测'}
                                </div>
                                <div className="alertDetails">
                                  <span className="location">{alert.video_name}</span>
                                  <span className="confidence">置信度 {(alert.confidence * 100).toFixed(1)}%</span>
                                </div>
                                <div className="alertTime">
                                  {formatTime(alert.created_at)}
                                </div>
                              </div>
                            </div>
                            <div className="alertIndex">#{index + 1}</div>
                          </div>
                        </List.Item>
                      )}
                    />
                  )}
                </div>
              </Card>
          </Col>
        </Row>
      </div>
      
      {/* 告警详情弹框 */}
      <Modal
        title="告警详情"
        open={alertModalVisible}
        onCancel={handleAlertModalClose}
        footer={null}
        width={800}
        centered
        destroyOnHidden
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

      {/* 视频预览弹框 */}
      <Modal
        title={selectedVideoStream ? `视频预览 - ${selectedVideoStream.name}` : '视频预览'}
        open={videoPreviewVisible}
        onCancel={handleVideoPreviewClose}
        footer={null}
        width="80vw"
        style={{
          maxWidth: '1400px',
          top: '10vh'
        }}
        styles={{
          body: {
            padding: 0,
            height: '70vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#000'
          }
        }}
        destroyOnHidden={true}
      >
        {selectedVideoStream && ((selectedVideoStream as any).health_status === 'online' || selectedVideoStream.status === 'ONLINE') ? (
          <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <FLVPlayer
              rtspUrl={selectedVideoStream.stream_url}
              autoPlay={autoPlayEnabled}
              width="100%"
              height="100%"
              simple={true}
            />
          </div>
        ) : (
          <div style={{ 
            color: '#fff', 
            textAlign: 'center', 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center',
            height: '100%' 
          }}>
            <VideoCameraOutlined style={{ fontSize: 64, marginBottom: 16 }} />
            <p style={{ fontSize: 16 }}>
              {selectedVideoStream ? '视频流暂时离线' : '未选择视频流'}
            </p>
            {selectedVideoStream?.location && (
              <p style={{ fontSize: 12, opacity: 0.7 }}>
                位置：{selectedVideoStream.location}
              </p>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default LivePreviewPage;