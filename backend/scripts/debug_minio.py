#!/usr/bin/env python3
"""
MinIO存储桶内容检查脚本
用于调试和检查MinIO中的文件状态
"""

import asyncio
import sys
import os
from datetime import timedelta

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(__file__))

from storage.services.minio_client import MinIOClient
from config.settings import StorageConfig
from utils.timezone_utils import now, now_isoformat

async def check_minio_status():
    """检查MinIO存储桶状态"""
    print("=== MinIO存储桶状态检查 ===")
    print(f"MinIO端点: {StorageConfig.MINIO_ENDPOINT}")
    
    minio_client = MinIOClient()
    
    # 检查各个存储桶
    buckets = ["videos", "images", "thumbnails", "annotations", "documents", "temp"]
    
    for bucket_name in buckets:
        try:
            print(f"\n--- 检查存储桶: {bucket_name} ---")
            
            # 列出文件
            objects = await minio_client.list_objects(bucket_name, limit=100)
            
            if not objects:
                print(f"  存储桶 {bucket_name} 为空")
                continue
                
            print(f"  文件数量: {len(objects)}")
            
            # 按日期排序显示最新的几个文件
            objects_sorted = sorted(objects, key=lambda x: x.last_modified, reverse=True)
            
            print("  最新的文件:")
            for i, obj in enumerate(objects_sorted[:5]):
                print(f"    {i+1}. {obj.object_key}")
                print(f"       大小: {obj.file_size} bytes")
                print(f"       修改时间: {obj.last_modified}")
            
            # 统计文件大小
            total_size = sum(obj.file_size for obj in objects)
            print(f"  总大小: {total_size / 1024 / 1024:.2f} MB")
            
            # 检查是否有很旧的文件
            cutoff_date = now() - timedelta(days=30)
            old_files = [obj for obj in objects if obj.last_modified < cutoff_date]
            
            if old_files:
                print(f"  ⚠️  发现 {len(old_files)} 个超过30天的文件")
                print("  最旧的文件:")
                old_files_sorted = sorted(old_files, key=lambda x: x.last_modified)
                for obj in old_files_sorted[:3]:
                    print(f"    - {obj.object_key} ({obj.last_modified})")
            else:
                print("  ✅ 没有超过30天的文件")
                
        except Exception as e:
            print(f"  ❌ 检查存储桶 {bucket_name} 失败: {e}")

async def check_cleanup_history():
    """检查是否有清理历史"""
    print("\n=== 检查清理历史 ===")
    
    # 这里可以添加检查日志文件的逻辑
    # 目前先检查是否有cleanup方法被调用的痕迹
    
    print("检查代码中的cleanup_expired_files方法是否被调用...")
    
    # 检查是否有定时任务配置
    try:
        # 模拟调用清理方法看看会发生什么（不实际执行删除）
        minio_client = MinIOClient()
        
        print("检查images存储桶中的过期文件...")
        objects = await minio_client.list_objects("images", limit=1000)
        
        cutoff_date = now() - timedelta(days=30)
        
        expired_objects = []
        for obj in objects:
            if obj.last_modified < cutoff_date:
                expired_objects.append(obj)
        
        if expired_objects:
            print(f"⚠️  发现 {len(expired_objects)} 个过期文件会被cleanup_expired_files方法删除:")
            for obj in expired_objects[:10]:  # 只显示前10个
                print(f"  - {obj.object_key} (修改时间: {obj.last_modified})")
        else:
            print("✅ 没有发现会被自动清理的过期文件")
            
    except Exception as e:
        print(f"❌ 检查清理历史失败: {e}")

async def main():
    """主函数"""
    await check_minio_status()
    await check_cleanup_history()

if __name__ == "__main__":
    asyncio.run(main())