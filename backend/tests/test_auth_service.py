"""
认证服务单元测试
覆盖 JWT token 生成/验证、密码哈希、token 过期、用户 CRUD 等场景
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from uuid import uuid4

import pytest
import bcrypt
import jwt

# 确保 backend 在 sys.path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# 设置测试用的 JWT 密钥（在导入 auth_service 之前）
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-unit-tests")

from services.auth_service import AuthService, SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_HOURS


# ============================================================================
# 密码哈希测试
# ============================================================================

class TestPasswordHashing:
    """密码哈希与验证测试"""

    def test_hash_password_生成有效哈希(self):
        """密码哈希应生成 bcrypt 格式的哈希值"""
        password = "my_secure_password"
        hashed = AuthService._hash_password(password)
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
        assert len(hashed) == 60

    def test_hash_password_相同密码生成不同哈希(self):
        """相同密码每次哈希结果不同（因为 salt 不同）"""
        password = "same_password"
        hash1 = AuthService._hash_password(password)
        hash2 = AuthService._hash_password(password)
        assert hash1 != hash2

    def test_verify_password_正确密码验证通过(self):
        """正确密码应验证通过"""
        password = "correct_password"
        hashed = AuthService._hash_password(password)
        assert AuthService._verify_password(password, hashed) is True

    def test_verify_password_错误密码验证失败(self):
        """错误密码应验证失败"""
        password = "correct_password"
        hashed = AuthService._hash_password(password)
        assert AuthService._verify_password("wrong_password", hashed) is False

    @pytest.mark.parametrize("password", [
        "短密",
        "a" * 72,  # bcrypt 最大长度
        "p@$$w0rd!#%^&*()",
        "中文密码测试",
        "   spaces   ",
    ])
    def test_hash_password_各种密码格式(self, password):
        """各种格式的密码都能正确哈希和验证"""
        hashed = AuthService._hash_password(password)
        assert AuthService._verify_password(password, hashed) is True


# ============================================================================
# JWT Token 测试
# ============================================================================

class TestJWTToken:
    """JWT Token 生成与验证测试"""

    def test_create_access_token_生成有效token(self):
        """创建的 token 应可正常解码"""
        data = {"sub": "user-123", "username": "testuser", "role": "user"}
        token = AuthService._create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0

        # 解码验证
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "user-123"
        assert payload["username"] == "testuser"
        assert "exp" in payload

    def test_create_access_token_包含过期时间(self):
        """Token 应包含正确的过期时间"""
        data = {"sub": "user-123", "username": "testuser"}
        token = AuthService._create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now_utc = datetime.now(tz=timezone.utc)

        # 过期时间应在 ACCESS_TOKEN_EXPIRE_HOURS 小时之内（允许几分钟误差）
        delta = exp - now_utc
        assert timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS - 1) < delta < timedelta(
            hours=ACCESS_TOKEN_EXPIRE_HOURS + 1
        )

    def test_verify_token_有效token返回TokenData(self):
        """有效 token 应返回 TokenData 对象"""
        data = {"sub": "user-456", "username": "admin"}
        token = AuthService._create_access_token(data)

        result = AuthService._verify_token(token)
        assert result is not None
        assert result.user_id == "user-456"
        assert result.username == "admin"

    def test_verify_token_过期token返回None(self):
        """过期 token 应返回 None"""
        data = {"sub": "user-789", "username": "expired_user"}
        # 手动创建一个已过期的 token
        to_encode = data.copy()
        to_encode["exp"] = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        expired_token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

        result = AuthService._verify_token(expired_token)
        assert result is None

    def test_verify_token_无效token返回None(self):
        """无效 token 应返回 None"""
        result = AuthService._verify_token("invalid.token.string")
        assert result is None

    def test_verify_token_错误密钥签名返回None(self):
        """使用错误密钥签名的 token 应返回 None"""
        data = {"sub": "user-000", "username": "hacker"}
        wrong_key_token = jwt.encode(
            {**data, "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1)},
            "wrong-secret-key",
            algorithm=ALGORITHM,
        )
        result = AuthService._verify_token(wrong_key_token)
        assert result is None

    def test_verify_token_缺少sub字段返回None(self):
        """缺少 sub 字段的 token 应返回 None"""
        payload = {
            "username": "no_sub_user",
            "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        result = AuthService._verify_token(token)
        assert result is None

    def test_create_access_token_不修改原始数据(self):
        """创建 token 时不应修改原始数据字典"""
        data = {"sub": "user-100", "username": "test"}
        original_keys = set(data.keys())
        AuthService._create_access_token(data)
        assert set(data.keys()) == original_keys


# ============================================================================
# 数据库对象转响应模型测试
# ============================================================================

class TestDBToResponse:
    """数据库对象转换为响应模型"""

    def test_db_to_response_正确转换所有字段(self):
        """数据库用户对象应正确映射到 UserResponse"""
        from models.auth import UserRoleEnum

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.role = UserRoleEnum.admin
        mock_user.full_name = "测试用户"
        mock_user.is_active = True
        mock_user.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        mock_user.last_login_at = datetime(2024, 6, 1, tzinfo=timezone.utc)

        result = AuthService._db_to_response(mock_user)

        assert result.id == str(mock_user.id)
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.role == "admin"
        assert result.full_name == "测试用户"
        assert result.is_active is True

    def test_db_to_response_role为字符串(self):
        """当 role 是普通字符串（无 value 属性）时也应正确处理"""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.username = "stringrole"
        mock_user.email = None
        # 使用一个没有 value 属性的对象
        mock_user.role = "viewer"
        mock_user.full_name = None
        mock_user.is_active = True
        mock_user.created_at = datetime.now(tz=timezone.utc)
        mock_user.last_login_at = None

        result = AuthService._db_to_response(mock_user)
        # 字符串有 value 属性（str 本身没有，但 hasattr 会检查），
        # 实际会走 str(db_user.role) 分支
        assert result.role == "viewer"


# ============================================================================
# 用户认证流程测试（mock 数据库）
# ============================================================================

class TestAuthenticateUser:
    """用户认证流程测试"""

    @pytest.mark.asyncio
    async def test_authenticate_user_用户不存在返回None(self, mock_db_session):
        """不存在的用户应返回 None"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("services.auth_service.DatabaseManager.get_session", return_value=mock_ctx):
            result = await AuthService.authenticate_user("nonexistent", "password")
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_密码错误返回None(self, mock_db_session):
        """密码错误应返回 None"""
        mock_user = MagicMock()
        mock_user.password_hash = AuthService._hash_password("correct_password")
        mock_user.id = uuid4()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("services.auth_service.DatabaseManager.get_session", return_value=mock_ctx):
            result = await AuthService.authenticate_user("testuser", "wrong_password")
            assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_user_正确凭据返回用户(self, mock_db_session):
        """正确凭据应返回用户对象并更新登录时间"""
        password = "correct_password"
        mock_user = MagicMock()
        mock_user.password_hash = AuthService._hash_password(password)
        mock_user.id = uuid4()

        # 第一次 execute 返回用户，第二次是 update 操作
        mock_result_select = MagicMock()
        mock_result_select.scalar_one_or_none.return_value = mock_user
        mock_result_update = MagicMock()

        mock_db_session.execute.side_effect = [mock_result_select, mock_result_update]

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("services.auth_service.DatabaseManager.get_session", return_value=mock_ctx):
            result = await AuthService.authenticate_user("testuser", password)
            assert result is mock_user
            # 验证 commit 被调用（更新最后登录时间）
            mock_db_session.commit.assert_called_once()


class TestLogin:
    """用户登录测试"""

    @pytest.mark.asyncio
    async def test_login_成功返回token和用户信息(self):
        """成功登录应返回 token 和用户响应"""
        from models.auth import UserLogin, UserRoleEnum

        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.role = UserRoleEnum.user
        mock_user.full_name = "测试用户"
        mock_user.is_active = True
        mock_user.created_at = datetime.now(tz=timezone.utc)
        mock_user.last_login_at = datetime.now(tz=timezone.utc)

        with patch.object(AuthService, "authenticate_user", return_value=mock_user):
            login_data = UserLogin(username="testuser", password="password")
            result = await AuthService.login(login_data)

            assert result.token is not None
            assert len(result.token) > 0
            assert result.user.username == "testuser"

    @pytest.mark.asyncio
    async def test_login_失败抛出ValueError(self):
        """认证失败应抛出 ValueError"""
        from models.auth import UserLogin

        with patch.object(AuthService, "authenticate_user", return_value=None):
            login_data = UserLogin(username="baduser", password="badpass")
            with pytest.raises(ValueError, match="用户名或密码错误"):
                await AuthService.login(login_data)


class TestChangePassword:
    """修改密码测试"""

    @pytest.mark.asyncio
    async def test_change_password_成功返回True(self, mock_db_session):
        """成功修改密码应返回 True"""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_db_session.execute.return_value = mock_result

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("services.auth_service.DatabaseManager.get_session", return_value=mock_ctx):
            result = await AuthService.change_password(str(uuid4()), "new_password")
            assert result is True

    @pytest.mark.asyncio
    async def test_change_password_用户不存在返回False(self, mock_db_session):
        """用户不存在时应返回 False（rowcount=0）"""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_db_session.execute.return_value = mock_result

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("services.auth_service.DatabaseManager.get_session", return_value=mock_ctx):
            result = await AuthService.change_password(str(uuid4()), "new_password")
            assert result is False
