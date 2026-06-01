"""
AI调用熔断器
防止AI服务过载，实现自动降级和恢复机制
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, Union
from dataclasses import dataclass
from enum import Enum
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 关闭状态，正常工作
    OPEN = "open"          # 开启状态，拒绝所有请求
    HALF_OPEN = "half_open"  # 半开状态，允许少量请求测试


@dataclass
class CircuitBreakerConfig:
    """熔断器配置"""
    failure_threshold: int = 5          # 失败阈值
    timeout_threshold: float = 30.0     # 超时阈值（秒）
    recovery_timeout: float = 60.0      # 恢复超时时间（秒）
    half_open_max_calls: int = 3        # 半开状态最大调用数
    monitoring_window: float = 300.0    # 监控窗口时间（秒）
    success_threshold: int = 3          # 半开状态成功阈值
    slow_call_threshold: float = 10.0   # 慢调用阈值（秒）
    slow_call_rate_threshold: float = 0.5  # 慢调用率阈值


@dataclass
class CallRecord:
    """调用记录"""
    timestamp: float
    success: bool
    duration: float
    error_type: str = ""


class AICircuitBreaker:
    """AI调用熔断器"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        
        # 调用记录
        self.call_records = deque(maxlen=1000)  # 最多保留1000条记录
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.last_state_change_time = time.time()
        
        # 半开状态计数
        self.half_open_calls = 0
        self.half_open_success_count = 0
        
        # 统计信息
        self.total_calls = 0
        self.total_failures = 0
        self.total_timeouts = 0
        self.total_slow_calls = 0
        
        logger.info(f"AI熔断器已初始化: {name}, 失败阈值={self.config.failure_threshold}")
    
    def _clean_old_records(self):
        """清理过期的调用记录"""
        current_time = time.time()
        window_start = current_time - self.config.monitoring_window
        
        # 移除窗口外的记录
        while self.call_records and self.call_records[0].timestamp < window_start:
            self.call_records.popleft()
    
    def _calculate_failure_rate(self) -> float:
        """计算失败率"""
        self._clean_old_records()
        
        if len(self.call_records) == 0:
            return 0.0
        
        failures = sum(1 for record in self.call_records if not record.success)
        return failures / len(self.call_records)
    
    def _calculate_slow_call_rate(self) -> float:
        """计算慢调用率"""
        self._clean_old_records()
        
        if len(self.call_records) == 0:
            return 0.0
        
        slow_calls = sum(1 for record in self.call_records 
                        if record.duration > self.config.slow_call_threshold)
        return slow_calls / len(self.call_records)
    
    def _should_trip(self) -> bool:
        """判断是否应该触发熔断"""
        if len(self.call_records) < self.config.failure_threshold:
            return False
        
        failure_rate = self._calculate_failure_rate()
        slow_call_rate = self._calculate_slow_call_rate()
        
        # 失败率过高
        if failure_rate >= 0.5:  # 50%失败率
            logger.warning(f"熔断器 {self.name} 失败率过高: {failure_rate:.2%}")
            return True
        
        # 慢调用率过高
        if slow_call_rate >= self.config.slow_call_rate_threshold:
            logger.warning(f"熔断器 {self.name} 慢调用率过高: {slow_call_rate:.2%}")
            return True
        
        # 连续失败次数过多
        recent_records = list(self.call_records)[-self.config.failure_threshold:]
        if len(recent_records) == self.config.failure_threshold:
            if all(not record.success for record in recent_records):
                logger.warning(f"熔断器 {self.name} 连续失败次数过多: {self.config.failure_threshold}")
                return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置（从OPEN转为HALF_OPEN）"""
        if self.state != CircuitState.OPEN:
            return False
        
        return (time.time() - self.last_state_change_time) >= self.config.recovery_timeout
    
    def _record_call(self, success: bool, duration: float, error_type: str = ""):
        """记录调用结果"""
        record = CallRecord(
            timestamp=time.time(),
            success=success,
            duration=duration,
            error_type=error_type
        )
        
        self.call_records.append(record)
        self.total_calls += 1
        
        if not success:
            self.total_failures += 1
            self.failure_count += 1
            self.last_failure_time = time.time()
        else:
            self.failure_count = 0  # 重置连续失败计数
        
        if duration > self.config.timeout_threshold:
            self.total_timeouts += 1
        
        if duration > self.config.slow_call_threshold:
            self.total_slow_calls += 1
    
    def _transition_to_open(self):
        """转换到OPEN状态"""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change_time = time.time()
            logger.error(f"熔断器 {self.name} 已开启 - 拒绝所有AI调用")
    
    def _transition_to_half_open(self):
        """转换到HALF_OPEN状态"""
        if self.state != CircuitState.HALF_OPEN:
            self.state = CircuitState.HALF_OPEN
            self.last_state_change_time = time.time()
            self.half_open_calls = 0
            self.half_open_success_count = 0
            logger.info(f"熔断器 {self.name} 进入半开状态 - 允许少量测试调用")
    
    def _transition_to_closed(self):
        """转换到CLOSED状态"""
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self.last_state_change_time = time.time()
            self.failure_count = 0
            logger.info(f"熔断器 {self.name} 已关闭 - 恢复正常AI调用")
    
    def can_execute(self) -> bool:
        """判断是否可以执行调用"""
        # 检查是否需要状态转换
        if self.state == CircuitState.OPEN and self._should_attempt_reset():
            self._transition_to_half_open()
        
        if self.state == CircuitState.CLOSED:
            # 检查是否需要开启熔断
            if self._should_trip():
                self._transition_to_open()
                return False
            return True
        
        elif self.state == CircuitState.HALF_OPEN:
            # 半开状态限制调用数量
            return self.half_open_calls < self.config.half_open_max_calls
        
        else:  # OPEN状态
            return False
    
    async def execute(self, func: Callable, *args, **kwargs) -> Any:
        """执行被保护的函数"""
        if not self.can_execute():
            raise CircuitBreakerOpenException(f"熔断器 {self.name} 处于开启状态")
        
        start_time = time.time()
        success = False
        error_type = ""
        
        try:
            # 如果是半开状态，增加调用计数
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
            
            # 执行函数
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            success = True
            
            # 如果是半开状态，记录成功
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_success_count += 1
                
                # 检查是否可以关闭熔断器
                if self.half_open_success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            
            return result
            
        except Exception as e:
            success = False
            error_type = type(e).__name__
            
            # 如果是半开状态且失败，立即开启熔断器
            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            
            raise
            
        finally:
            duration = time.time() - start_time
            self._record_call(success, duration, error_type)
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        self._clean_old_records()
        
        # 计算平均响应时间
        durations = [record.duration for record in self.call_records]
        avg_duration = statistics.mean(durations) if durations else 0.0
        
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_timeouts": self.total_timeouts,
            "total_slow_calls": self.total_slow_calls,
            "failure_rate": self._calculate_failure_rate(),
            "slow_call_rate": self._calculate_slow_call_rate(),
            "avg_response_time": avg_duration,
            "recent_calls_count": len(self.call_records),
            "last_failure_time": self.last_failure_time,
            "state_change_time": self.last_state_change_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "timeout_threshold": self.config.timeout_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "monitoring_window": self.config.monitoring_window
            }
        }
    
    def reset(self):
        """重置熔断器"""
        self.state = CircuitState.CLOSED
        self.call_records.clear()
        self.failure_count = 0
        self.half_open_calls = 0
        self.half_open_success_count = 0
        self.last_state_change_time = time.time()
        logger.info(f"熔断器 {self.name} 已重置")


class CircuitBreakerOpenException(Exception):
    """熔断器开启异常"""
    pass


class AICircuitBreakerManager:
    """AI熔断器管理器"""
    
    def __init__(self):
        self.breakers: Dict[str, AICircuitBreaker] = {}
        
    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> AICircuitBreaker:
        """获取或创建熔断器"""
        if name not in self.breakers:
            self.breakers[name] = AICircuitBreaker(name, config)
        return self.breakers[name]
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """获取所有熔断器统计信息"""
        return {
            "breakers": {name: breaker.get_statistics() 
                        for name, breaker in self.breakers.items()},
            "total_breakers": len(self.breakers),
            "open_breakers": len([b for b in self.breakers.values() 
                                if b.state == CircuitState.OPEN]),
            "half_open_breakers": len([b for b in self.breakers.values() 
                                     if b.state == CircuitState.HALF_OPEN])
        }
    
    def reset_all(self):
        """重置所有熔断器"""
        for breaker in self.breakers.values():
            breaker.reset()
        logger.info("所有AI熔断器已重置")


# 创建全局实例
ai_circuit_breaker_manager = AICircuitBreakerManager()