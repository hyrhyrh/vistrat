"""
视频分析任务模型
单独管理分析任务的状态和生命周期
"""

from datetime import datetime
from typing import List, Dict, Any
from uuid import uuid4
from utils.timezone_utils import now, now_isoformat


class VideoAnalysisTask:
    """视频分析任务"""
    
    def __init__(self, video_id: str, template_ids: List[str]):
        self.id = str(uuid4())
        self.video_id = video_id
        self.template_ids = template_ids
        self.status = "pending"  # pending, running, completed, failed
        self.progress = 0.0
        self.created_at = now()
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.results = []
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'video_id': self.video_id,
            'template_ids': self.template_ids,
            'status': self.status,
            'progress': self.progress,
            'analysis_progress': int(self.progress * 100),  # 添加百分比进度
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'result_count': len(self.results)
        }