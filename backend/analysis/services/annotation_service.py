"""
图像标注服务
处理AI检测结果的可视化标注，支持多种标注样式
"""

import cv2
import numpy as np
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

from models.analysis_result import AnnotationObject, BoundingBox, AlertSeverity
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


class AnnotationService:
    """图像标注服务"""
    
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.6
        self.thickness = 2
        
        # 严重程度颜色映射
        self.severity_colors = {
            AlertSeverity.INFO: (0, 255, 0),      # 绿色
            AlertSeverity.LOW: (0, 255, 255),     # 黄色
            AlertSeverity.MEDIUM: (0, 165, 255),  # 橙色
            AlertSeverity.HIGH: (0, 0, 255),      # 红色
            AlertSeverity.CRITICAL: (128, 0, 128) # 紫色
        }
        
        # 中文字体支持（如果可用）
        self.chinese_font_path = self._find_chinese_font()
    
    async def annotate_image(self, image: np.ndarray, 
                           annotations: List[AnnotationObject],
                           title: Optional[str] = None,
                           timestamp: Optional[str] = None) -> np.ndarray:
        """
        在图像上添加检测标注
        
        Args:
            image: 原始图像
            annotations: 标注对象列表
            title: 图像标题
            timestamp: 时间戳
            
        Returns:
            标注后的图像
        """
        try:
            # 复制图像避免修改原图
            annotated_image = image.copy()
            
            # 添加标题和时间戳
            if title or timestamp:
                annotated_image = self._add_header_info(annotated_image, title, timestamp)
            
            # 绘制检测框和标签
            for annotation in annotations:
                annotated_image = self._draw_annotation(annotated_image, annotation)
            
            # 添加统计信息
            annotated_image = self._add_statistics_panel(annotated_image, annotations)
            
            return annotated_image
            
        except Exception as e:
            logger.error(f"图像标注失败: {e}")
            return image
    
    async def create_detection_summary_image(self, annotations: List[AnnotationObject],
                                           original_image: np.ndarray) -> np.ndarray:
        """创建检测结果汇总图像"""
        try:
            # 创建汇总画布
            height, width = original_image.shape[:2]
            summary_width = min(400, width // 3)
            summary_image = np.zeros((height, summary_width, 3), dtype=np.uint8)
            summary_image[:] = (40, 40, 40)  # 深灰背景
            
            # 绘制标题
            title = "检测结果汇总"
            self._draw_text_chinese(summary_image, title, (10, 30), (255, 255, 255))
            
            # 统计各类检测结果
            detection_stats = self._calculate_detection_stats(annotations)
            
            y_offset = 70
            for category, stats in detection_stats.items():
                # 分类标题
                self._draw_text_chinese(summary_image, f"{category}:", (10, y_offset), (200, 200, 200))
                y_offset += 30
                
                # 统计信息
                for stat_name, value in stats.items():
                    text = f"  {stat_name}: {value}"
                    color = self._get_stat_color(stat_name, value)
                    self._draw_text_chinese(summary_image, text, (15, y_offset), color)
                    y_offset += 25
                
                y_offset += 10
            
            # 合并原图和汇总图
            combined_image = np.hstack([original_image, summary_image])
            return combined_image
            
        except Exception as e:
            logger.error(f"创建汇总图像失败: {e}")
            return original_image
    
    def _draw_annotation(self, image: np.ndarray, annotation: AnnotationObject) -> np.ndarray:
        """绘制单个标注对象"""
        try:
            bbox = annotation.bounding_box
            
            # 计算像素坐标
            h, w = image.shape[:2]
            x1 = int(bbox.x * w)
            y1 = int(bbox.y * h)
            x2 = int((bbox.x + bbox.width) * w)
            y2 = int((bbox.y + bbox.height) * h)
            
            # 获取颜色
            if annotation.color.startswith('#'):
                # 解析十六进制颜色
                color_hex = annotation.color[1:]
                color = tuple(int(color_hex[i:i+2], 16) for i in (4, 2, 0))  # BGR格式
            else:
                color = self.severity_colors.get(annotation.severity, (0, 255, 0))
            
            # 绘制边界框
            cv2.rectangle(image, (x1, y1), (x2, y2), color, self.thickness)
            
            # 准备标签文本
            confidence_text = f"{annotation.confidence:.2f}"
            label_text = f"{annotation.label} ({confidence_text})"
            
            if annotation.is_violation:
                label_text = f"⚠️ {label_text}"
            
            # 计算文本尺寸
            text_size = cv2.getTextSize(label_text, self.font, self.font_scale, self.thickness)[0]
            
            # 绘制标签背景
            cv2.rectangle(image, (x1, y1 - text_size[1] - 10), 
                         (x1 + text_size[0] + 10, y1), color, -1)
            
            # 绘制标签文本
            cv2.putText(image, label_text, (x1 + 5, y1 - 5),
                       self.font, self.font_scale, (255, 255, 255), 1)
            
            # 如果有违规原因，添加详细信息
            if annotation.is_violation and annotation.violation_reason:
                reason_y = y2 + 20
                self._draw_text_chinese(image, annotation.violation_reason, 
                                      (x1, reason_y), color)
            
            return image
            
        except Exception as e:
            logger.error(f"绘制标注失败: {e}")
            return image
    
    def _add_header_info(self, image: np.ndarray, title: Optional[str], 
                        timestamp: Optional[str]) -> np.ndarray:
        """添加标题和时间戳信息"""
        try:
            header_height = 50
            h, w = image.shape[:2]
            
            # 创建扩展图像
            extended_image = np.zeros((h + header_height, w, 3), dtype=np.uint8)
            extended_image[:] = (30, 30, 30)  # 深灰背景
            
            # 复制原图像
            extended_image[header_height:, :] = image
            
            # 绘制标题
            if title:
                self._draw_text_chinese(extended_image, title, (10, 25), (255, 255, 255))
            
            # 绘制时间戳
            if timestamp:
                timestamp_text = f"时间: {timestamp}"
                text_size = cv2.getTextSize(timestamp_text, self.font, self.font_scale, 1)[0]
                self._draw_text_chinese(extended_image, timestamp_text, 
                                      (w - text_size[0] - 10, 25), (200, 200, 200))
            
            return extended_image
            
        except Exception as e:
            logger.error(f"添加标题信息失败: {e}")
            return image
    
    def _add_statistics_panel(self, image: np.ndarray, 
                            annotations: List[AnnotationObject]) -> np.ndarray:
        """添加统计信息面板"""
        try:
            if not annotations:
                return image
            
            h, w = image.shape[:2]
            panel_width = 200
            panel_height = 150
            
            # 在右上角绘制统计面板
            x_start = w - panel_width - 10
            y_start = 10
            
            # 绘制面板背景
            cv2.rectangle(image, (x_start, y_start), 
                         (x_start + panel_width, y_start + panel_height),
                         (0, 0, 0), -1)  # 黑色背景
            cv2.rectangle(image, (x_start, y_start), 
                         (x_start + panel_width, y_start + panel_height),
                         (255, 255, 255), 1)  # 白色边框
            
            # 统计信息
            total_objects = len(annotations)
            violations = len([a for a in annotations if a.is_violation])
            avg_confidence = np.mean([a.confidence for a in annotations])
            
            # 绘制统计文本
            stats_text = [
                f"检测对象: {total_objects}",
                f"违规数量: {violations}",
                f"平均置信度: {avg_confidence:.2f}",
                f"违规率: {violations/total_objects:.1%}" if total_objects > 0 else "违规率: 0%"
            ]
            
            for i, text in enumerate(stats_text):
                y_pos = y_start + 25 + i * 25
                color = (0, 0, 255) if i == 1 and violations > 0 else (255, 255, 255)
                cv2.putText(image, text, (x_start + 10, y_pos),
                           self.font, 0.5, color, 1)
            
            return image
            
        except Exception as e:
            logger.error(f"添加统计面板失败: {e}")
            return image
    
    def _draw_text_chinese(self, image: np.ndarray, text: str, 
                          position: Tuple[int, int], color: Tuple[int, int, int]):
        """绘制中文文本（如果支持）"""
        try:
            x, y = position
            
            # 如果有中文字体，使用PIL绘制
            if self.chinese_font_path:
                # TODO(annotation): 使用PIL实现中文字体绘制，替代OpenCV的英文回退方案
                pass
            
            # 回退到OpenCV英文绘制
            cv2.putText(image, text, position, self.font, self.font_scale, color, 1)
            
        except Exception as e:
            logger.error(f"绘制文本失败: {e}")
    
    def _find_chinese_font(self) -> Optional[str]:
        """查找系统中的中文字体"""
        possible_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/PingFang.ttc",
            "/Windows/Fonts/simhei.ttf"
        ]
        
        for font_path in possible_fonts:
            if Path(font_path).exists():
                return font_path
        
        return None
    
    def _calculate_detection_stats(self, annotations: List[AnnotationObject]) -> Dict[str, Dict[str, Any]]:
        """计算检测统计信息"""
        stats = {}
        
        # 按类别分组
        by_class = {}
        for annotation in annotations:
            class_name = annotation.class_name
            if class_name not in by_class:
                by_class[class_name] = []
            by_class[class_name].append(annotation)
        
        # 计算各类别统计
        for class_name, objects in by_class.items():
            violations = [obj for obj in objects if obj.is_violation]
            confidences = [obj.confidence for obj in objects]
            
            stats[class_name] = {
                "总数": len(objects),
                "违规": len(violations),
                "置信度": f"{np.mean(confidences):.2f}"
            }
        
        return stats
    
    def _get_stat_color(self, stat_name: str, value: Any) -> Tuple[int, int, int]:
        """根据统计项目获取颜色"""
        if stat_name == "违规" and isinstance(value, int) and value > 0:
            return (0, 0, 255)  # 红色
        elif stat_name == "置信度":
            try:
                conf_value = float(str(value))
                if conf_value > 0.8:
                    return (0, 255, 0)  # 绿色 - 高置信度
                elif conf_value > 0.6:
                    return (0, 255, 255)  # 黄色 - 中等置信度
                else:
                    return (0, 165, 255)  # 橙色 - 低置信度
            except Exception:
                pass  # 置信度值解析失败，使用默认颜色

        return (255, 255, 255)  # 默认白色
    
    async def create_violation_heatmap(self, annotations: List[AnnotationObject],
                                     image_shape: Tuple[int, int]) -> np.ndarray:
        """创建违规热力图"""
        try:
            h, w = image_shape
            heatmap = np.zeros((h, w), dtype=np.float32)
            
            # 为每个违规对象添加热力值
            for annotation in annotations:
                if not annotation.is_violation:
                    continue
                
                bbox = annotation.bounding_box
                x1 = int(bbox.x * w)
                y1 = int(bbox.y * h)
                x2 = int((bbox.x + bbox.width) * w)
                y2 = int((bbox.y + bbox.height) * h)
                
                # 根据严重程度设置热力值
                heat_value = self._get_severity_heat_value(annotation.severity)
                heatmap[y1:y2, x1:x2] += heat_value * annotation.confidence
            
            # 应用高斯模糊平滑热力图
            heatmap = cv2.GaussianBlur(heatmap, (21, 21), 0)
            
            # 归一化到0-255
            if heatmap.max() > 0:
                heatmap = (heatmap / heatmap.max() * 255).astype(np.uint8)
            
            # 应用颜色映射
            heatmap_colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
            
            return heatmap_colored
            
        except Exception as e:
            logger.error(f"创建热力图失败: {e}")
            return np.zeros((*image_shape, 3), dtype=np.uint8)
    
    async def save_annotated_image(self, annotated_image: np.ndarray, 
                                 output_path: str, quality: int = 95) -> bool:
        """保存标注图像"""
        try:
            # 确保输出目录存在
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # 保存图像
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            success = cv2.imwrite(output_path, annotated_image, encode_params)
            
            if success:
                logger.info(f"标注图像已保存: {output_path}")
            else:
                logger.error(f"保存标注图像失败: {output_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"保存标注图像异常: {e}")
            return False
    
    def _get_severity_heat_value(self, severity: AlertSeverity) -> float:
        """根据严重程度获取热力值"""
        heat_values = {
            AlertSeverity.INFO: 0.2,
            AlertSeverity.LOW: 0.4,
            AlertSeverity.MEDIUM: 0.6,
            AlertSeverity.HIGH: 0.8,
            AlertSeverity.CRITICAL: 1.0
        }
        return heat_values.get(severity, 0.5)
    
    async def batch_annotate_frames(self, frames: List[np.ndarray],
                                  frame_annotations: List[List[AnnotationObject]],
                                  output_dir: str) -> List[str]:
        """批量标注视频帧"""
        try:
            output_paths = []
            
            for i, (frame, annotations) in enumerate(zip(frames, frame_annotations)):
                # 生成输出路径
                output_path = Path(output_dir) / f"frame_{i:06d}_annotated.jpg"
                
                # 标注图像
                annotated_frame = await self.annotate_image(
                    frame, annotations, 
                    title=f"Frame {i+1}",
                    timestamp=now().strftime("%Y-%m-%d %H:%M:%S")
                )
                
                # 保存图像
                success = await self.save_annotated_image(
                    annotated_frame, str(output_path)
                )
                
                if success:
                    output_paths.append(str(output_path))
            
            logger.info(f"批量标注完成: {len(output_paths)} 张图像")
            return output_paths
            
        except Exception as e:
            logger.error(f"批量标注失败: {e}")
            return []
    
    async def create_comparison_image(self, original: np.ndarray, 
                                    annotated: np.ndarray) -> np.ndarray:
        """创建原图与标注图的对比图像"""
        try:
            # 确保两图尺寸一致
            h1, w1 = original.shape[:2]
            h2, w2 = annotated.shape[:2]
            
            if h1 != h2 or w1 != w2:
                annotated = cv2.resize(annotated, (w1, h1))
            
            # 水平拼接
            comparison = np.hstack([original, annotated])
            
            # 添加分割线
            split_x = w1
            cv2.line(comparison, (split_x, 0), (split_x, h1), (255, 255, 255), 2)
            
            # 添加标签
            cv2.putText(comparison, "Original", (10, 30), 
                       self.font, 0.8, (255, 255, 255), 2)
            cv2.putText(comparison, "Annotated", (w1 + 10, 30), 
                       self.font, 0.8, (255, 255, 255), 2)
            
            return comparison
            
        except Exception as e:
            logger.error(f"创建对比图像失败: {e}")
            return original