"""
用户数据库模型（v3.0）
精简用户表，仅保留核心认证字段
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import UUID
from pydantic import BaseModel, Field

from models.base import Base, TimestampMixin, ProjectMixin


class UserDB(TimestampMixin, ProjectMixin, Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='user')


# Pydantic 模型
class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=100, description="用户名")
    password: str = Field(..., min_length=6, description="密码")
    role: Optional[str] = Field(default="user", description="用户角色")
    project_id: Optional[str] = Field(None, description="项目ID")


class UserResponse(BaseModel):
    """用户响应"""
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    role: str = Field(..., description="用户角色")
    project_id: Optional[str] = Field(None, description="项目ID")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True
