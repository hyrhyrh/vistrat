"""
用户认证API端点
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from models.auth import UserCreate, UserLogin, UserResponse, LoginResponse
from services.auth_service import AuthService
from utils.sso_crypto import sso_crypto

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserResponse:
    """获取当前登录用户（从HTTP Authorization头）"""
    try:
        user = await AuthService.get_current_user(credentials.credentials)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证令牌",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        logger.error(f"获取当前用户失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_from_query(token: Optional[str] = Query(None, description="认证令牌")) -> UserResponse:
    """获取当前登录用户（从查询参数，用于SSE等无法设置Header的场景）"""
    logger.info(f"[Query Auth] 收到token认证请求, token存在: {token is not None}")

    if not token:
        logger.warning("[Query Auth] Token为空，拒绝访问")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )

    try:
        logger.info("[Query Auth] 调用AuthService验证token")
        user = await AuthService.get_current_user(token)
        if not user:
            logger.warning("[Query Auth] AuthService返回None，token验证失败")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authenticated",
            )
        logger.info(f"[Query Auth] 认证成功, 用户: {user.username}")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Query Auth] 获取当前用户失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authenticated",
        )


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """用户注册"""
    try:
        user = await AuthService.create_user(user_data)
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="注册失败")


@router.post("/login", response_model=LoginResponse)
async def login(login_data: UserLogin):
    """用户登录"""
    try:
        result = await AuthService.login(login_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="登录失败")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user


@router.post("/logout")
async def logout():
    """用户登出（客户端需要清除token）"""
    return {"message": "成功登出"}


@router.get("/verify")
async def verify_token(current_user: UserResponse = Depends(get_current_user)):
    """验证token有效性"""
    return {"valid": True, "user": current_user}


@router.get("/sso-login", response_model=LoginResponse)
async def sso_login(token: str = Query(..., description="加密的登录凭证")):
    """
    SSO单点登录接口

    通过加密的token参数进行单点登录，解密后验证用户并返回JWT token

    Args:
        token: 加密的用户凭证（包含用户名和密码）

    Returns:
        LoginResponse: 包含JWT token和用户信息

    Example:
        GET /auth/sso-login?token=<encrypted_credentials>
    """
    try:
        # 解密token获取用户名和密码
        credentials = sso_crypto.decrypt_credentials(token)

        if not credentials:
            logger.warning("[SSO Login] 解密凭证失败")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的登录凭证"
            )

        username = credentials.get("username")
        password = credentials.get("password")

        if not username or not password:
            logger.warning("[SSO Login] 凭证格式不正确")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的登录凭证"
            )

        logger.info(f"[SSO Login] 尝试SSO登录, 用户名: {username}")

        # 使用AuthService进行登录验证
        login_data = UserLogin(username=username, password=password)
        result = await AuthService.login(login_data)

        logger.info(f"[SSO Login] SSO登录成功, 用户: {username}")
        return result

    except ValueError as e:
        logger.warning(f"[SSO Login] 登录验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[SSO Login] SSO登录失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )