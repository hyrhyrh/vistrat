"""
AI供应商配置数据模型
"""

from enum import Enum as PyEnum
from typing import List, Optional, Dict, Any
from uuid import uuid4
from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Text, Boolean, TIMESTAMP, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database.connection import Base


class AIProviderConfigDB(Base):
    """AI供应商配置表"""
    __tablename__ = 'ai_provider_configs'
    __table_args__ = {'comment': 'AI供应商配置表 - 存储各AI厂商的API配置信息'}
    
    # 主键和基本信息
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='配置唯一ID')
    provider_name = Column(String(100), nullable=False, unique=True, comment='供应商名称')
    display_name = Column(String(200), nullable=False, comment='显示名称')
    icon = Column(String(50), default='🤖', comment='图标')
    description = Column(Text, comment='供应商描述')
    
    # API配置
    api_base_url = Column(String(500), nullable=False, comment='API基础地址')
    api_key = Column(String(500), comment='API密钥')
    api_version = Column(String(50), default='v1', comment='API版本')
    
    # 模型配置
    available_models = Column(JSON, default=[], comment='可用模型列表')
    default_model = Column(String(200), comment='默认模型')
    
    # 请求配置
    max_tokens_limit = Column(JSON, default={}, comment='Token限制配置')
    request_headers = Column(JSON, default={}, comment='请求头配置') 
    request_timeout = Column(Integer, default=60, comment='请求超时时间')
    
    # 状态和扩展
    is_active = Column(Boolean, default=True, comment='是否启用')
    sort_order = Column(Integer, default=0, comment='排序顺序')
    extra_config = Column(JSON, default={}, comment='扩展配置')
    
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


# Pydantic模型
class AIProviderConfigBase(BaseModel):
    """AI供应商配置基础模型"""
    provider_name: str = Field(..., description="供应商名称", max_length=100)
    display_name: str = Field(..., description="显示名称", max_length=200)
    icon: str = Field("🤖", description="图标", max_length=50)
    description: Optional[str] = Field(None, description="供应商描述")
    
    api_base_url: str = Field(..., description="API基础地址", max_length=500)
    api_key: Optional[str] = Field(None, description="API密钥")
    api_version: str = Field("v1", description="API版本", max_length=50)
    
    available_models: List[str] = Field(default_factory=list, description="可用模型列表")
    default_model: Optional[str] = Field(None, description="默认模型")
    
    max_tokens_limit: Dict[str, int] = Field(default_factory=dict, description="Token限制配置")
    request_headers: Dict[str, str] = Field(default_factory=dict, description="请求头配置")
    request_timeout: int = Field(60, description="请求超时时间")
    
    is_active: bool = Field(True, description="是否启用")
    sort_order: int = Field(0, description="排序顺序")
    extra_config: Dict[str, Any] = Field(default_factory=dict, description="扩展配置")


class AIProviderConfigCreate(AIProviderConfigBase):
    """创建AI供应商配置请求模型"""
    pass


class AIProviderConfigUpdate(BaseModel):
    """更新AI供应商配置请求模型"""
    display_name: Optional[str] = Field(None, description="显示名称")
    icon: Optional[str] = Field(None, description="图标")
    description: Optional[str] = Field(None, description="供应商描述")
    
    api_base_url: Optional[str] = Field(None, description="API基础地址")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_version: Optional[str] = Field(None, description="API版本")
    
    available_models: Optional[List[str]] = Field(None, description="可用模型列表")
    default_model: Optional[str] = Field(None, description="默认模型")
    
    max_tokens_limit: Optional[Dict[str, int]] = Field(None, description="Token限制配置")
    request_headers: Optional[Dict[str, str]] = Field(None, description="请求头配置")
    request_timeout: Optional[int] = Field(None, description="请求超时时间")
    
    is_active: Optional[bool] = Field(None, description="是否启用")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="扩展配置")


class AIProviderConfigResponse(AIProviderConfigBase):
    """AI供应商配置响应模型"""
    id: str = Field(..., description="配置唯一ID")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class AIProviderSimple(BaseModel):
    """简化的AI供应商信息"""
    id: str = Field(..., description="配置ID")
    provider_name: str = Field(..., description="供应商名称")
    display_name: str = Field(..., description="显示名称")
    icon: str = Field(..., description="图标")
    available_models: List[str] = Field(..., description="可用模型列表")
    is_active: bool = Field(..., description="是否启用")
    
    class Config:
        from_attributes = True