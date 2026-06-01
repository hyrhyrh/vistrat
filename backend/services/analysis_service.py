"""v3.0 分析服务 -- 消费帧队列，调用 AI 分析，写入结果"""

import asyncio
import base64
import logging
from uuid import UUID

import cv2
from sqlalchemy.orm.attributes import flag_modified

from config.settings import AIAnalysisConfig
from database.connection import DatabaseManager
from models.analysis_task import AnalysisTaskDB
from services.ai_client import AIAnalysisClient, parse_ai_response, ANALYSIS_PROMPT_SUFFIX
from services.frame_extractor import FrameData

logger = logging.getLogger(__name__)


class AnalysisService:
    """消费帧队列，调用 AI 分析，结构化解析，写入数据库"""

    def __init__(
        self,
        input_queue: asyncio.Queue,
        ai_client: AIAnalysisClient,
        stream_id: str | None = None,
    ):
        self.input_queue = input_queue
        self.ai_client = ai_client
        self._stream_id = stream_id
        self.running = False
        self._stats = {"frames_analyzed": 0, "violations_found": 0, "errors": 0}

    async def run(self, prompt: str):
        """主循环：从队列消费帧并分析"""
        self.running = True
        logger.info("分析服务已启动")

        while self.running:
            try:
                frame_data = await asyncio.wait_for(
                    self.input_queue.get(), timeout=5.0
                )
            except asyncio.TimeoutError:
                continue
            await self._process_frame(frame_data, prompt)

        logger.info("分析服务已停止")

    async def _process_frame(self, frame_data: FrameData, prompt: str):
        """处理单帧：编码 -> AI 分析 -> 置信度过滤 -> 存储"""
        try:
            # JPEG 编码为 base64
            _, buffer = cv2.imencode(
                ".jpg", frame_data.frame, [cv2.IMWRITE_JPEG_QUALITY, 85]
            )
            image_base64 = base64.b64encode(buffer.tobytes()).decode("utf-8")

            # 拼接提示词后缀
            full_prompt = prompt + ANALYSIS_PROMPT_SUFFIX

            # 调用 AI
            result = await self.ai_client.analyze_frame(image_base64, full_prompt)
            self._stats["frames_analyzed"] += 1

            # 置信度过滤
            confidence = result.get("confidence", 0.0)
            has_violation = result.get("has_violation", False)

            if has_violation and confidence >= AIAnalysisConfig.CONFIDENCE_THRESHOLD:
                # 高置信度违规
                self._stats["violations_found"] += 1
                await self._save_result(frame_data, result, high_confidence=True)
                logger.info(
                    "检测到高置信度违规 (%.2f): task=%s",
                    confidence,
                    frame_data.task_id,
                )
                # 高置信度违规 - 生成告警（per ALERT-01）
                try:
                    from services.alert_service_v3 import AlertServiceV3
                    await AlertServiceV3.create_alert(
                        stream_id=self._stream_id or str(frame_data.task_id),
                        task_id=str(frame_data.task_id),
                        result=result,
                        snapshot_path=None,
                    )
                except Exception as e:
                    logger.warning(f"告警生成失败（不阻塞分析）: {e}")
            else:
                # 低置信度或无违规
                await self._save_result(frame_data, result, high_confidence=False)

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(
                "帧处理失败 (task=%s): %s", frame_data.task_id, e
            )

    async def _save_result(
        self, frame_data: FrameData, result: dict, high_confidence: bool
    ):
        """将分析结果追加到 AnalysisTaskDB.result JSONB"""
        try:
            async with DatabaseManager.get_session() as session:
                task_id = (
                    UUID(frame_data.task_id)
                    if isinstance(frame_data.task_id, str)
                    else frame_data.task_id
                )
                task = await session.get(AnalysisTaskDB, task_id)
                if task:
                    existing = task.result or {"frames": []}
                    existing["frames"].append(
                        {
                            "timestamp": frame_data.timestamp,
                            "reason": frame_data.reason,
                            "result": result,
                            "high_confidence": high_confidence,
                        }
                    )
                    task.result = existing
                    flag_modified(task, "result")
        except Exception as e:
            logger.error("保存分析结果失败 (task=%s): %s", frame_data.task_id, e)

    async def stop(self):
        """停止分析服务"""
        self.running = False

    @property
    def stats(self) -> dict:
        """返回统计信息"""
        return dict(self._stats)
