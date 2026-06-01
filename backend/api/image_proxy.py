"""
图片代理服务 - 提供MinIO存储图片的安全访问
解决MinIO直接访问权限问题，提供统一的图片访问接口
"""

import logging
import asyncio
from typing import Optional
from urllib.parse import unquote, urlparse
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from storage.services.minio_client import MinIOClient
from config.settings import StorageConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image-proxy", tags=["图片代理"])

# 全局MinIO客户端
minio_client = MinIOClient()


@router.get("/minio/{bucket_name}/{object_path:path}", summary="MinIO图片代理")
async def get_minio_image(
    bucket_name: str,
    object_path: str
):
    """
    通过代理访问MinIO存储的图片
    
    Args:
        bucket_name: 存储桶名称
        object_path: 对象路径（支持嵌套路径）
        
    Returns:
        图片内容
    """
    try:
        # 解码URL编码的路径
        object_path = unquote(object_path)
        
        logger.info(f"代理访问MinIO图片: {bucket_name}/{object_path}")
        
        # 从MinIO下载图片
        image_data = await minio_client.download_file(bucket_name, object_path)
        
        # 根据文件扩展名确定内容类型
        content_type = "image/jpeg"  # 默认
        if object_path.lower().endswith('.png'):
            content_type = "image/png"
        elif object_path.lower().endswith('.gif'):
            content_type = "image/gif"
        elif object_path.lower().endswith('.webp'):
            content_type = "image/webp"
        elif object_path.lower().endswith('.bmp'):
            content_type = "image/bmp"
        
        # 返回图片内容
        return Response(
            content=image_data,
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=3600",  # 缓存1小时
                "Content-Disposition": f"inline; filename={object_path.split('/')[-1]}"
            }
        )
        
    except Exception as e:
        logger.error(f"代理访问MinIO图片失败: {bucket_name}/{object_path} - {e}")
        raise HTTPException(
            status_code=404, 
            detail=f"图片不存在或访问失败: {bucket_name}/{object_path}"
        )


@router.get("/presigned", summary="生成预签名URL")
async def get_presigned_url(
    bucket_name: str = Query(..., description="存储桶名称"),
    object_path: str = Query(..., description="对象路径"),
    expiry_hours: int = Query(1, description="有效期（小时）")
):
    """
    生成MinIO预签名URL
    
    Args:
        bucket_name: 存储桶名称  
        object_path: 对象路径
        expiry_hours: URL有效期（小时）
        
    Returns:
        预签名URL
    """
    try:
        # 解码URL编码的路径
        object_path = unquote(object_path)
        
        logger.info(f"生成预签名URL: {bucket_name}/{object_path}")
        
        # 生成预签名URL
        presigned_url = await minio_client.get_presigned_url(
            bucket_name=bucket_name,
            object_key=object_path,
            expiry_hours=expiry_hours
        )
        
        return {
            "success": True,
            "presigned_url": presigned_url,
            "expires_in_hours": expiry_hours,
            "bucket_name": bucket_name,
            "object_path": object_path
        }
        
    except Exception as e:
        logger.error(f"生成预签名URL失败: {bucket_name}/{object_path} - {e}")
        raise HTTPException(
            status_code=500,
            detail=f"生成预签名URL失败: {str(e)}"
        )


@router.get("/url-convert", summary="转换MinIO URL")
async def convert_minio_url(url: str = Query(..., description="原始MinIO URL")):
    """
    将MinIO直接URL转换为代理URL
    
    Args:
        url: 原始MinIO URL (如: http://localhost:9000/images/analysis/xxx.jpg)
        
    Returns:
        代理URL (如: /api/image-proxy/minio/images/analysis/xxx.jpg)
    """
    try:
        # 解析URL
        parsed_url = urlparse(url)
        
        # 检查是否是MinIO URL
        if not parsed_url.netloc.startswith(StorageConfig.MINIO_ENDPOINT.split(':')[0]):
            return {
                "success": False,
                "message": "不是有效的MinIO URL",
                "original_url": url
            }
        
        # 提取路径部分（去除开头的'/'）
        path_parts = parsed_url.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            return {
                "success": False,
                "message": "URL路径格式不正确",
                "original_url": url
            }
        
        bucket_name = path_parts[0]
        object_path = '/'.join(path_parts[1:])
        
        # 生成代理URL
        proxy_url = f"/api/image-proxy/minio/{bucket_name}/{object_path}"
        
        return {
            "success": True,
            "original_url": url,
            "proxy_url": proxy_url,
            "bucket_name": bucket_name,
            "object_path": object_path
        }
        
    except Exception as e:
        logger.error(f"转换MinIO URL失败: {url} - {e}")
        return {
            "success": False,
            "message": f"URL转换失败: {str(e)}",
            "original_url": url
        }


@router.get("/test", summary="测试图片代理服务")
async def test_image_proxy():
    """测试图片代理服务状态"""
    try:
        # 测试MinIO连接
        await minio_client._ensure_buckets_exist()
        
        return {
            "success": True,
            "message": "图片代理服务正常",
            "minio_endpoint": StorageConfig.MINIO_ENDPOINT,
            "available_endpoints": [
                "/api/image-proxy/minio/{bucket_name}/{object_path}",
                "/api/image-proxy/presigned",
                "/api/image-proxy/url-convert"
            ]
        }
        
    except Exception as e:
        logger.error(f"图片代理服务测试失败: {e}")
        return {
            "success": False,
            "message": f"服务测试失败: {str(e)}"
        }