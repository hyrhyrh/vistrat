"""
存储服务单元测试
覆盖文件保存、异常视频/截图保存、URL 转换、临时文件清理等场景
"""

import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import numpy as np
import pytest

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from services.storage import StorageService


# ============================================================================
# save_uploaded_file 测试
# ============================================================================

class TestSaveUploadedFile:
    """上传文件保存测试"""

    @patch("services.storage.PathConfig")
    def test_save_uploaded_file_正常保存(self, mock_path_config, tmp_path):
        """应正确保存文件内容并返回路径"""
        mock_path_config.UPLOAD_DIR = tmp_path
        content = b"fake video content"
        filename = "test_video.mp4"

        result = StorageService.save_uploaded_file(content, filename)

        saved_file = tmp_path / filename
        assert saved_file.exists()
        assert saved_file.read_bytes() == content
        assert result == str(saved_file)

    @patch("services.storage.PathConfig")
    def test_save_uploaded_file_创建目录(self, mock_path_config, tmp_path):
        """上传目录不存在时应自动创建"""
        upload_dir = tmp_path / "new_dir" / "uploads"
        mock_path_config.UPLOAD_DIR = upload_dir

        StorageService.save_uploaded_file(b"data", "file.txt")

        assert upload_dir.exists()

    @patch("services.storage.PathConfig")
    def test_save_uploaded_file_空文件(self, mock_path_config, tmp_path):
        """空内容也应正常保存"""
        mock_path_config.UPLOAD_DIR = tmp_path
        result = StorageService.save_uploaded_file(b"", "empty.txt")
        assert (tmp_path / "empty.txt").stat().st_size == 0


# ============================================================================
# save_warning_video 测试
# ============================================================================

class TestSaveWarningVideo:
    """异常视频保存测试"""

    @pytest.mark.asyncio
    @patch("services.storage.cv2")
    @patch("services.storage.PathConfig")
    async def test_save_warning_video_正常保存(self, mock_path_config, mock_cv2, tmp_path):
        """应创建视频文件并写入所有帧"""
        mock_path_config.WARNING_DIR = tmp_path
        mock_writer = MagicMock()
        mock_cv2.VideoWriter_fourcc.return_value = 1234
        mock_cv2.VideoWriter.return_value = mock_writer

        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        result = await StorageService.save_warning_video(frames, "test_warning", 25.0)

        assert "test_warning.mp4" in result
        assert mock_writer.write.call_count == 5
        mock_writer.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_warning_video_空帧列表抛异常(self):
        """空帧列表应抛出 ValueError"""
        with pytest.raises(ValueError, match="帧数据为空"):
            await StorageService.save_warning_video([], "empty", 25.0)

    @pytest.mark.asyncio
    @patch("services.storage.cv2")
    @patch("services.storage.PathConfig")
    async def test_save_warning_video_灰度帧转换(self, mock_path_config, mock_cv2, tmp_path):
        """灰度帧应自动转换为 BGR"""
        mock_path_config.WARNING_DIR = tmp_path
        mock_writer = MagicMock()
        mock_cv2.VideoWriter_fourcc.return_value = 1234
        mock_cv2.VideoWriter.return_value = mock_writer
        mock_cv2.cvtColor.return_value = np.zeros((480, 640, 3), dtype=np.uint8)

        # 灰度帧（2D）
        gray_frame = np.zeros((480, 640), dtype=np.uint8)
        await StorageService.save_warning_video([gray_frame], "gray", 25.0)

        mock_cv2.cvtColor.assert_called_once()


# ============================================================================
# save_warning_image 测试
# ============================================================================

class TestSaveWarningImage:
    """异常截图保存测试"""

    @pytest.mark.asyncio
    @patch("services.storage.cv2")
    @patch("services.storage.PathConfig")
    async def test_save_warning_image_正常保存(self, mock_path_config, mock_cv2, tmp_path):
        """应保存 JPEG 截图"""
        mock_path_config.WARNING_DIR = tmp_path
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cv2.imwrite.return_value = True

        result = await StorageService.save_warning_image(frame, "alert_001")

        assert "alert_001.jpg" in result
        mock_cv2.imwrite.assert_called_once()

    @pytest.mark.asyncio
    @patch("services.storage.cv2")
    @patch("services.storage.PathConfig")
    async def test_save_warning_image_float帧自动转换(self, mock_path_config, mock_cv2, tmp_path):
        """float 类型帧应自动转为 uint8"""
        mock_path_config.WARNING_DIR = tmp_path
        frame = np.zeros((480, 640, 3), dtype=np.float32)
        mock_cv2.imwrite.return_value = True

        await StorageService.save_warning_image(frame, "float_frame")

        # 验证传入 imwrite 的帧已转为 uint8
        call_args = mock_cv2.imwrite.call_args
        saved_frame = call_args[0][1]
        assert saved_frame.dtype == np.uint8


# ============================================================================
# URL 转换测试
# ============================================================================

class TestURLConversion:
    """URL 转换函数测试"""

    def test_convert_to_proxy_url_生产环境完整URL(self):
        """生产环境应返回带公网 base URL 的代理路径"""
        with patch("config.settings.ServerConfig") as mock_server, \
             patch("config.settings.StorageConfig") as mock_storage:
            mock_server.PUBLIC_BASE_URL = "http://10.0.0.1:16532"
            mock_storage.MINIO_SECURE = False

            minio_url = "http://minio:9000/images/analysis/task1/frame_000001.jpg"
            result = StorageService.convert_to_proxy_url(minio_url)

            assert result.startswith("http://10.0.0.1:16532/api/image-proxy/minio/")
            assert "images/analysis/task1/frame_000001.jpg" in result

    def test_convert_to_proxy_url_开发环境相对路径(self):
        """开发环境（localhost）应返回相对路径"""
        with patch("config.settings.ServerConfig") as mock_server:
            mock_server.PUBLIC_BASE_URL = "http://localhost:16532"

            minio_url = "http://minio:9000/images/test.jpg"
            result = StorageService.convert_to_proxy_url(minio_url)

            assert result.startswith("/api/image-proxy/minio/")
            assert "images/test.jpg" in result

    def test_convert_to_proxy_url_非URL直接返回(self):
        """非 URL 格式应原样返回"""
        assert StorageService.convert_to_proxy_url("") == ""
        assert StorageService.convert_to_proxy_url("/local/path.jpg") == "/local/path.jpg"

    def test_convert_to_internal_url_替换端点(self):
        """应将外部端点替换为内部端点"""
        with patch("config.settings.StorageConfig") as mock_storage:
            mock_storage.MINIO_INTERNAL_ENDPOINT = "172.19.0.2:9000"
            mock_storage.MINIO_SECURE = False
            mock_storage.MINIO_ENDPOINT = "minio:9000"

            url = "http://minio:9000/images/test.jpg"
            result = StorageService.convert_to_internal_url(url)

            assert "172.19.0.2:9000" in result
            assert "images/test.jpg" in result

    def test_convert_to_internal_url_非URL原样返回(self):
        """非 HTTP URL 应原样返回"""
        assert StorageService.convert_to_internal_url("") == ""
        assert StorageService.convert_to_internal_url("/local/file") == "/local/file"

    def test_convert_to_internal_url_localhost端口替换(self):
        """localhost:9010 端口也应被替换"""
        with patch("config.settings.StorageConfig") as mock_storage:
            mock_storage.MINIO_INTERNAL_ENDPOINT = "172.19.0.2:9000"
            mock_storage.MINIO_SECURE = False
            mock_storage.MINIO_ENDPOINT = "minio:9000"

            url = "http://localhost:9010/images/test.jpg"
            result = StorageService.convert_to_internal_url(url)
            assert "172.19.0.2:9000" in result


# ============================================================================
# cleanup_temp_files 测试
# ============================================================================

class TestCleanupTempFiles:
    """临时文件清理测试"""

    @patch("services.storage.PathConfig")
    def test_cleanup_temp_files_删除匹配文件(self, mock_path_config, tmp_path):
        """应删除匹配模式的临时文件"""
        mock_path_config.BACKEND_DIR = tmp_path

        # 创建一些临时文件
        (tmp_path / "temp_001.jpg").write_bytes(b"data")
        (tmp_path / "output_frame.jpg").write_bytes(b"data")
        (tmp_path / "important.py").write_bytes(b"keep")

        StorageService.cleanup_temp_files()

        # 匹配模式的文件应被删除
        assert not (tmp_path / "temp_001.jpg").exists()
        # 不匹配的文件应保留
        assert (tmp_path / "important.py").exists()


# ============================================================================
# insert_to_vector_db 测试
# ============================================================================

class TestInsertToVectorDB:
    """向量数据库插入测试"""

    @pytest.mark.asyncio
    @patch("services.storage.RAGConfig")
    async def test_insert_to_vector_db_RAG未启用(self, mock_rag):
        """RAG 未启用时应返回 disabled 状态"""
        mock_rag.ENABLE_RAG = False
        result = await StorageService.insert_to_vector_db(["doc1", "doc2"])
        assert result["status"] == "disabled"

    @pytest.mark.asyncio
    @patch("services.storage.RAGConfig")
    async def test_insert_to_vector_db_成功插入(self, mock_rag):
        """启用 RAG 时应成功调用 API"""
        mock_rag.ENABLE_RAG = True
        mock_rag.VECTOR_API_URL = "http://rag-api/insert"

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "count": 2}
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("services.storage.httpx.AsyncClient", return_value=mock_client_instance):
            result = await StorageService.insert_to_vector_db(["doc1", "doc2"])
            assert result["status"] == "ok"

    @pytest.mark.asyncio
    @patch("services.storage.RAGConfig")
    async def test_insert_to_vector_db_请求失败返回错误(self, mock_rag):
        """API 请求失败应返回错误状态"""
        mock_rag.ENABLE_RAG = True
        mock_rag.VECTOR_API_URL = "http://rag-api/insert"

        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = Exception("Connection refused")
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("services.storage.httpx.AsyncClient", return_value=mock_client_instance):
            result = await StorageService.insert_to_vector_db(["doc1"])
            assert result["status"] == "error"
            assert "Connection refused" in result["message"]


# ============================================================================
# upload_frame_image 测试
# ============================================================================

class TestUploadFrameImage:
    """帧图片上传测试"""

    @pytest.mark.asyncio
    async def test_upload_frame_image_成功上传(self, tmp_path, mock_minio_client):
        """成功上传应返回代理 URL"""
        # 创建测试图片文件
        img_path = tmp_path / "frame.jpg"
        img_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

        service = StorageService()
        service.minio_client = mock_minio_client

        with patch("config.settings.StorageConfig") as mock_sc, \
             patch.object(StorageService, "convert_to_proxy_url",
                         return_value="/api/image-proxy/minio/images/analysis/t1/frame_000001.jpg"):
            mock_sc.MINIO_SECURE = False
            mock_sc.MINIO_ENDPOINT = "minio:9000"
            result = await service.upload_frame_image(str(img_path), "task-1", 1)

        assert "/api/image-proxy/" in result

    @pytest.mark.asyncio
    async def test_upload_frame_image_失败返回本地路径(self, mock_minio_client):
        """上传失败应回退返回本地路径"""
        service = StorageService()
        service.minio_client = mock_minio_client
        service.minio_client.upload_file.side_effect = Exception("upload failed")

        result = await service.upload_frame_image("/nonexistent/frame.jpg", "t1", 0)
        assert result == "/nonexistent/frame.jpg"
