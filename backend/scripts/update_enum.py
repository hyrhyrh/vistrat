#!/usr/bin/env python3
"""
更新数据库枚举类型脚本
"""

import asyncio
from database.db_utils import get_sync_connection
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DatabaseConfig

async def update_enum_types():
    """更新数据库枚举类型为大写值"""
    
    conn = await asyncpg.connect(
        host=DatabaseConfig.DB_HOST,
        port=DatabaseConfig.DB_PORT,
        user=DatabaseConfig.DB_USER,
        password=DatabaseConfig.DB_PASSWORD,
        database=DatabaseConfig.DB_NAME
    )
    
    try:
        # 删除并重建枚举类型
        await conn.execute("""
            -- 临时修改列类型
            ALTER TABLE video_files ALTER COLUMN status TYPE VARCHAR USING status::VARCHAR;
            
            -- 删除旧枚举
            DROP TYPE IF EXISTS video_status_enum CASCADE;
            
            -- 创建新枚举（大写值）
            CREATE TYPE video_status_enum AS ENUM (
                'PENDING',
                'UPLOADING', 
                'READY',
                'ANALYZING',
                'COMPLETED',
                'ERROR',
                'DELETED'
            );
            
            -- 更新现有数据（小写转大写）
            UPDATE video_files SET status = UPPER(status);
            
            -- 恢复列类型
            ALTER TABLE video_files ALTER COLUMN status TYPE video_status_enum USING status::video_status_enum;
            
            -- 设置默认值
            ALTER TABLE video_files ALTER COLUMN status SET DEFAULT 'PENDING';
        """)
        
        print("✅ 枚举类型更新成功")
        
    except Exception as e:
        print(f"❌ 枚举类型更新失败: {e}")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_enum_types())