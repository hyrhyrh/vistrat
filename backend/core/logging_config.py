"""
统一日志配置和格式化
提供结构化的日志记录功能
"""

import logging
import sys
import json
import os
import glob
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler

from core.exceptions import BaseBusinessException

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))


class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        # 基础日志信息
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=BEIJING_TZ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # 添加业务异常详情
        if hasattr(record, 'business_exception') and isinstance(record.business_exception, BaseBusinessException):
            log_data["business_error"] = record.business_exception.to_dict()
        
        # 添加额外上下文
        if hasattr(record, 'context') and record.context:
            log_data["context"] = record.context
        
        # 添加用户ID（如果存在）
        if hasattr(record, 'user_id') and record.user_id:
            log_data["user_id"] = record.user_id
        
        # 添加请求ID（如果存在）
        if hasattr(record, 'request_id') and record.request_id:
            log_data["request_id"] = record.request_id
        
        return json.dumps(log_data, ensure_ascii=False, separators=(',', ':'))


class SimpleFormatter(logging.Formatter):
    """简单格式化器（开发环境使用）"""

    def format(self, record: logging.LogRecord) -> str:
        # 时间戳（北京时间）
        timestamp = datetime.fromtimestamp(record.created, tz=BEIJING_TZ).strftime('%Y-%m-%d %H:%M:%S')
        
        # 基础格式
        base_format = f"{timestamp} | {record.levelname:8} | {record.name:20} | {record.getMessage()}"
        
        # 添加位置信息
        if record.levelno >= logging.WARNING:
            base_format += f" [{record.module}:{record.funcName}:{record.lineno}]"
        
        # 添加异常信息
        if record.exc_info:
            base_format += f"\n{self.formatException(record.exc_info)}"
        
        # 添加业务异常详情
        if hasattr(record, 'business_exception') and isinstance(record.business_exception, BaseBusinessException):
            exc = record.business_exception
            base_format += f"\n业务错误: [{exc.error_code.code}] {exc.details}"
            if exc.context:
                base_format += f"\n上下文: {exc.context}"
        
        return base_format


class DailyRotatingFileHandler(TimedRotatingFileHandler):
    """按日期滚动的文件处理器，文件名格式: YYYY-MM-DD-{basename}.log"""

    def __init__(self, log_dir: Path, basename: str, **kwargs):
        self.log_dir = log_dir
        self.basename = basename
        # 生成今天的日志文件名
        filename = self._get_current_filename()
        super().__init__(filename, when='midnight', interval=1, backupCount=0, encoding='utf-8')
        self.suffix = "%Y-%m-%d"

    def _get_current_filename(self) -> str:
        """获取当前日期的日志文件名"""
        today = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        return str(self.log_dir / f"{today}-{self.basename}.log")

    def doRollover(self):
        """执行日志滚动"""
        if self.stream:
            self.stream.close()
            self.stream = None
        # 切换到新的日志文件
        self.baseFilename = self._get_current_filename()
        if not self.delay:
            self.stream = self._open()


class LoggerManager:
    """日志管理器"""

    def __init__(self, log_dir: str = "logs", structured: bool = False, log_retention_days: int = 30):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.structured = structured
        self.log_retention_days = log_retention_days
        self._setup_logging()
        self._cleanup_old_logs()

    def _setup_logging(self):
        """设置日志配置"""
        # 根日志器配置
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # 清除现有处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # 选择格式化器
        formatter = StructuredFormatter() if self.structured else SimpleFormatter()

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

        # 按日期滚动的文件处理器 - 所有日志
        all_log_handler = DailyRotatingFileHandler(self.log_dir, "aiwatch")
        all_log_handler.setLevel(logging.DEBUG)
        all_log_handler.setFormatter(formatter)
        root_logger.addHandler(all_log_handler)

        # 按日期滚动的文件处理器 - 错误日志
        error_log_handler = DailyRotatingFileHandler(self.log_dir, "error")
        error_log_handler.setLevel(logging.ERROR)
        error_log_handler.setFormatter(formatter)
        root_logger.addHandler(error_log_handler)

        # 设置第三方库日志级别
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    def _cleanup_old_logs(self):
        """清理过期的日志文件"""
        if self.log_retention_days <= 0:
            return

        cutoff_date = datetime.now(BEIJING_TZ) - timedelta(days=self.log_retention_days)
        cutoff_str = cutoff_date.strftime("%Y-%m-%d")

        # 查找所有日志文件
        log_patterns = [
            str(self.log_dir / "*-aiwatch.log"),
            str(self.log_dir / "*-error.log")
        ]

        deleted_count = 0
        for pattern in log_patterns:
            for log_file in glob.glob(pattern):
                try:
                    # 从文件名提取日期
                    filename = Path(log_file).name
                    date_str = filename.split('-')[0:3]  # ['YYYY', 'MM', 'DD']
                    if len(date_str) == 3:
                        file_date = '-'.join(date_str)
                        if file_date < cutoff_str:
                            os.remove(log_file)
                            deleted_count += 1
                            logging.info(f"已删除过期日志文件: {filename}")
                except Exception as e:
                    logging.warning(f"清理日志文件失败 {log_file}: {e}")

        if deleted_count > 0:
            logging.info(f"日志清理完成，共删除 {deleted_count} 个过期文件（保留 {self.log_retention_days} 天）")

    def get_logger(self, name: str) -> logging.Logger:
        """获取日志器"""
        return logging.getLogger(name)


class LogContext:
    """日志上下文管理器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.context = {}
    
    def set_context(self, **kwargs):
        """设置上下文"""
        self.context.update(kwargs)
        return self
    
    def log(self, level: int, message: str, exception: Optional[Exception] = None, **kwargs):
        """记录日志"""
        # 合并上下文
        context = {**self.context, **kwargs}
        
        # 创建日志记录
        record = self.logger.makeRecord(
            self.logger.name, level, "", 0, message, (), None
        )
        
        # 添加上下文信息
        if context:
            record.context = context
        
        # 添加异常信息
        if exception:
            if isinstance(exception, BaseBusinessException):
                record.business_exception = exception
            else:
                record.exc_info = (type(exception), exception, exception.__traceback__)
        
        # 发送日志
        self.logger.handle(record)
    
    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        self.log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        self.log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """记录ERROR级别日志"""
        self.log(logging.ERROR, message, exception, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        self.log(logging.DEBUG, message, **kwargs)


def get_logger(name: str) -> logging.Logger:
    """获取日志器的便捷方法"""
    return logging.getLogger(name)


def get_logger_context(name: str) -> LogContext:
    """获取带上下文的日志器"""
    return LogContext(logging.getLogger(name))


# 初始化日志管理器（开发环境使用简单格式）
# 从环境变量读取日志保留天数，默认30天
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))
log_manager = LoggerManager(structured=False, log_retention_days=LOG_RETENTION_DAYS)