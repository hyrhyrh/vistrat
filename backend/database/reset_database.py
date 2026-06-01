"""
数据库重置脚本
删除所有表并重新执行video_multi.sql初始化脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from database.db_utils import get_sync_connection
from config.settings import DatabaseConfig


def reset_database():
    """重置数据库：删除所有表并重新初始化"""
    conn = None

    try:
        print("=" * 60)
        print("🔄 开始重置数据库...")
        print("=" * 60)

        # 连接数据库
        print(f"\n📍 数据库: {DatabaseConfig.DB_HOST}:{DatabaseConfig.DB_PORT}/{DatabaseConfig.DB_NAME}")
        print(f"👤 用户: {DatabaseConfig.DB_USER}")
        conn = get_sync_connection(autocommit=False)
        print("✅ 数据库连接成功\n")

        # 步骤1: 清理public schema
        print("🗑️  步骤1/3: 删除所有表和对象...")
        conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        conn.execute("CREATE SCHEMA public")
        conn.execute(f"GRANT ALL ON SCHEMA public TO {DatabaseConfig.DB_USER}")
        conn.execute("GRANT ALL ON SCHEMA public TO public")
        conn.commit()
        print("✅ 所有表和对象已删除\n")

        # 步骤2: 执行video_multi.sql
        print("📄 步骤2/3: 执行 video_multi.sql 初始化脚本...")
        schema_path = Path(__file__).parent / "video_multi.sql"

        if not schema_path.exists():
            raise FileNotFoundError(f"找不到 video_multi.sql 文件: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        print(f"📖 读取脚本文件: {schema_path}")
        print(f"📦 脚本大小: {len(schema_sql)} 字符")

        conn.execute(schema_sql)
        conn.commit()
        print("✅ video_multi.sql 执行完成\n")

        # 步骤3: 验证表结构
        print("🔍 步骤3/3: 验证表结构...")
        cursor = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()

        print(f"✅ 共创建 {len(tables)} 个表:\n")
        for idx, (table_name,) in enumerate(tables, 1):
            print(f"   {idx:2d}. {table_name}")

        print("\n" + "=" * 60)
        print("🎉 数据库重置完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 数据库重置失败: {e}")
        import traceback
        print(f"\n详细错误:\n{traceback.format_exc()}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            print("\n🔒 数据库连接已关闭")


if __name__ == "__main__":
    reset_database()
