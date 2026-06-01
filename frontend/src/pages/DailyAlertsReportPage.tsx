/**
 * 每日预警报表页面
 * 独立页面，用于企业微信推送链接
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Form,
  Select,
  DatePicker,
  Table,
  Image,
  Tag,
  Space,
  Row,
  Col,
  Typography,
  message,
  Spin
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs, { Dayjs } from 'dayjs';
import axios from 'axios';

const { Title, Text } = Typography;
const { Option } = Select;

// 使用相对路径，适配公网和内网访问
// 浏览器会自动使用当前访问的域名和端口
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// 筛选选项接口
interface FilterOptions {
  algorithm_names: string[];
  camera_names: string[];
}

// 告警记录接口
interface AlertRecord {
  id: string;
  camera_name: string;
  algorithm_name: string;
  image_url: string;
  confidence: number;
  description: string;
  created_at: string;
}

// 告警查询响应接口
interface AlertsResponse {
  total: number;
  page: number;
  page_size: number;
  records: AlertRecord[];
}

const DailyAlertsReportPage: React.FC = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [filterOptions, setFilterOptions] = useState<FilterOptions>({
    algorithm_names: [],
    camera_names: []
  });
  const [alertsData, setAlertsData] = useState<AlertsResponse>({
    total: 0,
    page: 1,
    page_size: 5,
    records: []
  });
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 5;

  // 加载筛选选项
  useEffect(() => {
    loadFilterOptions();
  }, []);

  // 首次加载时查询当天数据
  useEffect(() => {
    loadAlerts();
  }, []);

  const loadFilterOptions = async () => {
    try {
      const response = await axios.get<FilterOptions>(
        `${API_BASE_URL}/api/daily-alerts-report/filter-options`
      );
      setFilterOptions(response.data);
    } catch (error) {
      console.error('加载筛选选项失败:', error);
      message.error('加载筛选选项失败');
    }
  };

  const loadAlerts = async (page: number = 1) => {
    setLoading(true);
    try {
      const values = form.getFieldsValue();
      const params: any = {
        page,
        page_size: pageSize
      };

      // 添加筛选条件
      if (values.algorithm_name) {
        params.algorithm_name = values.algorithm_name;
      }
      if (values.camera_name) {
        params.camera_name = values.camera_name;
      }
      if (values.date) {
        params.date_str = values.date.format('YYYY-MM-DD');
      }

      const response = await axios.get<AlertsResponse>(
        `${API_BASE_URL}/api/daily-alerts-report/alerts`,
        { params }
      );

      setAlertsData(response.data);
      setCurrentPage(page);
    } catch (error) {
      console.error('查询告警数据失败:', error);
      message.error('查询告警数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    setCurrentPage(1);
    loadAlerts(1);
  };

  const handlePageChange = (page: number) => {
    loadAlerts(page);
  };

  const handleReset = () => {
    form.resetFields();
    setCurrentPage(1);
    loadAlerts(1);
  };

  // 表格列定义
  const columns: ColumnsType<AlertRecord> = [
    {
      title: '相机名称',
      dataIndex: 'camera_name',
      key: 'camera_name',
      width: 150,
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '算法名称',
      dataIndex: 'algorithm_name',
      key: 'algorithm_name',
      width: 150,
      render: (text: string) => (
        <Tag color="blue">{text}</Tag>
      )
    },
    {
      title: '预警图片',
      dataIndex: 'image_url',
      key: 'image_url',
      width: 200,
      render: (url: string) => {
        if (!url) return <Text type="secondary">无图片</Text>;

        // 处理图片URL
        let imageUrl = url;
        if (url.startsWith('/')) {
          imageUrl = `${API_BASE_URL}${url}`;
        } else if (url.startsWith('http://localhost') || url.startsWith('http://127.0.0.1')) {
          imageUrl = url.replace(/https?:\/\/(localhost|127\.0\.0\.1):\d+/, API_BASE_URL);
        }

        return (
          <Image
            src={imageUrl}
            alt="预警图片"
            width={120}
            height={80}
            style={{ objectFit: 'cover', cursor: 'pointer' }}
            preview={{
              mask: '点击查看大图'
            }}
          />
        );
      }
    },
    {
      title: '置信度',
      dataIndex: 'confidence',
      key: 'confidence',
      width: 100,
      render: (value: number) => {
        const percent = (value * 100).toFixed(1);
        let color = 'default';
        if (value >= 0.8) color = 'success';
        else if (value >= 0.6) color = 'warning';
        else color = 'error';

        return <Tag color={color}>{percent}%</Tag>;
      }
    },
    {
      title: 'AI描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => (
        <Text style={{ fontSize: '13px' }}>{text || '无描述'}</Text>
      )
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => {
        try {
          return dayjs(text).format('YYYY-MM-DD HH:mm:ss');
        } catch {
          return text;
        }
      }
    }
  ];

  return (
    <div style={{
      padding: '24px',
      minHeight: '100vh',
      background: '#f0f2f5'
    }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* 页面标题 */}
        <Card>
          <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
            每日预警报表
          </Title>
          <Text type="secondary">查看和筛选每日告警数据</Text>
        </Card>

        {/* 筛选条件 */}
        <Card title="筛选条件">
          <Form
            form={form}
            layout="vertical"
            initialValues={{
              date: dayjs() // 默认当天
            }}
            onFinish={handleSearch}
          >
            <Row gutter={16}>
              <Col xs={24} sm={12} md={6}>
                <Form.Item
                  label="算法名称"
                  name="algorithm_name"
                >
                  <Select
                    placeholder="请选择算法"
                    allowClear
                    showSearch
                    optionFilterProp="children"
                  >
                    {filterOptions.algorithm_names.map(name => (
                      <Option key={name} value={name}>
                        {name}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>

              <Col xs={24} sm={12} md={6}>
                <Form.Item
                  label="相机名称"
                  name="camera_name"
                >
                  <Select
                    placeholder="请选择相机"
                    allowClear
                    showSearch
                    optionFilterProp="children"
                  >
                    {filterOptions.camera_names.map(name => (
                      <Option key={name} value={name}>
                        {name}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>

              <Col xs={24} sm={12} md={6}>
                <Form.Item
                  label="日期"
                  name="date"
                >
                  <DatePicker
                    style={{ width: '100%' }}
                    format="YYYY-MM-DD"
                    placeholder="选择日期"
                  />
                </Form.Item>
              </Col>

              <Col xs={24} sm={12} md={6}>
                <Form.Item label=" ">
                  <Space>
                    <button
                      type="submit"
                      style={{
                        padding: '4px 15px',
                        background: '#1890ff',
                        color: 'white',
                        border: 'none',
                        borderRadius: '2px',
                        cursor: 'pointer'
                      }}
                    >
                      查询
                    </button>
                    <button
                      type="button"
                      onClick={handleReset}
                      style={{
                        padding: '4px 15px',
                        background: 'white',
                        border: '1px solid #d9d9d9',
                        borderRadius: '2px',
                        cursor: 'pointer'
                      }}
                    >
                      重置
                    </button>
                  </Space>
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </Card>

        {/* 告警列表 */}
        <Card
          title={`告警列表 (共 ${alertsData.total} 条)`}
        >
          <Spin spinning={loading}>
            <Table
              columns={columns}
              dataSource={alertsData.records}
              rowKey="id"
              pagination={{
                current: currentPage,
                pageSize: pageSize,
                total: alertsData.total,
                onChange: handlePageChange,
                showSizeChanger: false,
                showTotal: (total) => `共 ${total} 条记录`
              }}
              scroll={{ x: 1000 }}
            />
          </Spin>
        </Card>
      </Space>
    </div>
  );
};

export default DailyAlertsReportPage;
