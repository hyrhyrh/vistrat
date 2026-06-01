"""
具备容错能力的AI分析器
提供超时控制、自动重试和熔断器保护
优化方案3: AI分析超时和重试
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """熔断器模式实现 - 保护系统不被故障服务拖垮"""

    def __init__(self, failure_threshold=5, timeout=60):
        """
        初始化熔断器

        Args:
            failure_threshold: 失败阈值,超过此值熔断器将打开
            timeout: 熔断超时时间(秒),之后进入半开状态
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout  # 熔断超时(秒)
        self.failure_count = 0
        self.success_count = 0  # 成功计数
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def is_closed(self) -> bool:
        """
        检查熔断器是否关闭(允许请求通过)

        Returns:
            True表示允许请求通过,False表示熔断中
        """
        if self.state == 'CLOSED':
            return True

        if self.state == 'OPEN':
            # 检查是否可以进入半开状态
            if self.last_failure_time and time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
                logger.info(
                    "🔄 AI服务熔断器进入半开状态,允许部分请求通过 "
                    f"(等待{self.timeout}秒后尝试恢复)"
                )
                return True
            return False

        # HALF_OPEN状态,允许请求通过
        return True

    def record_success(self):
        """记录成功请求"""
        self.success_count += 1

        if self.state == 'HALF_OPEN':
            # 半开状态下成功,关闭熔断器
            self.state = 'CLOSED'
            self.failure_count = 0
            logger.info(
                f"✅ AI服务熔断器已关闭,服务恢复正常 "
                f"(成功次数: {self.success_count})"
            )
        elif self.state == 'CLOSED':
            # 正常状态下成功,重置失败计数
            if self.failure_count > 0:
                self.failure_count = max(0, self.failure_count - 1)

    def record_failure(self):
        """记录失败请求"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            if self.state != 'OPEN':
                self.state = 'OPEN'
                logger.warning(
                    f"⚠️ AI服务熔断器已打开 - 连续失败{self.failure_count}次, "
                    f"{self.timeout}秒后将尝试恢复"
                )

        if self.state == 'HALF_OPEN':
            # 半开状态下失败,重新打开熔断器
            self.state = 'OPEN'
            self.last_failure_time = time.time()
            logger.warning("⚠️ AI服务熔断器重新打开,服务未恢复")

    def get_status(self) -> Dict[str, Any]:
        """
        获取熔断器状态

        Returns:
            状态信息字典
        """
        return {
            'state': self.state,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time,
            'threshold': self.failure_threshold,
            'timeout': self.timeout
        }

    def reset(self):
        """手动重置熔断器"""
        self.state = 'CLOSED'
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("🔄 AI服务熔断器已手动重置")


class ResilientAIAnalyzer:
    """具备容错能力的AI分析器 - 提供超时控制和熔断保护"""

    def __init__(self, base_analyzer, timeout=30, max_retries=3):
        """
        初始化容错AI分析器

        Args:
            base_analyzer: 基础AI分析器实例
            timeout: 超时时间(秒)
            max_retries: 最大重试次数
        """
        self.base_analyzer = base_analyzer
        self.timeout = timeout  # 超时时间(秒)
        self.max_retries = max_retries
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,  # 连续失败5次触发熔断
            timeout=60  # 熔断60秒后尝试恢复
        )

        # 统计信息
        self.total_requests = 0
        self.total_successes = 0
        self.total_failures = 0
        self.total_timeouts = 0
        self.total_retries = 0

    async def analyze_with_timeout_retry(
        self,
        image_path: str,
        prompt: str,
        model_config_id: str
    ) -> Dict[str, Any]:
        """
        带超时和重试的AI分析

        Args:
            image_path: 图片路径
            prompt: 提示词
            model_config_id: 模型配置ID

        Returns:
            分析结果字典

        Raises:
            Exception: AI分析失败
        """
        self.total_requests += 1
        retry_count = 0

        while retry_count <= self.max_retries:
            try:
                # 检查熔断器状态
                if not self.circuit_breaker.is_closed():
                    status = self.circuit_breaker.get_status()
                    raise Exception(
                        f"AI服务熔断中 (状态: {status['state']}, "
                        f"失败次数: {status['failure_count']}/{status['threshold']})"
                    )

                # 带超时的AI分析
                logger.debug(
                    f"开始AI分析 (超时={self.timeout}s, 重试={retry_count}/{self.max_retries})"
                )

                start_time = time.time()
                result = await asyncio.wait_for(
                    self.base_analyzer.analyze_frame_with_ai(
                        image_path=image_path,
                        prompt=prompt,
                        model_config_id=model_config_id
                    ),
                    timeout=self.timeout
                )
                elapsed = time.time() - start_time

                # 成功,记录到熔断器和统计
                self.circuit_breaker.record_success()
                self.total_successes += 1

                logger.debug(f"✅ AI分析成功 (耗时: {elapsed:.2f}s)")

                return result

            except asyncio.TimeoutError:
                # 超时
                retry_count += 1
                self.total_timeouts += 1

                logger.warning(
                    f"⏱️ AI分析超时 (第{retry_count}/{self.max_retries}次重试), "
                    f"超时阈值={self.timeout}秒"
                )

                # 记录失败到熔断器
                self.circuit_breaker.record_failure()

                if retry_count <= self.max_retries:
                    # 指数退避
                    delay = min(2 ** retry_count, 10)
                    logger.debug(f"等待{delay}秒后重试...")
                    await asyncio.sleep(delay)
                    self.total_retries += 1
                else:
                    self.total_failures += 1
                    raise Exception(
                        f"AI分析超时,已重试{self.max_retries}次 "
                        f"(超时阈值: {self.timeout}秒)"
                    )

            except Exception as e:
                # 其他异常
                retry_count += 1

                # 判断是否是熔断异常
                if "熔断" in str(e):
                    self.total_failures += 1
                    raise  # 熔断异常直接抛出,不重试

                logger.error(
                    f"❌ AI分析异常: {e} "
                    f"(第{retry_count}/{self.max_retries}次重试)"
                )

                # 记录失败到熔断器
                self.circuit_breaker.record_failure()

                if retry_count <= self.max_retries:
                    # 固定2秒延迟
                    await asyncio.sleep(2)
                    self.total_retries += 1
                else:
                    self.total_failures += 1
                    raise

        # 理论上不会到达这里
        self.total_failures += 1
        raise Exception(f"AI分析失败,已达最大重试次数: {self.max_retries}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取分析统计信息

        Returns:
            统计信息字典
        """
        success_rate = (
            self.total_successes / self.total_requests * 100
            if self.total_requests > 0 else 0
        )

        return {
            'total_requests': self.total_requests,
            'total_successes': self.total_successes,
            'total_failures': self.total_failures,
            'total_timeouts': self.total_timeouts,
            'total_retries': self.total_retries,
            'success_rate': round(success_rate, 2),
            'circuit_breaker': self.circuit_breaker.get_status(),
            'config': {
                'timeout': self.timeout,
                'max_retries': self.max_retries
            }
        }

    def reset_statistics(self):
        """重置统计信息"""
        self.total_requests = 0
        self.total_successes = 0
        self.total_failures = 0
        self.total_timeouts = 0
        self.total_retries = 0
        logger.info("📊 AI分析统计信息已重置")

    def reset_circuit_breaker(self):
        """重置熔断器"""
        self.circuit_breaker.reset()
