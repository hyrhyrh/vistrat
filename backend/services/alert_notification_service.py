"""
告警通知服务
支持定时汇总通知和即时严重告警通知
优化方案10: 告警通知系统
"""

import asyncio
import logging
import time
import re
import os
from datetime import datetime, time as dt_time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from collections import deque

import redis
import redis.asyncio as aioredis
from pytz import timezone
from sqlalchemy import select

from .notification_adapters import (
    NotificationAdapter,
    NotificationMessage,
    NotificationSeverity,
    WeChatWorkAdapter
)
from database.connection import DatabaseManager
from models.system_config import SystemConfigDB
from agent.llm.claude_es_client import ClaudeESClient
from config.settings import ElasticsearchConfig

logger = logging.getLogger(__name__)


def clean_ai_response(text: str) -> str:
    """
    清理AI响应中的工具调用标记和其他内部信息

    Args:
        text: 原始AI响应文本

    Returns:
        清理后的文本，只保留最终分析报告
    """
    if not text:
        return text

    # 1. 移除工具调用开始标记及其内容（包含完整的JSON）
    # 匹配 __TOOL_CALL_START__{...}__TOOL_CALL_START__
    text = re.sub(r'__TOOL_CALL_START__\{.*?\}__TOOL_CALL_START__', '', text, flags=re.DOTALL)

    # 2. 移除工具调用结果标记及其内容（包含完整的JSON）
    # 匹配 __TOOL_CALL_RESULT__{...}__TOOL_CALL_RESULT__
    text = re.sub(r'__TOOL_CALL_RESULT__\{.*?\}__TOOL_CALL_RESULT__', '', text, flags=re.DOTALL)

    # 3. 移除可能残留的单个标记（没有配对的）
    text = re.sub(r'__TOOL_CALL_START__', '', text)
    text = re.sub(r'__TOOL_CALL_RESULT__', '', text)
    text = re.sub(r'__TOOL_CALL_END__', '', text)

    # 4. 移除"我需要修正查询语句"等工具调用相关的说明文本（但不删除后面的内容）
    # 只移除这一行，保留后续的分析报告
    text = re.sub(r'我需要修正查询语句.*?\n', '\n', text)
    text = re.sub(r'让我重新执行查询.*?\n', '\n', text)

    # 5. 清理多余的空行（超过2个连续换行）
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 6. 去掉首尾空白
    text = text.strip()

    return text


@dataclass
class AlertRecord:
    """告警记录"""
    alert_type: str  # 告警类型
    severity: NotificationSeverity  # 严重级别
    message: str  # 告警消息
    timestamp: float  # 时间戳
    source: str = "系统监控"  # 来源
    extra_data: Optional[Dict[str, Any]] = None  # 额外数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['severity'] = self.severity.value
        return result


class AlertNotificationService:
    """
    告警通知服务

    功能:
    1. 定时AI智能分析通知(每天11:30和17:30,调用Claude分析今日告警)
    2. 即时严重告警通知(可配置)
    3. 告警缓存和去重
    4. 多通知渠道支持
    """

    def __init__(self):
        self.adapters: List[NotificationAdapter] = []
        self.alert_buffer: deque = deque(maxlen=1000)  # 告警缓冲区,最多1000条

        # 配置参数
        self.enable_scheduled_notification = True  # 启用定时通知
        self.enable_instant_notification = True  # 启用即时通知

        # 🔧 修正：使用北京时间（Asia/Shanghai）
        self.timezone = timezone('Asia/Shanghai')
        self.scheduled_times = [
            dt_time(11, 30),  # 北京时间 上午11:30
            dt_time(17, 30)   # 北京时间 下午17:30
        ]

        # 运行状态
        self._running = False
        self._scheduler_task = None

        # 🆕 Redis分布式锁（多worker环境必须）
        self.redis_client: Optional[aioredis.Redis] = None
        self.lock_key_prefix = "alert_notification:scheduled_lock:"
        self.lock_timeout = 300  # 锁超时5分钟（防止死锁）

        # 统计信息
        self.total_alerts_received = 0
        self.total_notifications_sent = 0
        self.total_scheduled_notifications = 0
        self.total_instant_notifications = 0
        self.last_scheduled_time = None
        self.last_instant_time = None

    async def _load_configuration(self):
        """从数据库加载配置"""
        async with DatabaseManager.get_session() as session:
            try:
                # 查询企业微信webhook配置
                result = await session.execute(
                    select(SystemConfigDB).where(SystemConfigDB.param_code == 'qywx_webhook')
                )
                config = result.scalar_one_or_none()

                if config:
                    self.qywx_webhook_url = config.param_val
                    logger.info(f"✓ 已加载企业微信Webhook配置")
                else:
                    logger.warning("⚠️ 未找到企业微信Webhook配置(param_code='qywx_webhook')")
                    self.qywx_webhook_url = None

                # 查询其他配置(可选)
                # 例如: 定时通知开关、即时通知开关等

            except Exception as e:
                logger.error(f"加载配置失败: {e}", exc_info=True)
                self.qywx_webhook_url = None

    async def initialize(self):
        """初始化告警通知服务"""
        try:
            logger.info("=" * 60)
            logger.info("初始化告警通知服务...")

            # 加载配置
            await self._load_configuration()

            # 🆕 初始化Redis连接（用于分布式锁）
            try:
                redis_host = os.getenv('REDIS_HOST', 'redis')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_db = int(os.getenv('REDIS_DB', 2))
                redis_password = os.getenv('REDIS_PASSWORD', '')

                # 创建异步Redis客户端（用于告警去重和分布式锁）
                self.redis_client = aioredis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password or None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # 测试异步连接
                await self.redis_client.ping()

                logger.info(f"✓ Redis异步连接成功 ({redis_host}:{redis_port}/{redis_db})")
            except Exception as e:
                logger.error(f"❌ Redis连接失败: {e}")
                logger.warning("⚠️ 将使用单机模式，多worker环境可能出现重复通知")
                self.redis_client = None

            # 初始化通知适配器
            await self._initialize_adapters()

            logger.info("✅ 告警通知服务初始化完成")
            logger.info(f"- 定时通知: {'启用' if self.enable_scheduled_notification else '禁用'}")
            logger.info(f"- 即时通知: {'启用' if self.enable_instant_notification else '禁用'}")
            logger.info(f"- 通知时间(北京时间): {', '.join(t.strftime('%H:%M') for t in self.scheduled_times)}")
            logger.info(f"- 通知渠道数: {len(self.adapters)}")
            logger.info(f"- 分布式锁: {'启用' if self.redis_client else '禁用'}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"告警通知服务初始化失败: {e}", exc_info=True)
            raise

    async def _initialize_adapters(self):
        """初始化通知适配器"""
        # 初始化企业微信适配器
        if self.qywx_webhook_url:
            try:
                wechat_adapter = WeChatWorkAdapter(self.qywx_webhook_url)
                self.adapters.append(wechat_adapter)
                logger.info("✓ 企业微信通知适配器已加载")
            except Exception as e:
                logger.error(f"企业微信适配器初始化失败: {e}")

        # 可扩展: 添加其他通知适配器(钉钉、邮件等)

        if not self.adapters:
            logger.warning("⚠️ 未配置任何通知适配器,告警通知功能将不可用")

    async def start(self):
        """启动告警通知服务"""
        if self._running:
            logger.warning("告警通知服务已在运行")
            return

        self._running = True

        # 启动定时调度器
        if self.enable_scheduled_notification:
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("✅ 定时告警通知调度器已启动")

        logger.info("✅ 告警通知服务已启动")

    async def stop(self):
        """停止告警通知服务"""
        self._running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 告警通知服务已停止")

    async def _scheduler_loop(self):
        """定时调度循环"""
        logger.info(f"定时通知调度器启动,通知时间(北京时间): {', '.join(t.strftime('%H:%M') for t in self.scheduled_times)}")

        while self._running:
            try:
                # 🔧 修正：使用北京时间
                now_beijing = datetime.now(self.timezone)
                current_time = now_beijing.time()

                # 检查是否到达定时通知时间
                for scheduled_time in self.scheduled_times:
                    # 时间匹配(允许1分钟误差)
                    time_diff = abs(
                        (current_time.hour * 60 + current_time.minute) -
                        (scheduled_time.hour * 60 + scheduled_time.minute)
                    )

                    if time_diff <= 1:
                        # 🆕 使用Redis分布式锁，确保只有一个worker执行
                        lock_acquired = await self._try_acquire_scheduled_lock(scheduled_time)
                        if not lock_acquired:
                            logger.info(f"⏭️ 跳过通知发送（其他worker已执行）")
                            continue

                        # 发送定时汇总通知
                        await self._send_scheduled_summary()
                        self.last_scheduled_time = time.time()

                        # 等待2分钟,避免重复触发
                        await asyncio.sleep(120)
                        break

                # 每分钟检查一次
                await asyncio.sleep(60)

            except Exception as e:
                logger.error(f"定时调度器异常: {e}", exc_info=True)
                await asyncio.sleep(60)

    async def _try_acquire_scheduled_lock(self, scheduled_time: dt_time) -> bool:
        """
        尝试获取定时通知的分布式锁（防止多worker重复执行）

        Args:
            scheduled_time: 定时时间

        Returns:
            是否成功获取锁
        """
        if not self.redis_client:
            # 没有Redis连接，降级为单机模式（可能重复）
            logger.warning("⚠️ Redis未连接，无法使用分布式锁")
            return True

        try:
            # 生成锁的key（按日期+时间，确保每天每个时间点只执行一次）
            now_beijing = datetime.now(self.timezone)
            lock_key = f"{self.lock_key_prefix}{now_beijing.strftime('%Y%m%d')}:{scheduled_time.strftime('%H%M')}"

            # 尝试获取锁（NX=只在不存在时设置，EX=过期时间）
            lock_acquired = await self.redis_client.set(
                lock_key,
                f"worker-{os.getpid()}",  # 记录是哪个worker获取的锁
                nx=True,  # 只在key不存在时设置
                ex=self.lock_timeout  # 超时自动释放（防止死锁）
            )

            if lock_acquired:
                logger.info(f"🔒 成功获取分布式锁: {lock_key}")
                return True
            else:
                logger.debug(f"🔓 锁已被其他worker占用: {lock_key}")
                return False

        except Exception as e:
            logger.error(f"❌ 获取分布式锁失败: {e}")
            # 锁获取失败，保守起见返回False（避免重复执行）
            return False

    async def _send_scheduled_summary(self):
        """发送定时汇总通知（调用AI分析助手生成专业日报）"""
        try:
            logger.info("📊 开始生成AI视频分析预警日报...")

            # 获取Elasticsearch配置
            es_url = ElasticsearchConfig.get_es_url()

            # 创建Claude ES客户端
            claude_client = ClaudeESClient(es_url=es_url)

            # 读取日报生成提示词
            prompt_file = "prompts/daily_alert_report_prompt.txt"
            try:
                with open(prompt_file, 'r', encoding='utf-8') as f:
                    daily_report_prompt = f.read()
                logger.info(f"✅ 成功加载日报提示词模板: {prompt_file}")
            except FileNotFoundError:
                logger.warning(f"⚠️ 日报提示词文件不存在: {prompt_file}，使用默认问题")
                daily_report_prompt = "请生成今日AI视频分析预警数据的详细日报，包括告警数量、类型分布、时段分布、区域分布、风险分析和行动建议。"

            # 构造完整的分析问题
            today_str = datetime.now(self.timezone).strftime("%Y-%m-%d")
            question = f"{daily_report_prompt}\n\n请为 {today_str} 生成AI视频分析预警日报。"

            logger.info(f"正在调用AI分析助手生成日报 (日期: {today_str})...")

            # 调用非流式分析方法
            ai_response = await claude_client.analyze(question=question)

            if not ai_response or not ai_response.strip():
                logger.warning("AI分析助手返回空响应，跳过通知")
                return

            logger.info(f"AI日报生成完成，原始响应长度: {len(ai_response)} 字符")
            logger.debug(f"原始AI响应前500字符:\n{ai_response[:500]}")

            # 清理AI响应，移除工具调用标记等内部信息
            cleaned_response = clean_ai_response(ai_response)

            if not cleaned_response or not cleaned_response.strip():
                logger.warning("清理后AI响应为空，跳过通知")
                logger.debug(f"清理前内容:\n{ai_response}")
                return

            logger.info(f"清理后响应长度: {len(cleaned_response)} 字符")
            logger.debug(f"清理后响应前500字符:\n{cleaned_response[:500]}")

            # 在消息末尾添加预警报表链接
            report_url = "http://<INTERNAL_HOST>:3009/daily-alerts-report"
            cleaned_response = f"{cleaned_response}\n\n---\n\n详细预警图片链接如下：\n{report_url}"

            # 创建通知消息
            message = NotificationMessage(
                title=f"📊 AI视频分析预警日报 ({today_str})",
                content=cleaned_response,
                severity=NotificationSeverity.INFO,
                timestamp=time.time(),
                source="AI分析助手"
            )

            # 发送到所有适配器
            success_count = 0
            for adapter in self.adapters:
                if await adapter.send(message):
                    success_count += 1

            if success_count > 0:
                self.total_scheduled_notifications += 1
                self.total_notifications_sent += success_count
                logger.info(f"✅ AI视频分析预警日报发送成功 ({success_count}/{len(self.adapters)}个渠道)")
            else:
                logger.error("❌ AI视频分析预警日报发送失败(所有渠道)")

        except Exception as e:
            logger.error(f"发送AI视频分析预警日报失败: {e}", exc_info=True)

    def _build_summary_content(self, severity_counts: Dict, alert_type_counts: Dict) -> str:
        """构建汇总内容"""
        content_lines = []

        # 严重级别统计
        content_lines.append("**告警级别统计**:")
        content_lines.append(f"- 🚨 严重: {severity_counts.get(NotificationSeverity.CRITICAL, 0)}条")
        content_lines.append(f"- ❌ 错误: {severity_counts.get(NotificationSeverity.ERROR, 0)}条")
        content_lines.append(f"- ⚠️ 警告: {severity_counts.get(NotificationSeverity.WARNING, 0)}条")
        content_lines.append(f"- ℹ️ 信息: {severity_counts.get(NotificationSeverity.INFO, 0)}条")

        # 告警类型统计(Top 5)
        if alert_type_counts:
            content_lines.append("\n**告警类型分布(Top 5)**:")
            sorted_types = sorted(alert_type_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            for alert_type, count in sorted_types:
                content_lines.append(f"- {alert_type}: {count}次")

        # 系统建议
        critical_count = severity_counts.get(NotificationSeverity.CRITICAL, 0)
        error_count = severity_counts.get(NotificationSeverity.ERROR, 0)

        if critical_count > 0:
            content_lines.append(f"\n⚠️ **警告**: 检测到{critical_count}条严重告警,请立即处理!")
        elif error_count > 5:
            content_lines.append(f"\n💡 **建议**: 检测到{error_count}条错误,建议检查系统状态")

        return "\n".join(content_lines)

    async def record_alert(self, alert: AlertRecord):
        """
        记录告警

        Args:
            alert: 告警记录
        """
        try:
            self.total_alerts_received += 1
            self.alert_buffer.append(alert)

            logger.debug(f"记录告警: [{alert.severity.value}] {alert.alert_type} - {alert.message}")

            # 如果是严重告警且启用即时通知,立即发送
            if (
                self.enable_instant_notification and
                alert.severity in [NotificationSeverity.CRITICAL, NotificationSeverity.ERROR]
            ):
                await self._send_instant_alert(alert)

        except Exception as e:
            logger.error(f"记录告警失败: {e}", exc_info=True)

    async def _send_instant_alert(self, alert: AlertRecord):
        """
        发送即时告警（带去重和限流机制）

        Args:
            alert: 告警记录
        """
        try:
            # 🔧 即时告警去重：相同告警类型在30分钟内只发送一次（跨所有worker）
            dedup_key = f"instant_alert:dedup:{alert.alert_type}:{alert.severity.value}"
            dedup_window = 1800  # 30分钟去重窗口

            if self.redis_client:
                try:
                    # 检查是否在去重窗口内
                    if await self.redis_client.exists(dedup_key):
                        logger.info(f"⏭️ 跳过重复告警（{dedup_window}秒内已发送）: {alert.alert_type}")
                        return

                    # 设置去重标记（带过期时间）
                    await self.redis_client.setex(dedup_key, dedup_window, "1")
                except Exception as redis_err:
                    logger.warning(f"Redis去重检查失败，继续发送告警: {redis_err}")

            # 创建通知消息
            message = NotificationMessage(
                title=f"即时告警: {alert.alert_type}",
                content=alert.message,
                severity=alert.severity,
                timestamp=alert.timestamp,
                source=alert.source,
                extra_data=alert.extra_data
            )

            # 发送到所有适配器
            success_count = 0
            for adapter in self.adapters:
                if await adapter.send(message):
                    success_count += 1

            if success_count > 0:
                self.total_instant_notifications += 1
                self.total_notifications_sent += success_count
                self.last_instant_time = time.time()
                logger.info(f"✅ 即时告警发送成功: {alert.alert_type} ({success_count}/{len(self.adapters)}个渠道)")
            else:
                logger.error(f"❌ 即时告警发送失败: {alert.alert_type}")

        except Exception as e:
            logger.error(f"发送即时告警失败: {e}", exc_info=True)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        adapter_stats = []
        for i, adapter in enumerate(self.adapters):
            stats = adapter.get_statistics()
            stats['adapter_type'] = adapter.__class__.__name__
            adapter_stats.append(stats)

        return {
            'service_status': 'running' if self._running else 'stopped',
            'total_alerts_received': self.total_alerts_received,
            'total_notifications_sent': self.total_notifications_sent,
            'total_scheduled_notifications': self.total_scheduled_notifications,
            'total_instant_notifications': self.total_instant_notifications,
            'alert_buffer_size': len(self.alert_buffer),
            'last_scheduled_time': self.last_scheduled_time,
            'last_instant_time': self.last_instant_time,
            'adapters_count': len(self.adapters),
            'adapters': adapter_stats,
            'configuration': {
                'enable_scheduled_notification': self.enable_scheduled_notification,
                'enable_instant_notification': self.enable_instant_notification,
                'scheduled_times': [t.strftime('%H:%M') for t in self.scheduled_times]
            }
        }

    async def send_test_notification(self):
        """发送测试通知"""
        try:
            message = NotificationMessage(
                title="测试通知",
                content="这是一条测试通知,用于验证告警通知系统是否正常工作。\n\n如果您收到此消息,说明通知功能配置正确。",
                severity=NotificationSeverity.INFO,
                timestamp=time.time(),
                source="告警通知服务",
                extra_data={
                    '测试时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    '服务状态': '运行中' if self._running else '已停止'
                }
            )

            success_count = 0
            for adapter in self.adapters:
                if await adapter.send(message):
                    success_count += 1

            return success_count > 0

        except Exception as e:
            logger.error(f"发送测试通知失败: {e}", exc_info=True)
            return False

    async def send_daily_report(self, report_content: str, title: str = "每日告警统计报表"):
        """
        发送自定义报表到企业微信

        Args:
            report_content: 报表内容(Markdown格式)
            title: 报表标题

        Returns:
            是否发送成功
        """
        try:
            message = NotificationMessage(
                title=title,
                content=report_content,
                severity=NotificationSeverity.INFO,
                timestamp=time.time(),
                source="告警统计服务",
                extra_data={
                    '生成时间': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    '报表类型': '每日告警统计'
                }
            )

            success_count = 0
            for adapter in self.adapters:
                if await adapter.send(message):
                    success_count += 1

            if success_count > 0:
                logger.info(f"✅ 告警统计报表发送成功 ({success_count}/{len(self.adapters)}个渠道)")
                return True
            else:
                logger.error("❌ 告警统计报表发送失败(所有渠道)")
                return False

        except Exception as e:
            logger.error(f"发送告警统计报表失败: {e}", exc_info=True)
            return False


# 创建全局实例
alert_notification_service = AlertNotificationService()
