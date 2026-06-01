"""
多模态AI分析器
负责视频内容分析和异常检测
"""

import time
import asyncio
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from services.ai_client import AIClient
from config.settings import RAGConfig
from models.time_range import TimeRange


logger = logging.getLogger(__name__)


class MultiModalAnalyzer:
    """多模态AI分析器"""
    
    def __init__(self):
        self.message_queue = []
        self.ai_client = AIClient()
        logger.info("多模态分析器初始化完成")

    def _format_timestamp(self, date_str: str) -> str:
        """格式化时间戳为中文描述"""
        try:
            year, month, day, hour, minute, second = date_str.split('-')
            am_pm = "上午" if int(hour) < 12 else "下午"
            hour_12 = hour if hour == '12' else str(int(hour) % 12)
            return f"{year}年{int(month)}月{int(day)}日{am_pm}{hour_12}点（{hour}时）{int(minute)}分{int(second)}秒"
        except Exception as e:
            logger.error(f"时间戳格式化失败: {e}")
            return date_str

    def _build_history_context(self) -> str:
        """构建历史上下文"""
        if not self.message_queue:
            return "录像视频刚刚开始。"
            
        history_parts = []
        for msg in self.message_queue:
            history_part = (f"历史视频内容总结: {msg.get('recursive_summary', '')}\n\n"
                          f"当前时间段：{msg['start_time']} - {msg['end_time']}\n"
                          f"该时间段视频描述如下：{msg['description']}\n\n"
                          f"该时间段异常提醒: {msg['alert']}")
            history_parts.append(history_part)
            
        return "\n".join(history_parts)

    async def analyze(self, frames: List[np.ndarray], fps: float, 
                     time_range: Optional[TimeRange] = None) -> Optional[Dict[str, Any]]:
        """
        分析视频帧序列
        
        Args:
            frames: 视频帧列表
            fps: 视频帧率
            time_range: 时间范围对象
            
        Returns:
            分析结果字典
        """
        start_time = time.time()
        
        try:
            # 构建历史上下文
            history_context = self._build_history_context()
            
            # 并行执行历史总结和视频描述
            logger.info("开始AI分析...")
            
            summary_task = self.ai_client.summarize_history(history_context)
            description_task = self.ai_client.describe_video(frames, time_range.to_timestamps() if time_range else None, fps)
            
            recursive_summary, description = await asyncio.gather(summary_task, description_task)
            
            # 如果只需要描述，直接返回
            if time_range is None:
                return {"description": description}
                
            # 保存历史记录
            await self._save_history_record(time_range.start_time, description)
            
            # 异常检测分析
            detection_result = await self.ai_client.detect_anomaly(
                recursive_summary=recursive_summary,
                current_time=time_range.format_chinese(),
                latest_description=description
            )
            
            analysis_time = time.time() - start_time
            logger.info(f"AI分析完成，耗时: {analysis_time:.2f}s")
            logger.info(f"检测结果: {detection_result}")
            
            # 处理异常情况
            if "无异常" not in detection_result:
                return await self._handle_anomaly_detected(
                    frames, time_range, description, detection_result, recursive_summary, analysis_time, fps
                )
            
            # 记录正常分析结果
            self._update_message_queue(time_range, description, detection_result)
            
            return {
                "alert": "无异常",
                "description": description,
                "analysis_time": analysis_time
            }
            
        except Exception as e:
            logger.error(f"视频分析失败: {str(e)}")
            return None

    async def _save_history_record(self, timestamp: str, description: str):
        """保存历史记录"""
        date_flag = self._format_timestamp(timestamp) + "："
        
        if RAGConfig.ENABLE_RAG:
            # 保存到向量数据库
            from services.storage import StorageService
            await StorageService.insert_to_vector_db([date_flag + description])
        else:
            # 保存到本地文件
            try:
                with open(RAGConfig.HISTORY_FILE, 'a', encoding='utf-8') as file:
                    file.write(date_flag + description + '\n')
                logger.debug("历史记录已保存到本地文件")
            except Exception as e:
                logger.error(f"保存历史记录失败: {e}")

    async def _handle_anomaly_detected(self, frames: List[np.ndarray], time_range: TimeRange,
                                     description: str, alert: str, recursive_summary: str, 
                                     analysis_time: float, fps: float) -> Dict[str, Any]:
        """处理检测到异常的情况"""
        try:
            from services.storage import StorageService
            
            # 保存异常视频和截图
            file_prefix = f"warning_{time_range.start_time}"
            video_file = await StorageService.save_warning_video(frames, file_prefix, fps)
            image_file = await StorageService.save_warning_image(frames[0], file_prefix)
            
            logger.warning(f"异常检测: {alert}")
            
            return {
                "alert": f'<span style="color:red;">{alert}</span>',
                "description": f'当前10秒监控消息描述：\n{description}\n\n历史监控内容:\n{recursive_summary}',
                "video_file_name": f"{file_prefix}.mp4",
                "picture_file_name": f"{file_prefix}.jpg",
                "analysis_time": analysis_time,
                "confidence": 0.9  # 可以后续优化为实际置信度
            }
            
        except Exception as e:
            logger.error(f"处理异常检测结果失败: {e}")
            return {
                "alert": alert,
                "description": description,
                "analysis_time": analysis_time
            }

    def _update_message_queue(self, time_range: TimeRange, description: str, alert: str):
        """更新消息队列"""
        self.message_queue.append({
            'start_time': time_range.start_time,
            'end_time': time_range.end_time,
            'description': description,
            'alert': alert
        })
        
        # 只保留最近15条消息
        self.message_queue = self.message_queue[-15:]

    def stop(self):
        """停止视频处理"""
        self._running = False
        if self.cap:
            self.cap.release()
        logger.info("视频处理器已停止")