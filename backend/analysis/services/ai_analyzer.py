"""
AI分析引擎 - 简化版
提供视频分析的统一入口，委托具体任务给专门的处理器
"""

import logging
from typing import List, Dict, Any, Optional, Callable

from models.analysis_result import VideoAnalysisResult
from models.video_metadata import VideoAnalysisTask, AnalysisStatus
from analysis.services.video_analyzer import VideoAnalyzer

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI分析引擎 - 统一入口"""
    
    def __init__(self):
        self.video_analyzer = VideoAnalyzer()
        
    async def analyze_video(self, video_path: str, prompt_template_ids: List[str],
                          task: VideoAnalysisTask, progress_callback: Optional[Callable] = None) -> VideoAnalysisResult:
        """
        分析视频 - 委托给VideoAnalyzer处理
        """
        return await self.video_analyzer.analyze_video(
            video_path, prompt_template_ids, task, progress_callback
        )