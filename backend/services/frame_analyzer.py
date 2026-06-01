"""
帧分析器服务
专门负责视频帧的AI分析处理，支持多厂商AI模型
"""

import logging
import re
from typing import List, Dict, Any, Optional

from services.unified_ai_client import unified_ai_client
from services.ai_config_manager import ai_config_manager

logger = logging.getLogger(__name__)


class FrameAnalyzer:
    """帧分析器"""
    
    def __init__(self):
        self.unified_client = unified_ai_client
    
    async def analyze_frame_with_ai(self, image_path: str, prompt: str, 
                                  model_config_id: Optional[str] = None,
                                  template: Optional[Any] = None) -> Dict[str, Any]:
        """使用AI分析单个帧"""
        try:
            # 如果有模板，优先使用模板关联的模型配置
            if template and hasattr(template, 'ai_model_config_id'):
                model_config_id = template.ai_model_config_id
                logger.debug(f"使用模板关联的模型: {model_config_id}")
            
            # 如果没有指定模型配置，使用默认配置
            if not model_config_id:
                # 尝试获取第一个可用的模型
                available_models = await self.unified_client.get_available_models()
                if available_models['success'] and available_models['models']:
                    model_config_id = available_models['models'][0]['id']
                    logger.debug(f"使用默认模型: {model_config_id}")
                else:
                    logger.error("没有可用的AI模型配置")
                    return self._create_error_response("没有可用的AI模型配置", image_path)
            
            logger.info(f"使用模型配置 {model_config_id} 分析帧: {image_path}")
            
            # 调用统一AI客户端
            result = await self.unified_client.analyze_image_with_config(
                image_path=image_path,
                model_config_id=model_config_id,
                custom_prompt=prompt
            )
            
            if result['success']:
                logger.debug(f"AI分析成功: {result['provider']}/{result['model_name']} "
                           f"耗时 {result['response_time']:.2f}s")

                return {
                    'ai_response': result['ai_response'],
                    'confidence': result['confidence'],
                    'model': result['model_name'],
                    'provider': result['provider'],
                    'model_config_id': result['model_config_id'],
                    'response_time': result['response_time'],
                    # ✅ 传递完整的API调用详情
                    'api_call_details': result.get('api_call_details', {}),
                    'prompt_used': result.get('prompt_used', '')
                }
            else:
                logger.error(f"AI分析失败: {result['error']}")
                return self._create_error_response(result['error'], image_path, model_config_id)
            
        except Exception as e:
            logger.error(f"AI分析帧异常 {image_path}: {e}")
            return self._create_error_response(str(e), image_path, model_config_id)
    
    async def analyze_frame_with_provider(self, image_path: str, prompt: str, 
                                        provider: str) -> Dict[str, Any]:
        """使用指定提供商分析帧（兼容旧接口）"""
        try:
            logger.info(f"使用提供商 {provider} 分析帧: {image_path}")
            
            result = await self.unified_client.analyze_image_with_provider(
                image_path=image_path,
                provider=provider,
                custom_prompt=prompt
            )
            
            if result['success']:
                return {
                    'ai_response': result['ai_response'],
                    'confidence': result['confidence'],
                    'model': result['model_name'],
                    'provider': result['provider'],
                    'model_config_id': result['model_config_id'],
                    'response_time': result['response_time'],
                    # ✅ 传递完整的API调用详情
                    'api_call_details': result.get('api_call_details', {}),
                    'prompt_used': result.get('prompt_used', '')
                }
            else:
                return self._create_error_response(result['error'], image_path, provider)
                
        except Exception as e:
            logger.error(f"AI分析帧异常 {image_path}: {e}")
            return self._create_error_response(str(e), image_path, provider)
    
    def _create_error_response(self, error_msg: str, image_path: str, 
                             model_info: str = 'unknown') -> Dict[str, Any]:
        """创建错误响应"""
        return {
            'ai_response': f"分析失败: {error_msg}",
            'confidence': 0.0,
            'model': model_info,
            'provider': 'unknown',
            'model_config_id': model_info,
            'response_time': 0.0,
            'error': error_msg
        }
    
    def extract_confidence(self, ai_response: str) -> float:
        """从AI响应中提取置信度"""
        try:
            confidence_patterns = [
                r'置信度[：:]\s*([\d.]+)',
                r'confidence[：:]\s*([\d.]+)',
                r'可信度[：:]\s*([\d.]+)',
                r'准确率[：:]\s*([\d.]+)',
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
            
            return 0.5  # 默认置信度
        except Exception as e:
            logger.warning(f"提取置信度失败: {e}")
            return 0.5
    
    def check_alert_condition(self, ai_response: str, template: Any) -> bool:
        """检查是否满足告警条件"""
        try:
            # 检查置信度阈值
            confidence = self.extract_confidence(ai_response)
            if hasattr(template, 'confidence_threshold'):
                if confidence < template.confidence_threshold:
                    return False
            
            # 检查检测标准
            if hasattr(template, 'detection_criteria') and template.detection_criteria:
                response_lower = ai_response.lower()
                for criterion in template.detection_criteria:
                    if criterion.lower() in response_lower:
                        return True
                return False
            
            # 默认基于关键词检查
            alert_keywords = [
                '发现异常', '检测到异常', '存在问题', '需要关注', 
                '违规', '危险', '异常行为', 'alert', 'warning'
            ]
            
            response_lower = ai_response.lower()
            return any(keyword in response_lower for keyword in alert_keywords)
            
        except Exception as e:
            logger.error(f"检查告警条件失败: {e}")
            return False