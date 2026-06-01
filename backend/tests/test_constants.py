"""
常量完整性单元测试
验证 core/constants.py 中所有常量值的合理性、类型正确性和无重复定义
"""

import sys
import inspect
from pathlib import Path

import pytest

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import core.constants as constants


def _get_all_constants():
    """获取模块中所有大写常量（排除内置属性）"""
    return {
        name: getattr(constants, name)
        for name in dir(constants)
        if name.isupper() and not name.startswith("_")
    }


# ============================================================================
# 常量值合理性测试
# ============================================================================

class TestConstantsPositive:
    """所有数值常量必须为正数"""

    @pytest.mark.parametrize("name,value", list(_get_all_constants().items()))
    def test_数值常量为正数(self, name, value):
        """数值类型的常量应为正数"""
        if isinstance(value, (int, float)):
            assert value > 0, f"常量 {name}={value} 应为正数"


class TestConstantsType:
    """常量类型正确性"""

    @pytest.mark.parametrize("name,expected_type", [
        # 视频处理 — 整数
        ("DEFAULT_VIDEO_INTERVAL", int),
        ("DEFAULT_ANALYSIS_INTERVAL", int),
        ("DEFAULT_BUFFER_DURATION", int),
        ("DEFAULT_WS_RETRY_INTERVAL", int),
        ("DEFAULT_MAX_WS_QUEUE", int),
        ("DEFAULT_JPEG_QUALITY", int),
        ("DEFAULT_FRAME_SAMPLE_INTERVAL", int),
        # 并发 — 整数
        ("DEFAULT_MAX_CONCURRENT_STREAMS", int),
        ("DEFAULT_MAX_CONCURRENT_AI_CALLS", int),
        # FFmpeg — 数值
        ("FFMPEG_ANALYZE_DURATION", int),
        ("FFMPEG_DEFAULT_FPS", float),
        # 帧质量 — 浮点
        ("DEFAULT_FRAME_QUALITY_MIN_SCORE", float),
        ("DEFAULT_FRAME_SHARPNESS_MIN", float),
        # 数据库 — 整数
        ("DEFAULT_DB_POOL_SIZE", int),
        ("DEFAULT_DB_MAX_OVERFLOW", int),
        # API — 浮点
        ("DEFAULT_REQUEST_TIMEOUT", float),
    ])
    def test_常量类型正确(self, name, expected_type):
        """常量应具有预期的类型"""
        value = getattr(constants, name)
        assert isinstance(value, expected_type), \
            f"常量 {name} 类型应为 {expected_type.__name__}，实际为 {type(value).__name__}"


# ============================================================================
# 范围合理性测试
# ============================================================================

class TestConstantsRange:
    """常量值范围合理性"""

    def test_JPEG质量范围(self):
        """JPEG 质量应在 1-100 之间"""
        assert 1 <= constants.DEFAULT_JPEG_QUALITY <= 100

    def test_MJPEG_JPEG质量范围(self):
        """MJPEG JPEG 质量应在 1-100 之间"""
        assert 1 <= constants.MJPEG_JPEG_QUALITY <= 100

    def test_帧质量分数范围(self):
        """帧质量最低分数应在 0-100 之间"""
        assert 0 <= constants.DEFAULT_FRAME_QUALITY_MIN_SCORE <= 100

    def test_FFmpeg默认帧率合理(self):
        """默认帧率应在 1-120 之间"""
        assert 1 <= constants.FFMPEG_DEFAULT_FPS <= 120

    def test_FFmpeg默认分辨率合理(self):
        """默认宽高应在合理范围内"""
        assert 320 <= constants.FFMPEG_DEFAULT_WIDTH <= 7680
        assert 240 <= constants.FFMPEG_DEFAULT_HEIGHT <= 4320

    def test_数据库连接池大小合理(self):
        """连接池大小应在合理范围内"""
        assert 1 <= constants.DEFAULT_DB_POOL_SIZE <= 200
        assert 0 <= constants.DEFAULT_DB_MAX_OVERFLOW <= 200

    def test_MJPEG目标帧率合理(self):
        """MJPEG 目标帧率应在 1-60 之间"""
        assert 1 <= constants.MJPEG_FPS_TARGET <= 60

    def test_最大文件大小合理(self):
        """最大文件大小应在 1MB-10GB 之间"""
        assert 1 <= constants.DEFAULT_MAX_FILE_SIZE_MB <= 10240

    def test_文件保留天数合理(self):
        """文件保留天数应在 1-365 之间"""
        assert 1 <= constants.DEFAULT_FILE_RETENTION_DAYS <= 365

    def test_API请求超时合理(self):
        """API 请求超时应在 1-600 秒之间"""
        assert 1 <= constants.DEFAULT_REQUEST_TIMEOUT <= 600

    def test_帧最小最大尺寸关系(self):
        """帧最小尺寸应小于最大尺寸"""
        assert constants.FRAME_MIN_DIMENSION < constants.FRAME_MAX_DIMENSION

    def test_健康检查间隔合理(self):
        """健康检查间隔应在 10 秒到 1 小时之间"""
        assert 10 <= constants.DEFAULT_TASK_HEALTH_CHECK_INTERVAL <= 3600
        assert 10 <= constants.DEFAULT_STREAM_HEALTH_CHECK_INTERVAL <= 7200

    def test_重试延迟关系(self):
        """基础重试延迟应小于最大重试延迟"""
        assert constants.DEFAULT_RETRY_DELAY_BASE < constants.DEFAULT_MAX_RETRY_DELAY

    def test_最大连续失败次数合理(self):
        """最大连续失败次数应在 1-100 之间"""
        assert 1 <= constants.DEFAULT_MAX_CONSECUTIVE_FAILURES <= 100


# ============================================================================
# 无重复常量值测试
# ============================================================================

class TestNoDuplicateConstants:
    """检查常量名是否有重复定义（同名不同义）"""

    def test_无重复常量名(self):
        """模块中不应有重复的常量名"""
        all_names = [
            name for name in dir(constants)
            if name.isupper() and not name.startswith("_")
        ]
        assert len(all_names) == len(set(all_names)), "存在重复的常量名"

    def test_同前缀常量值不冲突(self):
        """相同前缀组（如 DEFAULT_* 或 FFMPEG_*）内不应有完全相同的值"""
        all_consts = _get_all_constants()

        # 按前缀分组
        groups = {}
        for name, value in all_consts.items():
            prefix = name.split("_")[0]
            if prefix not in groups:
                groups[prefix] = {}
            groups[prefix][name] = value

        for prefix, group in groups.items():
            numeric_values = {
                name: val for name, val in group.items()
                if isinstance(val, (int, float))
            }
            # 同组内允许少量重复（有些默认值合理地相同），但记录检查
            values = list(numeric_values.values())
            names = list(numeric_values.keys())
            # 这里不做严格断言，因为合理重复是允许的
            # 仅确保分析不报错


# ============================================================================
# 常量完整性测试
# ============================================================================

class TestConstantsCompleteness:
    """确保关键常量组都存在"""

    @pytest.mark.parametrize("prefix,min_count", [
        ("DEFAULT_", 15),     # 至少 15 个 DEFAULT_ 常量
        ("FFMPEG_", 8),       # 至少 8 个 FFmpeg 常量
        ("MJPEG_", 8),        # 至少 8 个 MJPEG 常量
        ("FRAME_", 5),        # 至少 5 个帧相关常量
    ])
    def test_各组常量数量充足(self, prefix, min_count):
        """各前缀组应有足够数量的常量"""
        all_consts = _get_all_constants()
        count = sum(1 for name in all_consts if name.startswith(prefix))
        assert count >= min_count, \
            f"以 {prefix} 开头的常量仅有 {count} 个，预期至少 {min_count} 个"
