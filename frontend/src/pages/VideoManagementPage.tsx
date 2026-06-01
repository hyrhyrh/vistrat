import React, { useState, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  message,
  Row,
  Col,
  Statistic,
  Upload
} from 'antd'
import {
  UploadOutlined,
  VideoCameraOutlined,
  CloudUploadOutlined,
  PlusOutlined
} from '@ant-design/icons'

import VideoSearchBar from '../components/video/VideoSearchBar'
import VideoListTable from '../components/video/VideoListTable'
import AlgorithmConfigModal from '../components/video/AlgorithmConfigModal'
import VideoPlayerModal from '../components/video/VideoPlayerModal'

const { TextArea } = Input
const { Option } = Select

interface VideoFile {
  id: string
  name: string
  original_filename: string
  file_path: string
  thumbnail_path?: string
  status: string
  tags: string[]
  analysis_progress: number
  file_size?: number
  duration?: number
  fps?: number
  width?: number
  height?: number
  created_at: string
  total_alerts: number
}

const VideoManagementPage: React.FC = () => {
  const [videos, setVideos] = useState<VideoFile[]>([])
  const [loading, setLoading] = useState(false)
  const [hasInitialized, setHasInitialized] = useState(false)
  const [uploadModalVisible, setUploadModalVisible] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [configModalVisible, setConfigModalVisible] = useState(false)
  const [playerModalVisible, setPlayerModalVisible] = useState(false)
  const [selectedVideo, setSelectedVideo] = useState<VideoFile | null>(null)
  const [playingVideoId, setPlayingVideoId] = useState<string | null>(null)
  
  const [statistics, setStatistics] = useState({
    total: 0,
    by_status: {},
    storage_usage_gb: 0
  })
  
  const [searchParams, setSearchParams] = useState({})
  const [uploadForm] = Form.useForm()
  const [editForm] = Form.useForm()

  useEffect(() => {
    if (!hasInitialized) {
      loadVideos()
      loadStatistics()
      setHasInitialized(true)
    }
  }, [])

  const loadVideos = async (params = {}) => {
    setLoading(true)
    try {
      // 过滤掉undefined和空值
      const filteredParams = Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null && value !== '')
        .reduce((acc, [key, value]) => ({ ...acc, [key]: value }), {})
      
      const queryParams = new URLSearchParams(filteredParams).toString()
      const response = await fetch(`/api/video-files/${queryParams ? '?' + queryParams : ''}`)
      const data = await response.json()
      setVideos(Array.isArray(data) ? data : [])
    } catch (error) {
      message.error('加载视频列表失败')
      setVideos([])
    } finally {
      setLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      const response = await fetch('/api/video-files/statistics/summary')
      const stats = await response.json()
      setStatistics(stats)
    } catch (error) {
      console.error('加载统计信息失败:', error)
    }
  }

  const handleSearch = (params: any) => {
    setSearchParams(params)
    loadVideos(params)
  }

  const handleReset = () => {
    setSearchParams({})
    loadVideos()
  }

  const handlePlay = async (video: VideoFile) => {
    try {
      setPlayingVideoId(video.id)
      message.loading({ content: '正在加载视频...', key: 'play-video', duration: 0 })

      // 模拟视频加载延迟（实际应用中可能需要预加载检查）
      await new Promise(resolve => setTimeout(resolve, 300))

      setSelectedVideo(video)
      setPlayerModalVisible(true)
      message.success({ content: '视频加载成功', key: 'play-video', duration: 2 })
    } catch (error) {
      message.error({ content: '视频加载失败，请重试', key: 'play-video', duration: 3 })
      console.error('播放视频失败:', error)
    } finally {
      setPlayingVideoId(null)
    }
  }

  const handleEdit = (video: VideoFile) => {
    setSelectedVideo(video)
    editForm.setFieldsValue({
      name: video.name,
      description: '',
      tags: video.tags
    })
    setEditModalVisible(true)
  }

  const handleDelete = async (videoId: string) => {
    try {
      const response = await fetch(`/api/video-files/${videoId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        message.success('视频删除成功')
        loadVideos(searchParams)
        loadStatistics()
      } else {
        throw new Error('删除失败')
      }
    } catch (error) {
      message.error('删除视频失败')
    }
  }

  const handleConfigure = (video: VideoFile) => {
    setSelectedVideo(video)
    setConfigModalVisible(true)
  }

  const handleConfigConfirm = (templateIds: string[]) => {
    loadVideos(searchParams)
    loadStatistics()
  }

  const [uploading, setUploading] = useState(false)
  
  const handleUploadSubmit = async (values: any) => {
    if (uploading) return // 防止重复提交
    
    console.log('Upload values:', values)
    setUploading(true)
    
    const formData = new FormData()
    
    // 获取上传的文件对象（使用fileList）
    let fileObj = null
    if (values.file && Array.isArray(values.file) && values.file.length > 0) {
      fileObj = values.file[0].originFileObj
    }
    
    if (!fileObj) {
      message.error('请选择要上传的文件')
      console.error('文件对象获取失败:', values.file)
      setUploading(false)
      return
    }
    
    formData.append('file', fileObj)
    if (values.name) formData.append('name', values.name)
    if (values.description) formData.append('description', values.description)
    if (values.tags && Array.isArray(values.tags)) formData.append('tags', values.tags.join(','))

    try {
      const response = await fetch('/api/video/upload', {
        method: 'POST',
        body: formData
      })
      
      if (response.ok) {
        message.success('视频上传成功')
        setUploadModalVisible(false)
        uploadForm.resetFields()
        loadVideos(searchParams)
        loadStatistics()
      } else {
        throw new Error('上传失败')
      }
    } catch (error) {
      message.error('上传视频失败')
    } finally {
      setUploading(false)
    }
  }

  const handleEditSubmit = async (values: any) => {
    if (!selectedVideo) return
    
    try {
      const response = await fetch(`/api/video-files/${selectedVideo.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(values)
      })
      
      if (response.ok) {
        message.success('视频信息更新成功')
        setEditModalVisible(false)
        editForm.resetFields()
        loadVideos(searchParams)
      } else {
        throw new Error('更新失败')
      }
    } catch (error) {
      message.error('更新视频信息失败')
    }
  }

  const statusCounts = statistics.by_status || {}

  return (
    <div style={{ padding: 24 }}>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="总视频数"
              value={statistics.total}
              prefix={<VideoCameraOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="分析中"
              value={statusCounts.analyzing || 0}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="已完成"
              value={statusCounts.completed || 0}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="存储使用"
              value={statistics.storage_usage_gb}
              suffix="GB"
              precision={2}
            />
          </Card>
        </Col>
      </Row>

      <Card>
        {/* 操作栏 */}
        <div style={{ marginBottom: 16 }}>
          <Space>
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => setUploadModalVisible(true)}
            >
              上传视频
            </Button>
{/*             <Button  */}
{/*               icon={<CloudUploadOutlined />} */}
{/*             > */}
{/*               批量导入 */}
{/*             </Button> */}
          </Space>
        </div>

        {/* 搜索栏 */}
        <VideoSearchBar
          onSearch={handleSearch}
          onReset={handleReset}
          loading={loading}
        />

        {/* 视频列表表格 */}
        <VideoListTable
          videos={videos}
          loading={loading}
          playingVideoId={playingVideoId}
          onPlay={handlePlay}
          onEdit={handleEdit}
          onDelete={handleDelete}
          onConfigure={handleConfigure}
        />

        {/* 编辑模态框 */}
        <Modal
          title="编辑视频信息"
          open={editModalVisible}
          onCancel={() => setEditModalVisible(false)}
          footer={null}
          width={600}
        >
          <Form
            form={editForm}
            layout="vertical"
            onFinish={handleEditSubmit}
          >
            <Form.Item
              name="name"
              label="视频名称"
              rules={[{ required: true, message: '请输入视频名称' }]}
            >
              <Input placeholder="输入视频名称" />
            </Form.Item>

            <Form.Item name="description" label="视频描述">
              <TextArea rows={3} placeholder="输入视频描述" />
            </Form.Item>

            <Form.Item name="tags" label="视频标签">
              <Select
                mode="tags"
                placeholder="输入标签（回车确认）"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit">
                  更新视频
                </Button>
                <Button onClick={() => setEditModalVisible(false)}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>

        {/* 算法配置模态框 */}
        <AlgorithmConfigModal
          open={configModalVisible}
          onCancel={() => setConfigModalVisible(false)}
          video={selectedVideo}
          onConfirm={handleConfigConfirm}
        />

        {/* 视频播放模态框 */}
        <VideoPlayerModal
          open={playerModalVisible}
          onCancel={() => setPlayerModalVisible(false)}
          video={selectedVideo}
        />

        {/* 上传视频模态框 */}
        <Modal
          title="上传视频"
          open={uploadModalVisible}
          onCancel={() => setUploadModalVisible(false)}
          footer={null}
          width={600}
        >
          <Form
            form={uploadForm}
            layout="vertical"
            onFinish={handleUploadSubmit}
          >
            <Form.Item
              name="file"
              label="选择视频文件"
              valuePropName="fileList"
              getValueFromEvent={(e) => {
                if (Array.isArray(e)) return e
                return e?.fileList
              }}
              rules={[{ required: true, message: '请选择视频文件' }]}
            >
              <Upload
                beforeUpload={() => false}
                maxCount={1}
                accept="video/*"
              >
                <Button icon={<UploadOutlined />}>选择文件</Button>
              </Upload>
            </Form.Item>

            <Form.Item
              name="name"
              label="视频名称"
              rules={[{ required: true, message: '请输入视频名称' }]}
            >
              <Input placeholder="输入视频名称" />
            </Form.Item>

            <Form.Item name="description" label="视频描述">
              <TextArea rows={3} placeholder="输入视频描述" />
            </Form.Item>

            <Form.Item name="tags" label="视频标签">
              <Select
                mode="tags"
                placeholder="输入标签（回车确认）"
                style={{ width: '100%' }}
              />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button type="primary" htmlType="submit" loading={uploading}>
                  {uploading ? '上传中...' : '上传视频'}
                </Button>
                <Button onClick={() => setUploadModalVisible(false)} disabled={uploading}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  )
}

export default VideoManagementPage