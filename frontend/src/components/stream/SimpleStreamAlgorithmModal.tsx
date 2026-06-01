import React, { useState, useEffect, useRef } from 'react'
import { 
  Modal, 
  Form, 
  Select, 
  Button, 
  Space, 
  Card, 
  Typography,
  message,
  Spin,
  Badge,
  Alert,
  Result,
  Descriptions,
  Steps,
  Divider,
  Row,
  Col,
  TimePicker,
  Checkbox,
  InputNumber,
  Switch
} from 'antd'
import { SettingOutlined, CheckCircleOutlined, PlayCircleOutlined, DeleteOutlined, CameraOutlined, ClockCircleOutlined, PlusOutlined, MinusCircleOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

const { Option } = Select
const { Title, Text } = Typography

interface AIAlgorithm {
  id: string
  name: string
  description: string
  provider: string
  model_name: string
  category: string
  status: string
  tags: string[]
}

// ROI区域类型定义
interface ROIRectangle {
  x: number
  y: number
  width: number
  height: number
}

interface ROIPolygon {
  points: Array<{x: number, y: number}>
}

interface ROIRegion {
  id: string
  type: 'rectangle' | 'polygon'
  name: string
  data: ROIRectangle | ROIPolygon
}

interface SimpleStreamAlgorithmModalProps {
  open: boolean
  onCancel: () => void
  stream: any
  onConfirm: () => void
}

const SimpleStreamAlgorithmModal: React.FC<SimpleStreamAlgorithmModalProps> = ({
  open,
  onCancel,
  stream,
  onConfirm
}) => {
  const [form] = Form.useForm()
  const [algorithms, setAlgorithms] = useState<AIAlgorithm[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedAlgorithms, setSelectedAlgorithms] = useState<string[]>([])
  const [currentConfiguredAlgorithms, setCurrentConfiguredAlgorithms] = useState<string[]>([])
  const [isConfigured, setIsConfigured] = useState(false)
  
  // ROI配置状态 - 改为每个算法独立的ROI配置
  const [algorithmROIs, setAlgorithmROIs] = useState<{[algorithmId: string]: ROIRegion | null}>({})
  const [currentSnapshot, setCurrentSnapshot] = useState<string | null>(null)
  const [selectedAlgorithmForROI, setSelectedAlgorithmForROI] = useState<string | null>(null)
  
  // ROI绘制状态
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isDrawing, setIsDrawing] = useState(false)
  const [startPoint, setStartPoint] = useState<{x: number, y: number} | null>(null)
  const [imageSize, setImageSize] = useState<{width: number, height: number}>({width: 0, height: 0})
  const [scaleFactor, setScaleFactor] = useState<{x: number, y: number}>({x: 1, y: 1})
  
  // ROI绘制模式和多边形状态
  const [roiDrawMode, setRoiDrawMode] = useState<'rectangle' | 'polygon'>('rectangle')
  const [currentPolygon, setCurrentPolygon] = useState<Array<{x: number, y: number}>>([])
  const [isDrawingPolygon, setIsDrawingPolygon] = useState(false)
  
  // 时间配置状态
  const [scheduleConfig, setScheduleConfig] = useState<{
    [algorithmId: string]: {
      enabled: boolean
      timeRanges: Array<{
        startTime: string
        endTime: string
        days: number[]
      }>
    }
  }>({})
  const [currentStep, setCurrentStep] = useState<'algorithm' | 'roi' | 'schedule' | 'ready' | 'analyzing'>('algorithm')

  useEffect(() => {
    if (open && stream) {
      // 首先重置状态
      setCurrentStep('algorithm')
      setIsConfigured(false)
      setSelectedAlgorithms([])
      setCurrentConfiguredAlgorithms([])
      setAlgorithmROIs({})
      setSelectedAlgorithmForROI(null)
      setCurrentSnapshot(null)
      setScheduleConfig({})
      setRoiDrawMode('rectangle')
      setCurrentPolygon([])
      setIsDrawingPolygon(false)
      form.resetFields()

      // 异步加载数据
      const initializeModal = async () => {
        await loadAIAlgorithms()
        await loadCurrentConfig()
      }

      initializeModal()
    }
  }, [open, stream?.id])

  const loadAIAlgorithms = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/ai-models/configs/')
      const data = await response.json()
      // 只显示激活状态的算法
      const activeAlgorithms = Array.isArray(data) ? data.filter(algo => algo.status === 'active') : []
      setAlgorithms(activeAlgorithms)
    } catch (error) {
      message.error('加载AI算法失败')
    } finally {
      setLoading(false)
    }
  }

  const loadCurrentConfig = async () => {
    if (!stream?.id) return
    
    try {
      const response = await fetch(`/api/video-streams/${stream.id}/analysis/templates`)
      const data = await response.json()
      
      console.log('[配置加载] 获取到的配置数据:', data)
      
      if (data.success && data.templates && data.templates.length > 0) {
        const currentAlgorithmIds = data.templates.map(t => t.template_id)
        console.log('[配置加载] 提取的算法ID:', currentAlgorithmIds)
        
        setCurrentConfiguredAlgorithms(currentAlgorithmIds)
        setSelectedAlgorithms(currentAlgorithmIds)
        form.setFieldsValue({ algorithm_ids: currentAlgorithmIds })
        setIsConfigured(true)
        setCurrentStep('ready')
        
        console.log('[配置加载] 状态已更新为ready，已选算法:', currentAlgorithmIds)
      } else {
        // 没有配置的算法
        console.log('[配置加载] 没有找到配置的算法')
        setCurrentConfiguredAlgorithms([])
        setSelectedAlgorithms([])
        setIsConfigured(false)
        setCurrentStep('algorithm')
      }
    } catch (error) {
      console.error('加载当前配置失败:', error)
    }
  }

  const handleSaveConfig = async () => {
    try {
      const values = await form.validateFields()
      const algorithmIds = values.algorithm_ids || selectedAlgorithms
      
      if (!algorithmIds.length) {
        message.warning('请选择至少一个分析算法')
        return
      }

      setLoading(true)

      // 为每个算法创建独立的分析任务
      let createdCount = 0
      let updatedCount = 0

      for (const algorithmId of algorithmIds) {
        try {
          // 构建任务配置数据
          const taskData = {
            stream_id: stream.id,
            algorithm_config_id: algorithmId,
            task_name: `${stream.name}_${algorithmId}_分析任务`,
            time_config: {
              enabled: scheduleConfig[algorithmId]?.enabled || false,
              time_ranges: scheduleConfig[algorithmId]?.timeRanges || [
                {
                  start_time: '07:00',
                  end_time: '18:00',
                  days: [1,2,3,4,5,6,0]
                }
              ],
              timezone: 'Asia/Shanghai'
            },
            roi_config: {
              enabled: Boolean(algorithmROIs[algorithmId]),
              regions: algorithmROIs[algorithmId] ? [algorithmROIs[algorithmId]!] : [],
              image_info: currentSnapshot ? {
                snapshot_url: currentSnapshot,
                width: imageSize.width,
                height: imageSize.height
              } : null
            },
            priority: 1,
            confidence_threshold: 0.7,
            analysis_interval: 10,
            auto_recover: true
          }

          console.log('配置任务:', taskData)

          // 调用任务创建/更新API
          const response = await fetch('/api/stream-tasks/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
          })

          if (response.ok) {
            const result = await response.json()
            // 根据operation_type统计创建和更新数量
            if (result.operation_type === 'updated') {
              updatedCount++
            } else {
              createdCount++
            }
          } else {
            const errorData = await response.json()
            const errorMsg = errorData.detail || errorData.message || '未知错误'
            console.error(`配置任务失败 ${algorithmId}:`, errorMsg)

            // 显示具体的错误信息
            if (response.status === 404) {
              message.error(`视频流或算法不存在，请刷新后重试`)
            } else if (response.status >= 500) {
              message.error(`服务器错误：${errorMsg}`)
            } else {
              message.error(`配置失败：${errorMsg}`)
            }
          }

        } catch (error: any) {
          console.error(`处理算法 ${algorithmId} 时出错:`, error)
          // 网络错误或其他异常
          if (error.name === 'TypeError' && error.message.includes('fetch')) {
            message.error('网络连接失败，请检查网络后重试')
          } else {
            message.error(`处理失败：${error.message || '未知错误'}`)
          }
        }
      }

      const totalSuccess = createdCount + updatedCount
      if (totalSuccess > 0) {
        // 根据创建和更新数量显示不同的提示
        if (createdCount > 0 && updatedCount > 0) {
          message.success(`任务配置成功：新建 ${createdCount} 个，更新 ${updatedCount} 个`)
        } else if (updatedCount > 0) {
          message.success(`成功更新 ${updatedCount} 个任务配置`)
        } else {
          message.success(`成功创建 ${createdCount} 个分析任务`)
        }

        setCurrentConfiguredAlgorithms(algorithmIds)
        setSelectedAlgorithms(algorithmIds)
        setIsConfigured(true)
        setCurrentStep('ready')
        onConfirm()
      } else {
        throw new Error('所有任务配置均失败，请查看详细错误信息')
      }

    } catch (error: any) {
      // 处理整体异常
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        message.error('网络连接失败，请检查网络后重试')
      } else {
        message.error(error.message || '配置任务失败，请重试')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSaveAndStart = async () => {
    try {
      await handleSaveConfig()
      if (currentStep === 'ready') {
        setCurrentStep('analyzing')
        await startAnalysis()
        setTimeout(() => {
          handleCancel()
        }, 2000)
      }
    } catch (error: any) {
      message.error(error.message || '操作失败')
    }
  }

  const startAnalysis = async () => {
    if (!stream?.id) return

    try {
      const response = await fetch(`/api/video-streams/${stream.id}/analysis/start`, {
        method: 'POST'
      })

      if (response.ok) {
        message.success('分析任务已启动')
      } else {
        // 读取响应体获取详细错误信息
        const errorData = await response.json()
        const errorMsg = errorData.error?.message || errorData.message || '启动分析失败'
        throw new Error(errorMsg)
      }
    } catch (error: any) {
      // 显示详细的错误信息
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        message.error('网络连接失败，请检查网络后重试')
      } else {
        // 如果错误信息太长，使用Modal显示
        const errorMsg = error.message || '启动分析失败'
        if (errorMsg.length > 100) {
          Modal.error({
            title: '启动分析失败',
            content: (
              <div style={{ maxHeight: '400px', overflow: 'auto', whiteSpace: 'pre-wrap' }}>
                {errorMsg}
              </div>
            ),
            width: 600
          })
        } else {
          message.error(errorMsg)
        }
      }
      throw error // 重新抛出以便上层处理
    }
  }

  const handleStartAnalysis = async () => {
    try {
      setLoading(true)
      setCurrentStep('analyzing')

      await startAnalysis()

      setTimeout(() => {
        handleCancel()
      }, 2000)
    } catch (error: any) {
      // startAnalysis已经显示了详细错误，这里只需恢复状态
      setCurrentStep('ready')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    setCurrentStep(currentConfiguredAlgorithms.length > 0 ? 'ready' : 'algorithm')
    setSelectedAlgorithms([...currentConfiguredAlgorithms])
    form.resetFields()
    onCancel()
  }

  const handleAlgorithmChange = (algorithmIds: string[]) => {
    setSelectedAlgorithms(algorithmIds)
    form.setFieldsValue({ algorithm_ids: algorithmIds })
  }

  // 获取MJPEG流快照
  const captureSnapshot = async () => {
    if (!stream?.id) return

    try {
      setLoading(true)
      console.log('[快照] 开始获取快照，stream:', stream)
      
      // 方法1: 尝试从当前正在播放的视频元素获取
      const videoElement = document.querySelector('img[src*="/api/mjpeg/stream/"]') as HTMLImageElement
      
      if (videoElement && videoElement.complete && videoElement.naturalWidth > 0) {
        console.log('[快照] 从现有视频元素获取快照')
        try {
          const canvas = document.createElement('canvas')
          const ctx = canvas.getContext('2d')
          
          canvas.width = videoElement.naturalWidth
          canvas.height = videoElement.naturalHeight
          ctx?.drawImage(videoElement, 0, 0)
          
          const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
          setCurrentSnapshot(dataUrl)
          console.log('[快照] 从现有元素获取成功')
          return
        } catch (canvasError) {
          console.warn('[快照] Canvas方法失败，尝试其他方法:', canvasError)
        }
      }
      
      // 方法2: 使用专门的快照API
      const timestamp = Date.now()
      const snapshotUrl = `/api/snapshot/stream/${encodeURIComponent(stream.stream_url)}?t=${timestamp}`
      console.log('[快照] 尝试获取新快照，URL:', snapshotUrl)
      
      return new Promise((resolve, reject) => {
        const img = new Image()
        
        // 设置超时
        const timeout = setTimeout(() => {
          console.error('[快照] 获取超时')
          reject(new Error('获取快照超时'))
        }, 10000)
        
        img.onload = () => {
          clearTimeout(timeout)
          console.log('[快照] 图片加载成功，尺寸:', img.width, 'x', img.height)
          
          try {
            const canvas = document.createElement('canvas')
            const ctx = canvas.getContext('2d')
            
            if (!ctx) {
              throw new Error('无法获取Canvas上下文')
            }
            
            canvas.width = img.width
            canvas.height = img.height
            ctx.drawImage(img, 0, 0)
            
            const dataUrl = canvas.toDataURL('image/jpeg', 0.8)
            setCurrentSnapshot(dataUrl)
            console.log('[快照] Canvas转换成功')
            resolve(dataUrl)
          } catch (canvasError) {
            console.error('[快照] Canvas处理失败:', canvasError)
            reject(canvasError)
          }
        }
        
        img.onerror = (error) => {
          clearTimeout(timeout)
          console.error('[快照] 图片加载失败:', error)
          message.error('获取视频快照失败：图片加载错误')
          reject(new Error('Failed to load snapshot image'))
        }
        
        img.onabort = () => {
          clearTimeout(timeout)
          console.error('[快照] 图片加载被中断')
          reject(new Error('Snapshot loading aborted'))
        }
        
        // 不设置crossOrigin，避免跨域问题
        img.src = snapshotUrl
        console.log('[快照] 开始加载图片...')
      })
    } catch (error) {
      console.error('[快照] 获取快照失败:', error)
      message.error('获取视频快照失败')
    } finally {
      setLoading(false)
    }
  }

  // 处理ROI区域变化
  const handleRoiChange = (roi: ROIRegion | null) => {
    if (selectedAlgorithmForROI) {
      setAlgorithmROIs(prev => ({
        ...prev,
        [selectedAlgorithmForROI]: roi
      }))
    }
  }

  // 获取当前选中算法的ROI
  const getCurrentROI = (): ROIRegion | null => {
    return selectedAlgorithmForROI ? (algorithmROIs[selectedAlgorithmForROI] || null) : null
  }

  // 绘制ROI区域到Canvas
  const drawROIRegions = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 清除画布
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 绘制当前选中算法的ROI区域
    const currentROI = getCurrentROI()
    if (currentROI) {
      if (currentROI.type === 'rectangle') {
        const rectData = currentROI.data as ROIRectangle
        const x = rectData.x * scaleFactor.x
        const y = rectData.y * scaleFactor.y
        const width = rectData.width * scaleFactor.x
        const height = rectData.height * scaleFactor.y

        // 绘制矩形边框
        ctx.strokeStyle = '#1890ff'
        ctx.lineWidth = 2
        ctx.strokeRect(x, y, width, height)

        // 绘制半透明填充
        ctx.fillStyle = 'rgba(24, 144, 255, 0.2)'
        ctx.fillRect(x, y, width, height)

        // 绘制区域标签
        ctx.fillStyle = '#1890ff'
        ctx.font = '12px Arial'
        ctx.fillText('矩形ROI', x + 4, y + 16)
      } else if (currentROI.type === 'polygon') {
        const polygonData = currentROI.data as ROIPolygon
        if (polygonData.points.length > 2) {
          // 绘制多边形
          ctx.beginPath()
          ctx.moveTo(polygonData.points[0].x * scaleFactor.x, polygonData.points[0].y * scaleFactor.y)
          for (let i = 1; i < polygonData.points.length; i++) {
            ctx.lineTo(polygonData.points[i].x * scaleFactor.x, polygonData.points[i].y * scaleFactor.y)
          }
          ctx.closePath()

          // 绘制边框
          ctx.strokeStyle = '#1890ff'
          ctx.lineWidth = 2
          ctx.stroke()

          // 绘制半透明填充
          ctx.fillStyle = 'rgba(24, 144, 255, 0.2)'
          ctx.fill()

          // 绘制区域标签
          ctx.fillStyle = '#1890ff'
          ctx.font = '12px Arial'
          const firstPoint = polygonData.points[0]
          ctx.fillText('多边形ROI', firstPoint.x * scaleFactor.x + 4, firstPoint.y * scaleFactor.y + 16)
        }
      }
    }

    // 绘制当前正在绘制的多边形
    if (isDrawingPolygon && currentPolygon.length > 0) {
      ctx.strokeStyle = '#ff4d4f'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 5])
      
      if (currentPolygon.length > 1) {
        ctx.beginPath()
        ctx.moveTo(currentPolygon[0].x * scaleFactor.x, currentPolygon[0].y * scaleFactor.y)
        for (let i = 1; i < currentPolygon.length; i++) {
          ctx.lineTo(currentPolygon[i].x * scaleFactor.x, currentPolygon[i].y * scaleFactor.y)
        }
        ctx.stroke()
      }
      
      // 绘制顶点
      currentPolygon.forEach((point, index) => {
        ctx.beginPath()
        ctx.arc(point.x * scaleFactor.x, point.y * scaleFactor.y, 4, 0, 2 * Math.PI)
        ctx.fillStyle = '#ff4d4f'
        ctx.fill()
      })
      
      ctx.setLineDash([])
    }
  }

  // 处理鼠标按下事件
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!currentSnapshot) return

    // 如果当前选中的算法已经有ROI区域，不允许再绘制
    const currentROI = getCurrentROI()
    if (currentROI) return

    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = (e.clientX - rect.left) / scaleFactor.x
    const y = (e.clientY - rect.top) / scaleFactor.y

    if (roiDrawMode === 'rectangle') {
      setIsDrawing(true)
      setStartPoint({ x, y })
    } else if (roiDrawMode === 'polygon') {
      // 多边形模式：点击添加顶点
      const newPoint = { x, y }
      
      if (!isDrawingPolygon) {
        // 开始绘制多边形
        setIsDrawingPolygon(true)
        setCurrentPolygon([newPoint])
      } else {
        // 检查是否点击在起始点附近（完成多边形）
        const firstPoint = currentPolygon[0]
        const distance = Math.sqrt(Math.pow(x - firstPoint.x, 2) + Math.pow(y - firstPoint.y, 2))
        
        if (distance < 20 && currentPolygon.length >= 3) {
          // 完成多边形绘制
          finishPolygon()
        } else {
          // 添加新顶点
          setCurrentPolygon(prev => [...prev, newPoint])
        }
      }
    }
  }

  // 完成多边形绘制
  const finishPolygon = () => {
    if (currentPolygon.length >= 3 && selectedAlgorithmForROI) {
      const newROI: ROIRegion = {
        id: `polygon_${Date.now()}`,
        type: 'polygon',
        name: '多边形ROI',
        data: { points: currentPolygon }
      }

      handleRoiChange(newROI)
      setCurrentPolygon([])
      setIsDrawingPolygon(false)
      message.success('多边形ROI区域已设置完成')
    }
  }

  // 处理鼠标移动事件
  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    // 重新绘制ROI区域
    drawROIRegions()
    
    if (roiDrawMode === 'rectangle' && isDrawing && startPoint && canvasRef.current) {
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')
      if (!ctx) return

      const rect = canvas.getBoundingClientRect()
      const currentX = (e.clientX - rect.left) / scaleFactor.x
      const currentY = (e.clientY - rect.top) / scaleFactor.y

      // 绘制当前正在绘制的矩形
      const width = currentX - startPoint.x
      const height = currentY - startPoint.y
      
      ctx.strokeStyle = '#ff4d4f'
      ctx.lineWidth = 2
      ctx.setLineDash([5, 5])
      ctx.strokeRect(
        startPoint.x * scaleFactor.x,
        startPoint.y * scaleFactor.y,
        width * scaleFactor.x,
        height * scaleFactor.y
      )
      ctx.setLineDash([])
    }
  }

  // 处理鼠标释放事件
  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (roiDrawMode !== 'rectangle' || !isDrawing || !startPoint) return

    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const endX = (e.clientX - rect.left) / scaleFactor.x
    const endY = (e.clientY - rect.top) / scaleFactor.y

    // 计算矩形区域
    const x = Math.min(startPoint.x, endX)
    const y = Math.min(startPoint.y, endY)
    const width = Math.abs(endX - startPoint.x)
    const height = Math.abs(endY - startPoint.y)

    // 只有当矩形足够大时才添加
    if (width > 10 && height > 10 && selectedAlgorithmForROI) {
      const newROI: ROIRegion = {
        id: `rectangle_${Date.now()}`,
        type: 'rectangle',
        name: '矩形ROI',
        data: {
          x: Math.round(x),
          y: Math.round(y),
          width: Math.round(width),
          height: Math.round(height)
        }
      }

      handleRoiChange(newROI)
      message.success('矩形ROI区域已设置完成')
    }

    setIsDrawing(false)
    setStartPoint(null)
  }

  // 当快照更新时重新计算尺寸和比例
  const handleImageLoad = (e: React.SyntheticEvent<HTMLImageElement>) => {
    const img = e.target as HTMLImageElement
    const canvas = canvasRef.current
    if (!canvas) return

    // 设置实际图片尺寸
    setImageSize({
      width: img.naturalWidth,
      height: img.naturalHeight
    })

    // 设置Canvas尺寸匹配显示的图片尺寸
    const displayWidth = img.offsetWidth
    const displayHeight = img.offsetHeight
    
    canvas.width = displayWidth
    canvas.height = displayHeight

    // 计算缩放因子
    setScaleFactor({
      x: displayWidth / img.naturalWidth,
      y: displayHeight / img.naturalHeight
    })

    // 重新绘制ROI区域
    setTimeout(drawROIRegions, 100)
  }

  // 删除ROI区域
  const deleteROIRegion = () => {
    if (selectedAlgorithmForROI) {
      handleRoiChange(null)
    }
    setCurrentPolygon([])
    setIsDrawingPolygon(false)
    message.success('已删除ROI区域')
  }

  // 重新绘制ROI区域
  const redrawROI = () => {
    if (selectedAlgorithmForROI) {
      handleRoiChange(null)
    }
    setCurrentPolygon([])
    setIsDrawingPolygon(false)
    message.info('请重新绘制ROI区域')
  }

  // 当ROI区域更新时重新绘制
  useEffect(() => {
    if (currentSnapshot) {
      drawROIRegions()
    }
  }, [algorithmROIs, selectedAlgorithmForROI, currentPolygon, isDrawingPolygon, scaleFactor])

  // 进入下一步
  const handleNextStep = () => {
    if (currentStep === 'algorithm') {
      if (selectedAlgorithms.length === 0) {
        message.warning('请选择至少一个AI算法')
        return
      }
      // 进入ROI配置步骤时,默认选中第一个算法
      if (selectedAlgorithms.length > 0 && !selectedAlgorithmForROI) {
        setSelectedAlgorithmForROI(selectedAlgorithms[0])
      }
      setCurrentStep('roi')
    } else if (currentStep === 'roi') {
      setCurrentStep('schedule')
    } else if (currentStep === 'schedule') {
      setCurrentStep('ready')
    }
  }

  // 返回上一步
  const handlePrevStep = () => {
    if (currentStep === 'roi') {
      setCurrentStep('algorithm')
    } else if (currentStep === 'schedule') {
      setCurrentStep('roi')
    } else if (currentStep === 'ready') {
      setCurrentStep('schedule')
    }
  }

  const getStatusColor = (status: string) => {
    const colors = {
      'active': '#52c41a',
      'draft': '#1890ff',
      'testing': '#fa8c16',
      'deprecated': '#ff4d4f'
    }
    return colors[status] || '#666666'
  }

  const getStatusName = (status: string) => {
    const names = {
      'active': '激活',
      'draft': '草稿',
      'testing': '测试中',
      'deprecated': '已弃用'
    }
    return names[status] || status
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 'algorithm':
        return (
          <Spin spinning={loading}>
            {stream && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={3} size="small">
                  <Descriptions.Item label="视频流名称">{stream.name}</Descriptions.Item>
                  <Descriptions.Item label="流类型">{stream.stream_type}</Descriptions.Item>
                  <Descriptions.Item label="状态">{stream.status}</Descriptions.Item>
                </Descriptions>
              </Card>
            )}

            <Form form={form} layout="vertical">
              <Form.Item
                name="algorithm_ids"
                label={<Title level={5}>选择AI分析算法</Title>}
                rules={[{ required: true, message: '请至少选择一个AI分析算法' }]}
              >
                <Select
                  mode="multiple"
                  placeholder="选择要使用的AI分析算法（可多选）"
                  style={{ width: '100%' }}
                  onChange={handleAlgorithmChange}
                >
                  {algorithms.map(algorithm => (
                    <Option key={algorithm.id} value={algorithm.id}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 'bold' }}>{algorithm.name}</div>
                          <div style={{ fontSize: 12, color: '#666' }}>
                            {algorithm.description}
                          </div>
                          <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                            {algorithm.provider} · {algorithm.model_name}
                          </div>
                        </div>
                        <Space>
                          {(algorithm.tags || []).slice(0, 2).map((tag, index) => (
                            <span key={index} style={{ 
                              fontSize: 11, 
                              color: '#666', 
                              backgroundColor: '#f0f0f0', 
                              padding: '2px 6px', 
                              borderRadius: 2 
                            }}>
                              {tag}
                            </span>
                          ))}
                          <Badge status="success" text={getStatusName(algorithm.status)} />
                        </Space>
                      </div>
                    </Option>
                  ))}
                </Select>
              </Form.Item>

              {selectedAlgorithms.length > 0 && (
                <Card size="small" title="已选择的AI算法" style={{ marginTop: 16 }}>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {selectedAlgorithms.map(algorithmId => {
                      const algorithm = algorithms.find(a => a.id === algorithmId)
                      return algorithm ? (
                        <div key={algorithmId} style={{ 
                          padding: 8, 
                          border: '1px solid #f0f0f0', 
                          borderRadius: 4 
                        }}>
                          <Space>
                            <Text strong>{algorithm.name}</Text>
                            <Text type="secondary">({algorithm.provider} · {algorithm.model_name})</Text>
                          </Space>
                          <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                            {algorithm.description}
                          </div>
                          <div style={{ marginTop: 4 }}>
                            {(algorithm.tags || []).map((tag, index) => (
                              <span key={index} style={{ 
                                fontSize: 11, 
                                color: '#666', 
                                backgroundColor: '#f0f0f0', 
                                padding: '2px 6px', 
                                borderRadius: 2, 
                                marginRight: 4 
                              }}>
                                {tag}
                              </span>
                            ))}
                          </div>
                        </div>
                      ) : null
                    })}
                  </Space>
                </Card>
              )}
            </Form>
          </Spin>
        )

      case 'roi':
        return (
          <Spin spinning={loading}>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={2} size="small">
                <Descriptions.Item label="已选算法">{selectedAlgorithms.length} 个</Descriptions.Item>
                <Descriptions.Item label="视频流">{stream?.name}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card 
              title={
                <Space>
                  <span style={{ fontSize: '16px' }}>🎯</span>
                  <Title level={5} style={{ margin: 0 }}>配置感兴趣区域 (ROI)</Title>
                </Space>
              } 
              size="small"
            >
              <Alert
                message="ROI区域配置"
                description="为每个AI算法配置独立的ROI区域。不同算法可以检测不同的区域，提高分析的针对性和准确性。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              {/* 算法选择下拉框 */}
              <Card size="small" style={{ marginBottom: 16, backgroundColor: '#fafafa' }}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>选择要配置ROI的算法:</Text>
                  <Select
                    value={selectedAlgorithmForROI}
                    onChange={(value) => setSelectedAlgorithmForROI(value)}
                    style={{ width: '100%' }}
                    placeholder="请选择一个算法"
                  >
                    {selectedAlgorithms.map(algorithmId => {
                      const algorithm = algorithms.find(a => a.id === algorithmId)
                      const hasROI = Boolean(algorithmROIs[algorithmId])
                      return algorithm ? (
                        <Option key={algorithmId} value={algorithmId}>
                          <Space>
                            <span style={{ fontWeight: 'bold' }}>{algorithm.name}</span>
                            {hasROI && <Badge status="success" text="已配置ROI" />}
                            {!hasROI && <Badge status="default" text="未配置" />}
                          </Space>
                        </Option>
                      ) : null
                    })}
                  </Select>
                  {selectedAlgorithmForROI && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      💡 当前正在为 "<strong>{algorithms.find(a => a.id === selectedAlgorithmForROI)?.name}</strong>" 配置ROI区域
                    </Text>
                  )}
                </Space>
              </Card>

              <Row gutter={16}>
                <Col span={12}>
                  <Card title="视频快照" size="small">
                    {!currentSnapshot ? (
                      <div style={{ 
                        height: 300, 
                        display: 'flex', 
                        alignItems: 'center', 
                        justifyContent: 'center',
                        border: '2px dashed #d9d9d9',
                        borderRadius: 6,
                        flexDirection: 'column'
                      }}>
                        <CameraOutlined style={{ fontSize: 48, color: '#d9d9d9', marginBottom: 16 }} />
                        <Text type="secondary">点击下方按钮获取视频快照</Text>
                        <Button 
                          type="primary" 
                          icon={<CameraOutlined />}
                          onClick={captureSnapshot}
                          style={{ marginTop: 12 }}
                        >
                          获取快照
                        </Button>
                      </div>
                    ) : (
                      <div style={{ position: 'relative' }}>
                        <img 
                          src={currentSnapshot} 
                          alt="Video Snapshot"
                          style={{ 
                            width: '100%', 
                            maxHeight: 300, 
                            objectFit: 'contain',
                            border: '1px solid #d9d9d9',
                            borderRadius: 4,
                            display: 'block'
                          }}
                          onLoad={handleImageLoad}
                        />
                        <canvas
                          ref={canvasRef}
                          style={{
                            position: 'absolute',
                            top: 0,
                            left: 0,
                            cursor: 'crosshair',
                            pointerEvents: 'auto'
                          }}
                          onMouseDown={handleMouseDown}
                          onMouseMove={handleMouseMove}
                          onMouseUp={handleMouseUp}
                          onMouseLeave={() => {
                            setIsDrawing(false)
                            setStartPoint(null)
                          }}
                        />
                        <div style={{ marginTop: 8, textAlign: 'center' }}>
                          <Space direction="vertical" size="small">
                            <Space>
                              <Button 
                                size="small"
                                icon={<CameraOutlined />}
                                onClick={captureSnapshot}
                              >
                                重新获取
                              </Button>
                              {getCurrentROI() && (
                                <>
                                  <Button
                                    size="small"
                                    type="primary"
                                    danger
                                    onClick={deleteROIRegion}
                                  >
                                    删除ROI
                                  </Button>
                                  <Button
                                    size="small"
                                    onClick={redrawROI}
                                  >
                                    重新绘制
                                  </Button>
                                </>
                              )}
                            </Space>

                            {!getCurrentROI() && (
                              <div style={{ padding: '8px', backgroundColor: '#f0f0f0', borderRadius: 4 }}>
                                <Text style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>绘制模式:</Text>
                                <Space>
                                  <Button 
                                    size="small"
                                    type={roiDrawMode === 'rectangle' ? 'primary' : 'default'}
                                    onClick={() => setRoiDrawMode('rectangle')}
                                  >
                                    矩形框
                                  </Button>
                                  <Button 
                                    size="small"
                                    type={roiDrawMode === 'polygon' ? 'primary' : 'default'}
                                    onClick={() => setRoiDrawMode('polygon')}
                                  >
                                    多边形
                                  </Button>
                                </Space>
                              </div>
                            )}
                          </Space>
                        </div>
                      </div>
                    )}
                  </Card>
                </Col>

                <Col span={12}>
                  <Card title="ROI区域设置" size="small">
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Alert
                        message="绘制操作说明"
                        description={
                          <ul style={{ margin: 0, paddingLeft: 16 }}>
                            <li><strong>矩形模式</strong>：在快照上按住鼠标左键拖拽绘制矩形</li>
                            <li><strong>多边形模式</strong>：点击快照上的点依次添加顶点，点击起始点完成绘制</li>
                            <li>每张图片只能设置一个ROI区域（降低算法复杂度）</li>
                            <li>可以删除当前区域并重新绘制</li>
                            <li>只有设置的ROI区域会被AI算法分析</li>
                          </ul>
                        }
                        type="info"
                        size="small"
                      />
                      
                      <div>
                        <Text strong>当前ROI区域: {getCurrentROI() ? '已设置' : '未设置'}</Text>
                        {getCurrentROI() ? (
                          <div style={{ marginTop: 8 }}>
                            <div style={{ 
                              padding: 12, 
                              backgroundColor: '#f6ffed',
                              border: '1px solid #b7eb8f',
                              borderRadius: 6,
                              fontSize: 13
                            }}>
                              <div style={{ fontWeight: 'bold', marginBottom: 8, color: '#389e0d' }}>
                                {getCurrentROI()!.type === 'rectangle' ? '矩形ROI区域' : '多边形ROI区域'}
                              </div>

                              {getCurrentROI()!.type === 'rectangle' && (
                                <div style={{ color: '#666' }}>
                                  <div>位置: ({(getCurrentROI()!.data as ROIRectangle).x}, {(getCurrentROI()!.data as ROIRectangle).y})</div>
                                  <div>尺寸: {(getCurrentROI()!.data as ROIRectangle).width} × {(getCurrentROI()!.data as ROIRectangle).height}</div>
                                </div>
                              )}

                              {getCurrentROI()!.type === 'polygon' && (
                                <div style={{ color: '#666' }}>
                                  <div>顶点数量: {(getCurrentROI()!.data as ROIPolygon).points.length}</div>
                                  <div style={{ fontSize: 11, marginTop: 4 }}>
                                    顶点坐标: {(getCurrentROI()!.data as ROIPolygon).points.map(p => `(${p.x},${p.y})`).join(', ')}
                                  </div>
                                </div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div style={{ 
                            marginTop: 8, 
                            padding: 12, 
                            backgroundColor: '#f5f5f5', 
                            border: '1px dashed #d9d9d9', 
                            borderRadius: 6,
                            textAlign: 'center',
                            color: '#999'
                          }}>
                            {isDrawingPolygon ? (
                              <div>
                                <div>正在绘制多边形...</div>
                                <div style={{ fontSize: 11, marginTop: 4 }}>
                                  已添加 {currentPolygon.length} 个顶点
                                  {currentPolygon.length >= 3 && <div>点击起始点完成绘制</div>}
                                </div>
                              </div>
                            ) : (
                              <div>
                                选择绘制模式后在快照上绘制ROI区域
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                    </Space>
                  </Card>
                </Col>
              </Row>
            </Card>
          </Spin>
        )

      case 'schedule':
        return (
          <Spin spinning={loading}>
            <Card size="small" style={{ marginBottom: 16 }}>
              <Descriptions column={3} size="small">
                <Descriptions.Item label="已选算法">{selectedAlgorithms.length} 个</Descriptions.Item>
                <Descriptions.Item label="ROI区域">
                  {Object.values(algorithmROIs).filter(roi => roi !== null).length} / {selectedAlgorithms.length} 个算法已配置
                </Descriptions.Item>
                <Descriptions.Item label="视频流">{stream?.name}</Descriptions.Item>
              </Descriptions>
            </Card>

            <Card 
              title={
                <Space>
                  <ClockCircleOutlined />
                  <Title level={5} style={{ margin: 0 }}>配置分析时间</Title>
                </Space>
              } 
              size="small"
            >
              <Alert
                message="时间配置说明"
                description="为每个AI算法配置运行时间段。只有在指定时间范围内，系统才会对视频流进行抽帧分析。不在时间范围内的视频不会被处理。"
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />

              <Space direction="vertical" style={{ width: '100%' }}>
                {selectedAlgorithms.map(algorithmId => {
                  const algorithm = algorithms.find(a => a.id === algorithmId)
                  const config = scheduleConfig[algorithmId] || { 
                    enabled: true, 
                    timeRanges: [{ startTime: '07:00', endTime: '18:00', days: [1,2,3,4,5,6,0] }] 
                  }
                  
                  return algorithm ? (
                    <Card key={algorithmId} size="small" style={{ backgroundColor: '#fafafa' }}>
                      <Row gutter={16} align="middle">
                        <Col span={6}>
                          <Space direction="vertical" size="small">
                            <Text strong>{algorithm.name}</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>
                              {algorithm.description}
                            </Text>
                          </Space>
                        </Col>
                        
                        <Col span={4}>
                          <Space direction="vertical" size="small">
                            <Text>启用时间控制</Text>
                            <Switch 
                              checked={config.enabled}
                              onChange={(enabled) => {
                                setScheduleConfig(prev => ({
                                  ...prev,
                                  [algorithmId]: { ...config, enabled }
                                }))
                              }}
                            />
                          </Space>
                        </Col>

                        {config.enabled && (
                          <>
                            <Col span={24}>
                              <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                  <Text strong>运行时间段</Text>
                                  {config.timeRanges.length < 4 && (
                                    <Button
                                      type="dashed"
                                      size="small"
                                      icon={<PlusOutlined />}
                                      onClick={() => {
                                        const newTimeRanges = [
                                          ...config.timeRanges,
                                          {
                                            startTime: '09:00',
                                            endTime: '18:00',
                                            days: [1, 2, 3, 4, 5]
                                          }
                                        ]
                                        setScheduleConfig(prev => ({
                                          ...prev,
                                          [algorithmId]: { ...config, timeRanges: newTimeRanges }
                                        }))
                                      }}
                                    >
                                      添加时间段
                                    </Button>
                                  )}
                                </div>

                                {config.timeRanges.map((timeRange, index) => (
                                  <Card
                                    key={index}
                                    size="small"
                                    style={{ marginTop: 8 }}
                                    title={<Text type="secondary">时间段 {index + 1}</Text>}
                                    extra={
                                      config.timeRanges.length > 1 && (
                                        <Button
                                          type="text"
                                          danger
                                          size="small"
                                          icon={<MinusCircleOutlined />}
                                          onClick={() => {
                                            const newTimeRanges = config.timeRanges.filter((_, i) => i !== index)
                                            setScheduleConfig(prev => ({
                                              ...prev,
                                              [algorithmId]: { ...config, timeRanges: newTimeRanges }
                                            }))
                                          }}
                                        >
                                          删除
                                        </Button>
                                      )
                                    }
                                  >
                                    <Row gutter={16}>
                                      <Col span={12}>
                                        <Space>
                                          <TimePicker
                                            value={dayjs(timeRange.startTime, 'HH:mm')}
                                            format="HH:mm"
                                            placeholder="开始时间"
                                            size="small"
                                            onChange={(time) => {
                                              const newTimeRanges = [...config.timeRanges]
                                              newTimeRanges[index] = {
                                                ...newTimeRanges[index],
                                                startTime: time?.format('HH:mm') || '00:00'
                                              }
                                              setScheduleConfig(prev => ({
                                                ...prev,
                                                [algorithmId]: { ...config, timeRanges: newTimeRanges }
                                              }))
                                            }}
                                          />
                                          <Text>至</Text>
                                          <TimePicker
                                            value={dayjs(timeRange.endTime, 'HH:mm')}
                                            format="HH:mm"
                                            placeholder="结束时间"
                                            size="small"
                                            onChange={(time) => {
                                              const newTimeRanges = [...config.timeRanges]
                                              newTimeRanges[index] = {
                                                ...newTimeRanges[index],
                                                endTime: time?.format('HH:mm') || '23:59'
                                              }
                                              setScheduleConfig(prev => ({
                                                ...prev,
                                                [algorithmId]: { ...config, timeRanges: newTimeRanges }
                                              }))
                                            }}
                                          />
                                        </Space>
                                      </Col>
                                      <Col span={12}>
                                        <Checkbox.Group
                                          value={timeRange.days || []}
                                          onChange={(days) => {
                                            const newTimeRanges = [...config.timeRanges]
                                            newTimeRanges[index] = { ...newTimeRanges[index], days: days as number[] }
                                            setScheduleConfig(prev => ({
                                              ...prev,
                                              [algorithmId]: { ...config, timeRanges: newTimeRanges }
                                            }))
                                          }}
                                        >
                                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                                            <Checkbox value={1}>一</Checkbox>
                                            <Checkbox value={2}>二</Checkbox>
                                            <Checkbox value={3}>三</Checkbox>
                                            <Checkbox value={4}>四</Checkbox>
                                            <Checkbox value={5}>五</Checkbox>
                                            <Checkbox value={6}>六</Checkbox>
                                            <Checkbox value={0}>日</Checkbox>
                                          </div>
                                        </Checkbox.Group>
                                      </Col>
                                    </Row>
                                  </Card>
                                ))}
                              </Space>
                            </Col>
                          </>
                        )}
                      </Row>
                    </Card>
                  ) : null
                })}
              </Space>
            </Card>
          </Spin>
        )

      case 'ready':
        return (
          <Spin spinning={loading}>
            {/* 配置成功提示 */}
            <Alert
              message="配置已保存"
              description={`已成功配置 ${currentConfiguredAlgorithms.length} 个AI分析算法，您可以立即启动分析或继续修改配置。`}
              type="success"
              showIcon
              style={{ marginBottom: 16 }}
            />

            {stream && (
              <Card size="small" style={{ marginBottom: 16 }}>
                <Descriptions column={3} size="small">
                  <Descriptions.Item label="视频流名称">{stream.name}</Descriptions.Item>
                  <Descriptions.Item label="流类型">{stream.stream_type}</Descriptions.Item>
                  <Descriptions.Item label="状态">{stream.status}</Descriptions.Item>
                </Descriptions>
              </Card>
            )}

            {currentConfiguredAlgorithms.length > 0 && (
              <Card title="当前配置的AI算法" size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  {currentConfiguredAlgorithms.map(algorithmId => {
                    const algorithm = algorithms.find(a => a.id === algorithmId)
                    return algorithm ? (
                      <div key={algorithmId} style={{ 
                        padding: 8, 
                        border: '1px solid #e6f7ff', 
                        borderRadius: 4,
                        backgroundColor: '#f6ffed'
                      }}>
                        <Space>
                          <CheckCircleOutlined style={{ color: '#52c41a' }} />
                          <Text strong>{algorithm.name}</Text>
                          <Text type="secondary">({algorithm.provider} · {algorithm.model_name})</Text>
                        </Space>
                        <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                          {algorithm.description}
                        </div>
                        <div style={{ marginTop: 4 }}>
                          {(algorithm.tags || []).map((tag, index) => (
                            <span key={index} style={{ 
                              fontSize: 11, 
                              color: '#52c41a', 
                              backgroundColor: '#f6ffed', 
                              border: '1px solid #b7eb8f',
                              padding: '2px 6px', 
                              borderRadius: 2, 
                              marginRight: 4 
                            }}>
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    ) : null
                  })}
                </Space>
              </Card>
            )}
          </Spin>
        )

      case 'analyzing':
        return (
          <Card>
            <Result
              status="success"
              title="分析已启动"
              subTitle={`${stream?.name} 的AI分析任务已成功启动，系统正在进行智能监控分析。`}
              extra={
                <Space>
                  <Text type="secondary">🎯 智能分析 • 📊 实时监控 • 🚨 即时告警</Text>
                </Space>
              }
            />
          </Card>
        )

      default:
        return null
    }
  }

  return (
    <Modal
      title={
        <Space>
          <SettingOutlined />
          配置视频流分析算法
        </Space>
      }
      open={open}
      onCancel={handleCancel}
      width={1200}
      footer={null}
      destroyOnHidden
    >
      <Spin spinning={loading}>
        {/* 步骤指示器 */}
        <Steps 
          current={
            currentStep === 'algorithm' ? 0 :
            currentStep === 'roi' ? 1 :
            currentStep === 'schedule' ? 2 :
            currentStep === 'ready' ? 3 : 4
          } 
          style={{ marginBottom: 24 }}
          items={[
            {
              title: '选择算法',
              description: '选择AI分析算法',
              icon: <SettingOutlined />
            },
            {
              title: '配置ROI',
              description: '设置关注区域',
              icon: <span style={{ fontSize: '14px' }}>🎯</span>
            },
            {
              title: '时间配置',
              description: '设置分析时间',
              icon: <span style={{ fontSize: '14px' }}>⏰</span>
            },
            {
              title: '准备就绪',
              description: '配置已完成',
              icon: <CheckCircleOutlined />
            },
            {
              title: '启动分析',
              description: '开始视频流分析',
              icon: <PlayCircleOutlined />
            }
          ]}
        />

        {renderStepContent()}

        {/* 智能按钮区域 */}
        <div style={{ 
          marginTop: 24, 
          borderTop: '1px solid #f0f0f0',
          paddingTop: 16
        }}>
          {currentStep === 'algorithm' && (
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button onClick={handleCancel}>取消</Button>
                <Button 
                  type="primary" 
                  onClick={handleNextStep}
                  disabled={selectedAlgorithms.length === 0}
                >
                  下一步：配置ROI
                </Button>
              </Space>
            </div>
          )}

          {currentStep === 'roi' && (
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button onClick={handlePrevStep}>上一步</Button>
                <Button onClick={handleNextStep}>跳过ROI配置</Button>
                <Button 
                  type="primary" 
                  onClick={handleNextStep}
                >
                  下一步：时间配置
                </Button>
              </Space>
            </div>
          )}

          {currentStep === 'schedule' && (
            <div style={{ textAlign: 'right' }}>
              <Space>
                <Button onClick={handlePrevStep}>上一步</Button>
                <Button 
                  type="primary" 
                  onClick={() => {
                    handleSaveConfig()
                  }}
                >
                  完成配置
                </Button>
              </Space>
            </div>
          )}

          {currentStep === 'ready' && (
            <div>
              <div style={{ textAlign: 'left', marginBottom: 12 }}>
                <Text type="secondary">
                  💡 提示：您可以继续修改配置，或者立即启动分析任务。
                </Text>
              </div>
              <div style={{ textAlign: 'right' }}>
                <Space>
                  <Button onClick={handleCancel}>完成并关闭</Button>
                  <Button 
                    onClick={() => setCurrentStep('algorithm')}
                    icon={<SettingOutlined />}
                  >
                    修改配置
                  </Button>
                  <Button 
                    type="primary" 
                    onClick={handleStartAnalysis}
                    style={{ background: '#52c41a', borderColor: '#52c41a' }}
                    icon={<PlayCircleOutlined />}
                  >
                    启动分析
                  </Button>
                </Space>
              </div>
            </div>
          )}

          {currentStep === 'analyzing' && (
            <div style={{ textAlign: 'center' }}>
              <Spin size="small" style={{ marginRight: 8 }} />
              <Text>正在启动分析任务，请稍候...</Text>
            </div>
          )}
        </div>
      </Spin>
    </Modal>
  )
}

export default SimpleStreamAlgorithmModal