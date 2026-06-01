"""
AI大模型编排相关数据模型
"""

from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Integer, Float, Text, Boolean, TIMESTAMP, JSON, ARRAY
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func

from database.connection import Base


# 枚举定义
class AIProviderEnum(PyEnum):
    """AI模型供应商枚举"""
    QWEN = "qwen"  # 通义千问
    MOONSHOT = "moonshot"  # Moonshot
    GPT = "gpt"  # OpenAI GPT
    CLAUDE = "claude"  # Anthropic Claude
    GEMINI = "gemini"  # Google Gemini
    BAIDU = "baidu"  # 百度文心一言
    LANYI = "lanyi"  # 蓝翼大模型


class AIModelTypeEnum(PyEnum):
    """AI模型类型枚举"""
    VISION = "vision"  # 视觉模型
    TEXT = "text"  # 文本模型
    MULTIMODAL = "multimodal"  # 多模态模型


class AlgorithmStatusEnum(PyEnum):
    """算法状态枚举"""
    DRAFT = "draft"  # 草稿
    TESTING = "testing"  # 测试中
    ACTIVE = "active"  # 已激活
    DEPRECATED = "deprecated"  # 已弃用


# 数据库模型
class AIModelConfigDB(Base):
    """AI模型配置表"""
    __tablename__ = 'ai_model_configs'
    __table_args__ = {'comment': 'AI大模型编排配置表 - 存储AI算法模板配置信息'}
    
    # 主键和基本信息
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='配置唯一ID')
    name = Column(String(255), nullable=False, comment='算法名称')
    description = Column(Text, comment='算法描述')
    
    # AI模型相关
    provider = Column(
        String(100), 
        nullable=False,
        comment='AI模型供应商名称(引用ai_provider_configs.provider_name)'
    )
    model_name = Column(String(200), nullable=False, comment='具体模型名称')
    model_type = Column(
        ENUM('vision', 'text', 'multimodal', name='ai_model_type_enum'),
        default='vision',
        comment='模型类型'
    )
    
    # 提示词配置
    system_prompt = Column(Text, comment='系统提示词')
    user_prompt = Column(Text, comment='用户提示词')
    
    # 模型参数
    temperature = Column(Float, default=0.7, comment='温度参数(0-2)')
    top_p = Column(Float, default=0.9, comment='Top-p参数(0-1)')
    max_tokens = Column(Integer, default=1000, comment='最大token数')
    
    # 业务配置
    confidence_threshold = Column(Float, default=0.7, comment='置信度阈值(0-1)')
    tags = Column(ARRAY(String), default=[], comment='算法标签')

    # 复合检测配置（新增）
    detection_capabilities = Column(
        JSON,
        default=[],
        comment='支持的检测能力列表，JSONB数组格式，示例: ["safety_helmet", "smoking", "using_phone"]'
    )

    # 状态和统计
    status = Column(
        ENUM('draft', 'testing', 'active', 'deprecated', name='algorithm_status_enum'),
        default='draft',
        comment='算法状态'
    )
    test_count = Column(Integer, default=0, comment='测试次数')
    success_count = Column(Integer, default=0, comment='成功次数')
    
    # 扩展配置
    extra_config = Column(JSON, default={}, comment='扩展配置JSON')
    
    # 时间戳
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.current_timestamp(), 
        comment='创建时间'
    )
    updated_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.current_timestamp(), 
        onupdate=func.current_timestamp(),
        comment='更新时间'
    )


class AITestResultDB(Base):
    """AI测试结果表"""
    __tablename__ = 'ai_test_results'
    __table_args__ = {'comment': 'AI算法测试结果表 - 存储调试测试的结果记录'}
    
    # 主键和关联
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='结果唯一ID')
    config_id = Column(UUID(as_uuid=True), nullable=False, comment='关联的配置ID')
    
    # 测试输入
    input_image_path = Column(String(1000), comment='测试图片路径')
    input_text = Column(Text, comment='输入文本')
    
    # 测试结果
    ai_response = Column(Text, comment='AI模型完整响应')
    confidence_score = Column(Float, comment='置信度分数')
    processing_time = Column(Float, comment='处理耗时(秒)')
    
    # 结果状态
    is_success = Column(Boolean, default=True, comment='是否成功')
    error_message = Column(Text, comment='错误信息')
    
    # 时间戳
    created_at = Column(
        TIMESTAMP(timezone=True), 
        server_default=func.current_timestamp(), 
        comment='创建时间'
    )


# Pydantic模型 - API请求响应
class AIModelConfigCreate(BaseModel):
    """创建AI模型配置请求"""
    model_config = ConfigDict(protected_namespaces=())

    name: str = Field(..., description="算法名称")
    description: Optional[str] = Field(None, description="算法描述")
    provider: str = Field(..., description="AI模型供应商名称")
    model_name: str = Field(..., description="具体模型名称")
    model_type: AIModelTypeEnum = Field(default=AIModelTypeEnum.VISION, description="模型类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    user_prompt: Optional[str] = Field(None, description="用户提示词")
    temperature: float = Field(default=0.7, ge=0, le=2, description="温度参数")
    top_p: float = Field(default=0.9, ge=0, le=1, description="Top-p参数")
    max_tokens: int = Field(default=1000, ge=1, le=4000, description="最大token数")
    confidence_threshold: float = Field(default=0.7, ge=0, le=1, description="置信度阈值")
    tags: List[str] = Field(default=[], description="算法标签")
    detection_capabilities: List[str] = Field(default=[], description="支持的检测能力列表，示例: ['safety_helmet', 'smoking']")
    extra_config: Dict[str, Any] = Field(default={}, description="扩展配置")


class AIModelConfigUpdate(BaseModel):
    """更新AI模型配置请求"""
    model_config = ConfigDict(protected_namespaces=())

    name: Optional[str] = Field(None, description="算法名称")
    description: Optional[str] = Field(None, description="算法描述")
    provider: Optional[str] = Field(None, description="AI模型供应商名称")
    model_name: Optional[str] = Field(None, description="具体模型名称")
    model_type: Optional[AIModelTypeEnum] = Field(None, description="模型类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    user_prompt: Optional[str] = Field(None, description="用户提示词")
    temperature: Optional[float] = Field(None, ge=0, le=2, description="温度参数")
    top_p: Optional[float] = Field(None, ge=0, le=1, description="Top-p参数")
    max_tokens: Optional[int] = Field(None, ge=1, le=4000, description="最大token数")
    confidence_threshold: Optional[float] = Field(None, ge=0, le=1, description="置信度阈值")
    tags: Optional[List[str]] = Field(None, description="算法标签")
    detection_capabilities: Optional[List[str]] = Field(None, description="支持的检测能力列表")
    status: Optional[AlgorithmStatusEnum] = Field(None, description="算法状态")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="扩展配置")


class AIModelConfigResponse(BaseModel):
    """AI模型配置响应"""
    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(..., description="配置ID")
    name: str = Field(..., description="算法名称")
    description: Optional[str] = Field(None, description="算法描述")
    provider: str = Field(..., description="AI模型供应商名称")
    model_name: str = Field(..., description="具体模型名称")
    model_type: AIModelTypeEnum = Field(..., description="模型类型")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    user_prompt: Optional[str] = Field(None, description="用户提示词")
    temperature: float = Field(..., description="温度参数")
    top_p: float = Field(..., description="Top-p参数")
    max_tokens: int = Field(..., description="最大token数")
    confidence_threshold: float = Field(..., description="置信度阈值")
    tags: List[str] = Field(..., description="算法标签")
    detection_capabilities: List[str] = Field(default=[], description="支持的检测能力列表")
    status: AlgorithmStatusEnum = Field(..., description="算法状态")
    test_count: int = Field(..., description="测试次数")
    success_count: int = Field(..., description="成功次数")
    extra_config: Dict[str, Any] = Field(..., description="扩展配置")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")


class AITestRequest(BaseModel):
    """AI测试请求"""
    config_id: str = Field(..., description="配置ID")
    image_data: Optional[str] = Field(None, description="图片base64数据")
    input_text: Optional[str] = Field(None, description="输入文本")


class AITestResponse(BaseModel):
    """AI测试响应"""
    id: str = Field(..., description="测试结果ID")
    ai_response: str = Field(..., description="AI模型响应")
    confidence_score: Optional[float] = Field(None, description="置信度分数")
    processing_time: float = Field(..., description="处理耗时(秒)")
    is_success: bool = Field(..., description="是否成功")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: str = Field(..., description="创建时间")


# 模型选项配置
AI_MODEL_OPTIONS = {
    AIProviderEnum.QWEN: [
        "qwen-vl-plus",
        "qwen-vl-max",
        "qwen-turbo",
        "qwen-plus",
        "qwen-max"
    ],
    AIProviderEnum.MOONSHOT: [
        "moonshot-v1-8k",
        "moonshot-v1-32k", 
        "moonshot-v1-128k"
    ],
    AIProviderEnum.GPT: [
        "gpt-4-vision-preview",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo"
    ],
    AIProviderEnum.CLAUDE: [
        "claude-3-opus",
        "claude-3-sonnet",
        "claude-3-haiku"
    ],
    AIProviderEnum.GEMINI: [
        "gemini-1.5-pro",
        "gemini-1.0-pro-vision",
        "gemini-1.0-pro"
    ],
    AIProviderEnum.BAIDU: [
        "ernie-4.0-turbo",
        "ernie-3.5-turbo",
        "ernie-bot-4"
    ],
    AIProviderEnum.LANYI: [
        "lanyi-instruct",
        "lanyi-qwen2.5-vl-72b-instruct",
        "lanyi-qwen3-235b-instruct",
        "lanyi-glm-4.5"
    ]
}