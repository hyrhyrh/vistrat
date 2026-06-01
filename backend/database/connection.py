"""
数据库连接管理器
负责PostgreSQL连接池管理和会话处理
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from config.settings import DatabaseConfig
from database.db_utils import get_sync_connection
from models.base import Base  # noqa: F401 — re-exported for backward compatibility

logger = logging.getLogger(__name__)

# 全局变量
async_engine = None
async_session_factory = None


class DatabaseManager:
    """数据库管理器"""

    @classmethod
    async def initialize(cls):
        """初始化数据库连接"""
        global async_engine, async_session_factory

        try:
            # 创建异步引擎 - asyncpg驱动（高性能异步驱动）
            async_engine = create_async_engine(
                DatabaseConfig.get_database_url(),
                pool_size=DatabaseConfig.DB_POOL_SIZE,
                max_overflow=DatabaseConfig.DB_MAX_OVERFLOW,
                pool_timeout=DatabaseConfig.DB_POOL_TIMEOUT,
                pool_recycle=DatabaseConfig.DB_POOL_RECYCLE,
                pool_pre_ping=DatabaseConfig.DB_POOL_PRE_PING,
                echo=False,  # 生产环境设为False
                # asyncpg驱动配置
                connect_args={
                    "server_settings": {
                        "application_name": "vistrat_backend",
                        "jit": "off"
                    }
                }
            )

            # 创建会话工厂
            async_session_factory = async_sessionmaker(
                bind=async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            logger.info("✅ 数据库连接初始化成功（asyncpg驱动）")

        except Exception as e:
            logger.error(f"❌ 数据库连接初始化失败: {e}")
            raise

    @classmethod
    async def close(cls):
        """关闭数据库连接"""
        global async_engine

        if async_engine:
            await async_engine.dispose()
            logger.info("数据库连接已关闭")

    @classmethod
    async def test_connection(cls) -> bool:
        """测试数据库连接"""
        try:
            async with cls.get_session() as session:
                result = await session.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    @staticmethod
    @asynccontextmanager
    async def get_session() -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话"""
        if not async_session_factory:
            raise RuntimeError("数据库未初始化，请先调用 initialize()")

        async with async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"数据库会话异常: {e}")
                raise
            finally:
                await session.close()


# FastAPI依赖函数
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖函数，获取数据库会话"""
    async with DatabaseManager.get_session() as session:
        yield session


async def init_database():
    """智能初始化数据库（仅在首次时执行 video_multi.sql）

    设计逻辑:
    1. 检查核心表是否完整存在
    2. 如果不完整,先彻底清理public schema(删除所有对象)
    3. 执行video_multi.sql重新创建完整结构
    """
    conn = None

    try:
        # 连接数据库
        logger.info("🔗 步骤1/5: 正在连接数据库...")
        logger.info(f"   📍 数据库: {DatabaseConfig.DB_HOST}:{DatabaseConfig.DB_PORT}/{DatabaseConfig.DB_NAME}")
        logger.info(f"   🔧 驱动: psycopg 3（同步连接用于初始化）")

        # 使用psycopg 3同步连接（初始化任务无需异步）
        # 注意: 必须使用autocommit=False,让schema.sql能正常执行并提交
        conn = get_sync_connection(autocommit=False)
        logger.info("✅ 步骤1/5: 数据库连接成功")

        # 检查是否需要初始化：检查核心表是否存在
        logger.info("🔍 步骤2/5: 检查核心表是否存在...")
        cursor = conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('users', 'video_streams', 'analysis_tasks', 'alerts')
        """)
        table_count = cursor.fetchone()[0]

        logger.info(f"✅ 步骤2/5: 查询完成，核心表数量: {table_count}/4")

        # 如果核心表不完整，执行初始化
        if table_count < 4:
            logger.info(f"⚠️  检测到数据库未初始化（核心表数: {table_count}/4），开始清理并执行 video_multi_v3.sql...")

            # 步骤3: 清理public schema
            logger.info("🔄 步骤3/5: 清理public schema...")
            conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
            conn.execute("CREATE SCHEMA public")
            conn.execute(f"GRANT ALL ON SCHEMA public TO {DatabaseConfig.DB_USER}")
            conn.execute("GRANT ALL ON SCHEMA public TO public")
            conn.commit()  # 提交schema清理
            logger.info("✅ 步骤3/5: public schema已清理完成")

            # 步骤4: 执行video_multi.sql
            logger.info("📄 步骤4/5: 执行 video_multi_v3.sql...")
            schema_path = Path(__file__).parent / "video_multi_v3.sql"
            if not schema_path.exists():
                raise FileNotFoundError(f"找不到 video_multi_v3.sql 文件: {schema_path}")

            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            conn.execute(schema_sql)
            conn.commit()  # 提交video_multi_v3.sql的所有DDL语句
            logger.info("✅ 步骤4/5: video_multi_v3.sql 执行完成")

            # 步骤5: 验证表结构
            logger.info("🔍 步骤5/5: 验证表结构...")
            cursor = conn.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public'
            """)
            final_table_count = cursor.fetchone()[0]
            logger.info(f"✅ 步骤5/5: 数据库初始化完成！共创建 {final_table_count} 个表")

        else:
            logger.info(f"✅ 数据库已存在完整表结构，跳过初始化（共 {table_count}/5 个核心表）")

    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        raise
    finally:
        if conn:
            conn.close()
            logger.info("🔒 数据库连接已关闭")
