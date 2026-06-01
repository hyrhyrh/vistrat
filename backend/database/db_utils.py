"""
数据库连接工具（混合驱动架构）
- 同步连接：使用psycopg 3（ARM初始化阶段，避免异步I/O阻塞）
- 异步连接：SQLAlchemy自动使用asyncpg驱动（ARM运行时，原生支持无greenlet依赖）

【重要】本文件中的异步函数仅用于兼容性保留，实际生产环境通过DatabaseManager使用asyncpg
"""

import logging
import sys

logger = logging.getLogger(__name__)

# 关键：在导入psycopg前增加详细日志
logger.info("📦 正在导入psycopg模块...")
try:
    import psycopg
    from psycopg import AsyncConnection, Connection
    from psycopg.rows import dict_row
    logger.info(f"✅ psycopg模块导入成功，版本: {psycopg.__version__}")
except ImportError as e:
    logger.error(f"❌ psycopg模块导入失败: {e}")
    logger.error("💡 请确认已安装: pip install psycopg[binary]==3.2.3")
    logger.error(f"📋 当前Python路径: {sys.executable}")
    logger.error(f"📋 sys.path: {sys.path}")
    raise

from config.settings import DatabaseConfig


class _SyncConnectionWrapper:
    """同步连接包装器，模拟异步连接接口

    【兼容性设计】让旧代码无需修改，内部使用同步连接避免线程问题
    """
    def __init__(self, use_dict_row: bool = False):
        self.use_dict_row = use_dict_row
        self._conn = None

    async def __aenter__(self):
        """支持 async with 语法"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """自动关闭连接"""
        if self._conn:
            self._conn.close()

    async def close(self):
        """关闭连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    async def execute(self, query: str, params=None):
        """执行SQL语句（模拟异步接口）"""
        conn = self._ensure_connection()
        return conn.execute(query, params)

    async def commit(self):
        """提交事务（模拟异步接口）"""
        conn = self._ensure_connection()
        conn.commit()

    async def rollback(self):
        """回滚事务（模拟异步接口）"""
        conn = self._ensure_connection()
        conn.rollback()

    def _ensure_connection(self):
        """确保连接已建立"""
        if not self._conn:
            self._conn = get_sync_connection(
                autocommit=False,
                use_dict_row=self.use_dict_row
            )
        return self._conn


async def get_async_connection(autocommit: bool = False, use_dict_row: bool = False):
    """【兼容性接口】获取数据库连接包装器

    ⚠️ 注意：返回的不是真正的异步连接，而是同步连接的包装器
    ⚠️ 这样可以避免 ARM/Windows 下的线程创建问题

    Args:
        autocommit: 是否自动提交（保留参数，实际未使用）
        use_dict_row: 是否返回dict格式（默认False，返回tuple）

    Returns:
        _SyncConnectionWrapper: 连接包装器对象

    使用示例：
        conn = await get_async_connection(use_dict_row=True)
        try:
            results = await fetch(conn, "SELECT * FROM users")
        finally:
            await conn.close()
    """
    return _SyncConnectionWrapper(use_dict_row=use_dict_row)


def get_sync_connection(autocommit: bool = False, use_dict_row: bool = False) -> Connection:
    """获取同步数据库连接（psycopg 3）

    Args:
        autocommit: 是否自动提交（默认False）
        use_dict_row: 是否返回dict格式（默认False，返回tuple）

    Returns:
        Connection: 同步数据库连接对象

    适用场景：
    - 简单的初始化检查
    - 不在async上下文中的操作
    - 脚本工具

    使用示例：
        # 返回tuple（默认）
        conn = get_sync_connection(autocommit=True)
        cursor = conn.execute("SELECT version()")
        version = cursor.fetchone()[0]

        # 返回dict
        conn = get_sync_connection(autocommit=True, use_dict_row=True)
        cursor = conn.execute("SELECT name FROM users WHERE id = %s", (user_id,))
        row = cursor.fetchone()
        name = row['name']
    """
    conn_string = DatabaseConfig.get_sync_database_url()

    try:
        # 根据参数决定是否使用dict_row
        kwargs = {
            'autocommit': autocommit,
            'connect_timeout': 30
        }
        if use_dict_row:
            kwargs['row_factory'] = dict_row

        conn = psycopg.Connection.connect(conn_string, **kwargs)
        logger.debug(f"✅ 同步数据库连接成功: {DatabaseConfig.DB_HOST}:{DatabaseConfig.DB_PORT}/{DatabaseConfig.DB_NAME}")
        return conn
    except Exception as e:
        logger.error(f"❌ 同步数据库连接失败: {e}")
        raise


# ========== 兼容性辅助函数 ==========

async def fetchval(conn, query: str, *args) -> any:
    """【兼容性接口】查询单个值（内部使用同步连接）

    Args:
        conn: 连接包装器（_SyncConnectionWrapper）
        query: SQL查询语句
        *args: 查询参数

    Returns:
        查询结果的第一行第一列的值

    使用示例：
        count = await fetchval(conn, "SELECT COUNT(*) FROM users WHERE active = %s", True)
    """
    real_conn = conn._ensure_connection()
    cursor = real_conn.execute(query, args if args else None)
    row = cursor.fetchone()
    return row[0] if row else None


async def fetchrow(conn, query: str, *args) -> dict:
    """【兼容性接口】查询单行（内部使用同步连接）

    Args:
        conn: 连接包装器（_SyncConnectionWrapper）
        query: SQL查询语句
        *args: 查询参数

    Returns:
        查询结果的第一行（dict格式）

    使用示例：
        user = await fetchrow(conn, "SELECT * FROM users WHERE id = %s", user_id)
        print(user['username'])
    """
    real_conn = conn._ensure_connection()
    cursor = real_conn.execute(query, args if args else None)
    return cursor.fetchone()


async def fetch(conn, query: str, *args) -> list[dict]:
    """【兼容性接口】查询多行（内部使用同步连接）

    Args:
        conn: 连接包装器（_SyncConnectionWrapper）
        query: SQL查询语句
        *args: 查询参数

    Returns:
        查询结果的所有行（list of dict）

    使用示例：
        users = await fetch(conn, "SELECT * FROM users WHERE role = %s", role)
        for user in users:
            print(user['username'])
    """
    real_conn = conn._ensure_connection()
    cursor = real_conn.execute(query, args if args else None)
    return cursor.fetchall()


# ========== API映射参考 ==========

"""
asyncpg → psycopg 3 API映射表：

1. 连接创建：
   asyncpg:   conn = await asyncpg.connect(url)
   psycopg:   conn = await get_async_connection()

2. 查询单值：
   asyncpg:   value = await conn.fetchval("SELECT COUNT(*) FROM t")
   psycopg:   value = await fetchval(conn, "SELECT COUNT(*) FROM t")
   或:        cursor = await conn.execute("SELECT COUNT(*) FROM t")
             value = (await cursor.fetchone())[0]

3. 查询单行：
   asyncpg:   row = await conn.fetchrow("SELECT * FROM t WHERE id = $1", id)
   psycopg:   row = await fetchrow(conn, "SELECT * FROM t WHERE id = %s", id)

4. 查询多行：
   asyncpg:   rows = await conn.fetch("SELECT * FROM t")
   psycopg:   rows = await fetch(conn, "SELECT * FROM t")

5. 执行SQL：
   asyncpg:   await conn.execute("INSERT INTO t VALUES ($1, $2)", val1, val2)
   psycopg:   await conn.execute("INSERT INTO t VALUES (%s, %s)", (val1, val2))

6. 事务：
   asyncpg:   async with conn.transaction(): ...
   psycopg:   async with conn.transaction(): ...  # ✅ 相同

7. 关闭连接：
   asyncpg:   await conn.close()
   psycopg:   await conn.close()  # ✅ 相同
"""
