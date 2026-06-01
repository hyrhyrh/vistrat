"""
任务健康监控和自动恢复服务

解决运行时任务停止后无法自动恢复的问题：
1. 定期检查所有启用的任务是否真正在运行
2. 监控视频流健康状态
3. 自动重启失败或停止的任务
4. 智能重试机制（避免频繁重试）
5. 详细的日志记录
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from utils.timezone_utils import now
from database.db_utils import get_async_connection, fetch

logger = logging.getLogger(__name__)


@dataclass
class TaskRecoveryRecord:
    """任务恢复记录"""
    task_id: str
    task_name: str
    stream_id: str
    stream_name: str
    last_check_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    failure_count: int = 0
    recovery_attempts: int = 0
    last_recovery_time: Optional[datetime] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0  # 连续失败次数


@dataclass
class StreamHealthRecord:
    """视频流健康记录"""
    stream_id: str
    stream_name: str
    rtsp_url: str
    last_check_time: Optional[datetime] = None
    last_online_time: Optional[datetime] = None
    last_offline_time: Optional[datetime] = None
    status: str = "UNKNOWN"  # ONLINE, OFFLINE, UNKNOWN
    check_count: int = 0
    consecutive_failures: int = 0  # 连续失败次数
    last_error: Optional[str] = None


class TaskHealthMonitor:
    """任务健康监控服务"""

    def __init__(
        self,
        check_interval: int = 300,  # 健康检查间隔（秒），默认5分钟
        stream_check_interval: int = 600,  # 视频流检查间隔（秒），默认10分钟
        retry_delay_base: int = 300,  # 基础重试延迟（秒），默认5分钟
        max_retry_delay: int = 3600,  # 最大重试延迟（秒），默认1小时
        max_consecutive_failures: int = 5  # 最大连续失败次数，超过后延长重试间隔
    ):
        self.check_interval = check_interval
        self.stream_check_interval = stream_check_interval
        self.retry_delay_base = retry_delay_base
        self.max_retry_delay = max_retry_delay
        self.max_consecutive_failures = max_consecutive_failures

        # 任务恢复记录
        self.task_records: Dict[str, TaskRecoveryRecord] = {}

        # 视频流健康记录
        self.stream_records: Dict[str, StreamHealthRecord] = {}

        # 监控状态
        self.is_running = False
        self.monitor_task = None
        self.stream_monitor_task = None

        # 统计信息
        self.total_checks = 0
        self.total_recoveries = 0
        self.total_failures = 0
        self.started_at = None

    async def start(self):
        """启动健康监控服务"""
        if self.is_running:
            logger.warning("任务健康监控已在运行中")
            return

        self.is_running = True
        self.started_at = now()

        logger.info(
            f"启动任务健康监控服务 - "
            f"任务检查间隔: {self.check_interval}秒, "
            f"视频流检查间隔: {self.stream_check_interval}秒"
        )

        # 启动两个独立的监控任务
        self.monitor_task = asyncio.create_task(self._monitor_loop())
        self.stream_monitor_task = asyncio.create_task(self._stream_monitor_loop())

        logger.info("✅ 任务健康监控服务已启动")

    async def stop(self):
        """停止健康监控服务"""
        if not self.is_running:
            return

        self.is_running = False

        # 取消监控任务
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        if self.stream_monitor_task:
            self.stream_monitor_task.cancel()
            try:
                await self.stream_monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("任务健康监控服务已停止")

    async def _monitor_loop(self):
        """任务健康监控主循环"""
        logger.info("任务健康监控循环已启动")

        # 首次启动延迟30秒，让系统完全启动
        await asyncio.sleep(30)

        while self.is_running:
            try:
                await self._check_all_tasks()
                self.total_checks += 1
            except Exception as e:
                logger.error(f"任务健康检查异常: {e}", exc_info=True)

            # 等待下一次检查
            await asyncio.sleep(self.check_interval)

    async def _stream_monitor_loop(self):
        """视频流健康监控循环"""
        logger.info("视频流健康监控循环已启动")

        # 首次启动延迟60秒，让系统完全启动
        await asyncio.sleep(60)

        while self.is_running:
            try:
                await self._check_all_streams()
            except Exception as e:
                logger.error(f"视频流健康检查异常: {e}", exc_info=True)

            # 等待下一次检查
            await asyncio.sleep(self.stream_check_interval)

    async def _check_all_tasks(self):
        """检查所有启用的任务"""
        try:
            # 1. 从数据库查询所有应该运行的任务
            conn = await get_async_connection(use_dict_row=True)
            try:
                query = """
                    SELECT
                        t.id, t.stream_id, t.task_name, t.status, t.is_active,
                        vs.name as stream_name, vs.stream_url, vs.status as stream_status
                    FROM stream_analysis_tasks t
                    LEFT JOIN video_streams vs ON t.stream_id = vs.id
                    WHERE t.status = 'enabled'
                        AND t.is_active = true
                        AND vs.id IS NOT NULL
                    ORDER BY t.priority DESC
                """
                tasks = await fetch(conn, query)

                if not tasks:
                    logger.debug("没有需要监控的启用任务")
                    return

                logger.info(f"开始检查 {len(tasks)} 个启用的任务...")

                # 2. 获取实际运行中的任务
                from services.stream_analysis_service import stream_analysis_service
                running_tasks = stream_analysis_service.running_tasks
                running_stream_ids = {
                    task.stream_id for task in running_tasks.values()
                    if task.status == "running"
                }

                logger.debug(f"当前运行中的流: {running_stream_ids}")

                # 3. 检查每个任务
                for task in tasks:
                    await self._check_single_task(task, running_stream_ids)

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"检查所有任务失败: {e}", exc_info=True)

    async def _check_single_task(self, task: Dict, running_stream_ids: set):
        """检查单个任务"""
        task_id = str(task['id'])
        stream_id = str(task['stream_id'])
        task_name = task['task_name']
        stream_name = task.get('stream_name', '未知流')
        stream_status = task.get('stream_status', 'OFFLINE')

        # 安全检查：如果视频流已被删除，跳过此任务
        if stream_name is None or stream_name == '未知流':
            logger.warning(
                f"⚠️  任务 {task_name} 对应的视频流已被删除 (stream_id: {stream_id})，"
                f"跳过健康检查。建议禁用此任务。"
            )
            return

        # 获取或创建任务记录
        if task_id not in self.task_records:
            self.task_records[task_id] = TaskRecoveryRecord(
                task_id=task_id,
                task_name=task_name,
                stream_id=stream_id,
                stream_name=stream_name
            )

        record = self.task_records[task_id]
        record.last_check_time = now()

        # 检查任务是否应该运行
        should_run = await self._should_task_run(task)

        # 检查任务是否真的在运行
        is_actually_running = stream_id in running_stream_ids

        # 🔧 修复：处理所有四种状态组合
        if not should_run:
            # 任务不应该运行
            if is_actually_running:
                # 但仍在运行 → 需要停止
                logger.warning(
                    f"⚠️ 任务 {task_name} 不在运行时间范围内但仍在运行，将停止任务"
                )
                try:
                    from services.stream_task_manager import stream_task_manager
                    await stream_task_manager.disable_task(task_id)
                    logger.info(f"✅ 已停止超时运行的任务: {task_name}")
                except Exception as e:
                    logger.error(f"❌ 停止任务失败: {task_name}, 错误: {e}")
            else:
                # 也没在运行 → 正常，无需操作
                logger.debug(f"任务 {task_name} 不在运行时间范围内，且未运行，跳过检查")
            return

        # 任务应该运行
        if is_actually_running:
            # 任务正常运行
            if record.consecutive_failures > 0:
                logger.info(
                    f"✅ 任务已恢复正常: {task_name} "
                    f"(之前连续失败 {record.consecutive_failures} 次)"
                )
            record.consecutive_failures = 0
            return

        # 任务应该运行但没有运行
        logger.warning(
            f"⚠️  发现任务未运行: {task_name} (流: {stream_name}, "
            f"流状态: {stream_status}, 连续失败: {record.consecutive_failures})"
        )

        # 检查是否应该尝试恢复
        if await self._should_attempt_recovery(record, stream_status):
            await self._attempt_task_recovery(task, record)
        else:
            delay = self._calculate_retry_delay(record.consecutive_failures)
            logger.info(
                f"暂不恢复任务 {task_name}: "
                f"等待 {delay // 60} 分钟后重试 "
                f"(连续失败: {record.consecutive_failures})"
            )

    async def _should_task_run(self, task: Dict) -> bool:
        """检查任务是否应该运行（考虑时间配置）"""
        try:
            time_config = task.get('time_config')
            if not time_config:
                return True  # 没有时间配置，默认应该运行

            from utils.time_config_checker import check_should_run_now
            should_run, reason = check_should_run_now(time_config)

            if not should_run:
                logger.debug(f"任务 {task['task_name']} 不在运行时间: {reason}")

            return should_run
        except Exception as e:
            logger.warning(f"检查任务时间配置失败: {e}")
            return True  # 出错时默认应该运行

    async def _should_attempt_recovery(
        self, record: TaskRecoveryRecord, stream_status: str
    ) -> bool:
        """判断是否应该尝试恢复任务"""
        # 如果视频流离线，不尝试恢复
        if stream_status == 'OFFLINE':
            logger.debug(
                f"视频流离线，暂不恢复任务: {record.task_name} "
                f"(等待流恢复)"
            )
            return False

        # 如果从未尝试恢复，立即尝试
        if record.last_recovery_time is None:
            return True

        # 计算距离上次恢复的时间
        time_since_last_recovery = (now() - record.last_recovery_time).total_seconds()

        # 根据连续失败次数计算重试延迟
        retry_delay = self._calculate_retry_delay(record.consecutive_failures)

        # 如果距离上次恢复时间超过重试延迟，可以重试
        return time_since_last_recovery >= retry_delay

    def _calculate_retry_delay(self, consecutive_failures: int) -> int:
        """
        计算重试延迟（指数退避策略）

        失败次数越多，重试间隔越长：
        - 0-1次: 5分钟
        - 2-3次: 10分钟
        - 4-5次: 20分钟
        - 6+次: 1小时
        """
        if consecutive_failures <= 1:
            return self.retry_delay_base  # 5分钟
        elif consecutive_failures <= 3:
            return self.retry_delay_base * 2  # 10分钟
        elif consecutive_failures <= 5:
            return self.retry_delay_base * 4  # 20分钟
        else:
            return min(
                self.retry_delay_base * 12,  # 1小时
                self.max_retry_delay
            )

    async def _attempt_task_recovery(
        self, task: Dict, record: TaskRecoveryRecord
    ):
        """尝试恢复任务"""
        task_id = str(task['id'])
        stream_id = str(task['stream_id'])
        task_name = task['task_name']

        try:
            logger.info(
                f"🔄 尝试恢复任务: {task_name} "
                f"(恢复次数: {record.recovery_attempts + 1}, "
                f"连续失败: {record.consecutive_failures})"
            )

            # 调用 enable_task 启动任务
            from services.stream_task_manager import stream_task_manager
            success = await stream_task_manager.enable_task(task_id)

            record.last_recovery_time = now()
            record.recovery_attempts += 1

            if success:
                logger.info(f"✅ 任务恢复成功: {task_name}")
                record.consecutive_failures = 0
                record.last_error = None
                self.total_recoveries += 1
            else:
                logger.error(f"❌ 任务恢复失败: {task_name}")
                record.consecutive_failures += 1
                record.failure_count += 1
                record.last_failure_time = now()
                record.last_error = "enable_task returned False"
                self.total_failures += 1

        except Exception as e:
            error_msg = str(e)
            logger.error(
                f"❌ 任务恢复异常: {task_name}, 错误: {error_msg}",
                exc_info=True
            )
            record.consecutive_failures += 1
            record.failure_count += 1
            record.last_failure_time = now()
            record.last_error = error_msg
            self.total_failures += 1

    async def _check_all_streams(self):
        """检查所有视频流的健康状态"""
        try:
            # 查询所有视频流
            conn = await get_async_connection(use_dict_row=True)
            try:
                query = """
                    SELECT id, name, stream_url, stream_type, status
                    FROM video_streams
                    ORDER BY created_at
                """
                streams = await fetch(conn, query)

                if not streams:
                    logger.debug("没有需要监控的视频流")
                    return

                logger.info(f"开始检查 {len(streams)} 个视频流的健康状态...")

                for stream in streams:
                    await self._check_single_stream(stream)

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"检查所有视频流失败: {e}", exc_info=True)

    async def _check_single_stream(self, stream: Dict):
        """检查单个视频流的健康状态"""
        stream_id = str(stream['id'])
        stream_name = stream.get('name', '未知流')
        stream_url = stream.get('stream_url', '')
        current_status = stream.get('status', 'OFFLINE')

        # 只检查RTSP流
        if not stream_url.startswith('rtsp://'):
            return

        # 获取或创建流记录
        if stream_id not in self.stream_records:
            self.stream_records[stream_id] = StreamHealthRecord(
                stream_id=stream_id,
                stream_name=stream_name,
                rtsp_url=stream_url,
                status=current_status
            )

        record = self.stream_records[stream_id]
        record.last_check_time = now()
        record.check_count += 1

        # 执行健康检查
        try:
            from utils.rtsp_health_checker import rtsp_health_checker

            # 放入线程执行，避免阻塞事件循环
            is_healthy, error_msg, stream_info = await asyncio.to_thread(
                rtsp_health_checker.check_rtsp_stream, stream_url, 10
            )

            new_status = "ONLINE" if is_healthy else "OFFLINE"

            # 状态变化检测
            status_changed = (record.status != new_status)

            if is_healthy:
                record.consecutive_failures = 0
                record.last_online_time = now()

                if status_changed and record.status == "OFFLINE":
                    logger.info(
                        f"✅ 视频流已恢复: {stream_name} "
                        f"({stream_info.get('resolution', 'N/A')}, "
                        f"{stream_info.get('fps', 'N/A')} FPS)"
                    )
                    # 视频流恢复，尝试重启相关任务
                    await self._on_stream_recovered(stream_id, stream_name)
            else:
                record.consecutive_failures += 1
                record.last_offline_time = now()
                record.last_error = error_msg

                if status_changed:
                    logger.warning(
                        f"⚠️  视频流离线: {stream_name}, 错误: {error_msg}"
                    )

            # 更新流记录状态
            record.status = new_status

            # 更新数据库中的状态
            if status_changed:
                await self._update_stream_status(stream_id, new_status)

        except Exception as e:
            logger.error(
                f"检查视频流健康状态失败: {stream_name}, 错误: {e}",
                exc_info=True
            )
            record.consecutive_failures += 1
            record.last_error = str(e)

    async def _update_stream_status(self, stream_id: str, status: str):
        """更新数据库中的视频流状态"""
        try:
            conn = await get_async_connection()
            try:
                query = """
                    UPDATE video_streams
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                await conn.execute(query, (status, stream_id))
                await conn.commit()
                logger.debug(f"已更新视频流状态: {stream_id} -> {status}")
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"更新视频流状态失败: {e}")

    async def _on_stream_recovered(self, stream_id: str, stream_name: str):
        """当视频流恢复时，尝试重启相关任务"""
        try:
            logger.info(f"视频流已恢复，查找相关任务: {stream_name}")

            # 查询该流的所有启用任务
            conn = await get_async_connection(use_dict_row=True)
            try:
                query = """
                    SELECT id, task_name, status, is_active
                    FROM stream_analysis_tasks
                    WHERE stream_id = %s AND status = 'enabled' AND is_active = true
                """
                tasks = await fetch(conn, query, stream_id)

                if not tasks:
                    logger.info(f"流 {stream_name} 没有启用的分析任务")
                    return

                logger.info(
                    f"找到 {len(tasks)} 个启用的任务，尝试重启..."
                )

                from services.stream_task_manager import stream_task_manager

                for task in tasks:
                    task_id = str(task['id'])
                    task_name = task['task_name']

                    try:
                        logger.info(f"重启任务: {task_name}")
                        success = await stream_task_manager.enable_task(task_id)

                        if success:
                            logger.info(f"✅ 任务重启成功: {task_name}")
                        else:
                            logger.warning(f"⚠️  任务重启失败: {task_name}")
                    except Exception as e:
                        logger.error(
                            f"重启任务失败: {task_name}, 错误: {e}"
                        )

            finally:
                await conn.close()

        except Exception as e:
            logger.error(f"处理流恢复事件失败: {e}", exc_info=True)

    def get_statistics(self) -> Dict[str, Any]:
        """获取监控统计信息"""
        uptime = (now() - self.started_at).total_seconds() if self.started_at else 0

        # 任务统计
        total_tasks = len(self.task_records)
        tasks_with_failures = sum(
            1 for r in self.task_records.values()
            if r.failure_count > 0
        )
        tasks_with_consecutive_failures = sum(
            1 for r in self.task_records.values()
            if r.consecutive_failures > 0
        )

        # 流统计
        total_streams = len(self.stream_records)
        online_streams = sum(
            1 for r in self.stream_records.values()
            if r.status == "ONLINE"
        )
        offline_streams = sum(
            1 for r in self.stream_records.values()
            if r.status == "OFFLINE"
        )

        return {
            "is_running": self.is_running,
            "uptime_seconds": int(uptime),
            "uptime_hours": round(uptime / 3600, 2),
            "total_checks": self.total_checks,
            "total_recoveries": self.total_recoveries,
            "total_failures": self.total_failures,
            "task_statistics": {
                "total_tasks_monitored": total_tasks,
                "tasks_with_failures": tasks_with_failures,
                "tasks_with_consecutive_failures": tasks_with_consecutive_failures
            },
            "stream_statistics": {
                "total_streams_monitored": total_streams,
                "online_streams": online_streams,
                "offline_streams": offline_streams
            },
            "configuration": {
                "check_interval_seconds": self.check_interval,
                "stream_check_interval_seconds": self.stream_check_interval,
                "retry_delay_base_seconds": self.retry_delay_base,
                "max_retry_delay_seconds": self.max_retry_delay
            }
        }

    def get_task_records(self) -> List[Dict[str, Any]]:
        """获取所有任务恢复记录"""
        records = []
        for record in self.task_records.values():
            records.append({
                "task_id": record.task_id,
                "task_name": record.task_name,
                "stream_id": record.stream_id,
                "stream_name": record.stream_name,
                "last_check_time": record.last_check_time.isoformat() if record.last_check_time else None,
                "last_failure_time": record.last_failure_time.isoformat() if record.last_failure_time else None,
                "failure_count": record.failure_count,
                "recovery_attempts": record.recovery_attempts,
                "consecutive_failures": record.consecutive_failures,
                "last_recovery_time": record.last_recovery_time.isoformat() if record.last_recovery_time else None,
                "last_error": record.last_error
            })
        return records

    def get_stream_records(self) -> List[Dict[str, Any]]:
        """获取所有视频流健康记录"""
        records = []
        for record in self.stream_records.values():
            records.append({
                "stream_id": record.stream_id,
                "stream_name": record.stream_name,
                "rtsp_url": record.rtsp_url,
                "status": record.status,
                "last_check_time": record.last_check_time.isoformat() if record.last_check_time else None,
                "last_online_time": record.last_online_time.isoformat() if record.last_online_time else None,
                "last_offline_time": record.last_offline_time.isoformat() if record.last_offline_time else None,
                "check_count": record.check_count,
                "consecutive_failures": record.consecutive_failures,
                "last_error": record.last_error
            })
        return records


# 创建全局单例
task_health_monitor = TaskHealthMonitor()
