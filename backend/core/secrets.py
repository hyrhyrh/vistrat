"""
密钥读取模块 — Docker Secrets + 环境变量双通道

优先级:
  1. /run/secrets/<name>  (Docker Secrets 文件挂载，生产环境)
  2. 环境变量 <NAME>      (开发环境/向后兼容)
  3. 默认值               (非敏感配置的兜底)

用法:
    from core.secrets import read_secret

    DB_PASSWORD = read_secret("db_password", "")
    # 生产: 读取 /run/secrets/db_password
    # 开发: 读取 os.environ["DB_PASSWORD"]

Docker Compose 配置:
    services:
      backend:
        secrets: [db_password, redis_password, ...]
    secrets:
      db_password:
        file: ./secrets/db_password
"""

import os
import logging

logger = logging.getLogger(__name__)

SECRETS_DIR = "/run/secrets"


def read_secret(name: str, default: str = "") -> str:
    """
    读取密钥值

    Args:
        name: 密钥名称（小写，如 db_password）
        default: 默认值

    Returns:
        密钥值（自动去除首尾空白和换行）
    """
    # 1. Docker Secrets 文件（生产环境）
    #    同时检查小写和原始名称: /run/secrets/db_password, /run/secrets/DB_PASSWORD
    for filename in (name.lower(), name):
        secret_file = os.path.join(SECRETS_DIR, filename)
        if os.path.isfile(secret_file):
            try:
                with open(secret_file, "r") as f:
                    value = f.read().strip()
                if value:
                    return value
            except Exception as e:
                logger.warning(f"读取密钥文件失败 {secret_file}: {e}")

    # 2. 环境变量（开发环境 / 向后兼容）
    env_value = os.getenv(name.upper(), "") or os.getenv(name, "")
    if env_value:
        return env_value

    # 3. 默认值
    return default
