"""
SSO单点登录加密解密工具
"""

import os
import base64
import logging
from typing import Optional, Dict
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# SSO加密密钥，从环境变量读取，如果没有则使用默认值
SSO_SECRET_KEY = os.getenv("SSO_SECRET_KEY", "")

# 如果没有设置环境变量，生成一个固定的密钥（生产环境应该使用环境变量）
if not SSO_SECRET_KEY:
    # 使用固定的密钥，确保重启后仍然可以解密之前生成的URL
    # 生产环境应该在.env文件中配置SSO_SECRET_KEY
    SSO_SECRET_KEY = "SSO_DEFAULT_KEY_PLEASE_CHANGE_IN_PRODUCTION_32BYTES"
    logger.warning("使用默认SSO密钥，生产环境请在.env文件中配置SSO_SECRET_KEY")

# 确保密钥长度为32字节（Fernet要求）
if len(SSO_SECRET_KEY) < 32:
    SSO_SECRET_KEY = SSO_SECRET_KEY.ljust(32, '0')
elif len(SSO_SECRET_KEY) > 32:
    SSO_SECRET_KEY = SSO_SECRET_KEY[:32]

# 将密钥转换为base64编码（Fernet要求）
FERNET_KEY = base64.urlsafe_b64encode(SSO_SECRET_KEY.encode())


class SSOCrypto:
    """SSO加密解密工具类"""

    def __init__(self):
        """初始化加密器"""
        self.cipher = Fernet(FERNET_KEY)

    def encrypt_credentials(self, username: str, password: str) -> str:
        """
        加密用户名和密码

        Args:
            username: 用户名
            password: 密码

        Returns:
            加密后的字符串（URL安全的base64编码）
        """
        try:
            # 将用户名和密码组合成一个字符串，使用特殊分隔符
            credentials = f"{username}||{password}"

            # 加密
            encrypted = self.cipher.encrypt(credentials.encode())

            # 返回URL安全的base64编码字符串
            return base64.urlsafe_b64encode(encrypted).decode()

        except Exception as e:
            logger.error(f"加密凭证失败: {e}")
            raise

    def decrypt_credentials(self, encrypted_str: str) -> Optional[Dict[str, str]]:
        """
        解密用户名和密码

        Args:
            encrypted_str: 加密的字符串

        Returns:
            包含username和password的字典，如果解密失败返回None
        """
        try:
            # 解码base64
            encrypted = base64.urlsafe_b64decode(encrypted_str.encode())

            # 解密
            decrypted = self.cipher.decrypt(encrypted)

            # 分割用户名和密码
            credentials = decrypted.decode()
            parts = credentials.split("||")

            if len(parts) != 2:
                logger.error("解密后的数据格式不正确")
                return None

            return {
                "username": parts[0],
                "password": parts[1]
            }

        except InvalidToken:
            logger.error("无效的加密令牌")
            return None
        except Exception as e:
            logger.error(f"解密凭证失败: {e}")
            return None

    @staticmethod
    def generate_sso_url(base_url: str, username: str, password: str) -> str:
        """
        生成SSO登录URL

        Args:
            base_url: 前端基础URL (例如: http://localhost:3000)
            username: 用户名
            password: 密码

        Returns:
            完整的SSO登录URL
        """
        crypto = SSOCrypto()
        encrypted = crypto.encrypt_credentials(username, password)
        return f"{base_url}/sso-login?token={encrypted}"


# 创建全局实例
sso_crypto = SSOCrypto()
