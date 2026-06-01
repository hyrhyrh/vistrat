import React, { useState, useEffect } from 'react';
import {
  Layout,
  Card,
  Table,
  Button,
  Input,
  Select,
  DatePicker,
  Row,
  Col,
  Tag,
  Statistic,
  Tabs,
  Space,
  Modal,
  Descriptions,
  Badge,
  Alert,
  Tooltip,
  Progress
} from 'antd';
import {
  SearchOutlined,
  EyeOutlined,
  BarChartOutlined,
  WarningOutlined,
  PlayCircleOutlined,
  FilterOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { RangePickerProps } from 'antd/es/date-picker';
import dayjs from 'dayjs';
import axios from 'axios';
import BoundingBoxOverlay from '../components/alert/BoundingBoxOverlay';
import type { DetectionObject, ImageSize } from '../types';

const { Content } = Layout;
const { Option } = Select;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

interface AnalysisTask {
  task_id: string;
  video_id: string;
  video_name: string;
  original_filename: string;
  analysis_status: string;
  total_frames_analyzed: number;
  total_alerts: number;
  analysis_duration: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  template_ids: string[];
  results_summary: Array<{
    template_id: string;
    template_name: string;
    alerts_count: number;
    avg_confidence: number;
  }>;
}

interface AlertRecord {
  task_id: string;
  video_id: string;
  video_name: string;
  frame_index: number;
  timestamp: number;
  video_time: string;
  template_name: string;
  analysis_type: string;  // 分析类型: video_analysis(离线分析) 或 stream_analysis(实时分析)
  confidence: number;
  description: string;
  severity: string;
  created_at: string;
  metadata?: any;
}

interface FrameResult {
  task_id: string;
  video_id: string;
  frame_index: number;
  timestamp: number;
  video_time: string;
  template_id: string;
  template_name: string;
  ai_response: string;
  confidence: number;
  has_alert: boolean;
  analyzed_at: string;
  detection_objects?: DetectionObject[];
  // 后端新增：帧图片 URL + 原图尺寸（用于 bounding box 预览）
  image_url?: string;
  image_size?: ImageSize;
}

interface Statistics {
  analysis_tasks: {
    total: number;
    status_distribution: Array<{ key: string; count: number }>;
    avg_duration_seconds: number;
    total_alerts_generated: number;
    avg_frames_analyzed: number;
  };
  alerts: {
    total: number;
    severity_distribution: Array<{ key: string; count: number }>;
    confidence_stats: any;
    alert_types: Array<{ key: string; count: number }>;
    hourly_distribution: Array<{ timestamp: string; count: number }>;
  };
}

const AnalysisResultsPage: React.FC = () => {
  // 状态管理
  const [activeTab, setActiveTab] = useState('tasks');
  const [analysisTasksData, setAnalysisTasksData] = useState<AnalysisTask[]>([]);
  const [alertsData, setAlertsData] = useState<AlertRecord[]>([]);
  const [frameResultsData, setFrameResultsData] = useState<FrameResult[]>([]);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [taskDetailModalVisible, setTaskDetailModalVisible] = useState(false);
  const [frameResultModalVisible, setFrameResultModalVisible] = useState(false);
  const [selectedTask, setSelectedTask] = useState<AnalysisTask | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');

  // 查询参数
  const [taskFilters, setTaskFilters] = useState({
    video_name: '',
    status: '',
    template_name: '',
    min_alerts: undefined as number | undefined,
    date_range: [] as any[]
  });

  const [alertFilters, setAlertFilters] = useState({
    video_name: '',
    analysis_type: '',
    severity: '',
    min_confidence: undefined as number | undefined,
    date_range: [] as any[]
  });

  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 分析任务表格列定义
  const taskColumns: ColumnsType<AnalysisTask> = [
    {
      title: '视频名称',
      dataIndex: 'video_name',
      key: 'video_name',
      ellipsis: true,
      render: (text: string, record: AnalysisTask) => (
        <Tooltip title={record.original_filename}>
          <span>{text}</span>
        </Tooltip>
      )
    },
    {
      title: '分析状态',
      dataIndex: 'analysis_status',
      key: 'analysis_status',
      render: (status: string) => {
        const colorMap: Record<string, string> = {
          'completed': 'success',
          'processing': 'processing',
          'failed': 'error',
          'queued': 'warning'
        };
        return <Badge status={colorMap[status] as any} text={status} />;
      }
    },
    {
      title: '分析帧数',
      dataIndex: 'total_frames_analyzed',
      key: 'total_frames_analyzed',
      sorter: true
    },
    {
      title: '预警数量',
      dataIndex: 'total_alerts',
      key: 'total_alerts',
      render: (alerts: number) => (
        <Tag color={alerts > 0 ? 'red' : 'green'}>
          {alerts > 0 ? <WarningOutlined /> : null} {alerts}
        </Tag>
      ),
      sorter: true
    },
    {
      title: '耗时(秒)',
      dataIndex: 'analysis_duration',
      key: 'analysis_duration',
      render: (duration: number) => duration?.toFixed(1) || '-',
      sorter: true
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => dayjs(time).format('MM-DD HH:mm'),
      sorter: true
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: AnalysisTask) => (
        <Space>
          <Button 
            type="primary" 
            size="small" 
            icon={<EyeOutlined />}
            onClick={() => showTaskDetail(record)}
          >
            查看详情
          </Button>
          <Button 
            type="default" 
            size="small" 
            icon={<PlayCircleOutlined />}
            onClick={() => showFrameResults(record.task_id)}
          >
            帧结果
          </Button>
        </Space>
      )
    }
  ];

  // 预警表格列定义
  const alertColumns: ColumnsType<AlertRecord> = [
    {
      title: '视频名称',
      dataIndex: 'video_name',
      key: 'video_name',
      ellipsis: true
    },
    {
      title: '时间位置',
      dataIndex: 'video_time',
      key: 'video_time',
      render: (time: string, record: AlertRecord) => (
        <span>{time} (#{record.frame_index})</span>
      )
    },
    {
      title: '分析类型',
      dataIndex: 'analysis_type',
      key: 'analysis_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          'video_analysis': '离线分析',
          'stream_analysis': '实时分析'
        };
        return <Tag>{typeMap[type] || type}</Tag>;
      }
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colorMap: Record<string, string> = {
          'critical': 'red',
          'high': 'orange',
          'medium': 'yellow',
          'low': 'blue'
        };
        const severityMap: Record<string, string> = {
          'critical': '严重',
          'high': '高',
          'medium': '中',
          'low': '低'
        };
        return <Tag color={colorMap[severity]}>{severityMap[severity] || severity}</Tag>;
      }
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: number) => (
        <Progress 
          percent={Math.round(confidence * 100)} 
          size="small" 
          strokeColor={confidence > 0.8 ? '#52c41a' : confidence > 0.6 ? '#faad14' : '#ff4d4f'}
        />
      ),
      sorter: true
    },
    {
      title: '模板',
      dataIndex: 'template_name',
      key: 'template_name',
      ellipsis: true
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 300
    },
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => dayjs(time).format('MM-DD HH:mm'),
      sorter: true
    }
  ];

  // 帧结果表格列定义
  const frameColumns: ColumnsType<FrameResult> = [
    {
      title: '预览',
      key: 'preview',
      width: 140,
      render: (_, record: FrameResult) =>
        record.image_url ? (
          <BoundingBoxOverlay
            imageUrl={record.image_url}
            detectionObjects={record.detection_objects}
            imageSize={record.image_size}
            width={120}
            height={80}
            objectFit="cover"
            showLabels={false}
          />
        ) : (
          <span style={{ color: '#999' }}>无</span>
        )
    },
    {
      title: '帧序号',
      dataIndex: 'frame_index',
      key: 'frame_index',
      sorter: true
    },
    {
      title: '时间位置',
      dataIndex: 'video_time',
      key: 'video_time'
    },
    {
      title: '模板名称',
      dataIndex: 'template_name',
      key: 'template_name',
      ellipsis: true
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      render: (confidence: number) => (
        <Progress 
          percent={Math.round(confidence * 100)} 
          size="small" 
          strokeColor={confidence > 0.8 ? '#52c41a' : confidence > 0.6 ? '#faad14' : '#ff4d4f'}
        />
      ),
      sorter: true
    },
    {
      title: '是否预警',
      dataIndex: 'has_alert',
      key: 'has_alert',
      render: (hasAlert: boolean) => (
        <Tag color={hasAlert ? 'red' : 'green'}>
          {hasAlert ? <WarningOutlined /> : null} {hasAlert ? '是' : '否'}
        </Tag>
      )
    },
    {
      title: 'AI分析结果',
      dataIndex: 'ai_response',
      key: 'ai_response',
      ellipsis: true,
      width: 300
    }
  ];

  // 获取分析任务数据
  const fetchAnalysisTasks = async (page = 1) => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pagination.pageSize
      };

      if (taskFilters.video_name) params.video_name = taskFilters.video_name;
      if (taskFilters.status) params.status = taskFilters.status;
      if (taskFilters.template_name) params.template_name = taskFilters.template_name;
      if (taskFilters.min_alerts !== undefined) params.min_alerts = taskFilters.min_alerts;
      if (taskFilters.date_range && taskFilters.date_range.length === 2) {
        params.start_date = taskFilters.date_range[0].format('YYYY-MM-DD');
        params.end_date = taskFilters.date_range[1].format('YYYY-MM-DD');
      }

      const response = await axios.get('/api/analysis-results/analysis-tasks', { params });
      
      if (response.data.success) {
        setAnalysisTasksData(response.data.data.results);
        setPagination({
          ...pagination,
          current: page,
          total: response.data.data.pagination.total
        });
      }
    } catch (error) {
      console.error('获取分析任务失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取预警数据
  const fetchAlerts = async (page = 1) => {
    setLoading(true);
    try {
      const params: any = {
        page,
        page_size: pagination.pageSize
      };

      if (alertFilters.video_name) params.video_name = alertFilters.video_name;
      if (alertFilters.analysis_type) params.analysis_type = alertFilters.analysis_type;
      if (alertFilters.severity) params.severity = alertFilters.severity;
      if (alertFilters.min_confidence !== undefined) params.min_confidence = alertFilters.min_confidence;
      if (alertFilters.date_range && alertFilters.date_range.length === 2) {
        params.start_date = alertFilters.date_range[0].format('YYYY-MM-DD');
        params.end_date = alertFilters.date_range[1].format('YYYY-MM-DD');
      }

      const response = await axios.get('/api/analysis-results/alerts', { params });
      
      if (response.data.success) {
        setAlertsData(response.data.data.alerts);
        setPagination({
          ...pagination,
          current: page,
          total: response.data.data.pagination.total
        });
      }
    } catch (error) {
      console.error('获取预警数据失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取统计信息
  const fetchStatistics = async () => {
    try {
      const params: any = {};
      
      const dateRange = taskFilters.date_range || alertFilters.date_range;
      if (dateRange && dateRange.length === 2) {
        params.start_date = dateRange[0].format('YYYY-MM-DD');
        params.end_date = dateRange[1].format('YYYY-MM-DD');
      }

      const response = await axios.get('/api/analysis-results/statistics', { params });
      
      if (response.data.success) {
        setStatistics(response.data.data);
      }
    } catch (error) {
      console.error('获取统计信息失败:', error);
    }
  };

  // 获取帧结果
  const fetchFrameResults = async (taskId: string) => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/analysis-results/frame-results/${taskId}`, {
        params: { page: 1, page_size: 100 }
      });
      
      if (response.data.success) {
        setFrameResultsData(response.data.data.frames);
      }
    } catch (error) {
      console.error('获取帧结果失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 显示任务详情
  const showTaskDetail = (task: AnalysisTask) => {
    setSelectedTask(task);
    setTaskDetailModalVisible(true);
  };

  // 显示帧结果
  const showFrameResults = async (taskId: string) => {
    setSelectedTaskId(taskId);
    await fetchFrameResults(taskId);
    setFrameResultModalVisible(true);
  };

  // 初始化数据
  useEffect(() => {
    if (activeTab === 'tasks') {
      fetchAnalysisTasks();
    } else if (activeTab === 'alerts') {
      fetchAlerts();
    } else if (activeTab === 'statistics') {
      fetchStatistics();
    }
  }, [activeTab]);

  // Tab切换处理
  const handleTabChange = (key: string) => {
    setActiveTab(key);
    setPagination({ ...pagination, current: 1 });
  };

  // 表格变化处理
  const handleTableChange = (paginationInfo: any) => {
    if (activeTab === 'tasks') {
      fetchAnalysisTasks(paginationInfo.current);
    } else if (activeTab === 'alerts') {
      fetchAlerts(paginationInfo.current);
    }
  };

  return (
    <Layout>
      <Content style={{ padding: '20px' }}>
        <Card title="分析结果历史查询" style={{ marginBottom: 20 }}>
          <Tabs activeKey={activeTab} onChange={handleTabChange}>
            <TabPane tab="分析任务" key="tasks">
              <Card size="small" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Input
                      placeholder="视频名称"
                      prefix={<SearchOutlined />}
                      value={taskFilters.video_name}
                      onChange={(e) => setTaskFilters({ ...taskFilters, video_name: e.target.value })}
                    />
                  </Col>
                  <Col span={4}>
                    <Select
                      placeholder="分析状态"
                      style={{ width: '100%' }}
                      value={taskFilters.status}
                      onChange={(value) => setTaskFilters({ ...taskFilters, status: value })}
                    >
                      <Option value="">全部</Option>
                      <Option value="completed">已完成</Option>
                      <Option value="processing">处理中</Option>
                      <Option value="failed">失败</Option>
                      <Option value="queued">排队中</Option>
                    </Select>
                  </Col>
                  <Col span={4}>
                    <Input
                      placeholder="最小预警数"
                      type="number"
                      value={taskFilters.min_alerts}
                      onChange={(e) => setTaskFilters({ ...taskFilters, min_alerts: e.target.value ? parseInt(e.target.value) : undefined })}
                    />
                  </Col>
                  <Col span={6}>
                    <RangePicker
                      style={{ width: '100%' }}
                      value={taskFilters.date_range}
                      onChange={(dates) => setTaskFilters({ ...taskFilters, date_range: dates || [] })}
                    />
                  </Col>
                  <Col span={4}>
                    <Space>
                      <Button 
                        type="primary" 
                        icon={<SearchOutlined />}
                        onClick={() => fetchAnalysisTasks(1)}
                      >
                        搜索
                      </Button>
                      <Button 
                        icon={<FilterOutlined />}
                        onClick={() => {
                          setTaskFilters({ video_name: '', status: '', template_name: '', min_alerts: undefined, date_range: [] });
                          fetchAnalysisTasks(1);
                        }}
                      >
                        重置
                      </Button>
                    </Space>
                  </Col>
                </Row>
              </Card>

              <Table
                columns={taskColumns}
                dataSource={analysisTasksData}
                rowKey="task_id"
                loading={loading}
                pagination={{
                  current: pagination.current,
                  pageSize: pagination.pageSize,
                  total: pagination.total,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条/共 ${total} 条`
                }}
                onChange={handleTableChange}
              />
            </TabPane>

            <TabPane tab="预警记录" key="alerts">
              <Card size="small" style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                  <Col span={6}>
                    <Input
                      placeholder="视频名称"
                      prefix={<SearchOutlined />}
                      value={alertFilters.video_name}
                      onChange={(e) => setAlertFilters({ ...alertFilters, video_name: e.target.value })}
                    />
                  </Col>
                  <Col span={4}>
                    <Select
                      placeholder="严重程度"
                      style={{ width: '100%' }}
                      value={alertFilters.severity}
                      onChange={(value) => setAlertFilters({ ...alertFilters, severity: value })}
                    >
                      <Option value="">全部</Option>
                      <Option value="critical">严重</Option>
                      <Option value="high">高</Option>
                      <Option value="medium">中</Option>
                      <Option value="low">低</Option>
                    </Select>
                  </Col>
                  <Col span={4}>
                    <Input
                      placeholder="最小置信度"
                      type="number"
                      step="0.1"
                      min="0"
                      max="1"
                      value={alertFilters.min_confidence}
                      onChange={(e) => setAlertFilters({ ...alertFilters, min_confidence: e.target.value ? parseFloat(e.target.value) : undefined })}
                    />
                  </Col>
                  <Col span={6}>
                    <RangePicker
                      style={{ width: '100%' }}
                      value={alertFilters.date_range}
                      onChange={(dates) => setAlertFilters({ ...alertFilters, date_range: dates || [] })}
                    />
                  </Col>
                  <Col span={4}>
                    <Space>
                      <Button 
                        type="primary" 
                        icon={<SearchOutlined />}
                        onClick={() => fetchAlerts(1)}
                      >
                        搜索
                      </Button>
                      <Button 
                        icon={<FilterOutlined />}
                        onClick={() => {
                          setAlertFilters({ video_name: '', analysis_type: '', severity: '', min_confidence: undefined, date_range: [] });
                          fetchAlerts(1);
                        }}
                      >
                        重置
                      </Button>
                    </Space>
                  </Col>
                </Row>
              </Card>

              <Table
                columns={alertColumns}
                dataSource={alertsData}
                rowKey={(record) => `${record.task_id}_${record.frame_index}`}
                loading={loading}
                pagination={{
                  current: pagination.current,
                  pageSize: pagination.pageSize,
                  total: pagination.total,
                  showSizeChanger: true,
                  showQuickJumper: true,
                  showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条/共 ${total} 条`
                }}
                onChange={handleTableChange}
              />
            </TabPane>

            <TabPane tab="统计信息" key="statistics">
              {statistics && (
                <Row gutter={16}>
                  <Col span={12}>
                    <Card title="分析任务统计" style={{ marginBottom: 16 }}>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Statistic title="总任务数" value={statistics.analysis_tasks.total} />
                        </Col>
                        <Col span={8}>
                          <Statistic 
                            title="总预警数" 
                            value={statistics.analysis_tasks.total_alerts_generated}
                            valueStyle={{ color: statistics.analysis_tasks.total_alerts_generated > 0 ? '#cf1322' : '#3f8600' }}
                          />
                        </Col>
                        <Col span={8}>
                          <Statistic 
                            title="平均耗时(秒)" 
                            value={statistics.analysis_tasks.avg_duration_seconds}
                            precision={1}
                          />
                        </Col>
                      </Row>
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card title="预警统计" style={{ marginBottom: 16 }}>
                      <Row gutter={16}>
                        <Col span={8}>
                          <Statistic title="总预警数" value={statistics.alerts.total} valueStyle={{ color: '#cf1322' }} />
                        </Col>
                        <Col span={8}>
                          <Statistic 
                            title="平均置信度" 
                            value={statistics.alerts.confidence_stats?.avg || 0}
                            precision={3}
                          />
                        </Col>
                        <Col span={8}>
                          <Statistic 
                            title="最高置信度" 
                            value={statistics.alerts.confidence_stats?.max || 0}
                            precision={3}
                          />
                        </Col>
                      </Row>
                    </Card>
                  </Col>
                </Row>
              )}
            </TabPane>
          </Tabs>
        </Card>

        {/* 任务详情弹窗 */}
        <Modal
          title="分析任务详情"
          visible={taskDetailModalVisible}
          onCancel={() => setTaskDetailModalVisible(false)}
          footer={null}
          width={800}
        >
          {selectedTask && (
            <Descriptions column={2} variant="bordered">
              <Descriptions.Item label="任务ID">{selectedTask.task_id}</Descriptions.Item>
              <Descriptions.Item label="视频名称">{selectedTask.video_name}</Descriptions.Item>
              <Descriptions.Item label="分析状态">
                <Badge status={selectedTask.analysis_status === 'completed' ? 'success' : 'processing'} text={selectedTask.analysis_status} />
              </Descriptions.Item>
              <Descriptions.Item label="预警数量">
                <Tag color={selectedTask.total_alerts > 0 ? 'red' : 'green'}>
                  {selectedTask.total_alerts}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="分析帧数">{selectedTask.total_frames_analyzed}</Descriptions.Item>
              <Descriptions.Item label="耗时">{selectedTask.analysis_duration?.toFixed(1)}秒</Descriptions.Item>
              <Descriptions.Item label="创建时间">{dayjs(selectedTask.created_at).format('YYYY-MM-DD HH:mm:ss')}</Descriptions.Item>
              <Descriptions.Item label="完成时间">
                {selectedTask.completed_at ? dayjs(selectedTask.completed_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="模板统计" span={2}>
                {selectedTask.results_summary?.map((summary, index) => (
                  <Tag key={index} style={{ marginBottom: 4 }}>
                    {summary.template_name}: {summary.alerts_count}预警 (置信度: {summary.avg_confidence?.toFixed(3)})
                  </Tag>
                ))}
              </Descriptions.Item>
            </Descriptions>
          )}
        </Modal>

        {/* 帧结果弹窗 */}
        <Modal
          title={`任务 ${selectedTaskId} - 帧分析结果`}
          visible={frameResultModalVisible}
          onCancel={() => setFrameResultModalVisible(false)}
          footer={null}
          width={1200}
        >
          <Table
            columns={frameColumns}
            dataSource={frameResultsData}
            rowKey={(record) => `${record.frame_index}`}
            loading={loading}
            pagination={{ pageSize: 20, showSizeChanger: false }}
            size="small"
          />
        </Modal>
      </Content>
    </Layout>
  );
};

export default AnalysisResultsPage;