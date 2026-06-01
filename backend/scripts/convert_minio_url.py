#!/usr/bin/env python3
"""
MinIO URL转换工具

用法：
    python convert_minio_url.py "http://minio:9000/images/streams/xxx/frame_001.jpg"
"""

import sys
import os

# 添加backend目录到Python路径
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.storage import StorageService
from config.settings import ServerConfig


def convert_url(minio_url: str, public_ip: str = None):
    """转换MinIO URL为代理URL"""

    print("=" * 80)
    print("MinIO URL 转换工具")
    print("=" * 80)

    print(f"\n【输入】MinIO内网URL:")
    print(f"  {minio_url}")

    # 转换URL
    proxy_url = StorageService.convert_to_proxy_url(minio_url)

    print(f"\n【输出】代理URL (开发环境):")
    print(f"  {proxy_url}")

    # 如果提供了公网IP，生成完整URL
    if public_ip:
        if proxy_url.startswith('/'):
            full_url = f"http://{public_ip}:16532{proxy_url}"
        else:
            full_url = proxy_url
        print(f"\n【输出】代理URL (生产环境 - {public_ip}):")
        print(f"  {full_url}")
        print(f"\n【测试】复制此URL到浏览器访问:")
        print(f"  {full_url}")

    print("\n" + "=" * 80)

    # 提取URL组成部分
    from urllib.parse import urlparse
    parsed = urlparse(minio_url)
    path_parts = parsed.path.strip('/').split('/', 1)

    if len(path_parts) >= 2:
        bucket_name = path_parts[0]
        object_path = path_parts[1]

        print("\n【URL组成部分】")
        print(f"  Bucket: {bucket_name}")
        print(f"  Object Path: {object_path}")
        print(f"  代理路径格式: /api/image-proxy/minio/{bucket_name}/{object_path}")

    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("用法：python convert_minio_url.py <MinIO_URL> [公网IP]")
        print("\n示例1（只转换，不指定IP）：")
        print('  python convert_minio_url.py "http://minio:9000/images/streams/xxx/frame_001.jpg"')
        print("\n示例2（转换并生成完整公网URL）：")
        print('  python convert_minio_url.py "http://minio:9000/images/streams/xxx/frame_001.jpg" "localhost"')
        sys.exit(1)

    minio_url = sys.argv[1]
    public_ip = sys.argv[2] if len(sys.argv) > 2 else None

    convert_url(minio_url, public_ip)


if __name__ == "__main__":
    main()
