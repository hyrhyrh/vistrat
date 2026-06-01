"""
分析结果汇总器
负责生成分析报告和统计信息
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from collections import Counter

from models.analysis_result import (
from utils.timezone_utils import now, now_isoformat
    VideoAnalysisResult, FrameAnalysisResult, AnnotationObject,
    AlertSeverity, DetectionType
)

logger = logging.getLogger(__name__)


class AnalysisSummarizer:
    """分析结果汇总器"""
    
    async def generate_analysis_summary(self, frame_results: List[FrameAnalysisResult]) -> str:
        """生成分析摘要"""
        if not frame_results:
            return "未检测到任何异常或目标对象"
        
        # 统计信息
        total_frames = len(frame_results)
        alert_frames = sum(1 for result in frame_results if result.has_alerts)
        total_objects = sum(len(result.objects) for result in frame_results)
        
        summary_parts = [
            f"总帧数: {total_frames}",
            f"告警帧数: {alert_frames}",
            f"检测对象总数: {total_objects}"
        ]
        
        if total_objects > 0:
            # 统计检测类别
            class_counts = {}
            severity_counts = Counter()
            
            for result in frame_results:
                for obj in result.objects:
                    class_name = obj.class_name
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
                    severity_counts[obj.severity.value] += 1
            
            # 主要检测类别
            if class_counts:
                top_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)[:3]
                class_summary = ", ".join([f"{cls}({count}次)" for cls, count in top_classes])
                summary_parts.append(f"主要检测类别: {class_summary}")
            
            # 严重程度分布
            if severity_counts:
                severity_summary = ", ".join([f"{sev}({count})" for sev, count in severity_counts.items()])
                summary_parts.append(f"告警级别分布: {severity_summary}")
        
        return " | ".join(summary_parts)
    
    def generate_detection_statistics(self, frame_results: List[FrameAnalysisResult]) -> Dict[str, Any]:
        """生成检测统计信息"""
        stats = {
            'total_frames': len(frame_results),
            'alert_frames': 0,
            'total_objects': 0,
            'class_distribution': {},
            'severity_distribution': {},
            'confidence_stats': {
                'min': 1.0,
                'max': 0.0,
                'avg': 0.0
            },
            'detection_timeline': []
        }
        
        all_confidences = []
        
        for i, result in enumerate(frame_results):
            if result.has_alerts:
                stats['alert_frames'] += 1
            
            frame_objects = len(result.objects)
            stats['total_objects'] += frame_objects
            
            # 时间线统计
            if frame_objects > 0:
                stats['detection_timeline'].append({
                    'frame_index': i,
                    'timestamp': result.timestamp,
                    'object_count': frame_objects,
                    'max_confidence': max([obj.confidence for obj in result.objects])
                })
            
            # 类别和严重程度统计
            for obj in result.objects:
                # 类别分布
                cls_name = obj.class_name
                if cls_name not in stats['class_distribution']:
                    stats['class_distribution'][cls_name] = 0
                stats['class_distribution'][cls_name] += 1
                
                # 严重程度分布
                severity = obj.severity.value
                if severity not in stats['severity_distribution']:
                    stats['severity_distribution'][severity] = 0
                stats['severity_distribution'][severity] += 1
                
                # 置信度统计
                conf = obj.confidence
                all_confidences.append(conf)
                stats['confidence_stats']['min'] = min(stats['confidence_stats']['min'], conf)
                stats['confidence_stats']['max'] = max(stats['confidence_stats']['max'], conf)
        
        # 计算平均置信度
        if all_confidences:
            stats['confidence_stats']['avg'] = sum(all_confidences) / len(all_confidences)
        else:
            stats['confidence_stats']['min'] = 0.0
        
        return stats
    
    async def create_video_analysis_result(self, task_id: str, video_path: str, 
                                   frame_results: List[FrameAnalysisResult],
                                   template_ids: List[str]) -> VideoAnalysisResult:
        """创建完整的视频分析结果"""
        summary = await self.generate_analysis_summary(frame_results)
        statistics = self.generate_detection_statistics(frame_results)
        
        # 判断是否有告警
        has_alerts = any(result.has_alerts for result in frame_results)
        
        return VideoAnalysisResult(
            task_id=task_id,
            video_path=video_path,
            analysis_time=now_isoformat(),
            frame_results=frame_results,
            summary=summary,
            has_alerts=has_alerts,
            template_ids=template_ids,
            metadata={
                'statistics': statistics,
                'total_frames_analyzed': len(frame_results),
                'processing_completed': True
            }
        )