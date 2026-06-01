"""
告警分发器
一帧多告警独立写入，每个violation创建独立的alert记录
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone
import uuid

from services.elasticsearch_service import elasticsearch_service
from core.alert_service import AlertService
from utils.timezone_utils import get_beijing_timestamp, now_isoformat

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """
    告警分发器 - 一帧多告警独立写入

    职责：
    - 接收复合检测的violations列表
    - 过滤has_violation=true的violations
    - 为每个violation独立创建alert记录
    - 写入ES video_alerts索引
    - WebSocket实时推送
    """

    def __init__(self):
        """初始化告警分发器"""
        self._total_dispatched = 0
        self._total_violations_processed = 0

    async def dispatch_alerts(
        self,
        task_id: str,
        video_id: str,
        video_name: str,
        frame_index: int,
        timestamp: float,
        violations: List[Dict],
        image_url: str,
        analysis_type: str = 'composite_detection'
    ) -> int:
        """
        分发多个告警到ES和WebSocket

        Args:
            task_id: 任务ID
            video_id: 视频ID
            video_name: 视频名称
            frame_index: 帧索引
            timestamp: 视频时间戳（秒）
            violations: 违规列表（来自CompositeResponseParser）
            image_url: 图片URL（MinIO）
            analysis_type: 分析类型，默认'composite_detection'

        Returns:
            成功分发的告警数量

        Example violations:
            [
                {
                    'type_code': 'safety_helmet',
                    'display_name': '未佩戴安全帽',
                    'has_violation': True,
                    'confidence': 0.92,
                    'violation_count': 1,
                    'conclusion': '发现1人未佩戴',
                    'severity': 'high',
                    'category': 'safety'
                },
                ...
            ]
        """
        if not violations:
            logger.debug(f"帧{frame_index}无violations，跳过告警分发")
            return 0

        self._total_violations_processed += len(violations)

        # 过滤has_violation=true的violations
        alert_violations = [v for v in violations if v.get('has_violation')]

        if not alert_violations:
            logger.debug(
                f"帧{frame_index}检测了{len(violations)}种类型，但均未发现违规"
            )
            return 0

        logger.info(
            f"🚨 帧{frame_index}检测到{len(alert_violations)}种违规类型，"
            f"开始分发{len(alert_violations)}个独立告警"
        )

        # 为每个violation创建独立的alert
        dispatched_count = 0

        for violation in alert_violations:
            try:
                success = await self._dispatch_single_alert(
                    task_id=task_id,
                    video_id=video_id,
                    video_name=video_name,
                    frame_index=frame_index,
                    timestamp=timestamp,
                    violation=violation,
                    image_url=image_url,
                    analysis_type=analysis_type
                )

                if success:
                    dispatched_count += 1
                    self._total_dispatched += 1

            except Exception as e:
                logger.error(
                    f"❌ 分发告警失败: type={violation.get('type_code')}, error={e}"
                )

        logger.info(
            f"✅ 帧{frame_index}告警分发完成: {dispatched_count}/{len(alert_violations)}个成功"
        )

        return dispatched_count

    async def _dispatch_single_alert(
        self,
        task_id: str,
        video_id: str,
        video_name: str,
        frame_index: int,
        timestamp: float,
        violation: Dict,
        image_url: str,
        analysis_type: str
    ) -> bool:
        """
        分发单个告警

        Args:
            task_id: 任务ID
            video_id: 视频ID
            video_name: 视频名称
            frame_index: 帧索引
            timestamp: 视频时间戳（秒）
            violation: 单个violation数据
            image_url: 图片URL
            analysis_type: 分析类型

        Returns:
            是否成功
        """
        # 1. 构建ES告警文档
        alert_doc = self._build_alert_document(
            task_id=task_id,
            video_id=video_id,
            video_name=video_name,
            frame_index=frame_index,
            timestamp=timestamp,
            violation=violation,
            image_url=image_url,
            analysis_type=analysis_type
        )

        # 2. 存储到ES
        es_success = await elasticsearch_service.store_alert(alert_doc)

        if not es_success:
            logger.warning(
                f"⚠️  告警存储ES失败: {violation.get('display_name')}"
            )

        # 3. WebSocket实时推送（独立于ES存储，确保实时性）
        try:
            await self._broadcast_alert(alert_doc, violation)
        except Exception as e:
            logger.error(f"WebSocket推送失败: {e}")

        return es_success

    def _build_alert_document(
        self,
        task_id: str,
        video_id: str,
        video_name: str,
        frame_index: int,
        timestamp: float,
        violation: Dict,
        image_url: str,
        analysis_type: str
    ) -> Dict:
        """
        构建ES告警文档

        Returns:
            符合video_alerts索引结构的文档
        """
        # 格式化video_time为MM:SS
        video_time = self._format_video_time(timestamp)

        # 使用北京时间
        beijing_time = now_isoformat()

        # 获取显示名称（优先使用display_name，回退到type_code）
        display_name = violation.get('display_name') or violation.get('type_code', 'unknown')

        # 构建完整的算法名称："违规行为分析 - {display_name}"
        full_algorithm_name = f"违规行为分析 - {display_name}"

        # 构建告警文档（保持video_alerts索引结构不变）
        alert_doc = {
            # 基础信息
            'task_id': task_id,
            'video_id': video_id,
            'video_name': video_name,
            'frame_index': frame_index,
            'timestamp': timestamp,
            'video_time': video_time,
            'created_at': beijing_time,

            # 检测类型信息（格式："违规行为分析 - 未佩戴安全帽"）
            'template_name': full_algorithm_name,
            'algorithm_name': full_algorithm_name,
            'detection_type_code': violation.get('type_code'),  # 类型编码，关联detection_type_templates
            'category': violation.get('category', 'unknown'),
            'algorithm_category': violation.get('category', 'unknown'),  # 兼容字段
            'severity': violation.get('severity', 'medium'),

            # AI分析结果
            'confidence': violation.get('confidence', 0.0),
            'description': violation.get('conclusion', ''),
            'ai_response': violation.get('conclusion', ''),  # 兼容字段
            'alert_content': violation.get('details', []),  # 详细信息

            # 违规统计
            'violation_count': violation.get('violation_count', 1),

            # 分析类型标记
            'analysis_type': analysis_type,

            # 图片信息
            'image_url': image_url,

            # 告警状态
            'resolved': False,

            # 元数据（扩展字段）
            'metadata': {
                'parse_strategy': violation.get('parse_strategy', 'unknown'),
                'is_composite_detection': True,
                'violation_type_code': violation.get('type_code')
            }
        }

        return alert_doc

    async def _broadcast_alert(self, alert_doc: Dict, violation: Dict):
        """
        WebSocket实时推送告警

        Args:
            alert_doc: ES告警文档
            violation: violation数据
        """
        # 构建WebSocket消息格式
        alert_message = {
            'task_id': alert_doc['task_id'],
            'video_id': alert_doc['video_id'],
            'title': f"视频分析告警: {alert_doc['video_name']}",
            'message': f"【{alert_doc['template_name']}】{alert_doc['description']}",
            'description': alert_doc['description'],
            'frame_index': alert_doc['frame_index'],
            'confidence': alert_doc['confidence'],
            'severity': alert_doc['severity'],
            'image_path': alert_doc['image_url'],
            'timestamp': alert_doc['timestamp'],
            'video_time': alert_doc['video_time'],
            'source': alert_doc['video_name'],
            'type': 'video_analysis',
            'detection_type': violation.get('type_code'),
            'violation_count': violation.get('violation_count', 1)
        }

        # 广播告警（AlertService已包含ES存储逻辑，但我们已经单独存储了）
        # 这里只用于WebSocket推送
        await AlertService.broadcast_alert(alert_message)

        logger.debug(
            f"📡 WebSocket推送告警: {alert_doc['template_name']}, "
            f"置信度{alert_doc['confidence']:.2f}"
        )

    def _format_video_time(self, timestamp: float) -> str:
        """
        格式化视频时间为MM:SS

        Args:
            timestamp: 时间戳（秒）

        Returns:
            "MM:SS"格式的时间字符串
        """
        minutes = int(timestamp // 60)
        seconds = int(timestamp % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def get_statistics(self) -> Dict:
        """
        获取分发器统计信息（用于监控）

        Returns:
            {
                'total_dispatched': 总分发告警数,
                'total_violations_processed': 总处理violations数
            }
        """
        return {
            'total_dispatched': self._total_dispatched,
            'total_violations_processed': self._total_violations_processed,
            'dispatch_rate': (
                self._total_dispatched / self._total_violations_processed
                if self._total_violations_processed > 0 else 0.0
            )
        }


# 全局单例实例（应用级别共享）
_global_alert_dispatcher: Optional[AlertDispatcher] = None


def get_alert_dispatcher() -> AlertDispatcher:
    """
    获取全局告警分发器实例（单例模式）

    Returns:
        AlertDispatcher实例
    """
    global _global_alert_dispatcher

    if _global_alert_dispatcher is None:
        _global_alert_dispatcher = AlertDispatcher()
        logger.info("✅ 创建全局AlertDispatcher实例")

    return _global_alert_dispatcher
