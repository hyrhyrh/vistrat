"""
检查video_streams表结构并修复缺失字段
"""

import asyncio
import logging
from sqlalchemy import text
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)

async def check_and_fix_video_streams_schema():
    """检查并修复video_streams表结构"""
    
    # 初始化数据库连接
    await DatabaseManager.initialize()
    
    async with DatabaseManager.get_session() as session:
        try:
            # 检查表是否存在
            check_table_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'video_streams'
            );
            """
            result = await session.execute(text(check_table_sql))
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("video_streams表不存在，需要创建")
                return False
            
            # 检查stream_url字段是否存在
            check_column_sql = """
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'video_streams'
                AND column_name = 'stream_url'
            );
            """
            result = await session.execute(text(check_column_sql))
            column_exists = result.scalar()
            
            if column_exists:
                logger.info("stream_url字段已存在")
                return True
            
            logger.info("stream_url字段不存在，开始添加...")
            
            # 添加stream_url字段
            add_column_sql = """
            ALTER TABLE video_streams 
            ADD COLUMN stream_url VARCHAR(1000) NOT NULL DEFAULT '';
            """
            
            await session.execute(text(add_column_sql))
            await session.commit()
            
            logger.info("成功添加stream_url字段")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"检查或修复表结构失败: {e}")
            return False

async def show_table_structure():
    """显示video_streams表结构"""
    await DatabaseManager.initialize()
    
    async with DatabaseManager.get_session() as session:
        try:
            # 查询表结构
            structure_sql = """
            SELECT 
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = 'video_streams'
            ORDER BY ordinal_position;
            """
            
            result = await session.execute(text(structure_sql))
            columns = result.fetchall()
            
            print("\nvideo_streams表结构:")
            print("-" * 80)
            print(f"{'字段名':<20} {'数据类型':<20} {'允许空值':<10} {'默认值':<20}")
            print("-" * 80)
            
            for column in columns:
                column_name, data_type, is_nullable, default_value = column
                default_str = str(default_value)[:18] if default_value else ""
                print(f"{column_name:<20} {data_type:<20} {is_nullable:<10} {default_str:<20}")
            
            print("-" * 80)
            print(f"共 {len(columns)} 个字段")
            
        except Exception as e:
            logger.error(f"查询表结构失败: {e}")

async def recreate_video_streams_table():
    """重建video_streams表"""
    await DatabaseManager.initialize()
    
    async with DatabaseManager.get_session() as session:
        try:
            logger.info("开始重建video_streams表...")
            
            # 删除现有表（如果存在）
            drop_sql = "DROP TABLE IF EXISTS video_streams CASCADE;"
            await session.execute(text(drop_sql))
            logger.info("已删除现有video_streams表")
            
            # 删除旧的枚举类型（如果存在）
            drop_enum_sqls = [
                "DROP TYPE IF EXISTS stream_status_enum CASCADE;",
                "DROP TYPE IF EXISTS stream_type_enum CASCADE;", 
                "DROP TYPE IF EXISTS stream_analysis_status_enum CASCADE;",
                "DROP TYPE IF EXISTS stream_template_analysis_status_enum CASCADE;"
            ]
            
            for sql in drop_enum_sqls:
                try:
                    await session.execute(text(sql))
                except Exception:
                    pass  # DROP IF EXISTS 可能因类型不存在而失败，忽略即可
            
            # 创建枚举类型
            enum_sqls = [
                "CREATE TYPE stream_status_enum AS ENUM ('OFFLINE', 'ONLINE', 'CONNECTING', 'ERROR', 'MAINTENANCE');",
                "CREATE TYPE stream_type_enum AS ENUM ('RTSP', 'RTMP', 'HLS', 'WEBRTC', 'HTTP_FLV', 'LOCAL_CAMERA');",
                "CREATE TYPE stream_analysis_status_enum AS ENUM ('NOT_STARTED', 'RUNNING', 'PAUSED', 'STOPPED', 'ERROR');"
            ]
            
            for sql in enum_sqls:
                await session.execute(text(sql))
            
            # 创建新表
            create_table_sql = """
            CREATE TABLE video_streams (
                -- 主键和基本信息
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(255) NOT NULL,
                description TEXT,
                
                -- 流配置信息
                stream_url VARCHAR(1000) NOT NULL,
                stream_type stream_type_enum NOT NULL DEFAULT 'RTSP',
                
                -- 认证信息
                username VARCHAR(100),
                password VARCHAR(100),
                
                -- 流状态
                status stream_status_enum NOT NULL DEFAULT 'OFFLINE',
                last_online_at TIMESTAMP WITH TIME ZONE,
                connection_error TEXT,
                
                -- 视频技术参数
                fps REAL,
                width INTEGER,
                height INTEGER,
                codec VARCHAR(50),
                
                -- 缩略图和截图
                thumbnail_path VARCHAR(1000),
                latest_frame_path VARCHAR(1000),
                
                -- 分析配置
                analysis_status stream_analysis_status_enum NOT NULL DEFAULT 'NOT_STARTED',
                analysis_interval INTEGER DEFAULT 10 CHECK (analysis_interval >= 1 AND analysis_interval <= 300),
                enable_recording BOOLEAN DEFAULT false,
                
                -- 统计信息
                total_analysis_count INTEGER DEFAULT 0,
                total_alerts INTEGER DEFAULT 0,
                last_analysis_at TIMESTAMP WITH TIME ZONE,
                last_alert_at TIMESTAMP WITH TIME ZONE,
                
                -- 位置和分组
                location VARCHAR(255),
                group_name VARCHAR(100),
                tags TEXT[] DEFAULT '{}',
                
                -- 时间戳
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            await session.execute(text(create_table_sql))
            
            # 创建索引
            index_sqls = [
                "CREATE INDEX idx_video_streams_status ON video_streams(status);",
                "CREATE INDEX idx_video_streams_name ON video_streams(name);",
                "CREATE INDEX idx_video_streams_created_at ON video_streams(created_at DESC);"
            ]
            
            for sql in index_sqls:
                await session.execute(text(sql))
            
            await session.commit()
            logger.info("video_streams表重建成功")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"重建表失败: {e}")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        print("检查video_streams表结构...")
        await show_table_structure()
        
        print("\n是否需要重建表? 当前表结构与模型不匹配")
        
        print("\n重建video_streams表...")
        success = await recreate_video_streams_table()
        
        if success:
            print("\n重建后的表结构:")
            await show_table_structure()
        else:
            print("表重建失败")
    
    asyncio.run(main())