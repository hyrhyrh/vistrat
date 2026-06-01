"""
时间配置检查工具
用于检查任务是否在配置的时间范围内运行
"""

from datetime import datetime, time as datetime_time
from typing import Dict, Any, Optional
import logging

# 使用系统统一的时区工具（修复Docker容器时区问题）
from utils.timezone_utils import get_beijing_now

logger = logging.getLogger(__name__)


def check_should_run_now(time_config: Optional[Dict[str, Any]]) -> tuple[bool, str]:
    """
    检查当前时间是否应该运行任务

    参数:
        time_config: 时间配置字典，格式：
        {
            "enabled": true,
            "timezone": "Asia/Shanghai",
            "time_ranges": [
                {
                    "start_time": "10:00",
                    "end_time": "10:30",
                    "days": [0, 1, 2, 3, 4, 5, 6]  # 0=周日, 1=周一, ..., 6=周六
                }
            ]
        }

    返回:
        (should_run, reason)
        - should_run: 是否应该运行 (True/False)
        - reason: 原因说明
    """
    try:
        # 如果没有时间配置，默认允许运行
        if not time_config:
            return True, "未配置时间限制，允许运行"

        # 如果时间配置未启用，允许运行
        if not time_config.get('enabled', False):
            return True, "时间配置未启用，允许运行"

        # 【关键修复】使用系统统一的时区工具获取北京时间
        # 避免Docker容器中datetime.now(tz)与系统时区不一致的问题
        current_dt = get_beijing_now()
        current_time = current_dt.time()
        current_weekday = current_dt.weekday()  # 0=周一, 1=周二, ..., 6=周日

        # 转换为 0=周日, 1=周一 格式（与前端一致）
        # Python: 0=周一, 6=周日
        # 前端: 0=周日, 1=周一, ..., 6=周六
        # 转换规则: Python的6 -> 前端的0, Python的0-5 -> 前端的1-6
        if current_weekday == 6:  # 周日
            current_day_frontend = 0
        else:
            current_day_frontend = current_weekday + 1

        logger.debug(f"当前北京时间: {current_dt.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                    f"Python weekday={current_weekday}, "
                    f"前端 day={current_day_frontend}")

        # 检查时间范围
        time_ranges = time_config.get('time_ranges', [])
        if not time_ranges:
            return True, "未配置时间范围，允许运行"

        # 遍历所有时间范围，只要有一个匹配就允许运行
        for time_range in time_ranges:
            start_time_str = time_range.get('start_time')
            end_time_str = time_range.get('end_time')
            days = time_range.get('days', [])

            # 检查是否在允许的星期几范围内
            if current_day_frontend not in days:
                logger.debug(f"当前星期({current_day_frontend})不在允许范围{days}内")
                continue

            # 解析时间
            try:
                start_time = datetime_time.fromisoformat(start_time_str)
                end_time = datetime_time.fromisoformat(end_time_str)
            except Exception as e:
                logger.error(f"时间格式解析失败: start_time={start_time_str}, "
                           f"end_time={end_time_str}, 错误={e}")
                continue

            # 检查当前时间是否在范围内
            in_time_range = False
            if start_time <= end_time:
                # 不跨天的情况 (如 10:00-18:00)
                in_time_range = start_time <= current_time <= end_time
            else:
                # 跨天的情况 (如 22:00-06:00)
                in_time_range = current_time >= start_time or current_time <= end_time

            if in_time_range:
                return True, (f"在允许的时间范围内: 星期{current_day_frontend}, "
                            f"{start_time_str}-{end_time_str}")

        # 所有时间范围都不匹配
        return False, (f"不在允许的时间范围内: 当前时间={current_time.strftime('%H:%M')}, "
                      f"星期{current_day_frontend}")

    except Exception as e:
        logger.error(f"检查时间配置失败: {e}")
        # 出错时默认允许运行，避免影响正常业务
        return True, f"时间配置检查异常，默认允许运行: {str(e)}"


def format_time_config_summary(time_config: Optional[Dict[str, Any]]) -> str:
    """
    格式化时间配置摘要（用于日志显示）

    返回:
        时间配置的可读摘要字符串
    """
    if not time_config or not time_config.get('enabled'):
        return "无时间限制"

    time_ranges = time_config.get('time_ranges', [])
    if not time_ranges:
        return "未配置具体时间范围"

    summaries = []
    weekday_names = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

    for time_range in time_ranges:
        start = time_range.get('start_time', '00:00')
        end = time_range.get('end_time', '23:59')
        days = time_range.get('days', [])

        # 转换星期几
        day_names = [weekday_names[d] for d in days if 0 <= d <= 6]
        days_str = ','.join(day_names) if day_names else '未指定'

        summaries.append(f"{days_str} {start}-{end}")

    return "; ".join(summaries)
