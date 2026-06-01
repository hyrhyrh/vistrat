#!/usr/bin/env python3
"""
视频流算法配置数据库迁移脚本
逐条执行SQL语句避免多语句问题
"""

import asyncio
import re
from sqlalchemy import text
from database.connection import DatabaseManager


async def run_migration():
    """执行数据库迁移"""
    try:
        await DatabaseManager.initialize()
        
        # 读取SQL文件
        with open('database/migration_video_stream_algorithm_configs.sql', 'r', encoding='utf-8') as f:
            full_sql = f.read()
        
        # 清理SQL并分割成单独的语句
        # 移除注释和空行
        lines = full_sql.split('\n')
        cleaned_lines = []
        in_function = False
        
        for line in lines:
            stripped = line.strip()
            
            # 跳过纯注释行
            if stripped.startswith('--') or not stripped:
                continue
                
            # 检测函数定义开始和结束
            if 'RETURNS TRIGGER AS $$' in line:
                in_function = True
            elif in_function and line.strip() == '$$ LANGUAGE plpgsql;':
                in_function = False
                cleaned_lines.append(line)
                continue
            
            cleaned_lines.append(line)
        
        cleaned_sql = '\n'.join(cleaned_lines)
        
        # 按分号分割SQL语句，但要考虑函数定义中的分号
        statements = []
        current_statement = []
        in_function_body = False
        
        for line in cleaned_lines:
            current_statement.append(line)
            
            if 'RETURNS TRIGGER AS $$' in line:
                in_function_body = True
            elif in_function_body and line.strip() == '$$ LANGUAGE plpgsql;':
                in_function_body = False
                # 函数定义结束，这是一个完整的语句
                statements.append('\n'.join(current_statement))
                current_statement = []
            elif not in_function_body and line.strip().endswith(';') and not line.strip().startswith('--'):
                # 普通SQL语句结束
                statements.append('\n'.join(current_statement))
                current_statement = []
        
        # 处理最后一个语句（如果有）
        if current_statement:
            statements.append('\n'.join(current_statement))
        
        print(f"共找到 {len(statements)} 个SQL语句需要执行")
        
        # 逐条执行SQL语句
        async with DatabaseManager.get_session() as session:
            for i, statement in enumerate(statements, 1):
                statement = statement.strip()
                if not statement:
                    continue
                    
                try:
                    print(f"执行第 {i} 个语句...")
                    # 提取语句的第一行作为描述
                    first_line = statement.split('\n')[0].strip()
                    if len(first_line) > 60:
                        first_line = first_line[:60] + "..."
                    print(f"  -> {first_line}")
                    
                    await session.execute(text(statement))
                    await session.commit()
                    print(f"  ✅ 执行成功")
                    
                except Exception as e:
                    print(f"  ❌ 执行失败: {e}")
                    print(f"  SQL: {statement[:200]}...")
                    # 对于某些错误（如已存在），我们可以继续
                    if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
                        print("  ⚠️  对象已存在，跳过")
                        continue
                    else:
                        raise
        
        print('\n✅ 数据库迁移执行完成')
        
    except Exception as e:
        print(f'\n❌ 数据库迁移失败: {e}')
        raise


if __name__ == "__main__":
    asyncio.run(run_migration())