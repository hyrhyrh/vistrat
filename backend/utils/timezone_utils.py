"""
时区工具模块
统一处理北京时间的时区转换
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


def get_beijing_now() -> datetime:
    """获取当前北京时间"""
    return datetime.now(BEIJING_TZ)


def get_beijing_now_str() -> str:
    """获取当前北京时间的ISO格式字符串"""
    return get_beijing_now().isoformat()


def utc_to_beijing(utc_dt: datetime) -> datetime:
    """将UTC时间转换为北京时间"""
    if utc_dt.tzinfo is None:
        # 如果没有时区信息，假设是UTC时间
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(BEIJING_TZ)


def beijing_to_utc(beijing_dt: datetime) -> datetime:
    """将北京时间转换为UTC时间"""
    if beijing_dt.tzinfo is None:
        # 如果没有时区信息，假设是北京时间
        beijing_dt = beijing_dt.replace(tzinfo=BEIJING_TZ)
    return beijing_dt.astimezone(timezone.utc)


def format_beijing_time(dt: Optional[datetime] = None) -> str:
    """格式化北京时间为字符串
    
    Args:
        dt: 要格式化的时间，如果为None则使用当前时间
        
    Returns:
        格式化的北京时间字符串
    """
    if dt is None:
        dt = get_beijing_now()
    elif dt.tzinfo is None:
        # 如果没有时区信息，假设是UTC时间并转换
        dt = dt.replace(tzinfo=timezone.utc).astimezone(BEIJING_TZ)
    elif dt.tzinfo != BEIJING_TZ:
        # 转换到北京时间
        dt = dt.astimezone(BEIJING_TZ)
    
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_beijing_timestamp() -> float:
    """获取北京时间的时间戳"""
    return get_beijing_now().timestamp()


# 兼容性函数，逐步替换原有的datetime.utcnow()调用
def now() -> datetime:
    """获取当前北京时间（不带时区信息，用于数据库存储）"""
    return get_beijing_now().replace(tzinfo=None)


def now_with_tz() -> datetime:
    """获取当前北京时间（带时区信息）"""
    return get_beijing_now()


def now_isoformat() -> str:
    """获取当前北京时间的ISO格式字符串（带时区信息）"""
    return get_beijing_now().isoformat()