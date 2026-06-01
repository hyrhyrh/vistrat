"""
测试SQLAlchemy对JSONB字段的处理
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text

async def test_sqlalchemy_jsonb():
    """测试SQLAlchemy查询JSONB字段"""
    from database.connection import DatabaseManager

    # 初始化数据库
    await DatabaseManager.initialize()

    print("=" * 80)
    print("测试SQLAlchemy AsyncSession对JSONB字段的处理")
    print("=" * 80)

    async with DatabaseManager.get_session() as db:
        query = text("""
        SELECT id, name, detection_capabilities
        FROM ai_model_configs
        WHERE id = :template_id
        """)
        result = await db.execute(query, {'template_id': 'edac6c8d-9a27-4f73-9112-0dcc5644e063'})
        row = result.fetchone()

        if row:
            config_id, name, detection_capabilities = row[0], row[1], row[2]
            print(f"✅ 配置读取成功")
            print(f"   ID: {config_id}")
            print(f"   名称: {name}")
            print(f"   detection_capabilities: {detection_capabilities}")
            print(f"   类型: {type(detection_capabilities)}")
            print(f"   是否为列表: {isinstance(detection_capabilities, list)}")

            if isinstance(detection_capabilities, list):
                print(f"   ✅ JSONB被正确解析为列表")
                print(f"   列表长度: {len(detection_capabilities)}")
                print(f"   元素: {detection_capabilities}")

                # 测试判断逻辑
                if detection_capabilities and len(detection_capabilities) > 1:
                    print(f"   ✅ 正确判定为复合检测模式 (len={len(detection_capabilities)} > 1)")
                else:
                    print(f"   判定为单检测模式 (len={len(detection_capabilities) if detection_capabilities else 0})")
            else:
                print(f"   ❌ JSONB未被解析为列表，需要手动json.loads()")
                import json
                parsed = json.loads(detection_capabilities)
                print(f"   解析后: {parsed}, 类型: {type(parsed)}")
                print(f"   解析后长度: {len(parsed)}")
        else:
            print("❌ 配置未找到")

    await DatabaseManager.close()

if __name__ == "__main__":
    asyncio.run(test_sqlalchemy_jsonb())
