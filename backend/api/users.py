"""
用户管理API端点
提供用户的增删改查和密码管理功能
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

from models.auth import UserCreate, UserResponse, UserRoleEnum
from services.auth_service import AuthService
from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["user_management"])


# Pydantic模型
class UserUpdateRequest(BaseModel):
    """用户更新请求模型"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role: Optional[UserRoleEnum] = Field(None, description="用户角色")
    is_active: Optional[bool] = Field(None, description="是否激活")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")


class ChangePasswordRequest(BaseModel):
    """修改密码请求模型"""
    user_id: str = Field(..., description="用户ID")
    new_password: str = Field(..., min_length=6, description="新密码")


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    id: str
    username: str
    email: Optional[str]
    role: str
    is_active: bool
    created_at: str  # 格式化为字符串
    last_login: Optional[str] = None  # 格式化为字符串
    full_name: Optional[str] = None


def check_admin_permission(current_user: UserResponse = Depends(get_current_user)):
    """检查管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


@router.get("", response_model=List[UserListResponse])
async def get_users(current_user: UserResponse = Depends(check_admin_permission)):
    """获取用户列表（仅管理员）"""
    try:
        users = await AuthService.get_all_users()
        
        # 转换为响应格式
        user_list = []
        for user in users:
            user_data = {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "role": user.role.value if hasattr(user.role, 'value') else str(user.role),
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login_at.isoformat() if user.last_login_at else None,
                "full_name": user.full_name
            }
            user_list.append(UserListResponse(**user_data))
        
        return user_list
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户列表失败"
        )


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: UserResponse = Depends(check_admin_permission)
):
    """创建新用户（仅管理员）"""
    try:
        user = await AuthService.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"创建用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建用户失败"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: str,
    current_user: UserResponse = Depends(check_admin_permission)
):
    """根据ID获取用户信息（仅管理员）"""
    try:
        user = await AuthService.get_user_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    user_data: UserUpdateRequest,
    current_user: UserResponse = Depends(check_admin_permission)
):
    """更新用户信息（仅管理员）"""
    try:
        # 检查用户是否存在
        existing_user = await AuthService.get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 防止管理员禁用自己
        if user_id == current_user.id and user_data.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能禁用自己的账户"
            )
        
        # 防止修改系统管理员用户的角色和状态
        if existing_user.username == "admin":
            if user_data.role is not None and user_data.role.value != "admin":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能修改系统管理员的角色"
                )
            if user_data.is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能禁用系统管理员用户"
                )
        
        # 更新用户信息
        updated_user = await AuthService.update_user(user_id, user_data.dict(exclude_unset=True))
        return updated_user
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户失败"
        )


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserResponse = Depends(check_admin_permission)
):
    """删除用户（仅管理员）"""
    try:
        # 检查用户是否存在
        existing_user = await AuthService.get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 防止管理员删除自己
        if user_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除自己的账户"
            )
        
        # 防止删除系统管理员用户(用户名为admin)
        if existing_user.username == "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能删除系统管理员用户"
            )
        
        # 删除用户
        success = await AuthService.delete_user(user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="删除用户失败"
            )
        
        return {"message": "用户删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败"
        )


@router.put("/{user_id}/password")
async def change_user_password(
    user_id: str,
    password_data: ChangePasswordRequest,
    current_user: UserResponse = Depends(check_admin_permission)
):
    """修改用户密码（仅管理员）"""
    try:
        # 检查用户是否存在
        existing_user = await AuthService.get_user_by_id(user_id)
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        # 验证user_id匹配
        if password_data.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户ID不匹配"
            )
        
        # 修改密码
        success = await AuthService.change_password(user_id, password_data.new_password)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="修改密码失败"
            )
        
        return {"message": "密码修改成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败"
        )