"""
通知适配器
支持多种通知渠道(企业微信、钉钉、邮件等)
优化方案10: 告警通知系统
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class NotificationSeverity(str, Enum):
    """通知严重级别"""
    INFO = "info"  # 信息
    WARNING = "warning"  # 警告
    ERROR = "error"  # 错误
    CRITICAL = "critical"  # 严重


@dataclass
class NotificationMessage:
    """通知消息结构"""
    title: str  # 标题
    content: str  # 内容
    severity: NotificationSeverity  # 严重级别
    timestamp: float  # 时间戳
    source: str = "AI监控系统"  # 来源
    extra_data: Optional[Dict[str, Any]] = None  # 额外数据

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['severity'] = self.severity.value
        return result


class NotificationAdapter(ABC):
    """通知适配器抽象基类"""

    def __init__(self):
        self.total_sent = 0
        self.total_failed = 0
        self.last_send_time = None

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """
        发送通知

        Args:
            message: 通知消息

        Returns:
            是否发送成功
        """
        pass

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            'total_sent': self.total_sent,
            'total_failed': self.total_failed,
            'last_send_time': self.last_send_time,
            'success_rate': (
                round(self.total_sent / (self.total_sent + self.total_failed) * 100, 2)
                if (self.total_sent + self.total_failed) > 0
                else 0.0
            )
        }


class WeChatWorkAdapter(NotificationAdapter):
    """
    企业微信群聊机器人适配器

    支持Markdown格式消息
    API文档: https://developer.work.weixin.qq.com/document/path/91770
    """

    def __init__(self, webhook_url: str):
        """
        初始化企业微信适配器

        Args:
            webhook_url: 企业微信群聊机器人Webhook地址
        """
        super().__init__()
        self.webhook_url = webhook_url
        self.timeout = 10.0  # 请求超时时间(秒)

    def _format_markdown_message(self, message: NotificationMessage) -> str:
        """
        格式化为Markdown消息

        企业微信支持的Markdown语法:
        - 标题: # 一级标题  ## 二级标题  ### 三级标题
        - 加粗: **加粗**
        - 斜体: *斜体*
        - 引用: > 引用文本
        - 代码: `代码`
        - 链接: [链接文字](http://example.com)
        - 列表: - 项目1
        """
        # 根据严重级别选择emoji和颜色标识
        severity_icons = {
            NotificationSeverity.INFO: "ℹ️",
            NotificationSeverity.WARNING: "⚠️",
            NotificationSeverity.ERROR: "❌",
            NotificationSeverity.CRITICAL: "🚨"
        }

        severity_names = {
            NotificationSeverity.INFO: "信息",
            NotificationSeverity.WARNING: "警告",
            NotificationSeverity.ERROR: "错误",
            NotificationSeverity.CRITICAL: "严重告警"
        }

        icon = severity_icons.get(message.severity, "📢")
        severity_name = severity_names.get(message.severity, "通知")

        # 格式化时间
        from datetime import datetime
        time_str = datetime.fromtimestamp(message.timestamp).strftime("%Y-%m-%d %H:%M:%S")

        # 构建Markdown消息
        markdown_content = f"""## {icon} {message.title}

**级别**: <font color="{'info' if message.severity == NotificationSeverity.INFO else 'warning' if message.severity == NotificationSeverity.WARNING else 'comment'}">{severity_name}</font>
**时间**: {time_str}
**来源**: {message.source}

---

{message.content}
"""

        # 添加额外数据
        if message.extra_data:
            markdown_content += "\n\n**详细信息**:\n"
            for key, value in message.extra_data.items():
                markdown_content += f"- {key}: `{value}`\n"

        return markdown_content

    async def send(self, message: NotificationMessage) -> bool:
        """
        发送通知到企业微信群聊

        Args:
            message: 通知消息

        Returns:
            是否发送成功
        """
        try:
            # 格式化为Markdown消息
            markdown_text = self._format_markdown_message(message)

            # 构建请求体
            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "content": markdown_text
                }
            }

            # 发送HTTP POST请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )

                # 检查响应
                if response.status_code == 200:
                    result = response.json()
                    if result.get('errcode') == 0:
                        self.total_sent += 1
                        self.last_send_time = time.time()
                        logger.info(f"✅ 企业微信通知发送成功: {message.title}")
                        return True
                    else:
                        error_msg = result.get('errmsg', 'Unknown error')
                        logger.error(f"❌ 企业微信通知发送失败: {error_msg}")
                        self.total_failed += 1
                        return False
                else:
                    logger.error(f"❌ 企业微信通知HTTP请求失败: {response.status_code}")
                    self.total_failed += 1
                    return False

        except httpx.TimeoutException:
            logger.error(f"❌ 企业微信通知发送超时: {message.title}")
            self.total_failed += 1
            return False
        except Exception as e:
            logger.error(f"❌ 企业微信通知发送异常: {e}", exc_info=True)
            self.total_failed += 1
            return False


class DingTalkAdapter(NotificationAdapter):
    """
    钉钉群聊机器人适配器(预留)

    API文档: https://open.dingtalk.com/document/robots/custom-robot-access
    """

    def __init__(self, webhook_url: str, secret: Optional[str] = None):
        super().__init__()
        self.webhook_url = webhook_url
        self.secret = secret

    async def send(self, message: NotificationMessage) -> bool:
        """发送通知到钉钉群聊(待实现)"""
        logger.warning("钉钉通知适配器尚未实现")
        return False


class EmailAdapter(NotificationAdapter):
    """
    邮件通知适配器(预留)

    支持SMTP协议发送邮件
    """

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        super().__init__()
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send(self, message: NotificationMessage) -> bool:
        """发送邮件通知(待实现)"""
        logger.warning("邮件通知适配器尚未实现")
        return False


class NotificationAdapterFactory:
    """通知适配器工厂"""

    @staticmethod
    def create_wechat_work_adapter(webhook_url: str) -> WeChatWorkAdapter:
        """创建企业微信适配器"""
        return WeChatWorkAdapter(webhook_url)

    @staticmethod
    def create_dingtalk_adapter(webhook_url: str, secret: Optional[str] = None) -> DingTalkAdapter:
        """创建钉钉适配器"""
        return DingTalkAdapter(webhook_url, secret)

    @staticmethod
    def create_email_adapter(smtp_host: str, smtp_port: int, username: str, password: str) -> EmailAdapter:
        """创建邮件适配器"""
        return EmailAdapter(smtp_host, smtp_port, username, password)
