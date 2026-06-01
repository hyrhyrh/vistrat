import React, { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  Layout,
  Card,
  Form,
  Input,
  Select,
  InputNumber,
  Button,
  Upload,
  message,
  Row,
  Col,
  Space,
  Tag,
  Tooltip,
  Spin,
  Alert,
  Typography,
  Divider,
  Modal,
  Image,
  Collapse,
  List,
  Badge,
  Checkbox,
  Switch,
  Transfer,
  Slider
} from 'antd'
import {
  UploadOutlined,
  PlayCircleOutlined,
  ClearOutlined,
  InfoCircleOutlined,
  RobotOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  EyeOutlined,
  SafetyCertificateOutlined,
  BulbOutlined,
  ThunderboltOutlined
} from '@ant-design/icons'
import type { UploadFile } from 'antd/lib/upload/interface'

const { Content } = Layout
const { TextArea } = Input
const { Option } = Select
const { Text, Title, Paragraph } = Typography
const { Panel } = Collapse

// 类别和严重程度的中文映射
const CATEGORY_MAP: Record<string, string> = {
  'safety': '安全装备',
  'behavior': '违规行为',
  'environment': '环境风险',
  'security': '安保威胁'
}

const SEVERITY_MAP: Record<string, string> = {
  'high': '高',
  'medium': '中',
  'low': '低',
  'critical': '严重'
}

interface AIProvider {
  value: string
  label: string
  icon: string
}

interface AIModelOptions {
  [key: string]: string[]
}

interface TestResult {
  id: string
  ai_response: string
  confidence_score?: number
  processing_time: number
  is_success: boolean
  error_message?: string
  created_at: string
}

interface DetectionTypeTemplate {
  type_code: string
  name: string  // API返回的检测类型名称（如"未佩戴安全帽"）
  category: string
  severity: string
  description: string
  enabled: boolean
}

interface ConfigForm {
  name: string
  description: string
  provider: string
  model_name: string
  model_type: string
  system_prompt: string
  user_prompt: string
  temperature: number
  top_p: number
  max_tokens: number
  confidence_threshold: number
  tags: string[]
  detection_capabilities: string[]
}

const AIModelPage: React.FC = () => {
  const { isAuthenticated } = useAuth()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const location = useLocation()
  
  // 数据状态
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [modelOptions, setModelOptions] = useState<AIModelOptions>({})
  const [availableModels, setAvailableModels] = useState<string[]>([])
  const [detectionTypeTemplates, setDetectionTypeTemplates] = useState<DetectionTypeTemplate[]>([])

  // 测试相关状态
  const [uploadedFile, setUploadedFile] = useState<UploadFile[]>([])
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [currentConfigId, setCurrentConfigId] = useState<string | null>(null)
  const [previewImageUrl, setPreviewImageUrl] = useState<string | null>(null)
  
  // AI生成相关状态
  const [generatingDescription, setGeneratingDescription] = useState(false)
  const [generatingPrompts, setGeneratingPrompts] = useState(false)

  // 复合检测相关状态
  const [compositeMode, setCompositeMode] = useState(false)
  const [selectedTypeKeys, setSelectedTypeKeys] = useState<string[]>([])

  // 获取认证头
  const getAuthHeaders = () => {
    const token = localStorage.getItem('token')
    if (!token) {
      throw new Error('未找到认证令牌，请重新登录')
    }
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    }
  }

  useEffect(() => {
    loadProviders()
    loadModelOptions()
    loadDetectionTypeTemplates()
  }, [])

  // 处理编辑模式下的数据填充
  useEffect(() => {
    const state = location.state as { editMode?: boolean; algorithmData?: any }
    if (state?.editMode && state?.algorithmData) {
      const algorithmData = state.algorithmData
      
      // 设置表单值
      form.setFieldsValue({
        name: algorithmData.name,
        description: algorithmData.description,
        provider: algorithmData.provider,
        model_name: algorithmData.model_name,
        system_prompt: algorithmData.system_prompt,
        user_prompt: algorithmData.user_prompt,
        temperature: algorithmData.temperature,
        top_p: algorithmData.top_p,
        max_tokens: algorithmData.max_tokens,
        confidence_threshold: algorithmData.confidence_threshold,
        tags: algorithmData.tags || [],
        detection_capabilities: algorithmData.detection_capabilities || []
      })

      // 恢复复合检测状态
      if (algorithmData.detection_capabilities && algorithmData.detection_capabilities.length > 0) {
        setCompositeMode(true)
        setSelectedTypeKeys(algorithmData.detection_capabilities)
      }

      // 设置当前配置ID（如果是编辑模式）
      setCurrentConfigId(algorithmData.id)

      // 根据供应商设置可用模型
      if (algorithmData.provider) {
        setAvailableModels(modelOptions[algorithmData.provider] || [])
      }
    }
  }, [location.state, form, modelOptions])

  // 清理预览URL，防止内存泄漏
  useEffect(() => {
    return () => {
      if (previewImageUrl) {
        URL.revokeObjectURL(previewImageUrl)
      }
    }
  }, [previewImageUrl])

  const loadProviders = async () => {
    try {
      const response = await fetch('/api/ai-models/providers')
      const data = await response.json()
      setProviders(data.providers)
    } catch (error) {
      message.error('加载AI供应商列表失败')
    }
  }

  const loadModelOptions = async () => {
    try {
      const response = await fetch('/api/ai-models/model-options')
      const data = await response.json()
      setModelOptions(data.model_options)
    } catch (error) {
      message.error('加载模型选项失败')
    }
  }

  const loadDetectionTypeTemplates = async () => {
    try {
      const response = await fetch('/api/video-files/detection-types/templates')
      const data = await response.json()
      if (data.templates) {
        setDetectionTypeTemplates(data.templates)
      }
    } catch (error) {
      console.error('加载检测类型模板失败:', error)
      // 不显示错误消息，因为这是可选功能
    }
  }

  const handleProviderChange = (provider: string) => {
    setAvailableModels(modelOptions[provider] || [])
    form.setFieldsValue({ model_name: undefined })
  }

  // 复合检测模式切换
  const handleCompositeModeChange = (checked: boolean) => {
    setCompositeMode(checked)
    if (!checked) {
      // 关闭复合检测时清空选择
      setSelectedTypeKeys([])
      form.setFieldsValue({ detection_capabilities: [] })
    }
  }

  // 处理检测类型选择变更
  const handleDetectionTypesChange = (targetKeys: string[]) => {
    setSelectedTypeKeys(targetKeys)
    form.setFieldsValue({ detection_capabilities: targetKeys })
  }

  // AI生成算法描述
  const handleGenerateDescription = async () => {
    try {
      const algorithmName = form.getFieldValue('name')
      if (!algorithmName) {
        message.warning('请先输入算法名称')
        return
      }

      if (!isAuthenticated) {
        message.error('请先登录')
        return
      }

      setGeneratingDescription(true)
      
      const response = await fetch('/api/ai-text/generate-description', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          algorithm_name: algorithmName
        })
      })

      if (!response.ok) {
        if (response.status === 401) {
          message.error('认证失败，请重新登录')
          return
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (result.success && result.data) {
        form.setFieldValue('description', result.data.description)
        message.success('算法描述生成成功')
      } else {
        message.error(result.error || '生成算法描述失败')
      }
    } catch (error) {
      console.error('Generate description error:', error)
      if (error.message.includes('未找到认证令牌')) {
        message.error('认证令牌无效，请重新登录')
      } else {
        message.error('生成算法描述时发生错误')
      }
    } finally {
      setGeneratingDescription(false)
    }
  }

  // AI生成提示词
  const handleGeneratePrompts = async () => {
    try {
      const algorithmName = form.getFieldValue('name')
      const algorithmDescription = form.getFieldValue('description') || ''
      
      if (!algorithmName) {
        message.warning('请先输入算法名称')
        return
      }

      if (!isAuthenticated) {
        message.error('请先登录')
        return
      }

      setGeneratingPrompts(true)
      
      const response = await fetch('/api/ai-text/generate-prompts', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({
          algorithm_name: algorithmName,
          algorithm_description: algorithmDescription
        })
      })

      if (!response.ok) {
        if (response.status === 401) {
          message.error('认证失败，请重新登录')
          return
        }
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      
      if (result.success && result.data) {
        // 设置生成的提示词
        const updateFields = {
          system_prompt: result.data.system_prompt,
          user_prompt: result.data.user_prompt
        }
        
        // 如果返回了输出格式配置，也一并设置（新增功能）
        if (result.data.output_format_config) {
          updateFields.output_format_config = JSON.stringify(result.data.output_format_config, null, 2)
          console.log('设置输出格式配置:', result.data.output_format_config)
        }
        
        form.setFieldsValue(updateFields)
        message.success('提示词和输出格式配置生成成功')
      } else {
        message.error(result.error || '生成提示词失败')
      }
    } catch (error) {
      console.error('Generate prompts error:', error)
      if (error.message.includes('未找到认证令牌')) {
        message.error('认证令牌无效，请重新登录')
      } else {
        message.error('生成提示词时发生错误')
      }
    } finally {
      setGeneratingPrompts(false)
    }
  }

  // 解析AI响应并格式化显示
  const parseAIResponse = (response: string) => {
    // 尝试解析结构化内容
    const lines = response.split('\n').filter(line => line.trim());
    const sections: { title: string; content: string[]; type: 'conclusion' | 'details' | 'warning' | 'info' }[] = [];
    
    let currentSection = { title: '', content: [] as string[], type: 'info' as const };
    
    lines.forEach(line => {
      const trimmedLine = line.trim();
      
      // 检测是否为标题（包含 ### 或 **）
      if (trimmedLine.includes('###') || (trimmedLine.startsWith('**') && trimmedLine.endsWith('**'))) {
        // 保存之前的section
        if (currentSection.title || currentSection.content.length > 0) {
          sections.push({ ...currentSection });
        }
        
        // 创建新section
        const title = trimmedLine.replace(/#{1,6}\s*|\*\*/g, '').trim();
        let type: 'conclusion' | 'details' | 'warning' | 'info' = 'info';
        
        if (title.includes('总体结论') || title.includes('结论')) type = 'conclusion';
        else if (title.includes('警告') || title.includes('危险') || title.includes('风险')) type = 'warning';
        else if (title.includes('详细') || title.includes('检测') || title.includes('分析')) type = 'details';
        
        currentSection = { title, content: [], type };
      } else if (trimmedLine.startsWith('-') || trimmedLine.match(/^\d+\./)) {
        // 列表项
        currentSection.content.push(trimmedLine.replace(/^[-\*\d\.]\s*/, ''));
      } else if (trimmedLine) {
        // 普通段落
        currentSection.content.push(trimmedLine);
      }
    });
    
    // 添加最后一个section
    if (currentSection.title || currentSection.content.length > 0) {
      sections.push(currentSection);
    }
    
    return sections.length > 0 ? sections : [{ title: 'AI分析结果', content: [response], type: 'info' as const }];
  }

  const handleUploadChange = (info: any) => {
    setUploadedFile(info.fileList)
    
    // 生成预览URL
    if (info.fileList.length > 0 && info.fileList[0].originFileObj) {
      const file = info.fileList[0].originFileObj
      const url = URL.createObjectURL(file)
      setPreviewImageUrl(url)
    } else {
      setPreviewImageUrl(null)
    }
  }

  const handleTest = async () => {
    try {
      // 获取所有表单数据（不只是验证必需字段）
      const values = await form.validateFields()
      
      if (!uploadedFile.length) {
        message.warning('请上传图片进行测试')
        return
      }

      setTesting(true)
      const formData = new FormData()
      
      // 添加配置参数
      formData.append('provider', values.provider)
      formData.append('model_name', values.model_name)
      formData.append('system_prompt', values.system_prompt || '')
      formData.append('user_prompt', values.user_prompt || '')
      formData.append('temperature', String(values.temperature || 0.7))
      formData.append('top_p', String(values.top_p || 0.9))
      formData.append('max_tokens', String(values.max_tokens || 1000))
      formData.append('confidence_threshold', String(values.confidence_threshold || 0.7))

      // 添加检测能力（优先使用复合检测）
      if (values.detection_capabilities && values.detection_capabilities.length > 0) {
        formData.append('detection_capabilities', JSON.stringify(values.detection_capabilities))
        console.log('🎯 使用复合检测模式，检测能力:', values.detection_capabilities)
      }

      // 添加图片
      if (uploadedFile.length > 0) {
        formData.append('image', uploadedFile[0].originFileObj as File)
      }

      const response = await fetch('/api/ai-models/test-config', {
        method: 'POST',
        body: formData
      })

      const result = await response.json()
      
      if (response.ok) {
        setTestResult(result)
        message.success('AI模型测试完成')
      } else {
        throw new Error(result.detail || '测试失败')
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请先填写必需的配置信息（AI供应商、模型）')
      } else {
        message.error(error.message || 'AI模型测试失败')
      }
    } finally {
      setTesting(false)
    }
  }

  const handleClear = () => {
    setUploadedFile([])
    setTestResult(null)
    if (previewImageUrl) {
      URL.revokeObjectURL(previewImageUrl)
      setPreviewImageUrl(null)
    }
  }

  const handleSaveAndActivate = async () => {
    try {
      // 验证表单
      const values = await form.validateFields()
      
      // 处理输出格式配置字段（新增功能）
      const processedValues = { ...values }
      if (values.output_format_config) {
        try {
          // 如果是字符串，尝试解析为JSON对象
          if (typeof values.output_format_config === 'string') {
            processedValues.output_format_config = JSON.parse(values.output_format_config)
          }
          console.log('处理后的输出格式配置:', processedValues.output_format_config)
        } catch (error) {
          console.error('解析输出格式配置失败:', error)
          message.warning('输出格式配置JSON格式错误，将使用默认配置')
          delete processedValues.output_format_config
        }
      }

      // 确保detection_capabilities格式正确（字符串数组）
      // 使用selectedTypeKeys状态作为数据源，而不是仅依赖表单值
      // 这样即使Transfer组件没有渲染（compositeMode=false），也能正确保存
      if (compositeMode && selectedTypeKeys.length > 0) {
        processedValues.detection_capabilities = selectedTypeKeys
      } else if (processedValues.detection_capabilities) {
        // 如果表单中有值，使用表单值
        processedValues.detection_capabilities = processedValues.detection_capabilities
      } else {
        // 否则设为空数组
        processedValues.detection_capabilities = []
      }

      console.log('保存配置数据:', {
        compositeMode,
        selectedTypeKeys,
        detection_capabilities: processedValues.detection_capabilities,
        detection_capabilities_type: typeof processedValues.detection_capabilities,
        detection_capabilities_length: processedValues.detection_capabilities?.length
      })

      // 检查是否为编辑模式
      const state = location.state as { editMode?: boolean; algorithmData?: any }
      const isEditMode = state?.editMode && currentConfigId

      let response: Response
      let successMessage: string

      if (isEditMode) {
        // 更新现有配置
        response = await fetch(`/api/ai-models/configs/${currentConfigId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...processedValues,
            tags: processedValues.tags || []
          })
        })
        successMessage = '算法已成功更新'
      } else {
        // 创建新配置
        response = await fetch('/api/ai-models/configs/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...processedValues,
            tags: processedValues.tags || []
          })
        })
        successMessage = '算法已成功入库并激活'
      }

      const result = await response.json()

      if (response.ok) {
        if (!isEditMode) {
          const configId = result.id
          
          // 立即激活配置（仅新建时）
          const activateResponse = await fetch(`/api/ai-models/configs/${configId}/activate`, {
            method: 'POST'
          })

          if (activateResponse.ok) {
            setCurrentConfigId(configId)
          } else {
            throw new Error('激活失败')
          }
        }
        
        message.success(successMessage)
      } else {
        throw new Error(result.detail || (isEditMode ? '更新失败' : '保存失败'))
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请检查表单输入')
      } else {
        message.error(error.message || (currentConfigId ? '算法更新失败' : '算法入库失败'))
      }
    }
  }

  return (
    <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
      <Content style={{ padding: '24px' }}>
        <Row gutter={24} style={{ height: '100%' }}>
          {/* 左侧配置面板 */}
          <Col span={12}>
            <Card 
              title={
                <Space>
                  <RobotOutlined />
                  <span>AI大模型配置</span>
                  <Button 
                    type="primary" 
                    size="small"
                    onClick={handleSaveAndActivate}
                    disabled={testing}
                  >
                    {currentConfigId ? '更新算法' : '算法入库'}
                  </Button>
                </Space>
              }
              style={{ height: '100%' }}
            >
              <Form
                form={form}
                layout="vertical"
                initialValues={{
                  model_type: 'vision',
                  temperature: 0.1,
                  top_p: 0.1,
                  max_tokens: 1000,
                  confidence_threshold: 0.6,
                  tags: []
                }}
                style={{ height: '100%', overflowY: 'auto' }}
              >
                <Form.Item
                  name="provider"
                  label="AI模型供应商"
                  rules={[{ required: true, message: '请选择AI模型供应商' }]}
                >
                  <Select
                    placeholder="选择AI供应商"
                    onChange={handleProviderChange}
                  >
                    {providers.map(provider => (
                      <Option key={provider.value} value={provider.value}>
                        <Space>
                          <span>{provider.icon}</span>
                          <span>{provider.label}</span>
                        </Space>
                      </Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item
                  name="model_name"
                  label="具体模型"
                  rules={[{ required: true, message: '请选择具体模型' }]}
                >
                  <Select placeholder="选择模型">
                    {availableModels.map(model => (
                      <Option key={model} value={model}>
                        {model}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>

                <Form.Item
                  name="name"
                  label="算法名称"
                  rules={[{ required: true, message: '请输入算法名称' }]}
                >
                  <Input placeholder="输入算法名称" />
                </Form.Item>

                <Form.Item
                  name="description"
                  label={
                    <Space>
                      <span>算法描述</span>
                      <Tooltip title="点击使用AI根据算法名称自动生成算法描述">
                        <Button
                          type="text"
                          size="small"
                          icon={<BulbOutlined />}
                          onClick={handleGenerateDescription}
                          loading={generatingDescription}
                          style={{ padding: 0, color: '#1890ff' }}
                        />
                      </Tooltip>
                    </Space>
                  }
                >
                  <TextArea rows={2} placeholder="描述算法的功能和用途" />
                </Form.Item>

                <Divider orientation="left">复合检测配置</Divider>

                {/* 复合检测说明 */}
                <Alert
                  message="💡 使用复合检测，无需手动编写提示词"
                  description={
                    <div>
                      <p style={{ marginBottom: 8 }}>
                        <strong>复合检测模式</strong>采用系统内置的专业提示词模板，您只需：
                      </p>
                      <ol style={{ marginBottom: 0, paddingLeft: 20 }}>
                        <li>开启复合检测开关</li>
                        <li>勾选需要的检测能力（如：安全帽、吸烟、攀爬等）</li>
                        <li>上传图片测试算法效果</li>
                      </ol>
                      <p style={{ marginTop: 8, marginBottom: 0, color: '#52c41a' }}>
                        ✅ 系统会自动组装高质量提示词，一次AI调用即可检测多种违规类型，大幅降低成本！
                      </p>
                    </div>
                  }
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                {/* 复合检测模式开关 */}
                <Form.Item
                  label={
                    <Space>
                      <span>启用复合检测</span>
                      <Tooltip title="启用后可在一次AI调用中同时检测多种违规类型，大幅降低成本">
                        <InfoCircleOutlined style={{ color: '#1890ff' }} />
                      </Tooltip>
                    </Space>
                  }
                  extra={compositeMode && selectedTypeKeys.length > 1 ? (
                    <Text type="success">
                      已选择{selectedTypeKeys.length}种检测类型，预估节省 {Math.round((selectedTypeKeys.length - 1) / selectedTypeKeys.length * 100)}% API调用成本
                    </Text>
                  ) : null}
                >
                  <Switch
                    checked={compositeMode}
                    onChange={handleCompositeModeChange}
                    checkedChildren="开启"
                    unCheckedChildren="关闭"
                  />
                </Form.Item>

                {/* 隐藏字段：确保detection_capabilities始终在表单中 */}
                <Form.Item
                  name="detection_capabilities"
                  hidden
                >
                  <Input />
                </Form.Item>

                {/* 检测类型选择器 */}
                {compositeMode && (
                  <Form.Item
                    label={
                      <Space>
                        <span>检测能力</span>
                        <Tooltip title="选择该算法支持检测的违规类型">
                          <InfoCircleOutlined style={{ color: '#1890ff' }} />
                        </Tooltip>
                      </Space>
                    }
                    extra="从左侧选择该算法能够检测的违规类型，支持同时检测多种类型"
                  >
                    <Transfer
                      dataSource={detectionTypeTemplates.map(t => ({
                        key: t.type_code,
                        title: t.name,  // 显示API返回的检测类型名称
                        category: t.category,
                        severity: t.severity,
                        description: t.description,
                        disabled: false
                      }))}
                      targetKeys={selectedTypeKeys}
                      onChange={handleDetectionTypesChange}
                      render={item => (
                        <Tooltip
                          title={item.description}
                          placement="topLeft"
                          overlayStyle={{ maxWidth: 400 }}
                        >
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <span>{item.title}</span>
                            <Text type="secondary" style={{ fontSize: '12px' }}>
                              {CATEGORY_MAP[item.category] || item.category} | {SEVERITY_MAP[item.severity] || item.severity}
                            </Text>
                          </Space>
                        </Tooltip>
                      )}
                      listStyle={{
                        width: 300,
                        height: 400
                      }}
                      titles={['可用检测类型', '已选检测类型']}
                      showSearch
                      filterOption={(inputValue, item) =>
                        item.title.toLowerCase().indexOf(inputValue.toLowerCase()) !== -1
                      }
                    />
                  </Form.Item>
                )}

                {/* 系统提示词和用户提示词已屏蔽 - 使用复合检测时由系统自动组装 */}
                {/*
                <Form.Item
                  name="system_prompt"
                  label={
                    <Space>
                      <span>系统提示词</span>
                      <Tooltip title="点击使用AI根据算法名称和描述自动生成专业的系统提示词和用户提示词">
                        <Button
                          type="text"
                          size="small"
                          icon={<ThunderboltOutlined />}
                          onClick={handleGeneratePrompts}
                          loading={generatingPrompts}
                          style={{ padding: 0, color: '#52c41a' }}
                        />
                      </Tooltip>
                    </Space>
                  }
                >
                  <TextArea rows={3} placeholder="定义AI的角色和基本行为..." />
                </Form.Item>

                <Form.Item
                  name="user_prompt"
                  label="用户提示词"
                >
                  <TextArea rows={3} placeholder="具体的分析任务指令..." />
                </Form.Item>
                */}

                {/* 输出格式配置字段 - 隐藏显示，由AI生成提示词接口自动填充 */}
                <Form.Item
                  name="output_format_config"
                  label="输出格式配置"
                  style={{ display: 'none' }}
                  tooltip="该字段由AI生成提示词时自动设置，定义了AI模型返回结果的JSON格式要求，不建议手动修改"
                >
                  <TextArea 
                    rows={8} 
                    placeholder="AI模型输出格式JSON配置..."
                    readOnly
                    style={{ fontFamily: 'monospace', fontSize: '12px' }}
                  />
                </Form.Item>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="top_p"
                      label={
                        <Space>
                          <span>Top-p</span>
                          <Tooltip title="控制输出的多样性，值越小输出越确定性，建议0.1-1.0">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={0}
                        max={1}
                        step={0.1}
                        precision={1}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="temperature"
                      label={
                        <Space>
                          <span>Temperature</span>
                          <Tooltip title="控制输出的随机性，值越小越精确，值越大越有创意，建议0.1-2.0">
                            <InfoCircleOutlined />
                          </Tooltip>
                        </Space>
                      }
                    >
                      <InputNumber
                        min={0}
                        max={2}
                        step={0.1}
                        precision={1}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="confidence_threshold"
                      label="置信度阈值"
                    >
                      <InputNumber
                        min={0}
                        max={1}
                        step={0.1}
                        style={{ width: '100%' }}
                        formatter={value => `${(value * 100).toFixed(0)}%`}
                        parser={value => parseFloat(value?.replace('%', '')) / 100}
                      />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="max_tokens"
                      label="最大Token数"
                    >
                      <InputNumber
                        min={1}
                        max={4000}
                        style={{ width: '100%' }}
                      />
                    </Form.Item>
                  </Col>
                </Row>

                <Form.Item
                  name="tags"
                  label="算法标签"
                >
                  <Select
                    mode="tags"
                    placeholder="输入标签，按回车添加"
                    style={{ width: '100%' }}
                  />
                </Form.Item>

              </Form>
            </Card>
          </Col>

          {/* 右侧调试预览面板 */}
          <Col span={12}>
            <Card
              title={
                <Space>
                  <PlayCircleOutlined />
                  <span>调试预览</span>
                </Space>
              }
              style={{ height: '100%' }}
            >
              <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                {/* 验证测试区域 */}
                <div style={{ marginBottom: 16 }}>
                  <Title level={5}>验证测试</Title>
                  
                  <Form.Item label="上传测试图片">
                    <Upload
                      fileList={uploadedFile}
                      onChange={handleUploadChange}
                      beforeUpload={() => false}
                      accept="image/*"
                      maxCount={1}
                    >
                      <Button icon={<UploadOutlined />}>
                        选择图片
                      </Button>
                    </Upload>
                    <div style={{ marginTop: 8, color: '#666', fontSize: '12px' }}>
                      使用当前配置参数和上传的图片进行AI算法验证
                    </div>
                  </Form.Item>

                  <div style={{ marginTop: 16 }}>
                    <Space>
                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={handleTest}
                        loading={testing}
                        disabled={!uploadedFile.length}
                      >
                        {testing ? '验证中...' : '开始验证'}
                      </Button>
                      <Button
                        icon={<ClearOutlined />}
                        onClick={handleClear}
                        disabled={testing}
                      >
                        清空
                      </Button>
                    </Space>
                  </div>
                </div>

                <Divider />

                {/* 图片预览区域 */}
                {previewImageUrl ? (
                  <div style={{ marginBottom: 16 }}>
                    <Title level={5}>图片预览</Title>
                    <div style={{
                      border: '1px solid #d9d9d9',
                      borderRadius: '6px',
                      padding: '8px',
                      textAlign: 'center',
                      backgroundColor: '#fafafa'
                    }}>
                      <Image
                        src={previewImageUrl}
                        alt="预览图片"
                        style={{
                          maxWidth: '100%',
                          maxHeight: '200px',
                          objectFit: 'contain'
                        }}
                        preview={{
                          mask: (
                            <div style={{ color: 'white' }}>
                              点击放大查看
                            </div>
                          )
                        }}
                      />
                      <div style={{ marginTop: 8, color: '#666', fontSize: '12px' }}>
                        {uploadedFile[0]?.name} ({Math.round((uploadedFile[0]?.size || 0) / 1024)}KB)
                      </div>
                    </div>
                  </div>
                ) : null}

                {/* 分析结果显示区域 */}
                <div style={{ flex: 1 }}>
                  {testResult ? (
                    <div>
                      <Title level={5}>分析结果</Title>
                      {testResult.is_success ? (
                        <div>
                          {/* 分析统计信息 */}
                          <Row gutter={16} style={{ marginBottom: 16 }}>
                            <Col span={8}>
                              <Card size="small" style={{ textAlign: 'center' }}>
                                <Badge 
                                  status={testResult.confidence_score >= 0.7 ? 'success' : 'warning'} 
                                  text={`置信度 ${(testResult.confidence_score * 100).toFixed(1)}%`}
                                />
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" style={{ textAlign: 'center' }}>
                                <Badge status="processing" text={`${testResult.processing_time.toFixed(2)}s`} />
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" style={{ textAlign: 'center' }}>
                                <Badge status="success" text="分析完成" />
                              </Card>
                            </Col>
                          </Row>

                          {/* 结构化AI响应 */}
                          <div>
                            {parseAIResponse(testResult.ai_response).map((section, index) => {
                              const getIcon = (type: string) => {
                                switch(type) {
                                  case 'conclusion': return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
                                  case 'warning': return <ExclamationCircleOutlined style={{ color: '#faad14' }} />;
                                  case 'details': return <EyeOutlined style={{ color: '#1890ff' }} />;
                                  default: return <InfoCircleOutlined style={{ color: '#666' }} />;
                                }
                              };

                              const getCardColor = (type: string) => {
                                switch(type) {
                                  case 'conclusion': return '#f6ffed';
                                  case 'warning': return '#fffbf0';
                                  case 'details': return '#f0f9ff';
                                  default: return '#fafafa';
                                }
                              };

                              return (
                                <Card
                                  key={index}
                                  size="small"
                                  style={{ 
                                    marginBottom: 12, 
                                    backgroundColor: getCardColor(section.type),
                                    border: `1px solid ${section.type === 'warning' ? '#ffe58f' : section.type === 'conclusion' ? '#b7eb8f' : '#bae7ff'}`
                                  }}
                                  title={
                                    <Space>
                                      {getIcon(section.type)}
                                      <span style={{ fontWeight: 'bold' }}>{section.title}</span>
                                    </Space>
                                  }
                                >
                                  {section.content.length > 1 ? (
                                    <List
                                      size="small"
                                      dataSource={section.content}
                                      renderItem={(item, idx) => (
                                        <List.Item key={idx} style={{ padding: '4px 0', border: 'none' }}>
                                          <Text>{item}</Text>
                                        </List.Item>
                                      )}
                                    />
                                  ) : (
                                    <Paragraph style={{ margin: 0, whiteSpace: 'pre-line' }}>
                                      {section.content[0]}
                                    </Paragraph>
                                  )}
                                </Card>
                              );
                            })}
                          </div>
                        </div>
                      ) : (
                        <Alert
                          message="分析失败"
                          description={testResult.error_message}
                          type="error"
                          showIcon
                        />
                      )}
                    </div>
                  ) : previewImageUrl ? (
                    <div style={{ 
                      height: '200px', 
                      border: '2px dashed #d9d9d9', 
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#999'
                    }}>
                      <div style={{ textAlign: 'center' }}>
                        <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                        <div>点击"开始验证"进行AI分析</div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ 
                      height: '300px', 
                      border: '2px dashed #d9d9d9', 
                      borderRadius: '6px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#999'
                    }}>
                      <div style={{ textAlign: 'center' }}>
                        <RobotOutlined style={{ fontSize: '48px', marginBottom: '16px' }} />
                        <div>请先上传图片，然后进行AI分析验证</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </Content>
    </Layout>
  )
}

export default AIModelPage