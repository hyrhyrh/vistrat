"""
创建视频流相关数据库表
"""

import asyncio
import logging
from sqlalchemy import text
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)

async def create_stream_tables():
    """创建视频流数据库表"""
    
    # 初始化数据库连接
    await DatabaseManager.initialize()
    
    # 读取SQL文件
    with open('database/video_streams_schema.sql', 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # 智能分割SQL语句，处理$$函数定义
    sql_statements = []
    current_statement = ""
    in_function = False
    
    for line in sql_content.split('\n'):
        current_statement += line + '\n'
        
        # 检测函数开始和结束
        if '$$' in line:
            in_function = not in_function
        
        # 如果遇到分号且不在函数内，则分割语句
        if line.strip().endswith(';') and not in_function:
            if current_statement.strip():
                sql_statements.append(current_statement.strip())
                current_statement = ""
    
    # 添加最后一个语句（如果有）
    if current_statement.strip():
        sql_statements.append(current_statement.strip())
    
    async with DatabaseManager.get_session() as session:
        try:
            for sql in sql_statements:
                if sql.strip():
                    logger.info(f"执行SQL: {sql[:100]}...")
                    await session.execute(text(sql))
            
            await session.commit()
            logger.info("视频流数据库表创建成功")
            
        except Exception as e:
            await session.rollback()
            logger.error(f"创建表失败: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(create_stream_tables())