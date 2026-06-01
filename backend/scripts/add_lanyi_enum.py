#!/usr/bin/env python3
"""
添加lanyi到ai_provider_enum枚举类型的数据库迁移脚本
"""

import asyncio
import logging
from database.connection import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_lanyi_enum():
    """添加lanyi到ai_provider_enum枚举"""
    try:
        # 初始化数据库连接
        await DatabaseManager.initialize()
        logger.info("数据库连接初始化成功")
        
        # 获取数据库连接
        async with DatabaseManager.get_session() as session:
            # 检查lanyi是否已存在
            from sqlalchemy import text
            check_sql = text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_enum 
                WHERE enumlabel = 'lanyi' 
                AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'ai_provider_enum')
            )
            """)
            result = await session.execute(check_sql)
            exists = result.scalar()
            
            if exists:
                logger.info("lanyi枚举值已存在，无需添加")
                return True
            
            # 添加lanyi到枚举类型
            alter_sql = text("ALTER TYPE ai_provider_enum ADD VALUE 'lanyi'")
            await session.execute(alter_sql)
            await session.commit()
            
            logger.info("✅ 成功添加lanyi到ai_provider_enum枚举类型")
            
            # 验证添加结果
            verify_sql = text("""
            SELECT enumlabel FROM pg_enum 
            WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'ai_provider_enum')
            ORDER BY enumlabel
            """)
            result = await session.execute(verify_sql)
            enum_values = [row[0] for row in result.fetchall()]
            
            logger.info(f"📋 当前ai_provider_enum值: {enum_values}")
            
            if 'lanyi' in enum_values:
                logger.info("🎯 lanyi枚举值验证成功")
                return True
            else:
                logger.error("❌ lanyi枚举值验证失败")
                return False
                
    except Exception as e:
        logger.error(f"❌ 添加枚举值失败: {e}")
        return False
    
    finally:
        await DatabaseManager.close()
        logger.info("数据库连接已关闭")

if __name__ == "__main__":
    result = asyncio.run(add_lanyi_enum())
    if result:
        print("🎉 数据库枚举更新成功！现在可以使用lanyi提供商了。")
    else:
        print("❌ 数据库枚举更新失败！")
    exit(0 if result else 1)