"""
统一AI客户端
支持多厂商AI模型调用，根据数据库配置动态选择
"""

import logging
import time
from typing import Dict, Any, Optional
from services.ai_providers import AIProviderFactory
from services.ai_config_manager import ai_config_manager
from services.output_format_manager import output_format_manager
from services.ai_circuit_breaker import ai_circuit_breaker_manager, CircuitBreakerConfig, CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class UnifiedAIClient:
    """统一AI客户端"""
    
    def __init__(self):
        self.provider_cache = {}
        self.cache_expire_time = 600  # 10分钟缓存
        
        # 初始化熔断器配置 - 性能优化: 更宽松的阈值以提高并发性能
        self.default_breaker_config = CircuitBreakerConfig(
            failure_threshold=5,      # 5次失败触发熔断 (从3增至5)
            timeout_threshold=45.0,   # 45秒超时 (从30增至45)
            recovery_timeout=45.0,    # 45秒后尝试恢复 (从60降至45)
            half_open_max_calls=5,    # 半开状态最多5次调用 (从2增至5)
            monitoring_window=240.0,  # 4分钟监控窗口 (从5分钟降至4分钟)
            success_threshold=3,      # 半开状态3次成功后恢复 (从2增至3)
            slow_call_threshold=20.0, # 20秒算慢调用 (从15增至20)
            slow_call_rate_threshold=0.7  # 70%慢调用率触发熔断 (从60%增至70%)
        )
        
    async def analyze_image_with_config(self, image_path: str, model_config_id: str, 
                                      custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """使用指定的模型配置分析图像（带熔断器保护）"""
        # 获取模型配置
        config = await ai_config_manager.get_model_config_by_id(model_config_id)
        if not config:
            logger.error(f"模型配置不存在: {model_config_id}")
            return self._create_error_response("模型配置不存在", model_config_id)
        
        # 获取或创建熔断器
        breaker_name = f"ai_model_{config['provider']}_{config['model_name']}"
        breaker = ai_circuit_breaker_manager.get_breaker(breaker_name, self.default_breaker_config)
        
        try:
            # 使用熔断器保护AI调用
            result = await breaker.execute(self._execute_ai_analysis, image_path, model_config_id, custom_prompt)
            return result
            
        except CircuitBreakerOpenException as e:
            logger.warning(f"AI调用被熔断器阻止: {e}")
            return self._create_error_response(
                f"AI服务暂时不可用 ({config['provider']}/{config['model_name']})", 
                model_config_id, 
                error_type="circuit_breaker_open"
            )
        except Exception as e:
            logger.error(f"AI分析失败: {e}")
            return self._create_error_response(str(e), model_config_id, error_type=type(e).__name__)
    
    async def _execute_ai_analysis(self, image_path: str, model_config_id: str, 
                                 custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """执行AI分析（内部方法，被熔断器保护）"""
        start_time = time.time()
        
        try:
            # 获取模型配置
            config = await ai_config_manager.get_model_config_by_id(model_config_id)
            
            # 创建AI提供商
            provider = self._get_or_create_provider(config)
            
            # 获取输出格式配置
            format_config = await output_format_manager.get_format_for_config(model_config_id)
            
            # 确定使用的提示词
            prompt = custom_prompt or config.get('user_prompt', '')
            if not prompt:
                prompt = "请分析这张图片中的内容。"
            
            # 构建增强的系统提示词，包含输出格式要求
            base_system_prompt = config.get('system_prompt', '')
            enhanced_system_prompt = output_format_manager.build_enhanced_system_prompt(
                base_system_prompt, format_config
            )
            
            # 组合完整的提示词
            if enhanced_system_prompt.strip():
                prompt = f"{enhanced_system_prompt}\n\n{prompt}"
            
            logger.info(f"使用模型 {config['name']} ({config['provider']}) 分析图像: {image_path}")

            # 根据模型类型准备合适的图片路径（本地模型使用内网URL，公网模型转base64）
            final_image_path = self._prepare_image_url_for_model(image_path, config)

            # 调用AI分析（使用详细版本获取完整请求/响应信息）
            kwargs = {
                'temperature': config.get('temperature', 0.2),
                'top_p': config.get('top_p', 0.7),
                'max_tokens': config.get('max_tokens', 300)
            }

            logger.info(f"📊 AI调用参数: max_tokens={kwargs['max_tokens']}, temperature={kwargs['temperature']}, top_p={kwargs['top_p']}")

            # 调用详细版本以获取完整的请求/响应信息
            detailed_result = await provider.analyze_image_detailed(final_image_path, prompt, **kwargs)

            response_time = time.time() - start_time

            # 更新成功计数
            await ai_config_manager.update_model_test_count(model_config_id, True)

            # 构建返回结果，包含完整的API调用信息
            result = {
                'success': True,
                'ai_response': detailed_result['ai_response'],
                'model_config_id': model_config_id,
                'model_name': config['model_name'],
                'provider': config['provider'],
                'confidence': self._extract_confidence(detailed_result['ai_response'], config.get('confidence_threshold', 0.8)),
                'response_time': response_time,
                'prompt_used': prompt,
                'format_config_used': {
                    'algorithm_type': format_config.get('algorithm_type', 'general'),
                    'has_custom_format': bool(config.get('output_format_config')),
                    'format_version': format_config.get('format_version', '1.0')
                },
                'circuit_breaker_used': True,
                # 添加完整的API调用信息
                'api_call_details': {
                    'raw_request': detailed_result.get('raw_request', {}),
                    'raw_response': detailed_result.get('raw_response', {}),
                    'api_endpoint': detailed_result.get('api_endpoint', ''),
                    'status_code': detailed_result.get('status_code', 0),
                    'headers': detailed_result.get('headers', {}),
                    'usage': detailed_result.get('usage', {})
                }
            }
            
            logger.info(f"AI分析完成: {config['provider']}/{config['model_name']} "
                       f"耗时 {response_time:.2f}s")
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            logger.error(f"AI分析失败: {e}")
            
            # 更新失败计数
            await ai_config_manager.update_model_test_count(model_config_id, False)
            
            raise  # 重新抛出异常，让熔断器处理
    
    async def analyze_image_with_provider(self, image_path: str, provider: str, 
                                        custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """使用指定提供商分析图像（兼容旧接口）"""
        try:
            # 获取提供商的默认配置
            config = await ai_config_manager.get_model_config_by_provider(provider)
            if not config:
                logger.warning(f"提供商 {provider} 无配置，使用默认配置")
                config = await ai_config_manager.get_default_fallback_config()
            
            return await self.analyze_image_with_config(
                image_path, config['id'], custom_prompt
            )
            
        except Exception as e:
            logger.error(f"通过提供商 {provider} 分析图像失败: {e}")
            return self._create_error_response(str(e), provider)
    
    def _get_or_create_provider(self, config: Dict[str, Any]):
        """获取或创建AI提供商实例"""
        provider_key = f"{config['provider']}_{config['model_name']}"
        
        if provider_key not in self.provider_cache:
            provider = AIProviderFactory.create_provider(config['provider'], config)
            self.provider_cache[provider_key] = {
                'provider': provider,
                'created_at': time.time()
            }
            logger.debug(f"创建新的AI提供商: {provider_key}")
        
        # 检查缓存是否过期
        cached_item = self.provider_cache[provider_key]
        if time.time() - cached_item['created_at'] > self.cache_expire_time:
            provider = AIProviderFactory.create_provider(config['provider'], config)
            self.provider_cache[provider_key] = {
                'provider': provider,
                'created_at': time.time()
            }
            logger.debug(f"刷新AI提供商缓存: {provider_key}")
        
        return self.provider_cache[provider_key]['provider']
    
    def _extract_confidence(self, ai_response: str, threshold: float = 0.8) -> float:
        """从AI响应中提取置信度"""
        try:
            import re
            
            # 尝试从JSON响应中提取
            import json
            try:
                response_data = json.loads(ai_response)
                if isinstance(response_data, dict):
                    # 查找置信度字段
                    confidence_fields = ['confidence', 'conf', 'score', 'probability']
                    for field in confidence_fields:
                        if field in response_data:
                            return float(response_data[field])
                    
                    # 查找violations中的confidence
                    if 'violations' in response_data and response_data['violations']:
                        confidences = [v.get('confidence', 0) for v in response_data['violations'] if isinstance(v, dict)]
                        if confidences:
                            return max(confidences)
                            
            except (json.JSONDecodeError, ValueError):
                pass
            
            # 正则表达式提取
            confidence_patterns = [
                r'置信度[：:]\s*([\d.]+)',
                r'confidence[：:]\s*([\d.]+)',
                r'可信度[：:]\s*([\d.]+)',
                r'准确率[：:]\s*([\d.]+)',
                r'"confidence"\s*:\s*([\d.]+)',
                r'([\d.]+)%'
            ]
            
            for pattern in confidence_patterns:
                matches = re.findall(pattern, ai_response, re.IGNORECASE)
                if matches:
                    confidence_value = float(matches[0])
                    # 如果是百分比形式，转换为小数
                    if confidence_value > 1:
                        confidence_value = confidence_value / 100
                    return min(max(confidence_value, 0.0), 1.0)
            
            return threshold  # 默认使用配置的阈值
            
        except Exception as e:
            logger.warning(f"提取置信度失败: {e}")
            return threshold
    
    def _create_error_response(self, error_msg: str, model_id: str, 
                             response_time: float = 0.0, error_type: str = "unknown") -> Dict[str, Any]:
        """创建错误响应"""
        return {
            'success': False,
            'ai_response': f"分析失败: {error_msg}",
            'model_config_id': model_id,
            'model_name': 'unknown',
            'provider': 'unknown',
            'confidence': 0.0,
            'error_type': error_type,
            'response_time': response_time,
            'error': error_msg
        }
    
    def get_circuit_breaker_stats(self) -> Dict[str, Any]:
        """获取所有熔断器统计信息"""
        return ai_circuit_breaker_manager.get_all_statistics()
    
    def reset_circuit_breakers(self):
        """重置所有熔断器"""
        ai_circuit_breaker_manager.reset_all()
        logger.info("所有AI熔断器已重置")
    
    async def test_model_config(self, model_config_id: str, 
                              test_image_path: Optional[str] = None) -> Dict[str, Any]:
        """测试指定的模型配置"""
        try:
            # 使用测试图片或默认提示
            if test_image_path:
                result = await self.analyze_image_with_config(
                    test_image_path, model_config_id, "请描述这张图片的内容。"
                )
            else:
                # 创建一个简单的测试图片
                import cv2
                import numpy as np
                test_img = np.zeros((100, 100, 3), dtype=np.uint8)
                cv2.putText(test_img, "TEST", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                test_path = "/tmp/test_image.jpg"
                cv2.imwrite(test_path, test_img)
                
                result = await self.analyze_image_with_config(
                    test_path, model_config_id, "这是一个测试图片，请简单回复'测试成功'。"
                )
                
                # 清理测试文件
                import os
                if os.path.exists(test_path):
                    os.remove(test_path)
            
            return result
            
        except Exception as e:
            logger.error(f"测试模型配置失败 {model_config_id}: {e}")
            return self._create_error_response(str(e), model_config_id)
    
    async def get_available_models(self) -> Dict[str, Any]:
        """获取可用的模型列表"""
        try:
            configs = await ai_config_manager.get_all_active_configs()

            models = []
            for config_id, config in configs.items():
                models.append({
                    'id': config_id,
                    'name': config['name'],
                    'provider': config['provider'],
                    'model_name': config['model_name'],
                    'model_type': config['model_type'],
                    'status': config['status']
                })

            return {
                'success': True,
                'models': models,
                'total': len(models)
            }

        except Exception as e:
            logger.error(f"获取可用模型失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'models': [],
                'total': 0
            }

    def _is_local_model(self, config: Dict[str, Any]) -> bool:
        """
        判断是否为本地部署的AI模型

        本地模型通常运行在Docker容器或localhost，需要使用内网URL访问MinIO
        公网模型使用外网API，应使用base64编码传输图片

        Args:
            config: 模型配置

        Returns:
            True表示本地模型，False表示公网模型
        """
        api_base_url = config.get('api_base_url', '').lower()
        provider = config.get('provider', '').lower()

        # 判断是否为本地模型的特征
        local_indicators = [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            ':8000',  # vLLM默认端口
            'vllm',   # vLLM provider
            'ollama',  # Ollama本地模型
        ]

        # 检查API URL或provider是否包含本地特征
        for indicator in local_indicators:
            if indicator in api_base_url or indicator in provider:
                logger.debug(f"检测到本地模型: {config.get('name')} (匹配: {indicator})")
                return True

        logger.debug(f"检测到公网模型: {config.get('name')}")
        return False

    def _prepare_image_url_for_model(self, image_path: str, config: Dict[str, Any]) -> str:
        """
        根据模型类型准备合适的图片路径

        - 本地模型：将MinIO外网URL转换为内网URL (http://vision_minio:9000/...)
        - 公网模型：保持本地路径，后续会由_prepare_image_data转为base64

        Args:
            image_path: 原始图片路径（可能是本地路径或MinIO URL）
            config: 模型配置

        Returns:
            处理后的图片路径
        """
        from services.storage import StorageService

        # 本地模型：需要使用内网URL访问MinIO
        if self._is_local_model(config):
            # 如果是MinIO URL，转换为内网URL
            if image_path.startswith('http'):
                internal_url = StorageService.convert_to_internal_url(image_path)
                logger.info(f"🔄 本地模型使用内网URL: {internal_url}")
                return internal_url
            else:
                # 如果是本地路径，保持不变（兼容性）
                return image_path

        # 公网模型：保持原路径，后续会转base64
        logger.debug(f"公网模型保持原路径: {image_path[:80]}...")
        return image_path


# 全局实例
unified_ai_client = UnifiedAIClient()