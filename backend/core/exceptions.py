"""
统一异常定义和处理
定义项目中的自定义异常类型和错误码
"""

from typing import Dict, Any, Optional
from enum import Enum


class ErrorCode(Enum):
    """错误码枚举"""
    # 通用错误 (1000-1099)
    UNKNOWN_ERROR = (1000, "未知错误")
    INVALID_PARAMETER = (1001, "参数无效")
    PERMISSION_DENIED = (1002, "权限不足")
    RESOURCE_NOT_FOUND = (1003, "资源不存在")
    OPERATION_FAILED = (1004, "操作失败")
    
    # 视频相关错误 (2000-2099)
    VIDEO_NOT_FOUND = (2000, "视频文件不存在")
    VIDEO_UPLOAD_FAILED = (2001, "视频上传失败")
    VIDEO_PROCESSING_FAILED = (2002, "视频处理失败")
    VIDEO_ANALYSIS_FAILED = (2003, "视频分析失败")
    INVALID_VIDEO_FORMAT = (2004, "不支持的视频格式")
    
    # AI模型相关错误 (3000-3099)
    AI_MODEL_ERROR = (3000, "AI模型错误")
    AI_API_ERROR = (3001, "AI API调用失败")
    MODEL_NOT_AVAILABLE = (3002, "模型不可用")
    ANALYSIS_TIMEOUT = (3003, "分析超时")
    CONFIDENCE_TOO_LOW = (3004, "置信度过低")
    
    # 数据库相关错误 (4000-4099)
    DATABASE_ERROR = (4000, "数据库错误")
    CONNECTION_FAILED = (4001, "数据库连接失败")
    TRANSACTION_FAILED = (4002, "事务执行失败")
    CONSTRAINT_VIOLATION = (4003, "数据约束违反")
    
    # 存储相关错误 (5000-5099)
    STORAGE_ERROR = (5000, "存储错误")
    FILE_NOT_FOUND = (5001, "文件不存在")
    UPLOAD_FAILED = (5002, "文件上传失败")
    DOWNLOAD_FAILED = (5003, "文件下载失败")
    STORAGE_QUOTA_EXCEEDED = (5004, "存储配额超限")
    
    # 认证相关错误 (6000-6099)
    AUTH_ERROR = (6000, "认证错误")
    INVALID_TOKEN = (6001, "无效令牌")
    TOKEN_EXPIRED = (6002, "令牌已过期")
    INVALID_CREDENTIALS = (6003, "凭据无效")
    USER_NOT_FOUND = (6004, "用户不存在")
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message


class BaseBusinessException(Exception):
    """业务异常基类"""
    
    def __init__(self, error_code: ErrorCode, details: Optional[str] = None, 
                 context: Optional[Dict[str, Any]] = None):
        self.error_code = error_code
        self.details = details or error_code.message
        self.context = context or {}
        super().__init__(self.details)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code.code,
            "error_type": self.error_code.name,
            "message": self.error_code.message,
            "details": self.details,
            "context": self.context
        }
    
    def __str__(self) -> str:
        return f"[{self.error_code.code}] {self.details}"


class VideoException(BaseBusinessException):
    """视频相关异常"""
    pass


class AIModelException(BaseBusinessException):
    """AI模型相关异常"""
    pass


class DatabaseException(BaseBusinessException):
    """数据库相关异常"""
    pass


class StorageException(BaseBusinessException):
    """存储相关异常"""
    pass


class AuthException(BaseBusinessException):
    """认证相关异常"""
    pass


class ValidationError(BaseBusinessException):
    """数据验证异常"""
    
    def __init__(self, field: str, message: str, value: Any = None):
        super().__init__(
            ErrorCode.INVALID_PARAMETER,
            f"字段 '{field}' 验证失败: {message}",
            {"field": field, "value": value}
        )