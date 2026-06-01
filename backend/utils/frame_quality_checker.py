"""
视频帧质量评估工具
用于检测和过滤模糊、低质量的视频帧
确保只处理清晰的关键帧(I帧)
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FrameQualityMetrics:
    """帧质量评估指标"""
    sharpness: float  # 清晰度(拉普拉斯方差)
    brightness: float  # 亮度(0-255)
    contrast: float  # 对比度(标准差)
    is_clear: bool  # 是否清晰
    quality_score: float  # 综合质量分数(0-100)


class FrameQualityChecker:
    """
    视频帧质量检查器
    使用多维度评估确保帧质量
    """

    def __init__(
        self,
        sharpness_threshold: float = 100.0,  # 清晰度阈值
        brightness_min: float = 30.0,  # 最小亮度
        brightness_max: float = 225.0,  # 最大亮度
        contrast_threshold: float = 30.0,  # 对比度阈值
    ):
        self.sharpness_threshold = sharpness_threshold
        self.brightness_min = brightness_min
        self.brightness_max = brightness_max
        self.contrast_threshold = contrast_threshold

    def calculate_sharpness(self, image: np.ndarray) -> float:
        """
        使用拉普拉斯算子计算图像清晰度

        原理: 拉普拉斯算子检测图像的二阶导数，清晰图像边缘明显，方差大

        Args:
            image: BGR或灰度图像

        Returns:
            清晰度分数，越大越清晰
        """
        try:
            # 转为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # 计算拉普拉斯方差
            laplacian = cv2.Laplacian(gray, cv2.CV_64F)
            variance = laplacian.var()

            return float(variance)

        except Exception as e:
            logger.error(f"计算清晰度失败: {e}")
            return 0.0

    def calculate_brightness(self, image: np.ndarray) -> float:
        """
        计算图像亮度

        Args:
            image: BGR或灰度图像

        Returns:
            平均亮度 (0-255)
        """
        try:
            # 转为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # 计算平均亮度
            mean_brightness = np.mean(gray)
            return float(mean_brightness)

        except Exception as e:
            logger.error(f"计算亮度失败: {e}")
            return 0.0

    def calculate_contrast(self, image: np.ndarray) -> float:
        """
        计算图像对比度

        使用标准差衡量对比度，标准差越大，对比度越高

        Args:
            image: BGR或灰度图像

        Returns:
            对比度分数
        """
        try:
            # 转为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            # 计算标准差
            contrast = np.std(gray)
            return float(contrast)

        except Exception as e:
            logger.error(f"计算对比度失败: {e}")
            return 0.0

    def check_local_quality(self, image: np.ndarray, grid_size: int = 4) -> Tuple[bool, float]:
        """
        检查图像局部质量，防止部分清晰部分模糊的情况

        将图像分成grid_size x grid_size的网格，检查每个块的质量
        如果有超过25%的块质量不达标，或块之间差异过大，认为图像质量不合格

        Args:
            image: BGR或灰度图像
            grid_size: 网格大小（默认4x4=16块）

        Returns:
            (是否通过局部质量检查, 最低块质量分数)
        """
        try:
            # 转为灰度图
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            h, w = gray.shape
            block_h = h // grid_size
            block_w = w // grid_size

            block_quality_scores = []
            block_sharpness_values = []
            low_quality_blocks = 0

            for i in range(grid_size):
                for j in range(grid_size):
                    # 提取块
                    y1, y2 = i * block_h, (i + 1) * block_h
                    x1, x2 = j * block_w, (j + 1) * block_w
                    block = gray[y1:y2, x1:x2]

                    # 计算块的清晰度（拉普拉斯方差）
                    laplacian = cv2.Laplacian(block, cv2.CV_64F)
                    block_sharpness = laplacian.var()
                    block_sharpness_values.append(block_sharpness)

                    # 计算块的对比度
                    block_contrast = np.std(block)

                    # 综合评分（清晰度权重更高）
                    block_score = block_sharpness * 0.7 + block_contrast * 0.3
                    block_quality_scores.append(block_score)

                    # 检查是否低质量块（阈值可调）
                    if block_sharpness < 100.0 or block_contrast < 20.0:  # 🔧 提升阈值
                        low_quality_blocks += 1

            total_blocks = grid_size * grid_size
            low_quality_ratio = low_quality_blocks / total_blocks
            min_block_score = min(block_quality_scores)
            max_block_sharpness = max(block_sharpness_values)
            min_block_sharpness = min(block_sharpness_values)

            # 检查1：超过25%的块质量不达标
            ratio_check = low_quality_ratio <= 0.25

            # 🆕 检查2：块之间清晰度差异过大（检测部分模糊/马赛克问题）
            # 马赛克会产生异常高的清晰度值，导致差异倍数过大
            # 分析：问题图片差异23.81倍，正常图片10.99倍
            sharpness_ratio = max_block_sharpness / (min_block_sharpness + 1)
            consistency_check = sharpness_ratio < 15.0  # 🔧 调整：10 → 15倍（区分问题和正常）

            # 🆕 检查3：清晰度标准差检查（检测不均匀性）
            # 分析：问题图片标准差18576，正常图片1056
            sharpness_std = np.std(block_sharpness_values)
            # 使用相对标准差（变异系数）：标准差/平均值
            mean_sharpness = np.mean(block_sharpness_values)
            coefficient_of_variation = sharpness_std / (mean_sharpness + 1)
            # 问题图片CV=18576/20081=0.92，正常图片CV=1056/2384=0.44
            uniformity_check = coefficient_of_variation < 0.7  # 🔧 设置为0.7（介于两者之间）

            is_pass = ratio_check and consistency_check and uniformity_check

            if not is_pass:
                sharpness_std = np.std(block_sharpness_values)
                mean_sharpness = np.mean(block_sharpness_values)
                coefficient_of_variation = sharpness_std / (mean_sharpness + 1)

                logger.debug(
                    f"⚠️ 局部质量检查失败: "
                    f"低质量块={low_quality_blocks}/{total_blocks}({low_quality_ratio*100:.1f}%), "
                    f"清晰度差异={sharpness_ratio:.2f}倍, "
                    f"变异系数={coefficient_of_variation:.2f}, "
                    f"最低块清晰度={min_block_sharpness:.2f}"
                )

            return is_pass, min_block_score

        except Exception as e:
            logger.error(f"局部质量检查失败: {e}")
            return False, 0.0

    def check_bottom_region_quality(self, image: np.ndarray) -> Tuple[bool, str]:
        """
        检查帧底部区域的完整性（检测部分解码问题）

        底部区域问题特征：
        1. 底部1/4区域全黑或全白（数据缺失）
        2. 底部区域与上部区域差异过大（解码不完整）
        3. 底部区域出现异常的马赛克或块状伪影

        Args:
            image: BGR图像

        Returns:
            (是否通过检查, 失败原因)
        """
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            height, width = gray.shape

            # 划分上部3/4和底部1/4区域
            split_point = int(height * 0.75)
            top_region = gray[:split_point, :]
            bottom_region = gray[split_point:, :]

            # 检查1：底部区域是否全黑或全白（数据缺失）
            bottom_mean = np.mean(bottom_region)
            if bottom_mean < 10:
                return False, f"底部区域全黑（亮度={bottom_mean:.2f}）"
            if bottom_mean > 245:
                return False, f"底部区域全白（亮度={bottom_mean:.2f}）"

            # 检查2：底部与上部亮度差异过大（解码不完整）
            top_mean = np.mean(top_region)
            brightness_diff = abs(bottom_mean - top_mean)
            if brightness_diff > 100:  # 亮度差异超过100
                return False, f"底部亮度异常（上部={top_mean:.2f}, 底部={bottom_mean:.2f}, 差异={brightness_diff:.2f}）"

            # 检查3：底部区域对比度是否极低（解码失败特征）
            bottom_std = np.std(bottom_region)
            if bottom_std < 15:  # 对比度极低
                return False, f"底部对比度极低（标准差={bottom_std:.2f}）"

            # 检查4：底部区域块状伪影检测
            # 将底部区域分成4x4块，检查块间差异
            bottom_h, bottom_w = bottom_region.shape
            block_h, block_w = bottom_h // 4, bottom_w // 4

            block_means = []
            for i in range(4):
                for j in range(4):
                    y1, y2 = i * block_h, (i + 1) * block_h
                    x1, x2 = j * block_w, (j + 1) * block_w
                    block = bottom_region[y1:y2, x1:x2]
                    block_means.append(np.mean(block))

            # 检查块间亮度差异是否过大（马赛克特征）
            block_mean_std = np.std(block_means)
            if block_mean_std > 50:  # 块间差异过大
                return False, f"底部区域块状伪影（块间差异={block_mean_std:.2f}）"

            return True, "底部区域质量正常"

        except Exception as e:
            logger.error(f"底部区域质量检查失败: {e}")
            return False, f"检查异常: {str(e)}"

    def detect_gray_frame(self, image: np.ndarray) -> bool:
        """
        检测灰色帧（解码失败的特征）

        灰色帧特征：
        1. 亮度接近128（中间灰）
        2. 对比度极低
        3. 色彩饱和度极低

        Args:
            image: BGR图像

        Returns:
            是否为灰色帧
        """
        try:
            # 转为灰度图检查亮度
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image

            mean_brightness = np.mean(gray)
            std_brightness = np.std(gray)

            # 灰色帧特征1：亮度在100-160之间（接近128）
            is_gray_brightness = 100 <= mean_brightness <= 160

            # 灰色帧特征2：对比度极低（标准差<20）
            is_low_contrast = std_brightness < 20

            # 如果是彩色图，检查色彩饱和度
            if len(image.shape) == 3:
                hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
                saturation = hsv[:, :, 1]
                mean_saturation = np.mean(saturation)

                # 灰色帧特征3：饱和度极低（<30）
                is_low_saturation = mean_saturation < 30

                is_gray = is_gray_brightness and is_low_contrast and is_low_saturation

                if is_gray:
                    logger.debug(
                        f"⚠️ 检测到灰色帧: 亮度={mean_brightness:.2f}, "
                        f"对比度={std_brightness:.2f}, 饱和度={mean_saturation:.2f}"
                    )
            else:
                is_gray = is_gray_brightness and is_low_contrast

                if is_gray:
                    logger.debug(
                        f"⚠️ 检测到灰色帧: 亮度={mean_brightness:.2f}, "
                        f"对比度={std_brightness:.2f}"
                    )

            return is_gray

        except Exception as e:
            logger.error(f"灰色帧检测失败: {e}")
            return False

    def check_frame_quality(
        self, frame: np.ndarray, verbose: bool = False, enable_strict_mode: bool = True
    ) -> FrameQualityMetrics:
        """
        综合评估帧质量（增强版）

        Args:
            frame: 输入帧(BGR格式)
            verbose: 是否输出详细日志
            enable_strict_mode: 是否启用严格模式（包括局部质量、灰色帧、底部区域检测）

        Returns:
            帧质量指标
        """
        try:
            # 🆕 严格模式：先检查是否为灰色帧（解码失败的典型特征）
            if enable_strict_mode and self.detect_gray_frame(frame):
                logger.warning("⚠️ 检测到灰色帧，质量评估失败")
                return FrameQualityMetrics(
                    sharpness=0.0,
                    brightness=0.0,
                    contrast=0.0,
                    is_clear=False,
                    quality_score=0.0,
                )

            # 🆕 严格模式：检查底部区域完整性（检测部分解码问题）
            if enable_strict_mode:
                bottom_ok, bottom_reason = self.check_bottom_region_quality(frame)
                if not bottom_ok:
                    logger.warning(f"⚠️ 底部区域检查失败: {bottom_reason}")
                    return FrameQualityMetrics(
                        sharpness=0.0,
                        brightness=0.0,
                        contrast=0.0,
                        is_clear=False,
                        quality_score=0.0,
                    )

            # 计算各项指标
            sharpness = self.calculate_sharpness(frame)
            brightness = self.calculate_brightness(frame)
            contrast = self.calculate_contrast(frame)

            # 质量判定
            is_sharp = sharpness >= self.sharpness_threshold
            is_brightness_ok = self.brightness_min <= brightness <= self.brightness_max
            is_contrast_ok = contrast >= self.contrast_threshold

            # 🆕 严格模式：局部质量检查
            local_quality_ok = True
            min_block_score = sharpness  # 默认使用全局清晰度
            if enable_strict_mode:
                local_quality_ok, min_block_score = self.check_local_quality(frame)
                if not local_quality_ok:
                    logger.debug(
                        f"⚠️ 局部质量检查失败: 最低块分数={min_block_score:.2f}"
                    )

            # 综合判定（严格模式下需要通过局部质量检查）
            is_clear = (
                is_sharp
                and is_brightness_ok
                and is_contrast_ok
                and (local_quality_ok if enable_strict_mode else True)
            )

            # 计算综合质量分数 (0-100)
            # 归一化各指标到0-100范围
            sharpness_score = min(100, (sharpness / self.sharpness_threshold) * 50)
            brightness_score = (
                25
                if is_brightness_ok
                else max(
                    0,
                    25
                    * (
                        1
                        - abs(brightness - (self.brightness_min + self.brightness_max) / 2)
                        / 128
                    ),
                )
            )
            contrast_score = min(25, (contrast / self.contrast_threshold) * 25)

            quality_score = sharpness_score + brightness_score + contrast_score

            # 🆕 严格模式惩罚：如果局部质量不达标，降低总分
            if enable_strict_mode and not local_quality_ok:
                quality_score *= 0.5  # 总分减半

            metrics = FrameQualityMetrics(
                sharpness=sharpness,
                brightness=brightness,
                contrast=contrast,
                is_clear=is_clear,
                quality_score=quality_score,
            )

            if verbose:
                logger.debug(
                    f"帧质量评估: "
                    f"清晰度={sharpness:.2f}(阈值{self.sharpness_threshold}), "
                    f"亮度={brightness:.2f}({self.brightness_min}-{self.brightness_max}), "
                    f"对比度={contrast:.2f}(阈值{self.contrast_threshold}), "
                    f"局部质量={'通过' if local_quality_ok else '失败'}, "
                    f"质量分数={quality_score:.2f}, "
                    f"是否清晰={is_clear}"
                )

            return metrics

        except Exception as e:
            logger.error(f"帧质量评估失败: {e}")
            return FrameQualityMetrics(
                sharpness=0.0,
                brightness=0.0,
                contrast=0.0,
                is_clear=False,
                quality_score=0.0,
            )

    def is_frame_clear(self, frame: np.ndarray) -> bool:
        """
        快速判断帧是否清晰

        Args:
            frame: 输入帧

        Returns:
            是否清晰
        """
        metrics = self.check_frame_quality(frame, verbose=False)
        return metrics.is_clear


# 创建全局实例（终极严格质量标准，确保100%清晰）
# ✨ 阈值极限提升，彻底杜绝模糊帧
frame_quality_checker = FrameQualityChecker(
    sharpness_threshold=800.0,  # 🔧 终极严格：500 → 800（只接受极度清晰的I帧）
    brightness_min=50.0,         # 🔧 提升：40 → 50（避免过暗）
    brightness_max=210.0,        # 🔧 降低：220 → 210（避免过亮）
    contrast_threshold=70.0,     # 🔧 提升：60 → 70（确保极高对比度）
)
