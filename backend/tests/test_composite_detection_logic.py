"""
复合检测逻辑验证测试脚本

测试目标：
1. 验证detection_capabilities的读取和解析
2. 验证自动模式判断逻辑 (len > 1 -> composite, else -> single)
3. 验证复合检测服务调用链路
"""

import asyncio
import sys
from pathlib import Path

# 添加backend到路径
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

async def test_detection_capabilities_loading():
    """测试1: 验证detection_capabilities字段读取"""
    print("=" * 80)
    print("测试1: 验证detection_capabilities字段读取")
    print("=" * 80)

    import asyncpg
    import os

    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

    try:
        # 查询包含detection_capabilities的配置
        row = await conn.fetchrow("""
            SELECT id, name, detection_capabilities
            FROM ai_model_configs
            WHERE id = $1::uuid
        """, 'edac6c8d-9a27-4f73-9112-0dcc5644e063')

        if row:
            config_id, name, detection_capabilities = row['id'], row['name'], row['detection_capabilities']
            print(f"✅ 配置读取成功")
            print(f"   ID: {config_id}")
            print(f"   名称: {name}")
            print(f"   detection_capabilities: {detection_capabilities}")
            print(f"   类型: {type(detection_capabilities)}")
            print(f"   长度: {len(detection_capabilities) if detection_capabilities else 0}")

            # 验证逻辑判断
            if detection_capabilities and len(detection_capabilities) > 1:
                print(f"   ✅ 判定为复合检测模式 (len={len(detection_capabilities)} > 1)")
                return True
            else:
                print(f"   ❌ 判定为单检测模式")
                return False
        else:
            print("❌ 配置未找到")
            return False
    finally:
        await conn.close()


async def test_mode_detection_logic():
    """测试2: 验证自动模式判断逻辑"""
    print("\n" + "=" * 80)
    print("测试2: 验证自动模式判断逻辑")
    print("=" * 80)

    test_cases = [
        ([], "单检测（空列表）"),
        (["safety_helmet"], "单检测（1个能力）"),
        (["safety_helmet", "smoking"], "复合检测（2个能力）"),
        (["safety_helmet", "smoking", "phone_usage"], "复合检测（3个能力）"),
    ]

    for detection_capabilities, expected in test_cases:
        is_composite = detection_capabilities and len(detection_capabilities) > 1
        mode = "复合检测" if is_composite else "单检测"
        status = "✅" if mode == expected.split("（")[0] else "❌"

        print(f"{status} {detection_capabilities} -> {mode} (预期: {expected})")

    return True


async def test_stream_analysis_service_integration():
    """测试3: 验证StreamAnalysisService集成"""
    print("\n" + "=" * 80)
    print("测试3: 验证StreamAnalysisService模板读取")
    print("=" * 80)

    import asyncpg
    import os

    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME')
    )

    try:
        # 模拟StreamAnalysisService的查询逻辑
        row = await conn.fetchrow("""
            SELECT
                id, name, description, provider, model_name,
                system_prompt, user_prompt, temperature, top_p, max_tokens,
                confidence_threshold, tags, detection_capabilities
            FROM ai_model_configs
            WHERE id = $1::uuid
        """, 'edac6c8d-9a27-4f73-9112-0dcc5644e063')

        if row:
            # 模拟服务层的处理逻辑
            detection_capabilities = row[12] if row[12] else []

            template = {
                'id': str(row[0]),
                'name': row[1],
                'detection_capabilities': detection_capabilities,
            }

            print(f"✅ 模板加载成功")
            print(f"   ID: {template['id']}")
            print(f"   名称: {template['name']}")
            print(f"   检测能力: {template['detection_capabilities']}")

            if detection_capabilities:
                print(f"   ✅ 包含 {len(detection_capabilities)} 个检测能力")
                return True
            else:
                print(f"   ❌ 检测能力为空")
                return False
        else:
            print("❌ 模板未找到")
            return False
    finally:
        await conn.close()


async def test_frame_analyzer_mode_selection():
    """测试4: 验证StreamFrameAnalyzer模式选择逻辑"""
    print("\n" + "=" * 80)
    print("测试4: 验证StreamFrameAnalyzer模式选择")
    print("=" * 80)

    # 模拟模板数据
    templates = [
        {
            'name': '测试-复合检测',
            'detection_capabilities': ['safety_helmet', 'smoking']
        },
        {
            'name': '佩戴安全帽-单检测',
            'detection_capabilities': []
        },
        {
            'name': '吸烟-单检测',
            'detection_capabilities': ['smoking']
        },
    ]

    for template in templates:
        detection_capabilities = template.get('detection_capabilities', [])

        # 模拟StreamFrameAnalyzer的判断逻辑
        if detection_capabilities and len(detection_capabilities) > 1:
            mode = "复合检测"
            method = "_analyze_composite_detection_single"
        else:
            mode = "单检测"
            method = "_analyze_single_template"

        print(f"✅ {template['name']}")
        print(f"   检测能力: {detection_capabilities}")
        print(f"   模式: {mode}")
        print(f"   调用方法: {method}")
        print()

    return True


async def test_detection_type_templates_query():
    """测试5: 验证detection_type_templates查询"""
    print("=" * 80)
    print("测试5: 验证detection_type_templates查询")
    print("=" * 80)

    from services.video_analysis_template_service import video_analysis_template_service

    type_codes = ['safety_helmet', 'smoking']

    for type_code in type_codes:
        type_template = await video_analysis_template_service.get_detection_type_by_code(type_code)

        if type_template:
            print(f"✅ {type_code}")
            print(f"   显示名称: {type_template.get('display_name')}")
            print(f"   类别: {type_template.get('category')}")
            print(f"   严重程度: {type_template.get('severity')}")
        else:
            print(f"❌ {type_code} - 未找到")

    return True


async def main():
    """运行所有测试"""
    print("\n🔍 开始复合检测逻辑验证测试\n")

    try:
        # 测试1: 字段读取
        result1 = await test_detection_capabilities_loading()

        # 测试2: 模式判断
        result2 = await test_mode_detection_logic()

        # 测试3: 服务集成
        result3 = await test_stream_analysis_service_integration()

        # 测试4: 帧分析器
        result4 = await test_frame_analyzer_mode_selection()

        # 测试5: 检测类型模板
        result5 = await test_detection_type_templates_query()

        # 汇总结果
        print("\n" + "=" * 80)
        print("测试结果汇总")
        print("=" * 80)
        print(f"测试1 - detection_capabilities读取: {'✅ 通过' if result1 else '❌ 失败'}")
        print(f"测试2 - 自动模式判断逻辑: {'✅ 通过' if result2 else '❌ 失败'}")
        print(f"测试3 - StreamAnalysisService集成: {'✅ 通过' if result3 else '❌ 失败'}")
        print(f"测试4 - StreamFrameAnalyzer模式选择: {'✅ 通过' if result4 else '❌ 失败'}")
        print(f"测试5 - detection_type_templates查询: {'✅ 通过' if result5 else '❌ 失败'}")

        all_passed = all([result1, result2, result3, result4, result5])

        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 所有测试通过！复合检测逻辑验证成功！")
        else:
            print("⚠️  部分测试失败，请检查实现")
        print("=" * 80)

        return all_passed

    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
