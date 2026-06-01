import React, { useState, useEffect } from 'react'
import {
  Drawer,
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
  Image,
  Modal,
  Empty,
  message,
  Pagination,
  Tooltip,
  Tag,
  ConfigProvider
} from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  EyeOutlined,
  ClearOutlined
} from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'
import zhCN from 'antd/locale/zh_CN'
import 'dayjs/locale/zh-cn'

// 设置dayjs为中文
dayjs.locale('zh-cn')

const { Title, Text } = Typography
const { RangePicker } = DatePicker
const { Option } = Select

interface AlertRecord {
  id: string
  timestamp: string
  alert_type: string
  algorithm_name: string
  camera_name?: string
  video_name?: string
  image_path?: string
  confidence: number
  detection_details: any
}

interface SearchParams {
  algorithm_name?: string
  camera_name?: string
  video_id?: string
  stream_id?: string
  video_name?: string
  start_time?: string
  end_time?: string
  page: number
  size: number
}

interface AlertDrawerProps {
  open: boolean
  onClose: () => void
  sourceId?: string
  sourceName?: string
  sourceType: 'video' | 'stream'
}

const AlertDrawer: React.FC<AlertDrawerProps> = ({
  open,
  onClose,
  sourceId,
  sourceName,
  sourceType
}) => {
  const [form] = Form.useForm()
  const [alerts, setAlerts] = useState<AlertRecord[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(6) // 抽屉中每页6张图片
  const [algorithmOptions, setAlgorithmOptions] = useState<string[]>([])
  const [previewImage, setPreviewImage] = useState<string>('')
  const [previewVisible, setPreviewVisible] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<AlertRecord | null>(null)

  // 初始化时间范围为一周
  const [timeRange, setTimeRange] = useState<[Dayjs, Dayjs]>([
    dayjs().subtract(7, 'day'),
    dayjs()
  ])

  useEffect(() => {
    if (open) {
      // 清空之前的数据，避免显示残留数据
      setAlerts([])
      setTotal(0)
      setCurrentPage(1)

      loadAlgorithmOptions()
      handleSearch() // 抽屉打开时自动搜索
    } else {
      // 抽屉关闭时也清理状态
      setAlerts([])
      setTotal(0)
      setLoading(false)
    }
  }, [open, sourceId])

  useEffect(() => {
    if (open) {
      handleSearch()
    }
  }, [currentPage, open])

  // 加载算法名称选项（从ai_model_configs表）
  const loadAlgorithmOptions = async () => {
    try {
      const response = await fetch('/api/ai-models/configs/')
      const data = await response.json()
      if (Array.isArray(data)) {
        // 去重算法名称
        const uniqueAlgorithms = [...new Set(data.map((item: any) => item.name).filter(Boolean))]
        setAlgorithmOptions(uniqueAlgorithms)
      }
    } catch (error) {
      console.error('加载算法选项失败:', error)
    }
  }

  // 搜索告警记录
  const handleSearch = async (resetPage = false) => {
    if (resetPage) {
      setCurrentPage(1)
    }
    
    setLoading(true)
    // 搜索开始时立即清空数据，避免显示残留数据
    setAlerts([])
    setTotal(0)
    try {
      const values = form.getFieldsValue()
      const params: SearchParams = {
        page: resetPage ? 1 : currentPage,
        size: pageSize,
      }

      // 添加搜索条件
      if (values.algorithm_name) {
        params.algorithm_name = values.algorithm_name
      }
      
      // 根据源类型和sourceId设置精确过滤条件（优先级最高）
      if (sourceId) {
        if (sourceType === 'video') {
          params.video_id = sourceId  // 使用视频ID进行精确过滤
        } else if (sourceType === 'stream') {
          params.stream_id = sourceId  // 使用流ID进行精确过滤
        }
      }
      
      // 用户手动选择的相机名称过滤（仅在未设置sourceId时生效）
      if (values.camera_name && !sourceId) {
        params.camera_name = values.camera_name
      }
      
      // 处理时间范围
      const [startTime, endTime] = timeRange
      params.start_time = startTime.toISOString()
      params.end_time = endTime.toISOString()

      // 调用后端API查询ES数据
      const queryString = new URLSearchParams(
        Object.entries(params).reduce((acc, [key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            acc[key] = String(value)
          }
          return acc
        }, {} as Record<string, string>)
      ).toString()

      const response = await fetch(`/api/alerts/search?${queryString}`)
      const data = await response.json()
      
      if (data.success) {
        setAlerts(data.data || [])
        setTotal(data.total || 0)
      } else {
        message.error('查询告警数据失败')
        setAlerts([])
        setTotal(0)
      }
    } catch (error) {
      console.error('搜索告警失败:', error)
      message.error('搜索告警失败')
      setAlerts([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }

  // 重置搜索条件
  const handleReset = () => {
    form.resetFields()
    setTimeRange([dayjs().subtract(7, 'day'), dayjs()])
    setCurrentPage(1)
    handleSearch(true)
  }

  // 页面变化
  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  // 预览图片
  const handleImagePreview = (alert: AlertRecord) => {
    if (alert.image_path) {
      setPreviewImage(alert.image_path)
      setSelectedAlert(alert)
      setPreviewVisible(true)
    }
  }

  // 格式化显示名称（相机名称或视频名称）
  const getDisplayName = (alert: AlertRecord) => {
    return alert.camera_name || alert.video_name || '未知来源'
  }

  // 渲染告警卡片
  const renderAlertCard = (alert: AlertRecord) => (
    <Col xs={24} sm={12} md={12} lg={8} key={alert.id}>
      <Card
        hoverable
        cover={
          alert.image_path ? (
            <div style={{ height: 180, overflow: 'hidden' }}>
              <Image
                src={alert.image_path}
                alt="告警图片"
                style={{ 
                  width: '100%', 
                  height: '100%', 
                  objectFit: 'cover',
                  cursor: 'pointer'
                }}
                preview={false}
                onClick={() => handleImagePreview(alert)}
              />
            </div>
          ) : (
            <div 
              style={{ 
                height: 180, 
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
            <div style={{ fontSize: '12px' }}>
              <Text strong ellipsis>{alert.algorithm_name || '未知算法'}</Text>
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
              {alert.confidence && (
                <div>
                  <Text type="secondary">置信度：</Text>
                  <Tag color={alert.confidence > 0.8 ? 'red' : alert.confidence > 0.6 ? 'orange' : 'blue'}>
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

  // 关闭抽屉时重置状态
  const handleClose = () => {
    // 完全清理所有状态
    setAlerts([])
    setTotal(0)
    setCurrentPage(1)
    setLoading(false)
    setPreviewVisible(false)
    setPreviewImage('')
    setSelectedAlert(null)
    form.resetFields()
    setTimeRange([dayjs().subtract(7, 'day'), dayjs()])
    onClose()
  }

  return (
    <>
      <Drawer
        title={`查看告警 - ${sourceName || '未知来源'}`}
        placement="right"
        width={800}
        open={open}
        onClose={handleClose}
        destroyOnClose
      >
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          {/* 查询选项 */}
          <Card title="查询条件" style={{ marginBottom: 16 }} size="small">
            <Form 
              form={form} 
              onFinish={() => handleSearch(true)}
              size="small"
            >
              <Row gutter={12} align="bottom">
                <Col xs={24} sm={sourceId ? 24 : 12}>
                  <Form.Item 
                    name="algorithm_name" 
                    label="算法名称"
                    style={{ marginBottom: 12 }}
                  >
                    <Select 
                      placeholder="选择算法"
                      allowClear
                      showSearch
                      optionFilterProp="children"
                      style={{ width: '100%' }}
                    >
                      {algorithmOptions.map(algorithm => (
                        <Option key={algorithm} value={algorithm}>
                          {algorithm}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                
                {!sourceId && (
                  <Col xs={24} sm={12}>
                    <Form.Item 
                      name="camera_name" 
                      label="相机名称"
                      style={{ marginBottom: 12 }}
                    >
                      <Input 
                        placeholder="输入相机名称"
                        allowClear
                      />
                    </Form.Item>
                  </Col>
                )}
                
                <Col xs={24} sm={sourceId ? 24 : 12}>
                  <Form.Item
                    label="时间范围"
                    style={{ marginBottom: 12 }}
                  >
                    <ConfigProvider locale={zhCN}>
                      <RangePicker
                        value={timeRange}
                        onChange={(dates) => {
                          if (dates) {
                            setTimeRange([dates[0]!, dates[1]!])
                          }
                        }}
                        showTime
                        format="MM-DD HH:mm"
                        style={{ width: '100%' }}
                        size="small"
                        placeholder={['开始时间', '结束时间']}
                      />
                    </ConfigProvider>
                  </Form.Item>
                </Col>
                
                <Col xs={24}>
                  <Form.Item style={{ marginBottom: 12 }}>
                    <Space>
                      <Button
                        type="primary"
                        icon={<SearchOutlined />}
                        loading={loading}
                        onClick={() => handleSearch(true)}
                        size="small"
                      >
                        查询
                      </Button>
                      <Button
                        icon={<ReloadOutlined />}
                        onClick={handleReset}
                        size="small"
                      >
                        重置
                      </Button>
                    </Space>
                  </Form.Item>
                </Col>
              </Row>
            </Form>
          </Card>

          {/* 告警列表 */}
          <Card 
            title={`告警列表 (共${total}条)`}
            size="small"
            style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column' }}
          >
            {alerts.length === 0 ? (
              <Empty 
                description="暂无告警数据"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
              />
            ) : (
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Row gutter={[12, 12]} style={{ flex: 1 }}>
                  {alerts.map(renderAlertCard)}
                </Row>
                
                <div style={{ textAlign: 'center', marginTop: 16, paddingTop: 16, borderTop: '1px solid #f0f0f0' }}>
                  <Pagination
                    current={currentPage}
                    total={total}
                    pageSize={pageSize}
                    onChange={handlePageChange}
                    showSizeChanger={false}
                    showQuickJumper
                    showTotal={(total, range) => 
                      `第 ${range[0]}-${range[1]} 条，共 ${total} 条`
                    }
                    size="small"
                  />
                </div>
              </div>
            )}
          </Card>
        </div>
      </Drawer>

      {/* 图片预览弹窗 */}
      <Modal
        title="告警详情"
        open={previewVisible}
        onCancel={() => {
          setPreviewVisible(false)
          setPreviewImage('')
          setSelectedAlert(null)
        }}
        footer={null}
        width="60vw"
        centered
        style={{ minWidth: '700px' }}
      >
        {selectedAlert && (
          <div>
            <Row gutter={24}>
              <Col span={16}>
                <Image
                  src={previewImage}
                  alt="告警图片"
                  style={{ width: '100%', maxHeight: '400px', objectFit: 'contain' }}
                />
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
                    <Text>{selectedAlert.alert_type}</Text>
                  </div>
                  {selectedAlert.confidence && (
                    <div>
                      <Text strong>置信度：</Text>
                      <Tag color={selectedAlert.confidence > 0.8 ? 'red' : selectedAlert.confidence > 0.6 ? 'orange' : 'blue'}>
                        {(selectedAlert.confidence * 100).toFixed(1)}%
                      </Tag>
                    </div>
                  )}
                  {selectedAlert.detection_details && (
                    <div>
                      <Text strong>检测详情：</Text>
                      <div style={{ 
                        background: '#f5f5f5', 
                        padding: 8, 
                        borderRadius: 4,
                        marginTop: 4,
                        fontSize: '12px',
                        maxHeight: '150px',
                        overflow: 'auto'
                      }}>
                        <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                          {JSON.stringify(selectedAlert.description, null, 2)}
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
    </>
  )
}

export default AlertDrawer