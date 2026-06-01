import React, { useState, useEffect, useMemo } from 'react'
import {
  Card,
  Space,
  Typography,
  Row,
  Col,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  Modal,
  Empty,
  Pagination,
  Tooltip,
  Tag,
  ConfigProvider
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  VideoCameraOutlined
} from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import zhCN from 'antd/locale/zh_CN'
import 'dayjs/locale/zh-cn'
import BoundingBoxOverlay from '../components/alert/BoundingBoxOverlay'
import AlertClipPlayer from '../components/alert/AlertClipPlayer'
import { useAlerts, type Alert } from '../hooks/useAlerts'

// 设置 dayjs 为中文
dayjs.locale('zh-cn')

const { Text } = Typography
const { RangePicker } = DatePicker
const { Option } = Select

// AI 模型配置接口（/api/ai-models/configs/ 返回的精简形态）
interface AIModelConfigItem {
  name?: string
}

// 已提交的筛选条件（与 Form 的临时输入隔离，确保只有点"查询"后才触发 SWR）
interface SubmittedFilters {
  algorithm_name?: string
  camera_name?: string
  startTime: Dayjs
  endTime: Dayjs
}

// 默认时间范围：最近一周
const defaultRange = (): [Dayjs, Dayjs] => [dayjs().subtract(7, 'day'), dayjs()]

const PAGE_SIZE = 8

const AlertsPage: React.FC = () => {
  const [form] = Form.useForm()

  // 已提交的筛选条件（驱动 useAlerts 请求）
  const [submitted, setSubmitted] = useState<SubmittedFilters>(() => {
    const [s, e] = defaultRange()
    return { startTime: s, endTime: e }
  })

  // 表单里临时编辑的时间范围（未点"查询"前不下发到 hook）
  const [timeRange, setTimeRange] = useState<[Dayjs, Dayjs]>(defaultRange)

  const [currentPage, setCurrentPage] = useState(1)
  const [algorithmOptions, setAlgorithmOptions] = useState<string[]>([])

  // Modal/预览相关
  const [previewVisible, setPreviewVisible] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)

  // 通过 hook 统一取数 —— SWR 订阅了 clip_ready / clip_failed 事件，
  // 收到消息后会 patch 对应 alert 的 clip_url / clip_status，触发本页重渲染。
  const { alerts, total, isLoading, refresh } = useAlerts({
    size: PAGE_SIZE,
    page: currentPage,
    algorithm_name: submitted.algorithm_name,
    camera_name: submitted.camera_name,
    start_time: submitted.startTime.toISOString(),
    end_time: submitted.endTime.toISOString()
  })

  // 加载算法名称选项（从 ai_model_configs 表）
  useEffect(() => {
    const loadAlgorithmOptions = async () => {
      try {
        const response = await fetch('/api/ai-models/configs/')
        const data: unknown = await response.json()
        if (Array.isArray(data)) {
          const names = (data as AIModelConfigItem[])
            .map((item) => item.name)
            .filter((n): n is string => typeof n === 'string' && n.length > 0)
          setAlgorithmOptions(Array.from(new Set(names)))
        }
      } catch (error) {
        console.error('加载算法选项失败:', error)
      }
    }
    loadAlgorithmOptions()
  }, [])

  // 查询：把 Form 当前值 + timeRange 提交到 submitted，并重置到第 1 页
  const handleSearch = () => {
    const values = form.getFieldsValue() as {
      algorithm_name?: string
      camera_name?: string
    }
    setSubmitted({
      algorithm_name: values.algorithm_name || undefined,
      camera_name: values.camera_name || undefined,
      startTime: timeRange[0],
      endTime: timeRange[1]
    })
    setCurrentPage(1)
  }

  // 重置：清空表单 + 时间范围，回到默认一周
  const handleReset = () => {
    form.resetFields()
    const [s, e] = defaultRange()
    setTimeRange([s, e])
    setSubmitted({ startTime: s, endTime: e })
    setCurrentPage(1)
  }

  // 分页切换
  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  // 打开详情 Modal
  const handleImagePreview = (alert: Alert) => {
    setSelectedAlert(alert)
    setPreviewVisible(true)
  }

  // 格式化显示名称（相机名称或视频名称）
  const getDisplayName = (alert: Alert): string => {
    return alert.camera_name || alert.video_name || '未知来源'
  }

  // 选中告警的图片 URL（Modal 内 BoundingBoxOverlay 和 AlertClipPlayer.poster 共用）
  const selectedImageUrl = selectedAlert?.image_path ?? ''

  // detection_details 可能是任意形态，渲染前先格式化
  const detectionDetailsText = useMemo(() => {
    if (!selectedAlert?.detection_details) return null
    try {
      return JSON.stringify(selectedAlert.detection_details, null, 2)
    } catch {
      return String(selectedAlert.detection_details)
    }
  }, [selectedAlert])

  // 渲染告警卡片
  const renderAlertCard = (alert: Alert) => (
    <Col xs={24} sm={12} md={12} lg={6} key={alert.id}>
      <Card
        hoverable
        cover={
          alert.image_path ? (
            <div style={{ height: 200, overflow: 'hidden' }}>
              <BoundingBoxOverlay
                imageUrl={alert.image_path}
                detectionObjects={alert.detection_objects}
                imageSize={alert.image_size}
                width="100%"
                height="100%"
                objectFit="cover"
                showLabels={false}
                onClick={() => handleImagePreview(alert)}
              />
            </div>
          ) : (
            <div
              style={{
                height: 200,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                background: '#f5f5f5',
                color: '#999'
              }}
            >
              暂无图片
            </div>
          )
        }
        actions={[
          <Tooltip title="查看详情" key="view">
            <EyeOutlined onClick={() => handleImagePreview(alert)} />
          </Tooltip>
        ]}
        size="small"
      >
        <Card.Meta
          title={
            <div style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: 4 }}>
              <Text strong ellipsis style={{ flex: 1 }}>
                {alert.algorithm_name || '未知算法'}
              </Text>
              {alert.clip_status === 'ready' && alert.clip_url && (
                <Tooltip title="含视频片段">
                  <VideoCameraOutlined style={{ color: '#1677ff' }} />
                </Tooltip>
              )}
            </div>
          }
          description={
            <div style={{ fontSize: '11px', lineHeight: '16px' }}>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">时间：</Text>
                <Text>{dayjs(alert.timestamp).format('MM-DD HH:mm:ss')}</Text>
              </div>
              <div style={{ marginBottom: 4 }}>
                <Text type="secondary">来源：</Text>
                <Text ellipsis title={getDisplayName(alert)}>
                  {getDisplayName(alert)}
                </Text>
              </div>
              {typeof alert.confidence === 'number' && (
                <div>
                  <Text type="secondary">置信度：</Text>
                  <Tag
                    color={
                      alert.confidence > 0.8
                        ? 'red'
                        : alert.confidence > 0.6
                        ? 'orange'
                        : 'blue'
                    }
                  >
                    {(alert.confidence * 100).toFixed(1)}%
                  </Tag>
                </div>
              )}
            </div>
          }
        />
      </Card>
    </Col>
  )

  return (
    <div style={{ padding: '24px' }}>
      {/* 查询选项 */}
      <Card title="查询条件" style={{ marginBottom: 24 }}>
        <Form form={form} onFinish={handleSearch}>
          <Row gutter={16} align="bottom">
            <Col xs={24} sm={12} md={6}>
              <Form.Item name="algorithm_name" label="算法名称" style={{ marginBottom: 16 }}>
                <Select
                  placeholder="选择算法"
                  allowClear
                  showSearch
                  optionFilterProp="children"
                  style={{ width: '100%' }}
                >
                  {algorithmOptions.map((algorithm) => (
                    <Option key={algorithm} value={algorithm}>
                      {algorithm}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Form.Item name="camera_name" label="相机名称" style={{ marginBottom: 16 }}>
                <Input placeholder="输入相机名称" allowClear />
              </Form.Item>
            </Col>

            <Col xs={24} sm={16} md={8}>
              <Form.Item label="时间范围" style={{ marginBottom: 16 }}>
                <ConfigProvider locale={zhCN}>
                  <RangePicker
                    value={timeRange}
                    onChange={(dates) => {
                      if (dates && dates[0] && dates[1]) {
                        setTimeRange([dates[0], dates[1]])
                      }
                    }}
                    showTime
                    format="YYYY-MM-DD HH:mm:ss"
                    style={{ width: '100%' }}
                    placeholder={['开始时间', '结束时间']}
                  />
                </ConfigProvider>
              </Form.Item>
            </Col>

            <Col xs={24} sm={8} md={4}>
              <Form.Item style={{ marginBottom: 16 }}>
                <Space>
                  <Button
                    type="primary"
                    icon={<SearchOutlined />}
                    loading={isLoading}
                    onClick={handleSearch}
                  >
                    查询
                  </Button>
                  <Button icon={<ReloadOutlined />} onClick={handleReset}>
                    重置
                  </Button>
                  <Button onClick={() => refresh()}>刷新</Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      {/* 下半部分：告警列表 */}
      <Card
        title={`告警列表 (共${total}条)`}
        extra={
          <Text type="secondary">每页显示{PAGE_SIZE}条，每行4张图片</Text>
        }
      >
        {alerts.length === 0 ? (
          <Empty
            description={isLoading ? '加载中…' : '暂无告警数据'}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            style={{ padding: '60px 0' }}
          />
        ) : (
          <>
            <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
              {alerts.map(renderAlertCard)}
            </Row>

            <div style={{ textAlign: 'center' }}>
              <Pagination
                current={currentPage}
                total={total}
                pageSize={PAGE_SIZE}
                onChange={handlePageChange}
                showSizeChanger={false}
                showQuickJumper
                showTotal={(t, range) => `第 ${range[0]}-${range[1]} 条，共 ${t} 条`}
              />
            </div>
          </>
        )}
      </Card>

      {/* 图片预览弹窗 */}
      <Modal
        title="告警详情"
        open={previewVisible}
        onCancel={() => {
          setPreviewVisible(false)
          setSelectedAlert(null)
        }}
        footer={null}
        width="60vw"
        centered
        style={{ minWidth: '800px' }}
      >
        {selectedAlert && (
          <div>
            <Row gutter={24}>
              <Col span={16}>
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <BoundingBoxOverlay
                    imageUrl={selectedImageUrl}
                    detectionObjects={selectedAlert.detection_objects}
                    imageSize={selectedAlert.image_size}
                    width="100%"
                    height="500px"
                    objectFit="contain"
                    showLabels
                  />
                  {/* Week 4：告警视频片段（告警前 5s + 后 10s） */}
                  <AlertClipPlayer
                    clipUrl={selectedAlert.clip_url}
                    clipStatus={selectedAlert.clip_status}
                    poster={selectedAlert.image_path}
                    width="100%"
                    height={400}
                  />
                </Space>
              </Col>
              <Col span={8}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text strong>告警时间：</Text>
                    <Text>{dayjs(selectedAlert.timestamp).format('YYYY-MM-DD HH:mm:ss')}</Text>
                  </div>
                  <div>
                    <Text strong>算法名称：</Text>
                    <Text>{selectedAlert.algorithm_name || '未知算法'}</Text>
                  </div>
                  <div>
                    <Text strong>来源：</Text>
                    <Text>{getDisplayName(selectedAlert)}</Text>
                  </div>
                  <div>
                    <Text strong>告警类型：</Text>
                    <Text>{selectedAlert.alert_type || '—'}</Text>
                  </div>
                  {typeof selectedAlert.confidence === 'number' && (
                    <div>
                      <Text strong>置信度：</Text>
                      <Tag
                        color={
                          selectedAlert.confidence > 0.8
                            ? 'red'
                            : selectedAlert.confidence > 0.6
                            ? 'orange'
                            : 'blue'
                        }
                      >
                        {(selectedAlert.confidence * 100).toFixed(1)}%
                      </Tag>
                    </div>
                  )}
                  {selectedAlert.description && (
                    <div>
                      <Text strong>告警描述：</Text>
                      <Text>{selectedAlert.description}</Text>
                    </div>
                  )}
                  {detectionDetailsText && (
                    <div>
                      <Text strong>检测详情：</Text>
                      <div
                        style={{
                          background: '#f5f5f5',
                          padding: 8,
                          borderRadius: 4,
                          marginTop: 4,
                          fontSize: '12px'
                        }}
                      >
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                          {detectionDetailsText}
                        </pre>
                      </div>
                    </div>
                  )}
                </Space>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default AlertsPage
