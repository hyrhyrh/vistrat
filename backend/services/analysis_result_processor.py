"""
分析结果处理器
负责处理分析结果、生成告警、存储数据
"""

import logging
from datetime import datetime
from typing import List, Dict, Any

from core.alert_service import AlertService
from services.elasticsearch_service import elasticsearch_service
from services.video_file_service import VideoFileService
from utils.timezone_utils import now_isoformat

logger = logging.getLogger(__name__)


class AnalysisResultProcessor:
    """分析结果处理器"""
    
    def __init__(self):
        self.alert_service = AlertService()
    
    async def process_analysis_results(self, task, results: List[Dict[str, Any]]):
        """处理分析结果"""
        try:
            if not results:
                logger.warning(f"任务 {task.id} 没有分析结果")
                return
            
            # 存储到 Elasticsearch
            await self._store_results_to_elasticsearch(task, results)
            
            # 生成告警消息
            await self._generate_alerts(task, results)
            
            logger.info(f"成功处理 {len(results)} 个分析结果")
            
        except Exception as e:
            logger.error(f"处理分析结果失败: {e}")
    
    async def _generate_alerts(self, task, results: List[Dict[str, Any]]):
        """生成告警消息（复合检测版本）"""
        try:
            # 检查是否为复合检测结果
            is_composite = any(r.get('composite_detection') for r in results)

            if is_composite:
                # 使用AlertDispatcher处理复合检测告警
                logger.info(f"检测到复合检测结果，使用AlertDispatcher分发告警")
                await self._generate_alerts_composite(task, results)
            else:
                # 向后兼容：处理非复合检测结果（历史数据）
                logger.info(f"检测到非复合检测结果，使用原有逻辑处理告警")
                await self._generate_alerts_legacy(task, results)

        except Exception as e:
            logger.error(f"生成告警消息失败: {e}")

    async def _generate_alerts_composite(self, task, results: List[Dict[str, Any]]):
        """
        生成复合检测告警（使用AlertDispatcher）

        Args:
            task: 分析任务
            results: 分析结果列表（复合检测格式）
        """
        try:
            from services.alert_dispatcher import get_alert_dispatcher

            alert_dispatcher = get_alert_dispatcher()

            # 获取视频信息
            video = await VideoFileService.get_video_by_id(task.video_id)
            video_name = video.name if video else f"Video-{task.video_id}"

            # 按帧分组
            frames = {}
            for result in results:
                frame_index = result.get('frame_index')
                if frame_index not in frames:
                    frames[frame_index] = {
                        'timestamp': result.get('timestamp'),
                        'image_url': result.get('image_url'),
                        'violations': []
                    }

                # 将result转换为violation格式
                violation = {
                    'type_code': result.get('detection_type_code'),
                    'display_name': result.get('template_name'),
                    'has_violation': result.get('has_alert', False),
                    'confidence': result.get('confidence', 0.0),
                    'violation_count': result.get('violation_count', 0),
                    'conclusion': result.get('ai_response', ''),
                    'details': result.get('details', []),
                    'severity': result.get('severity', 'medium'),
                    'category': result.get('category', 'unknown')
                }
                frames[frame_index]['violations'].append(violation)

            # 逐帧分发告警
            total_dispatched = 0
            for frame_index, frame_data in frames.items():
                dispatched_count = await alert_dispatcher.dispatch_alerts(
                    task_id=task.id,
                    video_id=task.video_id,
                    video_name=video_name,
                    frame_index=frame_index,
                    timestamp=frame_data['timestamp'],
                    violations=frame_data['violations'],
                    image_url=frame_data['image_url'],
                    analysis_type='composite_detection'
                )
                total_dispatched += dispatched_count

            logger.info(
                f"✅ 复合检测告警分发完成: {len(frames)}帧, "
                f"成功分发{total_dispatched}个告警"
            )

            # 更新视频文件的告警总数
            if total_dispatched > 0:
                from services.video_file_service import VideoFileService
                await VideoFileService.update_video(
                    task.video_id,
                    {'total_alerts': total_dispatched}
                )
                logger.info(f"📊 已更新视频 {task.video_id} 的告警总数: {total_dispatched}")

        except Exception as e:
            logger.error(f"生成复合检测告警失败: {e}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")

    async def _generate_alerts_legacy(self, task, results: List[Dict[str, Any]]):
        """生成告警消息（原逻辑 - 向后兼容）"""
        try:
            # 检查has_alert字段，如果没有则检查has_violation字段
            alert_results = [r for r in results if (r.get('has_alert', False) or r.get('has_violation', False))]

            if alert_results:
                # 获取视频信息
                video = await VideoFileService.get_video_by_id(task.video_id)
                video_name = video.name if video else f"Video-{task.video_id}"

                for result in alert_results:
                    # 调试日志：检查image_path字段
                    logger.info(f"生成告警消息 - 帧 {result.get('frame_index', 0)}: image_url={result.get('image_url') or result.get('image_path')}")

                    alert_message = {
                        'id': f"{task.id}_{result.get('frame_index', 0)}",
                        'type': 'video_analysis',
                        'severity': self._determine_alert_severity(result.get('confidence', 0.5)),
                        'title': f'视频分析告警: {video_name}',
                        'message': result.get('ai_response', '检测到异常情况'),
                        'source': 'video_analysis_service',
                        'video_id': task.video_id,
                        'task_id': task.id,
                        'frame_index': result.get('frame_index'),
                        'timestamp': result.get('timestamp'),
                        'confidence': result.get('confidence'),
                        'image_path': result.get('image_url') or result.get('image_path'),  # 兼容新旧字段名
                        'template_id': result.get('template_name'),  # 使用template_name而不是template_id
                        'template_category': result.get('category', 'unknown'),
                        'description': result.get('ai_response', '')[:200],  # 截取前200字符
                        'created_at': now_isoformat()
                    }

                    # 推送预警并存储到ES
                    await self.alert_service.broadcast_alert(alert_message)

                logger.info(f"生成 {len(alert_results)} 条预警消息")

        except Exception as e:
            logger.error(f"生成告警消息失败: {e}")
    
    async def _store_results_to_elasticsearch(self, task, results: List[Dict[str, Any]]):
        """存储分析结果到Elasticsearch"""
        try:
            # 获取视频信息
            video = await VideoFileService.get_video_by_id(task.video_id)
            if not video:
                logger.warning(f"无法获取视频信息用于ES存储: {task.video_id}")
                return
            
            # 准备分析任务总结数据
            alert_results = [r for r in results if (r.get('has_alert', False) or r.get('has_violation', False))]
            
            analysis_summary = {
                "video_name": video.name,
                "original_filename": video.original_filename,
                "template_ids": task.template_ids,
                "status": task.status,
                "frames_analyzed": len(results),
                "total_alerts": len(alert_results),
                "duration": (task.completed_at - task.started_at).total_seconds() if task.completed_at and task.started_at else 0,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "results_summary": self._create_results_summary(results)
            }
            
            # 存储分析任务结果
            await elasticsearch_service.store_analysis_result(
                task.id, task.video_id, analysis_summary
            )
            
            # 批量存储帧分析结果
            if results:
                frame_results = []
                for result in results:
                    frame_data = {
                        **result,
                        "task_id": task.id,
                        "video_id": task.video_id,
                        "video_name": video.name,
                        "analyzed_at": now_isoformat()
                    }
                    frame_results.append(frame_data)
                
                # 批量存储帧结果
                await elasticsearch_service.bulk_store_frame_results(frame_results)
            
            logger.info(f"成功存储 {len(results)} 个帧分析结果到Elasticsearch")
            
        except Exception as e:
            logger.error(f"存储结果到Elasticsearch失败: {e}")
    
    def _create_results_summary(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """创建结果总结"""
        try:
            summary = []
            
            # 按模板ID分组统计
            template_stats = {}
            for result in results:
                template_id = result.get('template_id', 'unknown')
                if template_id not in template_stats:
                    template_stats[template_id] = {
                        'template_id': template_id,
                        'total_frames': 0,
                        'alert_frames': 0,
                        'avg_confidence': 0.0,
                        'max_confidence': 0.0,
                        'min_confidence': 1.0
                    }
                
                stats = template_stats[template_id]
                stats['total_frames'] += 1
                
                confidence = result.get('confidence', 0.0)
                stats['max_confidence'] = max(stats['max_confidence'], confidence)
                stats['min_confidence'] = min(stats['min_confidence'], confidence)
                
                if result.get('has_alert', False) or result.get('has_violation', False):
                    stats['alert_frames'] += 1
            
            # 计算平均置信度
            for template_id, stats in template_stats.items():
                template_results = [r for r in results if r.get('template_id') == template_id]
                if template_results:
                    avg_conf = sum(r.get('confidence', 0.0) for r in template_results) / len(template_results)
                    stats['avg_confidence'] = round(avg_conf, 3)
                    stats['alert_rate'] = round(stats['alert_frames'] / stats['total_frames'], 3)
                
                summary.append(stats)
            
            return summary
            
        except Exception as e:
            logger.error(f"创建结果总结失败: {e}")
            return []
    
    def _determine_alert_severity(self, confidence: float) -> str:
        """根据置信度确定告警严重程度"""
        if confidence >= 0.9:
            return "critical"
        elif confidence >= 0.7:
            return "high"
        elif confidence >= 0.5:
            return "medium"
        else:
            return "low"