"""
测试Qwen API连接和基本功能
"""
import asyncio
from openai import OpenAI
from config.settings import APIConfig

async def test_qwen_api():
    """测试Qwen API"""
    print("=" * 60)
    print("Qwen API 测试")
    print("=" * 60)

    # 显示配置
    print(f"\n📋 配置信息:")
    print(f"  API Key: {APIConfig.QWEN_API_KEY[:20]}... (长度: {len(APIConfig.QWEN_API_KEY)})")
    print(f"  API URL: {APIConfig.QWEN_API_URL}")
    print(f"  Model: {APIConfig.QWEN_MODEL}")

    # 提取base_url
    base_url = APIConfig.QWEN_API_URL.replace("/chat/completions", "")
    print(f"  Base URL: {base_url}")

    try:
        # 创建客户端
        print("\n🔧 创建OpenAI客户端...")
        client = OpenAI(
            api_key=APIConfig.QWEN_API_KEY,
            base_url=base_url
        )
        print("✅ 客户端创建成功")

        # 测试1: 简单文本生成(非流式)
        print("\n📝 测试1: 简单文本生成(非流式)...")
        response = client.chat.completions.create(
            model=APIConfig.QWEN_MODEL,
            messages=[
                {"role": "user", "content": "你好,请回复'测试成功'"}
            ],
            temperature=0.1,
            max_tokens=50,
            stream=False
        )
        print(f"✅ 响应: {response.choices[0].message.content}")

        # 测试2: 流式文本生成
        print("\n📝 测试2: 流式文本生成...")
        stream_response = client.chat.completions.create(
            model=APIConfig.QWEN_MODEL,
            messages=[
                {"role": "user", "content": "数到5"}
            ],
            temperature=0.1,
            max_tokens=100,
            stream=True
        )

        print("流式输出: ", end="", flush=True)
        for chunk in stream_response:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n✅ 流式生成成功")

        # 测试3: Function Calling
        print("\n📝 测试3: Function Calling...")
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "获取指定城市的天气信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "城市名称"
                            }
                        },
                        "required": ["city"]
                    }
                }
            }
        ]

        fc_response = client.chat.completions.create(
            model=APIConfig.QWEN_MODEL,
            messages=[
                {"role": "user", "content": "北京今天天气怎么样"}
            ],
            tools=tools,
            tool_choice="auto",
            stream=False
        )

        message = fc_response.choices[0].message
        if message.tool_calls:
            print(f"✅ Function Calling成功")
            print(f"  调用工具: {message.tool_calls[0].function.name}")
            print(f"  参数: {message.tool_calls[0].function.arguments}")
        else:
            print(f"⚠️  没有触发Function Calling")
            print(f"  回复: {message.content}")

        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    asyncio.run(test_qwen_api())
