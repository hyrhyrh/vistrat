"""
应用最小化的video_streams表结构
只保留8个必要字段：名称、流地址、类型、位置、分组、描述、标签、状态
"""

import asyncio
import logging
from sqlalchemy import text
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)

async def apply_minimal_schema():
    """应用最小化的表结构"""
    
    await DatabaseManager.initialize()
    
    async with DatabaseManager.get_session() as session:
        try:
            logger.info("开始应用最小化video_streams表结构...")
            
            # 读取SQL脚本
            with open('database/video_streams_minimal_schema.sql', 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割SQL语句
            sql_statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                # 跳过注释行
                if line.strip().startswith('--') or not line.strip():
                    continue
                    
                current_statement += line + '\n'
                
                # 如果遇到分号，则分割语句
                if line.strip().endswith(';'):
                    if current_statement.strip():
                        sql_statements.append(current_statement.strip())
                        current_statement = ""
            
            # 添加最后一个语句（如果有）
            if current_statement.strip():
                sql_statements.append(current_statement.strip())
            
            # 执行SQL语句
            for i, sql in enumerate(sql_statements):
                if sql.strip():
                    logger.info(f"执行SQL语句 {i+1}/{len(sql_statements)}: {sql[:50]}...")
                    try:
                        await session.execute(text(sql))
                    except Exception as e:
                        logger.warning(f"SQL语句执行警告: {e}")
                        continue
            
            await session.commit()
            logger.info("最小化video_streams表结构应用成功！")
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"应用表结构失败: {e}")
            return False

async def show_new_structure():
    """显示新的表结构"""
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
            
            print("\n最小化video_streams表结构:")
            print("=" * 80)
            print(f"{'字段名':<20} {'数据类型':<20} {'允许空值':<10} {'默认值':<20}")
            print("=" * 80)
            
            for column in columns:
                column_name, data_type, is_nullable, default_value = column
                default_str = str(default_value)[:18] if default_value else ""
                print(f"{column_name:<20} {data_type:<20} {is_nullable:<10} {default_str:<20}")
            
            print("=" * 80)
            print(f"共 {len(columns)} 个字段（精简设计）")
            
            # 查询测试数据
            count_sql = "SELECT COUNT(*) FROM video_streams;"
            result = await session.execute(text(count_sql))
            count = result.scalar()
            print(f"表中包含 {count} 条测试数据")
            
        except Exception as e:
            logger.error(f"查询表结构失败: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    async def main():
        print("应用最小化video_streams表结构...")
        success = await apply_minimal_schema()
        
        if success:
            print("\n应用成功！新表结构:")
            await show_new_structure()
        else:
            print("表结构应用失败")
    
    asyncio.run(main())