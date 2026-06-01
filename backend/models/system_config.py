"""
系统配置模型
对应PostgreSQL表: system_configs
从MySQL dc_system_param 转换而来
"""

from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from database.connection import Base


class SystemConfigDB(Base):
    """系统配置数据库模型"""
    __tablename__ = 'system_configs'
    __table_args__ = {'comment': '系统配置参数表'}

    param_code = Column(
        String(50), 
        primary_key=True,
        comment='配置参数编码(主键)'
    )
    param_desc = Column(
        String(250), 
        nullable=False,
        comment='配置参数描述'
    )
    param_val = Column(
        String(1000), 
        nullable=False,
        comment='配置参数值'
    )
    ext_val = Column(
        String(1000), 
        nullable=True,
        default=None,
        comment='扩展配置值'
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment='创建时间'
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        comment='更新时间'
    )

    def __repr__(self):
        return f"<SystemConfig(code='{self.param_code}', desc='{self.param_desc}')>"


# Pydantic模型
class SystemConfigBase(BaseModel):
    """系统配置基础模型"""
    param_code: str = Field(..., max_length=50, description="配置参数编码")
    param_desc: str = Field(..., max_length=250, description="配置参数描述")
    param_val: str = Field(..., max_length=1000, description="配置参数值")
    ext_val: Optional[str] = Field(None, max_length=1000, description="扩展配置值")


class SystemConfigCreate(SystemConfigBase):
    """创建系统配置模型"""
    pass


class SystemConfigUpdate(BaseModel):
    """更新系统配置模型"""
    param_desc: Optional[str] = Field(None, max_length=250, description="配置参数描述")
    param_val: Optional[str] = Field(None, max_length=1000, description="配置参数值")
    ext_val: Optional[str] = Field(None, max_length=1000, description="扩展配置值")


class SystemConfigResponse(SystemConfigBase):
    """系统配置响应模型"""
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class SystemConfigList(BaseModel):
    """系统配置列表响应"""
    configs: list[SystemConfigResponse] = Field(..., description="配置列表")
    total: int = Field(..., description="总数量")