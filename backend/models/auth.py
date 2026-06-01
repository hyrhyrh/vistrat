"""
用户认证相关的数据模型
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, String, Boolean, TIMESTAMP, Text, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

from database.connection import Base


class UserRoleEnum(PyEnum):
    """用户角色枚举"""
    admin = "admin"
    user = "user"
    viewer = "viewer"


# SQLAlchemy数据库模型
class UserDB(Base):
    """用户数据库表模型"""
    __tablename__ = "users"
    __table_args__ = {'comment': '用户信息表'}
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, comment='用户唯一ID')
    username = Column(String(50), unique=True, nullable=False, comment='用户名')
    email = Column(String(100), unique=True, comment='邮箱')
    password_hash = Column(String(255), nullable=False, comment='密码哈希')
    role = Column(Enum(UserRoleEnum, name='user_role_enum'), default=UserRoleEnum.user, comment='用户角色')
    is_active = Column(Boolean, default=True, comment='是否激活')
    
    # 用户信息
    full_name = Column(String(100), comment='全名')
    # phone = Column(String(20), comment='电话')
    # department = Column(String(100), comment='部门')
    
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
    last_login_at = Column(TIMESTAMP(timezone=True), comment='最后登录时间')

    # 关系
    agent_history = relationship("AgentHistoryDB", back_populates="user", cascade="all, delete-orphan")
    agent_sessions = relationship("AgentSessionDB", back_populates="user", cascade="all, delete-orphan")


# Pydantic模型用于API
class UserCreate(BaseModel):
    """创建用户请求模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    password: str = Field(..., min_length=6, description="密码")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    # phone: Optional[str] = Field(None, max_length=20, description="电话")
    # department: Optional[str] = Field(None, max_length=100, description="部门")
    role: Optional[UserRoleEnum] = Field(UserRoleEnum.user, description="用户角色")


class UserLogin(BaseModel):
    """用户登录请求模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """用户信息响应模型"""
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role: str = Field(..., description="用户角色")
    full_name: Optional[str] = Field(None, description="全名")
    # phone: Optional[str] = Field(None, description="电话")
    # department: Optional[str] = Field(None, description="部门")
    is_active: bool = Field(..., description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    last_login_at: Optional[datetime] = Field(None, description="最后登录时间")

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """登录响应模型"""
    token: str = Field(..., description="JWT令牌")
    user: UserResponse = Field(..., description="用户信息")


class TokenData(BaseModel):
    """Token数据模型"""
    user_id: Optional[str] = None
    username: Optional[str] = None