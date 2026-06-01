#!/usr/bin/env python3
"""
测试AI模型选项动态获取功能
"""

import asyncio
import sys
import logging
import json
from pathlib import Path

# 添加项目路径
sys.path.append(str(Path(__file__).parent))

from database.connection import DatabaseManager
from services.ai_model_service import AIModelService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_model_options():
    """测试模型选项获取功能"""
    print("🧪 测试AI模型选项动态获取功能")
    print("=" * 50)
    
    try:
        # 初始化数据库连接
        print("📊 初始化数据库连接...")
        await DatabaseManager.initialize()
        print("✅ 数据库连接成功")
        
        # 获取模型选项
        print("\n📋 获取模型选项...")
        options = await AIModelService.get_model_options()
        
        print("✅ 成功获取模型选项:")
        print(f"📈 总共 {len(options)} 个AI提供商")
        
        for provider, models in options.items():
            print(f"\n🔹 {provider}:")
            print(f"   📦 {len(models)} 个可用模型")
            for model in models:
                print(f"   - {model}")
        
        # 检查蓝翼模型
        if 'lanyi' in options:
            print("\n🎯 蓝翼模型配置检查:")
            lanyi_models = options['lanyi']
            print(f"   ✅ 找到蓝翼模型: {len(lanyi_models)} 个")
            if 'lanyi-instruct' in lanyi_models:
                print("   ✅ 包含正确的 lanyi-instruct 模型")
            else:
                print("   ⚠️  未找到 lanyi-instruct 模型")
        else:
            print("\n❌ 未找到蓝翼模型配置")
        
        # 验证JSON格式
        print("\n🔄 验证JSON序列化...")
        json_str = json.dumps(options, ensure_ascii=False, indent=2)
        print("✅ JSON序列化成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        logger.exception("测试过程中发生错误")
        return False
    
    finally:
        # 清理数据库连接
        try:
            await DatabaseManager.close()
            print("\n🔒 数据库连接已关闭")
        except Exception:
            pass  # 测试结束清理数据库连接，忽略关闭异常

if __name__ == "__main__":
    result = asyncio.run(test_model_options())
    exit(0 if result else 1)