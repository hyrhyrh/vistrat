"""
异步工具函数 — 统一的阻塞调用包装器

提供在异步上下文中安全执行阻塞操作的工具函数，
防止阻塞事件循环导致的死锁和性能问题。

使用场景：
- 在 async 函数中调用同步第三方库（如 cv2、subprocess 等）
- 包装文件 IO 操作
- 包装 CPU 密集型计算

用法示例：
    from utils.async_helpers import run_blocking

    # 在 async 函数中安全调用阻塞操作
    result = await run_blocking(cv2.imread, image_path)
    await run_blocking(cv2.imwrite, output_path, frame)
"""

import asyncio
import logging
from functools import wraps
from typing import TypeVar, Callable, Any

logger = logging.getLogger(__name__)

T = TypeVar("T")


async def run_blocking(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    在线程池中运行阻塞函数，防止阻塞事件循环。

    内部使用 asyncio.to_thread，它会将函数提交到默认的线程池执行器。
    适用于同步 IO、CPU 密集型操作、不支持异步的第三方库调用等场景。

    Args:
        func: 要执行的同步（阻塞）函数
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        函数的返回值

    Raises:
        与原始函数相同的异常
    """
    if kwargs:
        # asyncio.to_thread 支持 kwargs（Python 3.9+）
        return await asyncio.to_thread(func, *args, **kwargs)
    else:
        return await asyncio.to_thread(func, *args)


def async_wrap(func: Callable[..., T]) -> Callable[..., Any]:
    """
    装饰器：将同步函数包装为异步函数。

    被装饰的函数将自动在线程池中执行，不会阻塞事件循环。

    用法示例：
        @async_wrap
        def heavy_computation(data):
            # CPU 密集型操作
            return process(data)

        # 现在可以 await 调用
        result = await heavy_computation(data)
    """
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        return await run_blocking(func, *args, **kwargs)
    return wrapper
