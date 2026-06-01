#!/usr/bin/env python3
"""
系统配置表迁移脚本
从MySQL dc_system_param 转换为 PostgreSQL system_configs
"""

import asyncio
import re
from sqlalchemy import text
from database.connection import DatabaseManager


async def run_system_config_migration():
    """执行系统配置表迁移"""
    try:
        await DatabaseManager.initialize()
        
        # 读取SQL文件
        with open('database/migration_system_config.sql', 'r', encoding='utf-8') as f:
            full_sql = f.read()
        
        # 清理SQL并分割成单独的语句
        lines = full_sql.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.strip()
            # 跳过注释行和空行
            if stripped.startswith('--') or not stripped:
                continue
            cleaned_lines.append(line)
        
        cleaned_sql = '\n'.join(cleaned_lines)
        
        # 按分号分割SQL语句，处理多行语句
        statements = []
        current_statement = []
        in_multiline = False
        
        for line in cleaned_lines:
            current_statement.append(line)
            
            # 检查是否是多行语句（如INSERT、COMMENT等）
            if re.search(r'(INSERT INTO|COMMENT ON|VALUES)', line.strip(), re.IGNORECASE):
                in_multiline = True
            
            # 如果行以分号结尾且不在多行语句中，则为语句结束
            if line.strip().endswith(';'):
                if in_multiline:
                    # 检查是否是多行语句的结束
                    if re.search(r'(ON CONFLICT.*DO NOTHING|;)$', line.strip(), re.IGNORECASE):
                        in_multiline = False
                        statements.append('\n'.join(current_statement))
                        current_statement = []
                else:
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
                        await session.rollback()
                        continue
                    else:
                        await session.rollback()
                        raise
        
        print('\n✅ 系统配置表迁移执行完成')
        
    except Exception as e:
        print(f'\n❌ 系统配置表迁移失败: {e}')
        raise


async def verify_system_config_table():
    """验证系统配置表创建情况"""
    try:
        await DatabaseManager.initialize()
        
        async with DatabaseManager.get_session() as session:
            # 检查表是否存在
            result = await session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'system_configs';
            """))
            table = result.fetchone()
            
            if table:
                print(f'✅ 表 {table[0]} 创建成功')
                
                # 检查表结构
                result = await session.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'system_configs'
                    ORDER BY ordinal_position;
                """))
                columns = result.fetchall()
                print(f'\n📋 表结构 ({len(columns)} 列):')
                for col in columns:
                    nullable = '可空' if col[2] == 'YES' else '非空'
                    default = f' (默认: {col[3]})' if col[3] else ''
                    print(f'  - {col[0]} ({col[1]}) - {nullable}{default}')
                
                # 检查预设配置数据
                result = await session.execute(text("""
                    SELECT param_code, param_desc, param_val 
                    FROM system_configs
                    ORDER BY param_code;
                """))
                configs = result.fetchall()
                print(f'\n🔧 预设配置 ({len(configs)} 条):')
                for config in configs:
                    print(f'  - {config[0]}: {config[1]} = {config[2]}')
                    
            else:
                print('❌ 表 system_configs 不存在')
                
    except Exception as e:
        print(f'❌ 验证失败: {e}')


async def main():
    """主函数"""
    print("=" * 60)
    print("🔧 系统配置表迁移 (MySQL -> PostgreSQL)")
    print("=" * 60)
    
    try:
        await run_system_config_migration()
        await verify_system_config_table()
        print("\n🎉 迁移和验证完成!")
        
    except Exception as e:
        print(f"\n💥 操作失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())