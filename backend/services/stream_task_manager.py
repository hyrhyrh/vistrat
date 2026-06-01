"""
增强版流任务管理器 - 在简化版基础上增加监控能力
保持向后兼容,新增统计跟踪和健康监控功能

【架构兼容】统一使用同步psycopg + ThreadPool，避免greenlet/thread问题

# FIXME(circular): 与 stream_analysis_service 存在循环依赖，当前通过延迟导入规避。
# stream_task_manager 在启动/停止任务时需要调用 stream_analysis_service 的分析功能，
# stream_analysis_service 在启停流分析时需要查询 stream_task_manager 的任务状态。
# 建议重构: 提取 StreamTaskCoordinator 协调层，两者都不直接引用对方。
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from database.connection import DatabaseManager
from database.db_utils import get_async_connection, fetchval, fetchrow, fetch
from config.settings import DatabaseConfig
from services.helpers.task_recovery_helper import recover_tasks_async, recover_tasks_sync
from services.helpers.task_statistics_helper import (
    get_task_stats as _get_task_stats_helper,
    get_all_tasks_stats as _get_all_tasks_stats_helper,
    get_manager_stats as _get_manager_stats_helper,
    update_task_heartbeat as _update_task_heartbeat_helper,
    record_task_error as _record_task_error_helper,
)
from utils.timezone_utils import now as beijing_now
from sqlalchemy import text

logger = logging.getLogger(__name__)


@dataclass
class TaskStats:
    """任务运行统计"""
    task_id: str
    frames_processed: int = 0
    alerts_generated: int = 0
    error_count: int = 0
    start_time: Optional[float] = None
    last_heartbeat: Optional[float] = None
    avg_processing_time_ms: float = 0.0
    last_error: Optional[str] = None


class StreamTaskManager:
    """增强版流任务管理器 - 保持向后兼容"""

    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.initialized = False

        # 新增: 任务统计跟踪
        self.task_stats: Dict[str, TaskStats] = {}

        # 新增: 全局统计
        self.total_tasks_created = 0
        self.total_tasks_started = 0
        self.total_tasks_stopped = 0
        self.total_tasks_failed = 0
    
    async def initialize(self):
        """初始化任务管理器(增强版)"""
        try:
            logger.info("=" * 60)
            logger.info("初始化增强版任务管理器...")
            logger.info("- 功能: 任务管理 + 统计跟踪 + 健康监控")
            self.initialized = True
            logger.info("✅ 任务管理器初始化完成")
            logger.info("=" * 60)
            return True
        except Exception as e:
            logger.error(f"任务管理器初始化失败: {e}")
            return False
    
    async def auto_recover_tasks(self):
        """系统重启时自动恢复所有已启用的任务 - 委托给 helpers.task_recovery_helper"""
        return await recover_tasks_async(self.enable_task)

    def auto_recover_tasks_sync(self):
        """系统重启时自动恢复任务检查（同步版本，ARM架构使用） - 委托给 helpers.task_recovery_helper"""
        return recover_tasks_sync()
    
    async def create_task_legacy(self, task_config: Dict[str, Any]) -> Optional[str]:
        """创建新任务（旧接口，保持向后兼容）"""
        try:
            task_id = f"task_{len(self.tasks) + 1}"
            self.tasks[task_id] = {
                **task_config,
                "id": task_id,
                "status": "created",
                "created_at": "2024-01-01T00:00:00Z"
            }
            logger.info(f"创建任务: {task_id}")
            return task_id
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return None
    
    async def start_task(self, task_id: str) -> bool:
        """启动任务"""
        try:
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = "running"
                logger.info(f"启动任务: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"启动任务失败: {e}")
            return False
    
    async def stop_task(self, task_id: str) -> bool:
        """停止任务"""
        try:
            if task_id in self.tasks:
                self.tasks[task_id]["status"] = "stopped"
                logger.info(f"停止任务: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"停止任务失败: {e}")
            return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        try:
            return self.tasks.get(task_id)
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return None
    
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        try:
            return list(self.tasks.values())
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return []
    
    async def get_task_list(self, stream_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """从数据库获取任务列表（兼容接口）"""
        try:
            logger.info(f"🔍 get_task_list调用: stream_id={stream_id}")

            # 导入数据库连接
            # asyncpg已替换为psycopg 3
            from config.settings import DatabaseConfig

            # 使用dict_row以便通过列名访问结果
            logger.debug("正在建立数据库连接...")
            conn = await get_async_connection(use_dict_row=True)
            logger.debug("✅ 数据库连接成功")

            try:
                if stream_id:
                    # 查询指定流的任务
                    logger.info(f"📋 查询指定流的任务: {stream_id}")
                    query = """
                        SELECT t.*, vs.name as stream_name,
                               COALESCE(amc.name, vsac.template_name) as algorithm_name
                        FROM stream_analysis_tasks t
                        LEFT JOIN video_streams vs ON t.stream_id = vs.id
                        LEFT JOIN ai_model_configs amc ON t.algorithm_config_id = amc.id
                        LEFT JOIN video_stream_algorithm_configs vsac ON t.algorithm_config_id = vsac.id
                        WHERE t.stream_id = %s
                        ORDER BY t.priority DESC, t.created_at
                    """
                    results = await fetch(conn, query, stream_id)
                    logger.info(f"📊 SQL查询返回 {len(results)} 行数据")
                else:
                    # 查询所有任务
                    logger.info("📋 查询所有任务")
                    query = """
                        SELECT t.*, vs.name as stream_name,
                               COALESCE(amc.name, vsac.template_name) as algorithm_name
                        FROM stream_analysis_tasks t
                        LEFT JOIN video_streams vs ON t.stream_id = vs.id
                        LEFT JOIN ai_model_configs amc ON t.algorithm_config_id = amc.id
                        LEFT JOIN video_stream_algorithm_configs vsac ON t.algorithm_config_id = vsac.id
                        ORDER BY t.priority DESC, t.created_at
                    """
                    results = await fetch(conn, query)
                    logger.info(f"📊 SQL查询返回 {len(results)} 行数据")
                
                # 转换为字典列表
                tasks = []
                logger.debug(f"开始转换 {len(results)} 行数据...")
                for idx, row in enumerate(results):
                    try:
                        task_dict = dict(row)

                        # 转换UUID字段为字符串
                        for uuid_field in ['id', 'stream_id', 'algorithm_config_id', 'created_by', 'updated_by']:
                            if task_dict.get(uuid_field):
                                task_dict[uuid_field] = str(task_dict[uuid_field])

                        # 转换时间字段为ISO格式字符串
                        for time_field in ['created_at', 'updated_at', 'last_run_at', 'next_run_at']:
                            if task_dict.get(time_field):
                                task_dict[time_field] = task_dict[time_field].isoformat()

                        # 转换JSON字段
                        import json
                        for json_field in ['time_config', 'roi_config']:
                            if task_dict.get(json_field):
                                if isinstance(task_dict[json_field], str):
                                    try:
                                        task_dict[json_field] = json.loads(task_dict[json_field])
                                    except Exception as e:
                                        logger.warning(f"JSON解析失败 {json_field}: {e}")
                                        task_dict[json_field] = {}
                                elif isinstance(task_dict[json_field], dict):
                                    # 已经是dict，不需要转换
                                    pass
                                else:
                                    logger.warning(f"未知类型 {json_field}: {type(task_dict[json_field])}")
                                    task_dict[json_field] = {}

                        # 添加运行状态字段（根据status判断）
                        task_dict['is_running'] = task_dict.get('status') == 'running'
                        task_dict['should_run_now'] = task_dict.get('status') == 'scheduled'

                        tasks.append(task_dict)
                        logger.debug(f"  ✅ 任务#{idx+1}: {task_dict.get('id', 'N/A')[:8]}... 转换成功")
                    except Exception as e:
                        logger.error(f"  ❌ 任务#{idx+1} 转换失败: {e}", exc_info=True)
                        continue

                logger.info(f"✅ 数据转换完成: {len(tasks)}/{len(results)} 个任务成功")
                if tasks:
                    logger.info(f"   示例任务字段: {list(tasks[0].keys())}")
                return tasks
                
            finally:
                await conn.close()
        except ImportError as e:
            # 数据库驱动导入失败（生产环境常见问题）
            logger.error(f"数据库驱动导入失败: {e}", exc_info=True)
            logger.warning("⚠️ psycopg库未正确安装，返回空任务列表")
            return []
        except Exception as e:
            logger.error(f"从数据库获取任务列表失败: {e}", exc_info=True)
            # 如果数据库查询失败，返回内存中的数据作为备用
            tasks = list(self.tasks.values())
            if stream_id:
                tasks = [task for task in tasks if task.get('stream_id') == stream_id]
            logger.info(f"使用内存数据，返回 {len(tasks)} 个任务")
            return tasks
    
    async def create_task(self, stream_id: str, algorithm_config_id: str, task_name: str,
                         time_config: Dict, roi_config: Dict, priority: int = 1,
                         confidence_threshold: float = 0.7, analysis_interval: int = 10,
                         auto_recover: bool = True) -> Optional[str]:
        """
        创建新任务(正确流程)

        参数:
            algorithm_config_id: 前端选择的AI算法ID,即 ai_model_configs.id

        流程:
            1. 在 video_stream_algorithm_configs 表中创建配置记录
            2. 在 stream_analysis_tasks 表中创建任务记录
        """
        try:
            import uuid
            from datetime import datetime
            import json
            # asyncpg已替换为psycopg 3
            from config.settings import DatabaseConfig

            # 生成新的ID
            stream_algorithm_config_id = str(uuid.uuid4())  # video_stream_algorithm_configs 表的ID
            task_id = str(uuid.uuid4())  # stream_analysis_tasks 表的ID

            # 连接数据库
            conn = await get_async_connection()
            try:
                # 1. 从 ai_model_configs 获取算法信息
                ai_model_row = await fetchrow(conn, """
                    SELECT name, description FROM ai_model_configs WHERE id = %s
                """, algorithm_config_id)

                if not ai_model_row:
                    raise ValueError(f"未找到AI算法配置: {algorithm_config_id}")

                algorithm_name = ai_model_row[0]  # fetchrow返回元组，第一列是name

                # 2. 检查是否已存在相同的配置（upsert逻辑）
                existing_config_row = await fetchrow(conn, """
                    SELECT id FROM video_stream_algorithm_configs
                    WHERE stream_id = %s AND template_id = %s
                """, stream_id, algorithm_config_id)

                current_time = beijing_now()

                if existing_config_row:
                    # 已存在，使用现有的ID，并更新配置
                    stream_algorithm_config_id = existing_config_row[0]
                    await conn.execute("""
                        UPDATE video_stream_algorithm_configs
                        SET priority = %s, confidence_threshold = %s,
                            is_active = true, updated_at = %s
                        WHERE id = %s
                    """, (priority, confidence_threshold, current_time, stream_algorithm_config_id))
                    await conn.commit()
                    logger.info(f"已更新视频流算法配置: {stream_algorithm_config_id}, 算法={algorithm_name}")
                else:
                    # 不存在，创建新配置
                    await conn.execute("""
                        INSERT INTO video_stream_algorithm_configs (
                            id, stream_id, template_id, template_name, priority,
                            confidence_threshold, is_active, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (stream_algorithm_config_id, stream_id, algorithm_config_id,
                        algorithm_name, priority, confidence_threshold, True, current_time, current_time))
                    await conn.commit()
                    logger.info(f"已创建视频流算法配置: {stream_algorithm_config_id}, 算法={algorithm_name}")

                # 获取视频流名称，用于生成任务名称
                stream_row = await fetchrow(conn, """
                    SELECT name FROM video_streams WHERE id = %s
                """, stream_id)

                stream_name = stream_row[0] if stream_row else f"流_{stream_id[:8]}"  # fetchrow返回元组，第一列是name

                # 生成正确的任务名称格式：[流名称]_[算法名称]_分析任务
                formatted_task_name = f"{stream_name}_{algorithm_name}_分析任务"
                logger.info(f"生成任务名称: {formatted_task_name}")

                # 3. 检查是否已存在同样的任务（upsert逻辑）
                existing_task_row = await fetchrow(conn, """
                    SELECT id FROM stream_analysis_tasks
                    WHERE stream_id = %s AND algorithm_config_id = %s
                """, stream_id, stream_algorithm_config_id)

                is_update = False
                if existing_task_row:
                    # 已存在，更新任务配置
                    task_id = existing_task_row[0]
                    await conn.execute("""
                        UPDATE stream_analysis_tasks
                        SET task_name = %s, time_config = %s, roi_config = %s,
                            priority = %s, confidence_threshold = %s,
                            analysis_interval = %s, auto_recover = %s,
                            status = 'enabled', is_active = true, updated_at = %s
                        WHERE id = %s
                    """, (formatted_task_name, json.dumps(time_config), json.dumps(roi_config),
                        priority, confidence_threshold, analysis_interval, auto_recover,
                        current_time, task_id))
                    await conn.commit()
                    is_update = True
                    logger.info(f"任务配置已更新: {task_id}, 使用算法配置={stream_algorithm_config_id}")
                else:
                    # 不存在，创建新任务
                    await conn.execute("""
                        INSERT INTO stream_analysis_tasks (
                            id, stream_id, algorithm_config_id, task_name, status,
                            is_active, time_config, roi_config, priority,
                            confidence_threshold, analysis_interval, auto_recover, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (task_id, stream_id, stream_algorithm_config_id, formatted_task_name, 'enabled',
                        True, json.dumps(time_config), json.dumps(roi_config), priority,
                        confidence_threshold, analysis_interval, auto_recover, current_time))
                    await conn.commit()
                    logger.info(f"任务已持久化到数据库: {task_id}, 使用算法配置={stream_algorithm_config_id}")

            finally:
                await conn.close()

            # 添加到内存
            task_data = {
                "id": task_id,
                "stream_id": stream_id,
                "algorithm_config_id": stream_algorithm_config_id,
                "task_name": formatted_task_name,  # 使用格式化后的任务名称
                "status": "enabled",
                "is_active": True,
                "is_running": True,  # 创建任务后立即启动视频流分析
                "should_run_now": False,
                "algorithm_name": algorithm_name,
                "stream_name": stream_name,  # 添加流名称字段
                "time_config": time_config,
                "roi_config": roi_config,
                "priority": priority,
                "confidence_threshold": confidence_threshold,
                "analysis_interval": analysis_interval,
                "auto_recover": auto_recover,
                "last_run_at": None,
                "created_at": datetime.now().isoformat()
            }
            self.tasks[task_id] = task_data

            operation = "更新" if is_update else "创建"
            operation_type = "updated" if is_update else "created"
            logger.info(f"{operation}任务成功: {task_id}, 任务名称={formatted_task_name}, AI算法={algorithm_name}")

            # 创建/更新任务后立即启动视频流分析
            try:
                from services.stream_analysis_service import stream_analysis_service

                # 检查该流是否已有运行中的分析任务
                stream_status = await stream_analysis_service.get_stream_analysis_status(stream_id)

                if stream_status.get('status') == 'running':
                    logger.info(f"视频流 {stream_id} 已有运行中的分析任务,跳过启动")
                else:
                    # 启动实时流分析
                    result = await stream_analysis_service.start_stream_analysis(stream_id)
                    logger.info(f"已启动视频流实时分析: stream_id={stream_id}, result={result}")

            except Exception as e:
                logger.warning(f"启动视频流分析失败: {e}")
                # 不影响任务创建/更新,仅记录警告
                # 任务状态保持为enabled,可以稍后重新启动

            # 返回task_id和操作类型
            return {"task_id": task_id, "operation_type": operation_type}

        except Exception as e:
            # 其他错误
            logger.error(f"创建/更新任务失败: {e}")
            raise  # 重新抛出异常,让调用方能够看到详细错误
    
    async def enable_task(self, task_id: str) -> bool:
        """启用任务（启用即运行）"""
        try:
            # asyncpg已替换为psycopg 3
            from config.settings import DatabaseConfig

            # 如果内存中没有任务,从数据库加载
            if task_id not in self.tasks:
                tasks = await self.get_task_list()
                for task in tasks:
                    if task['id'] == task_id:
                        self.tasks[task_id] = task
                        logger.info(f"从数据库加载任务到内存: {task_id}")
                        break

            if task_id in self.tasks:
                # 更新内存中的状态
                self.tasks[task_id]["is_active"] = True
                self.tasks[task_id]["status"] = "enabled"
                self.tasks[task_id]["is_running"] = True  # 启用即运行
                self.tasks[task_id]["should_run_now"] = False  # 已经在运行,不需要待运行状态

                # 更新数据库
                conn = await get_async_connection()
                try:
                    current_time = beijing_now()
                    await conn.execute("""
                        UPDATE stream_analysis_tasks
                        SET status = 'enabled', is_active = true, updated_at = %s
                        WHERE id = %s
                    """, (current_time, task_id))
                    await conn.commit()
                    logger.info(f"启用任务并更新数据库: {task_id}")
                finally:
                    await conn.close()

                # 新增: 初始化任务统计
                if task_id not in self.task_stats:
                    self.task_stats[task_id] = TaskStats(
                        task_id=task_id,
                        start_time=time.time(),
                        last_heartbeat=time.time()
                    )
                else:
                    # 重置统计(重新启用时)
                    self.task_stats[task_id].start_time = time.time()
                    self.task_stats[task_id].last_heartbeat = time.time()

                self.total_tasks_started += 1

                # 启动实际的视频流分析
                stream_id = self.tasks[task_id]["stream_id"]
                try:
                    from services.stream_analysis_service import stream_analysis_service

                    # 检查该流是否已有运行中的分析任务
                    stream_status = await stream_analysis_service.get_stream_analysis_status(stream_id)

                    if stream_status.get('status') == 'running':
                        logger.info(f"视频流 {stream_id} 已有运行中的分析任务,跳过启动")
                    else:
                        # 启动实时流分析
                        result = await stream_analysis_service.start_stream_analysis(stream_id)
                        logger.info(f"已启动视频流实时分析: stream_id={stream_id}, result={result}")

                except Exception as e:
                    logger.warning(f"启动视频流分析失败: {e}")
                    # 记录错误到统计
                    if task_id in self.task_stats:
                        self.task_stats[task_id].error_count += 1
                        self.task_stats[task_id].last_error = str(e)
                    self.total_tasks_failed += 1

                return True
            return False
        except Exception as e:
            logger.error(f"启用任务失败: {e}")
            return False
    
    async def disable_task(self, task_id: str) -> bool:
        """停用任务（停用即停止运行）"""
        try:
            # asyncpg已替换为psycopg 3
            from config.settings import DatabaseConfig

            # 如果内存中没有任务,从数据库加载
            if task_id not in self.tasks:
                tasks = await self.get_task_list()
                for task in tasks:
                    if task['id'] == task_id:
                        self.tasks[task_id] = task
                        logger.info(f"从数据库加载任务到内存: {task_id}")
                        break

            if task_id in self.tasks:
                # 停止实际的视频流分析
                stream_id = self.tasks[task_id]["stream_id"]
                try:
                    from services.stream_analysis_service import stream_analysis_service

                    # 停止实时流分析
                    result = await stream_analysis_service.stop_stream_analysis(stream_id)
                    logger.info(f"已停止视频流实时分析: stream_id={stream_id}, result={result}")

                except Exception as e:
                    logger.warning(f"停止视频流分析失败: {e}")
                    # 不影响任务停用状态,仅记录警告

                # 更新内存中的状态
                self.tasks[task_id]["is_active"] = False
                self.tasks[task_id]["status"] = "disabled"
                self.tasks[task_id]["is_running"] = False  # 停用即停止运行
                self.tasks[task_id]["should_run_now"] = False  # 清除待运行状态

                # 更新数据库
                conn = await get_async_connection()
                try:
                    current_time = beijing_now()
                    await conn.execute("""
                        UPDATE stream_analysis_tasks
                        SET status = 'disabled', is_active = false, updated_at = %s
                        WHERE id = %s
                    """, (current_time, task_id))
                    await conn.commit()
                    logger.info(f"停用任务并更新数据库: {task_id}")
                finally:
                    await conn.close()

                # 新增: 更新统计
                self.total_tasks_stopped += 1
                if task_id in self.task_stats:
                    # 保留统计信息,但不更新心跳
                    pass

                return True
            return False
        except Exception as e:
            logger.error(f"停用任务失败: {e}")
            return False
    
    async def start_analysis(self, task_id: str) -> bool:
        """启动任务分析"""
        try:
            if task_id in self.tasks and self.tasks[task_id]["is_active"]:
                self.tasks[task_id]["is_running"] = True
                logger.info(f"启动任务分析: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"启动任务分析失败: {e}")
            return False
    
    async def stop_analysis(self, task_id: str) -> bool:
        """停止任务分析"""
        try:
            if task_id in self.tasks:
                self.tasks[task_id]["is_running"] = False
                logger.info(f"停止任务分析: {task_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"停止任务分析失败: {e}")
            return False
    
    async def start_task_analysis(self, task_id: str) -> Dict[str, Any]:
        """启动任务分析（API兼容方法）"""
        success = await self.start_analysis(task_id)
        return {"success": success}
    
    async def stop_task_analysis(self, task_id: str) -> Dict[str, Any]:
        """停止任务分析（API兼容方法）"""
        success = await self.stop_analysis(task_id)
        return {"success": success}
    
    async def delete_task(self, task_id: str) -> bool:
        """删除任务（同时删除内存和数据库中的数据）"""
        try:
            # asyncpg已替换为psycopg 3
            from config.settings import DatabaseConfig

            # 如果内存中没有任务,从数据库加载
            if task_id not in self.tasks:
                tasks = await self.get_task_list()
                for task in tasks:
                    if task['id'] == task_id:
                        self.tasks[task_id] = task
                        logger.info(f"从数据库加载任务到内存: {task_id}")
                        break

            if task_id not in self.tasks:
                logger.warning(f"任务不存在: {task_id}")
                return False

            # 1. 先停止视频流分析
            stream_id = self.tasks[task_id].get("stream_id")
            if stream_id:
                try:
                    from services.stream_analysis_service import stream_analysis_service
                    result = await stream_analysis_service.stop_stream_analysis(stream_id)
                    logger.info(f"已停止视频流分析: stream_id={stream_id}, result={result}")
                except Exception as e:
                    logger.warning(f"停止视频流分析失败: {e}")

            # 2. 停止任务分析（内存状态）
            await self.stop_analysis(task_id)

            # 3. 从数据库删除任务记录
            conn = await get_async_connection()
            try:
                # 删除 stream_analysis_tasks 表中的记录
                await conn.execute("""
                    DELETE FROM stream_analysis_tasks WHERE id = %s
                """, (task_id,))
                await conn.commit()
                logger.info(f"已从数据库删除任务记录: {task_id}")

                # 获取并删除关联的 video_stream_algorithm_configs 记录
                algorithm_config_id = self.tasks[task_id].get("algorithm_config_id")
                if algorithm_config_id:
                    await conn.execute("""
                        DELETE FROM video_stream_algorithm_configs WHERE id = %s
                    """, (algorithm_config_id,))
                    await conn.commit()
                    logger.info(f"已从数据库删除算法配置记录: {algorithm_config_id}")

            finally:
                await conn.close()

            # 4. 从内存中删除任务
            del self.tasks[task_id]
            logger.info(f"任务删除成功（内存+数据库）: {task_id}")

            return True

        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False
    
    async def _get_algorithm_name(self, algorithm_config_id: str) -> str:
        """从数据库获取算法名称"""
        try:
            # 导入数据库连接
            # asyncpg已替换为psycopg 3
            from config.settings import DatabaseConfig

            conn = await get_async_connection()
            try:
                # 查询算法配置
                result = await fetchrow(conn, 
                    "SELECT template_name FROM video_stream_algorithm_configs WHERE id = %s",
                    algorithm_config_id
                )
                if result:
                    return result['template_name']
                else:
                    logger.warning(f"未找到算法配置ID: {algorithm_config_id}")
                    return "未知算法"
            finally:
                await conn.close()
        except Exception as e:
            logger.error(f"获取算法名称失败: {e}")
            return "未知算法"

    # ==================== 统计和监控方法（委托给 helpers.task_statistics_helper） ====================

    def get_task_stats(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务统计信息 - 委托给 helpers.task_statistics_helper"""
        return _get_task_stats_helper(task_id, self.task_stats, self.tasks)

    def get_all_tasks_stats(self) -> List[Dict[str, Any]]:
        """获取所有任务的统计信息 - 委托给 helpers.task_statistics_helper"""
        return _get_all_tasks_stats_helper(self.task_stats, self.tasks)

    def get_manager_stats(self) -> Dict[str, Any]:
        """获取任务管理器整体统计 - 委托给 helpers.task_statistics_helper"""
        return _get_manager_stats_helper(
            self.tasks, self.task_stats,
            self.total_tasks_created, self.total_tasks_started,
            self.total_tasks_stopped, self.total_tasks_failed,
            self.initialized
        )

    def update_task_heartbeat(self, task_id: str, frames_processed: int = None,
                            alerts_generated: int = None, processing_time_ms: float = None):
        """更新任务心跳和统计 - 委托给 helpers.task_statistics_helper"""
        _update_task_heartbeat_helper(
            self.task_stats, task_id,
            frames_processed, alerts_generated, processing_time_ms
        )

    def record_task_error(self, task_id: str, error_message: str):
        """记录任务错误 - 委托给 helpers.task_statistics_helper"""
        _record_task_error_helper(self.task_stats, task_id, error_message)


# 创建全局实例
stream_task_manager = StreamTaskManager()