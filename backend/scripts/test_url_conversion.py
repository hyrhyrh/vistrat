"""
URL转换功能测试脚本

用于测试MinIO URL转换为公网可访问的代理URL功能
"""

import os
import sys

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.storage import StorageService
from config.settings import ServerConfig


def test_url_conversion():
    """测试URL转换功能"""

    print("=" * 80)
    print("URL转换功能测试")
    print("=" * 80)

    # 显示当前配置
    print(f"\n【当前配置】")
    print(f"PUBLIC_BASE_URL: {ServerConfig.PUBLIC_BASE_URL}")
    print(f"PORT: {ServerConfig.PORT}")

    # 测试用例
    test_cases = [
        {
            "name": "实时流图片URL - Docker内网地址",
            "input": "http://minio:9000/images/streams/d40dad17-6109-4e2d-a201-376347ca20da/frame_000666.jpg",
            "expected_path": "/api/image-proxy/minio/images/streams/d40dad17-6109-4e2d-a201-376347ca20da/frame_000666.jpg"
        },
        {
            "name": "离线分析图片URL - localhost地址",
            "input": "http://localhost:9010/images/analysis/task123/frame_000100.jpg",
            "expected_path": "/api/image-proxy/minio/images/analysis/task123/frame_000100.jpg"
        },
        {
            "name": "实时流图片URL - vision_minio容器",
            "input": "http://vision_minio:9000/images/streams/abc123/frame_000001.jpg",
            "expected_path": "/api/image-proxy/minio/images/streams/abc123/frame_000001.jpg"
        }
    ]

    print(f"\n【测试用例】")
    success_count = 0

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {test_case['name']}")
        print(f"输入URL: {test_case['input']}")

        # 执行转换
        result = StorageService.convert_to_proxy_url(test_case['input'])
        print(f"输出URL: {result}")

        # 验证结果
        if 'localhost' in ServerConfig.PUBLIC_BASE_URL or '127.0.0.1' in ServerConfig.PUBLIC_BASE_URL:
            # 开发环境：应该是相对路径
            expected = test_case['expected_path']
            if result == expected:
                print(f"✅ 测试通过（开发环境相对路径）")
                success_count += 1
            else:
                print(f"❌ 测试失败")
                print(f"期望: {expected}")
                print(f"实际: {result}")
        else:
            # 生产环境：应该包含完整的公网URL
            expected = f"{ServerConfig.PUBLIC_BASE_URL}{test_case['expected_path']}"
            if result == expected:
                print(f"✅ 测试通过（生产环境完整URL）")
                success_count += 1
            else:
                print(f"❌ 测试失败")
                print(f"期望: {expected}")
                print(f"实际: {result}")

    # 汇总结果
    print("\n" + "=" * 80)
    print(f"测试结果: {success_count}/{len(test_cases)} 通过")

    if success_count == len(test_cases):
        print("✅ 所有测试通过！")
    else:
        print(f"❌ {len(test_cases) - success_count} 个测试失败")

    print("=" * 80)

    # 演示生产环境配置示例
    print(f"\n【生产环境配置示例】")
    print("如果您的公网IP是 <INTERNAL_HOST>，请在 .env 文件中配置：")
    print("PUBLIC_BASE_URL=http://<INTERNAL_HOST>:16532")
    print("\n或者如果使用域名：")
    print("PUBLIC_BASE_URL=https://your-domain.com")
    print("\n配置后，生成的URL将是：")
    print("http://<INTERNAL_HOST>:16532/api/image-proxy/minio/images/streams/xxx/frame_001.jpg")
    print("=" * 80)


if __name__ == "__main__":
    test_url_conversion()
