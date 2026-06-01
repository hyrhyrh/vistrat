"""
流任务表初始化脚本
用于在应用启动时自动创建stream_analysis_tasks表
"""

import logging
from pathlib import Path
from sqlalchemy import text
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)

async def init_stream_tasks_table():
    """初始化stream_analysis_tasks表（从SQL文件）"""
    try:
        # 读取SQL脚本
        sql_file = Path(__file__).parent / "migrations" / "create_stream_analysis_tasks.sql"
        if not sql_file.exists():
            logger.warning(f"迁移脚本不存在: {sql_file}")
            return False

        sql_content = sql_file.read_text(encoding='utf-8')

        # 使用异步数据库会话
        async with DatabaseManager.get_session() as session:
            # 检查表是否已存在
            result = await session.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'stream_analysis_tasks'
                )
            """)
            table_exists = result.scalar()

            if table_exists:
                logger.info("stream_analysis_tasks表已存在，跳过创建")

                # 检查记录数
                result = await session.execute("SELECT COUNT(*) FROM stream_analysis_tasks")
                count = result.scalar()
                logger.info(f"当前表中有 {count} 条记录")
                return True

            # 创建表
            logger.info("正在创建stream_analysis_tasks表...")
            await session.execute(sql_content)
            await session.commit()

            # 验证创建成功
            result = await session.execute("SELECT COUNT(*) FROM stream_analysis_tasks")
            count = result.scalar()
            result = await session.execute("""
                SELECT COUNT(*) FROM information_schema.columns
                WHERE table_name = 'stream_analysis_tasks'
            """)
            column_count = result.scalar()

            logger.info(f"✅ stream_analysis_tasks表创建成功: {column_count}个字段, {count}条记录")
            return True

    except Exception as e:
        logger.error(f"初始化stream_analysis_tasks表失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")
        return False

async def ensure_stream_tasks_table():
    """确保stream_analysis_tasks表存在，如果不存在则创建简化版本"""
    try:
        logger.info("🔧 [步骤1/5] 连接数据库...")

        # 定义SQL语句
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS stream_analysis_tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            stream_id UUID NOT NULL,
            algorithm_config_id UUID NOT NULL,
            task_name VARCHAR(255) NOT NULL,

            status VARCHAR(20) NOT NULL DEFAULT 'enabled',
            is_active BOOLEAN NOT NULL DEFAULT true,
            auto_recover BOOLEAN NOT NULL DEFAULT true,

            time_config JSONB NOT NULL DEFAULT '{}',
            roi_config JSONB DEFAULT '{}',

            priority INTEGER NOT NULL DEFAULT 1,
            confidence_threshold FLOAT NOT NULL DEFAULT 0.7,
            analysis_interval INTEGER NOT NULL DEFAULT 10,

            last_run_at TIMESTAMP WITH TIME ZONE,
            next_run_at TIMESTAMP WITH TIME ZONE,
            run_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            last_error_message TEXT,

            total_frames_processed INTEGER NOT NULL DEFAULT 0,
            total_alerts_generated INTEGER NOT NULL DEFAULT 0,
            avg_processing_time FLOAT DEFAULT 0,

            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by UUID,
            updated_by UUID
        );
        """

        create_indexes_sql = """
        CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_stream_id ON stream_analysis_tasks(stream_id);
        CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_status ON stream_analysis_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_active ON stream_analysis_tasks(is_active);
        """

        async with DatabaseManager.get_session() as session:
            logger.info("✅ [步骤1/5] 数据库连接成功")

            logger.info("🔍 [步骤2/5] 检查stream_analysis_tasks表是否存在...")
            # 检查表是否存在
            result = await session.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'stream_analysis_tasks'
                )
            """))
            table_exists = result.scalar()
            logger.info(f"📊 [步骤2/5] 查询结果: table_exists={table_exists}")

            if table_exists:
                logger.info("✅ [步骤3/5] stream_analysis_tasks表已存在，跳过创建")
                return True

            # 创建表
            logger.info("⚠️  [步骤3/5] stream_analysis_tasks表不存在，开始创建...")
            logger.info("🔨 [步骤4/5] 执行CREATE TABLE语句...")
            await session.execute(text(create_table_sql))
            logger.info("✅ [步骤4/5] 表结构创建完成")

            logger.info("🔨 [步骤5/5] 创建索引...")
            await session.execute(text(create_indexes_sql))
            await session.commit()
            logger.info("✅ [步骤5/5] 索引创建完成")

            logger.info("✅ stream_analysis_tasks基础表及索引全部创建成功")
            return True

    except Exception as e:
        logger.error(f"❌ 确保stream_analysis_tasks表存在失败: {e}")
        import traceback
        logger.error(f"📋 详细错误堆栈:\n{traceback.format_exc()}")
        return False