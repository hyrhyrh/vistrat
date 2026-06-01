"""
存储服务模块
负责文件存储、视频保存、历史记录管理
"""

import cv2
import os
import httpx
import logging
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

from config.settings import RAGConfig, PathConfig
from storage.services.minio_client import MinIOClient
from utils.async_helpers import run_blocking


logger = logging.getLogger(__name__)


class StorageService:
    """存储服务"""
    
    def __init__(self):
        self.minio_client = MinIOClient()
    
    @staticmethod
    async def save_warning_video(frames: List[np.ndarray], file_prefix: str, fps: float) -> str:
        """保存异常视频文件"""
        try:
            if not frames:
                raise ValueError("帧数据为空")

            # 构建输出路径
            output_path = PathConfig.WARNING_DIR / f"{file_prefix}.mp4"

            def _write_video():
                """同步写入视频文件"""
                # 获取视频参数
                height, width = frames[0].shape[:2]
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')

                # 创建视频写入器
                video_writer = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

                # 写入所有帧
                for frame in frames:
                    # 确保帧格式正确
                    f = frame
                    if f.dtype != np.uint8:
                        f = f.astype(np.uint8)
                    if len(f.shape) == 2:
                        f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
                    video_writer.write(f)

                video_writer.release()

            # NOTE(async): cv2.VideoWriter 是阻塞IO操作，必须在线程池中运行
            await run_blocking(_write_video)

            logger.info(f"异常视频已保存: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"保存异常视频失败: {e}")
            raise

    @staticmethod
    async def save_warning_image(frame: np.ndarray, file_prefix: str) -> str:
        """保存异常截图"""
        try:
            output_path = PathConfig.WARNING_DIR / f"{file_prefix}.jpg"

            # 确保帧格式正确
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

            # NOTE(async): cv2.imwrite 是阻塞IO操作，必须在线程池中运行
            await run_blocking(cv2.imwrite, str(output_path), frame)

            logger.info(f"异常截图已保存: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"保存异常截图失败: {e}")
            raise

    @staticmethod
    async def insert_to_vector_db(docs: List[str], table_name: str = "video_analysis") -> Dict:
        """插入文档到向量数据库"""
        try:
            if not RAGConfig.ENABLE_RAG:
                logger.warning("RAG功能未启用")
                return {"status": "disabled"}

            data = {
                "docs": docs,
                "table_name": table_name
            }

            # 使用 httpx 异步 HTTP 客户端替代同步 requests
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(RAGConfig.VECTOR_API_URL, json=data)
                response.raise_for_status()

            logger.info(f"文档已插入向量数据库: {len(docs)} 条")
            return response.json()

        except Exception as e:
            logger.error(f"向量数据库插入失败: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def save_uploaded_file(file_content: bytes, filename: str) -> str:
        """保存上传的文件"""
        try:
            # 确保上传目录存在
            PathConfig.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            
            file_path = PathConfig.UPLOAD_DIR / filename
            
            with open(file_path, 'wb') as f:
                f.write(file_content)
                
            logger.info(f"文件已保存: {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"文件保存失败: {e}")
            raise

    @staticmethod
    def cleanup_temp_files():
        """清理临时文件"""
        try:
            temp_patterns = ["*.jpg", "*.png", "temp_*", "output_frame.*"]
            
            for pattern in temp_patterns:
                for file_path in PathConfig.BACKEND_DIR.glob(pattern):
                    if file_path.is_file():
                        file_path.unlink()
                        logger.debug(f"清理临时文件: {file_path}")
                        
        except Exception as e:
            logger.error(f"清理临时文件失败: {e}")

    async def upload_frame_image(self, image_path: str, task_id: str, frame_index: int) -> str:
        """
        上传离线视频分析帧图片到MinIO，并返回公网可访问的代理URL

        Args:
            image_path: 本地图片路径
            task_id: 分析任务ID
            frame_index: 帧索引

        Returns:
            公网可访问的代理URL，格式如：
                - 开发环境: /api/image-proxy/minio/images/analysis/{task_id}/frame_{frame_index}.jpg
                - 生产环境: http://公网IP:端口/api/image-proxy/minio/images/analysis/{task_id}/frame_{frame_index}.jpg
        """
        try:
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # 构建对象键
            object_key = f"analysis/{task_id}/frame_{frame_index:06d}.jpg"

            # 上传到MinIO
            bucket_name = "images"
            file_info = await self.minio_client.upload_file(
                bucket_name=bucket_name,
                object_key=object_key,
                file_content=image_data,
                content_type="image/jpeg",
                metadata={
                    "task_id": task_id,
                    "frame_index": str(frame_index),
                    "uploaded_at": str(Path(image_path).stat().st_mtime),
                    "data_type": "video_frame"
                }
            )

            # 生成MinIO内网URL
            from config.settings import StorageConfig
            protocol = "https" if StorageConfig.MINIO_SECURE else "http"
            minio_url = f"{protocol}://{StorageConfig.MINIO_ENDPOINT}/{bucket_name}/{object_key}"

            # 转换为公网可访问的代理URL
            proxy_url = StorageService.convert_to_proxy_url(minio_url)

            logger.debug(f"离线视频帧图片上传成功: MinIO={minio_url}, Proxy={proxy_url}")
            return proxy_url

        except Exception as e:
            logger.error(f"上传帧图片失败 {image_path}: {e}")
            # 返回本地路径作为备选
            return image_path

    async def upload_stream_frame_image(self, image_path: str, stream_id: str, frame_index: int) -> str:
        """
        上传实时流帧图片到MinIO，并返回公网可访问的代理URL

        Args:
            image_path: 本地图片路径
            stream_id: 流ID
            frame_index: 帧索引

        Returns:
            公网可访问的代理URL，格式如：
                - 开发环境: /api/image-proxy/minio/images/streams/{stream_id}/frame_{frame_index}.jpg
                - 生产环境: http://公网IP:端口/api/image-proxy/minio/images/streams/{stream_id}/frame_{frame_index}.jpg
        """
        try:
            # 读取图片文件
            with open(image_path, 'rb') as f:
                image_data = f.read()

            # 构建对象键 - 使用不同的路径前缀区分实时流
            object_key = f"streams/{stream_id}/frame_{frame_index:06d}.jpg"

            # 上传到MinIO
            bucket_name = "images"
            file_info = await self.minio_client.upload_file(
                bucket_name=bucket_name,
                object_key=object_key,
                file_content=image_data,
                content_type="image/jpeg",
                metadata={
                    "stream_id": stream_id,
                    "frame_index": str(frame_index),
                    "uploaded_at": str(Path(image_path).stat().st_mtime),
                    "data_type": "stream_frame"
                }
            )

            # 生成MinIO内网URL
            from config.settings import StorageConfig
            protocol = "https" if StorageConfig.MINIO_SECURE else "http"
            minio_url = f"{protocol}://{StorageConfig.MINIO_ENDPOINT}/{bucket_name}/{object_key}"

            # 转换为公网可访问的代理URL
            proxy_url = StorageService.convert_to_proxy_url(minio_url)

            logger.debug(f"实时流帧图片上传成功: MinIO={minio_url}, Proxy={proxy_url}")
            return proxy_url

        except Exception as e:
            logger.error(f"上传实时流帧图片失败 {image_path}: {e}")
            # 返回本地路径作为备选
            return image_path

    async def upload_alert_clip(self, alert_id: str, local_mp4_path: str) -> str:
        """上传告警视频片段到 MinIO alert-clips 桶，返回公网可访问的代理 URL。

        约定：
            - bucket: alert-clips（如不存在会由 _ensure_buckets_exist 自动创建）
            - key: {alert_id}.mp4
            - content_type: video/mp4

        Args:
            alert_id: 告警 ID（作为对象键主文件名）
            local_mp4_path: 本地 mp4 文件绝对路径

        Returns:
            代理 URL 字符串（与 upload_frame_image 风格一致，复用 convert_to_proxy_url）。
        """
        try:
            with open(local_mp4_path, "rb") as f:
                clip_data = f.read()

            bucket_name = "alert-clips"
            object_key = f"{alert_id}.mp4"

            await self.minio_client.upload_file(
                bucket_name=bucket_name,
                object_key=object_key,
                file_content=clip_data,
                content_type="video/mp4",
                metadata={
                    "alert_id": alert_id,
                    "data_type": "alert_clip",
                },
            )

            from config.settings import StorageConfig
            protocol = "https" if StorageConfig.MINIO_SECURE else "http"
            minio_url = f"{protocol}://{StorageConfig.MINIO_ENDPOINT}/{bucket_name}/{object_key}"
            proxy_url = StorageService.convert_to_proxy_url(minio_url)

            logger.info(
                f"告警片段上传成功: alert_id={alert_id} size={len(clip_data)} "
                f"proxy={proxy_url}"
            )
            return proxy_url

        except Exception as e:
            logger.error(f"上传告警片段失败 alert_id={alert_id} path={local_mp4_path}: {e}")
            raise

    def generate_presigned_get(self, bucket: str, key: str, expires: int = 900) -> str:
        """
        生成 MinIO 预签名 GET URL（同步调用，底层 minio SDK 本身是 HTTP 无状态签名）

        用途：提供给 A100 推理服务（Vistrat Inference Tier 2）拉取原始帧图片。

        Args:
            bucket: 桶名
            key: 对象键
            expires: 过期秒数，默认 15 分钟

        Returns:
            预签名 URL 字符串
        """
        from datetime import timedelta
        try:
            url = self.minio_client.client.presigned_get_object(
                bucket_name=bucket,
                object_name=key,
                expires=timedelta(seconds=expires),
            )
            logger.debug(f"生成预签名GET URL: {bucket}/{key} 过期={expires}s")
            return url
        except Exception as e:
            logger.error(f"生成预签名URL失败 {bucket}/{key}: {e}")
            raise

    @staticmethod
    def convert_to_internal_url(external_url: str) -> str:
        """
        将MinIO URL转换为Docker内网URL（供本地AI模型访问）

        Args:
            external_url: MinIO URL，可能是以下格式之一：
                - http://localhost:9010/images/...  (宿主机访问)
                - http://minio:9000/images/...      (容器间访问)

        Returns:
            内网URL，使用MinIO容器IP地址，如 http://172.19.0.2:9000/images/...
        """
        from config.settings import StorageConfig

        # 如果不是MinIO URL，直接返回
        if not external_url or not external_url.startswith('http'):
            return external_url

        # 获取配置
        internal_endpoint = StorageConfig.MINIO_INTERNAL_ENDPOINT
        protocol = "https" if StorageConfig.MINIO_SECURE else "http"

        # 需要处理的所有可能的MinIO端点格式
        possible_endpoints = [
            StorageConfig.MINIO_ENDPOINT,  # 可能是 minio:9000 或 localhost:9000
            "localhost:9010",              # 宿主机访问端口
            "minio:9000",                  # Docker容器名访问
            "vision_minio:9000"            # Docker容器完整名称
        ]

        # 尝试匹配并替换
        internal_base = f"{protocol}://{internal_endpoint}"

        for endpoint in possible_endpoints:
            external_base = f"{protocol}://{endpoint}"
            if external_url.startswith(external_base):
                internal_url = external_url.replace(external_base, internal_base, 1)
                logger.debug(f"URL转换: {external_url} -> {internal_url}")
                return internal_url

        # 如果没有匹配，可能URL中已经是bucket路径，尝试直接拼接
        logger.warning(f"未匹配到MinIO端点，保持原URL: {external_url}")
        return external_url

    @staticmethod
    def convert_to_proxy_url(minio_url: str) -> str:
        """
        将MinIO内网URL转换为公网可访问的代理URL

        Args:
            minio_url: MinIO内网URL，格式如：
                - http://minio:9000/images/streams/xxx/frame_001.jpg
                - http://localhost:9010/images/analysis/xxx.jpg

        Returns:
            代理URL，格式如：
                - http://<INTERNAL_HOST>:16532/api/image-proxy/minio/images/streams/xxx/frame_001.jpg
                - 如果配置了PUBLIC_BASE_URL，则使用公网地址
                - 如果未配置，则使用相对路径 /api/image-proxy/minio/...
        """
        from config.settings import StorageConfig, ServerConfig
        from urllib.parse import urlparse

        # 如果不是URL格式，直接返回
        if not minio_url or not minio_url.startswith('http'):
            return minio_url

        try:
            # 解析MinIO URL
            parsed = urlparse(minio_url)
            path_parts = parsed.path.strip('/').split('/', 1)  # 分割成 [bucket_name, object_path]

            if len(path_parts) < 2:
                logger.warning(f"MinIO URL格式不正确，无法转换: {minio_url}")
                return minio_url

            bucket_name = path_parts[0]
            object_path = path_parts[1]

            # 构建代理路径
            proxy_path = f"/api/image-proxy/minio/{bucket_name}/{object_path}"

            # 获取公网基础URL
            public_base_url = ServerConfig.PUBLIC_BASE_URL.rstrip('/')

            # 如果PUBLIC_BASE_URL是默认的localhost，使用相对路径（适用于开发环境）
            if 'localhost' in public_base_url or '127.0.0.1' in public_base_url:
                proxy_url = proxy_path
            else:
                # 生产环境使用完整URL
                proxy_url = f"{public_base_url}{proxy_path}"

            logger.debug(f"URL转换为代理地址: {minio_url} -> {proxy_url}")
            return proxy_url

        except Exception as e:
            logger.error(f"转换MinIO URL为代理URL失败: {minio_url}, 错误: {e}")
            return minio_url


# 创建全局实例
storage_service = StorageService()