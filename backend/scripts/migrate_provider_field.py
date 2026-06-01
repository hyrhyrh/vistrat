#!/usr/bin/env python3
"""
数据库迁移脚本：将ai_model_configs表的provider字段从枚举类型修改为VARCHAR类型
支持动态配置AI提供商，无需修改数据库结构
"""

import asyncio
import logging
from sqlalchemy import text
from database.connection import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_provider_field():
    """迁移provider字段从枚举到VARCHAR"""
    try:
        await DatabaseManager.initialize()
        logger.info("数据库连接初始化成功")
        
        async with DatabaseManager.get_session() as session:
            # 第一步：检查当前字段类型
            check_type_sql = text("""
            SELECT column_name, data_type, udt_name 
            FROM information_schema.columns 
            WHERE table_name = 'ai_model_configs' AND column_name = 'provider'
            """)
            result = await session.execute(check_type_sql)
            current_info = result.fetchone()
            
            if current_info:
                logger.info(f"当前provider字段信息: {current_info}")
                
                # 如果已经是VARCHAR类型，跳过迁移
                if current_info[1] == 'character varying':
                    logger.info("provider字段已经是VARCHAR类型，无需迁移")
                    return True
            
            logger.info("开始迁移provider字段...")
            
            # 第二步：创建临时列
            add_temp_column_sql = text("""
            ALTER TABLE ai_model_configs 
            ADD COLUMN provider_temp VARCHAR(100)
            """)
            await session.execute(add_temp_column_sql)
            logger.info("✅ 创建临时列 provider_temp")
            
            # 第三步：复制数据到临时列
            copy_data_sql = text("""
            UPDATE ai_model_configs 
            SET provider_temp = provider::text
            """)
            await session.execute(copy_data_sql)
            logger.info("✅ 复制数据到临时列")
            
            # 第四步：删除原始列
            drop_original_sql = text("""
            ALTER TABLE ai_model_configs 
            DROP COLUMN provider
            """)
            await session.execute(drop_original_sql)
            logger.info("✅ 删除原始枚举列")
            
            # 第五步：重命名临时列
            rename_column_sql = text("""
            ALTER TABLE ai_model_configs 
            RENAME COLUMN provider_temp TO provider
            """)
            await session.execute(rename_column_sql)
            logger.info("✅ 重命名临时列为provider")
            
            # 第六步：添加非空约束
            add_constraint_sql = text("""
            ALTER TABLE ai_model_configs 
            ALTER COLUMN provider SET NOT NULL
            """)
            await session.execute(add_constraint_sql)
            logger.info("✅ 添加非空约束")
            
            # 第七步：添加注释
            add_comment_sql = text("""
            COMMENT ON COLUMN ai_model_configs.provider IS 'AI模型供应商名称(引用ai_provider_configs.provider_name)'
            """)
            await session.execute(add_comment_sql)
            logger.info("✅ 添加字段注释")
            
            await session.commit()
            logger.info("🎉 迁移完成！")
            
            # 验证迁移结果
            verify_sql = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'ai_model_configs' AND column_name = 'provider'
            """)
            result = await session.execute(verify_sql)
            new_info = result.fetchone()
            
            if new_info:
                logger.info(f"📋 迁移后字段信息: {new_info}")
                
                # 检查数据完整性
                count_sql = text("SELECT COUNT(*) FROM ai_model_configs")
                result = await session.execute(count_sql)
                total_count = result.scalar()
                logger.info(f"📊 数据完整性检查: 总记录数 {total_count}")
                
                return True
            else:
                logger.error("❌ 迁移验证失败")
                return False
                
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        # 尝试回滚（删除临时列）
        try:
            async with DatabaseManager.get_session() as session:
                rollback_sql = text("""
                ALTER TABLE ai_model_configs 
                DROP COLUMN IF EXISTS provider_temp
                """)
                await session.execute(rollback_sql)
                await session.commit()
                logger.info("🔄 已清理临时列")
        except Exception:
            pass  # 回滚清理失败不影响错误返回
        return False
    
    finally:
        await DatabaseManager.close()
        logger.info("数据库连接已关闭")

async def check_migration_status():
    """检查迁移状态"""
    try:
        await DatabaseManager.initialize()
        
        async with DatabaseManager.get_session() as session:
            # 检查字段类型
            check_sql = text("""
            SELECT 
                column_name, 
                data_type, 
                is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'ai_model_configs' AND column_name = 'provider'
            """)
            result = await session.execute(check_sql)
            field_info = result.fetchone()
            
            if field_info:
                print("📋 当前provider字段状态:")
                print(f"   字段名: {field_info[0]}")
                print(f"   数据类型: {field_info[1]}")
                print(f"   可为空: {field_info[2]}")
                
                if field_info[1] == 'character varying':
                    print("✅ 字段类型正确 (VARCHAR)")
                else:
                    print(f"⚠️  字段类型为: {field_info[1]} (需要迁移)")
            else:
                print("❌ 未找到provider字段")
                
            # 检查示例数据
            sample_sql = text("""
            SELECT id, name, provider, model_name 
            FROM ai_model_configs 
            LIMIT 3
            """)
            result = await session.execute(sample_sql)
            samples = result.fetchall()
            
            if samples:
                print("\n📊 示例数据:")
                for sample in samples:
                    print(f"   {sample[1]} | {sample[2]} | {sample[3]}")
    
    except Exception as e:
        print(f"❌ 检查失败: {e}")
    
    finally:
        await DatabaseManager.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        asyncio.run(check_migration_status())
    else:
        print("🚀 开始AI模型配置表provider字段迁移...")
        result = asyncio.run(migrate_provider_field())
        if result:
            print("🎉 迁移成功！现在支持动态配置AI提供商")
            print("💡 提示：运行 'python migrate_provider_field.py check' 查看迁移状态")
        else:
            print("❌ 迁移失败！")
        exit(0 if result else 1)