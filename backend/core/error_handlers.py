"""
统一错误处理器
为FastAPI应用提供统一的异常处理逻辑
"""

import logging
from typing import Dict, Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException

from core.exceptions import BaseBusinessException, ErrorCode
from core.logging_config import get_logger_context

logger_ctx = get_logger_context(__name__)


async def business_exception_handler(request: Request, exc: BaseBusinessException) -> JSONResponse:
    """业务异常处理器"""
    logger_ctx.set_context(
        request_url=str(request.url),
        request_method=request.method,
        error_code=exc.error_code.code
    ).error(f"业务异常: {exc.details}", exception=exc)
    
    # 根据错误类型确定HTTP状态码
    status_code_mapping = {
        ErrorCode.RESOURCE_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.PERMISSION_DENIED: status.HTTP_403_FORBIDDEN,
        ErrorCode.INVALID_PARAMETER: status.HTTP_400_BAD_REQUEST,
        ErrorCode.INVALID_CREDENTIALS: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.USER_NOT_FOUND: status.HTTP_404_NOT_FOUND,
        ErrorCode.INVALID_TOKEN: status.HTTP_401_UNAUTHORIZED,
        ErrorCode.TOKEN_EXPIRED: status.HTTP_401_UNAUTHORIZED,
    }
    
    http_status = status_code_mapping.get(exc.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return JSONResponse(
        status_code=http_status,
        content={
            "success": False,
            "error": exc.to_dict(),
            "timestamp": logger_ctx.context.get("timestamp"),
            "path": str(request.url.path)
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """数据验证异常处理器"""
    logger_ctx.set_context(
        request_url=str(request.url),
        request_method=request.method,
        validation_errors=exc.errors()
    ).warning(f"请求数据验证失败: {len(exc.errors())} 个错误")
    
    # 提取验证错误详情
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
            "input": error.get("input")
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "error_code": ErrorCode.INVALID_PARAMETER.code,
                "error_type": "VALIDATION_ERROR",
                "message": "请求数据验证失败",
                "details": f"发现 {len(errors)} 个验证错误",
                "validation_errors": errors
            },
            "timestamp": logger_ctx.context.get("timestamp"),
            "path": str(request.url.path)
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP异常处理器"""
    logger_ctx.set_context(
        request_url=str(request.url),
        request_method=request.method,
        status_code=exc.status_code
    ).warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "error_code": exc.status_code,
                "error_type": "HTTP_ERROR",
                "message": exc.detail,
                "details": exc.detail
            },
            "timestamp": logger_ctx.context.get("timestamp"),
            "path": str(request.url.path)
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """通用异常处理器"""
    logger_ctx.set_context(
        request_url=str(request.url),
        request_method=request.method,
        exception_type=type(exc).__name__
    ).error(f"未捕获异常: {str(exc)}", exception=exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "error_code": ErrorCode.UNKNOWN_ERROR.code,
                "error_type": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "details": "请联系管理员或稍后重试"
            },
            "timestamp": logger_ctx.context.get("timestamp"),
            "path": str(request.url.path)
        }
    )


def register_error_handlers(app):
    """注册所有错误处理器"""
    app.add_exception_handler(BaseBusinessException, business_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)


# 异常处理装饰器
def handle_exceptions(error_code: ErrorCode = ErrorCode.OPERATION_FAILED):
    """异常处理装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except BaseBusinessException:
                # 业务异常直接重新抛出
                raise
            except Exception as e:
                # 转换为业务异常
                logger_ctx.error(f"函数 {func.__name__} 执行失败", exception=e)
                raise BaseBusinessException(
                    error_code,
                    f"操作失败: {str(e)}",
                    {"function": func.__name__, "args": str(args), "kwargs": str(kwargs)}
                ) from e
        return wrapper
    return decorator