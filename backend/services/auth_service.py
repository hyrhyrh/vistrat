"""
用户认证服务
"""

import logging
import os
from datetime import datetime, timedelta
from utils.timezone_utils import now, beijing_to_utc
from typing import Optional, List, Dict, Any
from uuid import UUID
import bcrypt
import jwt
from sqlalchemy import select, update, delete

from database.connection import DatabaseManager
from models.auth import UserDB, UserCreate, UserLogin, UserResponse, LoginResponse, TokenData, UserRoleEnum
from config.settings import ServerConfig

logger = logging.getLogger(__name__)

# JWT配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if not SECRET_KEY:
    import warnings
    SECRET_KEY = "dev-only-insecure-key-do-not-use-in-production"
    warnings.warn("JWT_SECRET_KEY 未设置，使用开发默认值。生产环境必须配置此变量！", stacklevel=2)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))  # 从环境变量读取,默认24小时


class AuthService:
    """认证服务"""
    
    @staticmethod
    def _hash_password(password: str) -> str:
        """密码哈希"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    @staticmethod
    def _create_access_token(data: dict) -> str:
        """创建JWT token"""
        to_encode = data.copy()
        # JWT需要使用UTC时间，所以先获取北京时间再转换
        beijing_expire = now() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
        expire = beijing_to_utc(beijing_expire)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def _verify_token(token: str) -> Optional[TokenData]:
        """验证JWT token"""
        try:
            logger.info("[Token Verify] 开始解码JWT token")
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
            username: str = payload.get("username")
            logger.info(f"[Token Verify] JWT解码成功, username={username}")
            if user_id is None:
                logger.warning("[Token Verify] payload中没有sub字段")
                return None
            return TokenData(user_id=user_id, username=username)
        except jwt.ExpiredSignatureError as e:
            logger.warning(f"[Token Verify] Token已过期: {e}")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"[Token Verify] Token无效: {e}")
            return None
        except Exception as e:
            logger.error(f"[Token Verify] Token验证异常: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _db_to_response(db_user: UserDB) -> UserResponse:
        """将数据库对象转换为响应模型"""
        return UserResponse(
            id=str(db_user.id),
            username=db_user.username,
            email=db_user.email,
            role=db_user.role.value if hasattr(db_user.role, 'value') else str(db_user.role),
            full_name=db_user.full_name,
            # phone=db_user.phone,
            # department=db_user.department,
            is_active=db_user.is_active,
            created_at=db_user.created_at,
            last_login_at=db_user.last_login_at
        )
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> UserResponse:
        """创建用户"""
        async with DatabaseManager.get_session() as session:
            # 检查用户名是否存在
            stmt = select(UserDB).where(UserDB.username == user_data.username)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                raise ValueError("用户名已存在")
            
            # 检查邮箱是否存在
            if user_data.email:
                stmt = select(UserDB).where(UserDB.email == user_data.email)
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    raise ValueError("邮箱已存在")
            
            # 创建用户
            password_hash = AuthService._hash_password(user_data.password)
            db_user = UserDB(
                username=user_data.username,
                email=user_data.email,
                password_hash=password_hash,
                full_name=user_data.full_name,
                # phone=user_data.phone,
                # department=user_data.department,
                role=user_data.role if user_data.role else UserRoleEnum.user
            )
            
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
            
            return AuthService._db_to_response(db_user)
    
    @staticmethod
    async def authenticate_user(username: str, password: str) -> Optional[UserDB]:
        """验证用户"""
        async with DatabaseManager.get_session() as session:
            stmt = select(UserDB).where(
                UserDB.username == username,
                UserDB.is_active == True
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                return None

            if not AuthService._verify_password(password, user.password_hash):
                return None

            # 更新最后登录时间
            stmt = update(UserDB).where(UserDB.id == user.id).values(
                last_login_at=now()
            )
            await session.execute(stmt)
            await session.commit()

            return user
    
    @staticmethod
    async def login(login_data: UserLogin) -> LoginResponse:
        """用户登录"""
        user = await AuthService.authenticate_user(login_data.username, login_data.password)
        if not user:
            raise ValueError("用户名或密码错误")
        
        # 创建token
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
        }
        access_token = AuthService._create_access_token(token_data)
        
        return LoginResponse(
            token=access_token,
            user=AuthService._db_to_response(user)
        )
    
    @staticmethod
    async def get_current_user(token: str) -> Optional[UserResponse]:
        """根据token获取当前用户"""
        logger.info("[Get Current User] 开始获取当前用户")
        token_data = AuthService._verify_token(token)
        if not token_data or not token_data.user_id:
            logger.warning("[Get Current User] Token验证失败或无user_id")
            return None

        logger.info(f"[Get Current User] Token验证成功, 查询数据库user_id={token_data.user_id}")
        async with DatabaseManager.get_session() as session:
            stmt = select(UserDB).where(
                UserDB.id == UUID(token_data.user_id),
                UserDB.is_active == True
            )
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.warning(f"[Get Current User] 数据库中未找到用户或用户未激活, user_id={token_data.user_id}")
                return None

            logger.info(f"[Get Current User] 查询成功, username={user.username}")
            return AuthService._db_to_response(user)
    
    @staticmethod
    async def init_admin_user():
        """初始化管理员用户"""
        try:
            async with DatabaseManager.get_session() as session:
                # 检查是否已存在admin用户
                stmt = select(UserDB).where(UserDB.username == "admin")
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    logger.info("管理员用户已存在")
                    return

                # 创建默认管理员用户
                from models.auth import UserRoleEnum
                admin_user = UserDB(
                    username="admin",
                    email="admin@example.com",
                    password_hash=AuthService._hash_password("admin123"),
                    role=UserRoleEnum.admin,
                    full_name="系统管理员",
                    is_active=True
                )

                session.add(admin_user)
                await session.commit()
                logger.info("默认管理员用户创建成功: admin/admin123")

        except Exception as e:
            logger.error(f"初始化管理员用户失败: {e}")
    
    # 用户管理相关方法
    @staticmethod
    async def get_all_users() -> List[UserDB]:
        """获取所有用户"""
        async with DatabaseManager.get_session() as session:
            stmt = select(UserDB).order_by(UserDB.created_at.desc())
            result = await session.execute(stmt)
            users = result.scalars().all()
            return list(users)

    @staticmethod
    async def get_user_by_id(user_id: str) -> Optional[UserResponse]:
        """根据ID获取用户"""
        try:
            async with DatabaseManager.get_session() as session:
                stmt = select(UserDB).where(UserDB.id == UUID(user_id))
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if not user:
                    return None

                return AuthService._db_to_response(user)
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None

    @staticmethod
    async def update_user(user_id: str, update_data: Dict[str, Any]) -> UserResponse:
        """更新用户信息"""
        async with DatabaseManager.get_session() as session:
            # 检查用户名和邮箱唯一性
            if 'username' in update_data:
                stmt = select(UserDB).where(
                    UserDB.username == update_data['username'],
                    UserDB.id != UUID(user_id)
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    raise ValueError("用户名已存在")

            if 'email' in update_data and update_data['email']:
                stmt = select(UserDB).where(
                    UserDB.email == update_data['email'],
                    UserDB.id != UUID(user_id)
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    raise ValueError("邮箱已存在")

            # 处理角色字段
            if 'role' in update_data:
                if isinstance(update_data['role'], str):
                    update_data['role'] = UserRoleEnum(update_data['role'])

            # 更新用户
            stmt = update(UserDB).where(UserDB.id == UUID(user_id)).values(**update_data)
            await session.execute(stmt)
            await session.commit()

            # 返回更新后的用户
            return await AuthService.get_user_by_id(user_id)

    @staticmethod
    async def delete_user(user_id: str) -> bool:
        """删除用户"""
        try:
            async with DatabaseManager.get_session() as session:
                stmt = delete(UserDB).where(UserDB.id == UUID(user_id))
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"删除用户失败: {e}")
            return False

    @staticmethod
    async def change_password(user_id: str, new_password: str) -> bool:
        """修改用户密码"""
        try:
            async with DatabaseManager.get_session() as session:
                password_hash = AuthService._hash_password(new_password)
                stmt = update(UserDB).where(UserDB.id == UUID(user_id)).values(
                    password_hash=password_hash
                )
                result = await session.execute(stmt)
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"修改密码失败: {e}")
            return False