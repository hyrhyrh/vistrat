"""
时间表达式解析器
"""
import re
from datetime import datetime, timedelta
from typing import Optional
from ..core.types import TimeWindow


class TimeParser:
    """时间表达式解析器"""

    # 时间表达式规则
    TIME_PATTERNS = [
        # 今天/今日
        (r"今天|今日", lambda: TimeParser._get_today()),
        # 昨天
        (r"昨天", lambda: TimeParser._get_yesterday()),
        # 最近N天
        (r"最近(\d+)天|近(\d+)天|过去(\d+)天", lambda match: TimeParser._get_recent_days(int(match.group(1) or match.group(2) or match.group(3)))),
        # 本周
        (r"本周|这周", lambda: TimeParser._get_this_week()),
        # 上周
        (r"上周|上星期", lambda: TimeParser._get_last_week()),
        # 本月
        (r"本月|这个月", lambda: TimeParser._get_this_month()),
        # 上月
        (r"上月|上个月", lambda: TimeParser._get_last_month()),
        # 最近N小时
        (r"最近(\d+)小时|近(\d+)小时", lambda match: TimeParser._get_recent_hours(int(match.group(1) or match.group(2)))),
    ]

    @staticmethod
    def parse(text: str) -> Optional[TimeWindow]:
        """
        解析时间表达式

        Args:
            text: 包含时间表达式的文本

        Returns:
            TimeWindow 或 None
        """
        for pattern, handler in TimeParser.TIME_PATTERNS:
            match = re.search(pattern, text)
            if match:
                if callable(handler):
                    try:
                        # 如果handler需要match对象,传入match
                        import inspect
                        sig = inspect.signature(handler)
                        if len(sig.parameters) > 0:
                            return handler(match)
                        else:
                            return handler()
                    except Exception:
                        return handler()
                return handler

        # 默认返回今天
        return None

    @staticmethod
    def _get_today() -> TimeWindow:
        """获取今天的时间窗口"""
        now = datetime.now()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
        return TimeWindow(start=start, end=end, label="今天")

    @staticmethod
    def _get_yesterday() -> TimeWindow:
        """获取昨天的时间窗口"""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        return TimeWindow(start=start, end=end, label="昨天")

    @staticmethod
    def _get_recent_days(days: int) -> TimeWindow:
        """获取最近N天的时间窗口"""
        now = datetime.now()
        start = now - timedelta(days=days)
        end = now
        return TimeWindow(start=start, end=end, label=f"最近{days}天")

    @staticmethod
    def _get_recent_hours(hours: int) -> TimeWindow:
        """获取最近N小时的时间窗口"""
        now = datetime.now()
        start = now - timedelta(hours=hours)
        end = now
        return TimeWindow(start=start, end=end, label=f"最近{hours}小时")

    @staticmethod
    def _get_this_week() -> TimeWindow:
        """获取本周的时间窗口"""
        now = datetime.now()
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now
        return TimeWindow(start=start, end=end, label="本周")

    @staticmethod
    def _get_last_week() -> TimeWindow:
        """获取上周的时间窗口"""
        now = datetime.now()
        last_week_start = now - timedelta(days=now.weekday() + 7)
        last_week_start = last_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        last_week_end = last_week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        return TimeWindow(start=last_week_start, end=last_week_end, label="上周")

    @staticmethod
    def _get_this_month() -> TimeWindow:
        """获取本月的时间窗口"""
        now = datetime.now()
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = now
        return TimeWindow(start=start, end=end, label="本月")

    @staticmethod
    def _get_last_month() -> TimeWindow:
        """获取上月的时间窗口"""
        now = datetime.now()
        first_day_this_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        start = last_day_last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end = last_day_last_month.replace(hour=23, minute=59, second=59, microsecond=999999)
        return TimeWindow(start=start, end=end, label="上月")
