"""
输出格式管理器
负责AI模型输出格式的配置管理、验证和缓存
支持配置化和硬编码格式的混合使用，确保向后兼容性
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from services.ai_config_manager import ai_config_manager

logger = logging.getLogger(__name__)


class OutputFormatManager:
    """输出格式管理器 - 统一管理AI模型输出格式"""
    
    def __init__(self):
        self._format_cache = {}  # 格式缓存
        self._cache_expire_time = 600  # 10分钟缓存过期时间
        self._default_formats = self._initialize_default_formats()
    
    def _initialize_default_formats(self) -> Dict[str, Dict[str, Any]]:
        """初始化默认格式库（从现有硬编码迁移）"""
        return {
            "safety_helmet": {
                "format_version": "1.0",
                "algorithm_type": "safety_helmet",
                "format_template": self._get_safety_helmet_format(),
                "custom_instructions": "请严格按照JSON格式返回安全帽检测结果，确保所有字段都存在且类型正确。",
                "validation_rules": {
                    "required_fields": ["has_violation", "person_count", "violation_count", "conclusion", "violations"],
                    "field_types": {
                        "has_violation": "boolean",
                        "person_count": "integer", 
                        "violation_count": "integer",
                        "conclusion": "string",
                        "violations": "array"
                    }
                }
            },
            "smoking_detection": {
                "format_version": "1.0",
                "algorithm_type": "smoking_detection",
                "format_template": self._get_smoking_format(),
                "custom_instructions": "请严格按照JSON格式返回吸烟检测结果。",
                "validation_rules": {
                    "required_fields": ["has_violation", "person_count", "violation_count", "conclusion", "violations"],
                    "field_types": {
                        "has_violation": "boolean",
                        "person_count": "integer",
                        "violation_count": "integer", 
                        "conclusion": "string",
                        "violations": "array"
                    }
                }
            },
            "fight_detection": {
                "format_version": "1.0",
                "algorithm_type": "fight_detection", 
                "format_template": self._get_fight_format(),
                "custom_instructions": "请严格按照JSON格式返回打架检测结果。",
                "validation_rules": {
                    "required_fields": ["has_violation", "person_count", "violation_count", "conclusion", "violations"],
                    "field_types": {
                        "has_violation": "boolean",
                        "person_count": "integer",
                        "violation_count": "integer",
                        "conclusion": "string", 
                        "violations": "array"
                    }
                }
            },
            "fire_smoke_detection": {
                "format_version": "1.0",
                "algorithm_type": "fire_smoke_detection",
                "format_template": self._get_fire_smoke_format(),
                "custom_instructions": "请严格按照JSON格式返回火灾烟雾检测结果。",
                "validation_rules": {
                    "required_fields": ["has_violation", "person_count", "violation_count", "conclusion", "violations"],
                    "field_types": {
                        "has_violation": "boolean",
                        "person_count": "integer",
                        "violation_count": "integer",
                        "conclusion": "string",
                        "violations": "array"
                    }
                }
            },
            "general": {
                "format_version": "1.0",
                "algorithm_type": "general",
                "format_template": self._get_general_format(),
                "custom_instructions": "请严格按照JSON格式返回检测结果。",
                "validation_rules": {
                    "required_fields": ["has_violation", "person_count", "violation_count", "conclusion", "violations"],
                    "field_types": {
                        "has_violation": "boolean",
                        "person_count": "integer",
                        "violation_count": "integer",
                        "conclusion": "string",
                        "violations": "array"
                    }
                }
            }
        }
    
    async def get_format_for_config(self, model_config_id: str) -> Dict[str, Any]:
        """
        获取指定模型配置的输出格式
        优先级：数据库配置 > 算法默认格式 > 通用格式
        """
        try:
            # 检查缓存
            cache_key = f"format_config_{model_config_id}"
            if self._is_cache_valid(cache_key):
                logger.debug(f"从缓存获取格式配置: {model_config_id}")
                return self._format_cache[cache_key]["data"]
            
            # 获取模型配置
            config = await ai_config_manager.get_model_config_by_id(model_config_id)
            if not config:
                logger.warning(f"模型配置不存在，使用通用格式: {model_config_id}")
                return self._get_default_format("general")
            
            # 检查是否有自定义输出格式配置
            output_format_config = config.get('output_format_config')
            if output_format_config and self._validate_format_config(output_format_config):
                format_result = output_format_config
                logger.info(f"使用数据库自定义格式: {model_config_id}")
            else:
                # 根据算法名称推断默认格式
                algorithm_name = config.get('name', '').lower()
                format_type = self._infer_format_type_from_algorithm(algorithm_name)
                format_result = self._get_default_format(format_type)
                logger.info(f"使用推断的默认格式 {format_type}: {model_config_id}")
            
            # 缓存结果
            self._format_cache[cache_key] = {
                "data": format_result,
                "timestamp": time.time()
            }
            
            return format_result
            
        except Exception as e:
            logger.error(f"获取格式配置失败，使用通用格式: {model_config_id}, 错误: {e}")
            return self._get_default_format("general")
    
    def get_default_format_by_algorithm(self, algorithm_name: str) -> Dict[str, Any]:
        """根据算法名称获取默认格式（向后兼容API）"""
        format_type = self._infer_format_type_from_algorithm(algorithm_name.lower())
        return self._get_default_format(format_type)
    
    def get_available_format_types(self) -> List[str]:
        """获取所有可用的格式类型"""
        return list(self._default_formats.keys())
    
    def validate_format_config(self, format_config: Dict[str, Any]) -> bool:
        """验证格式配置的合法性"""
        return self._validate_format_config(format_config)
    
    def build_enhanced_system_prompt(self, base_system_prompt: str,
                                   format_config: Dict[str, Any]) -> str:
        """构建增强的系统提示词，包含输出格式要求"""
        try:
            # ✅ 处理 base_system_prompt 可能为 None 的情况
            base_prompt = base_system_prompt or ""

            format_template = format_config.get('format_template', '')
            custom_instructions = format_config.get('custom_instructions', '')

            if not format_template:
                return base_prompt if base_prompt else "你是一个专业的AI视觉分析专家。"

            # 构建格式指令部分
            format_instruction = "\n\n=== 输出格式要求 ===\n"
            if custom_instructions:
                format_instruction += f"{custom_instructions}\n\n"

            format_instruction += "请严格按照以下JSON格式返回分析结果：\n"
            format_instruction += f"```json\n{format_template}\n```\n"
            format_instruction += "\n注意：请确保返回的JSON格式完全符合上述模板，所有字段都必须存在。"

            # 组合完整的系统提示词
            if base_prompt.strip():
                return f"{base_prompt.strip()}{format_instruction}"
            else:
                return f"你是一个专业的AI视觉分析专家。{format_instruction}"

        except Exception as e:
            logger.error(f"构建增强系统提示词失败: {e}")
            return base_system_prompt or "你是一个专业的AI视觉分析专家。"
    
    def _infer_format_type_from_algorithm(self, algorithm_name: str) -> str:
        """根据算法名称推断格式类型（从原AITextGenerator逻辑迁移）"""
        algorithm_name = algorithm_name.lower()
        
        if "安全帽" in algorithm_name or "helmet" in algorithm_name:
            return "safety_helmet"
        elif "吸烟" in algorithm_name or "smoking" in algorithm_name:
            return "smoking_detection" 
        elif "打架" in algorithm_name or "fight" in algorithm_name:
            return "fight_detection"
        elif any(keyword in algorithm_name for keyword in ["火灾", "烟雾", "fire", "smoke"]):
            return "fire_smoke_detection"
        else:
            return "general"
    
    def _get_default_format(self, format_type: str) -> Dict[str, Any]:
        """获取指定类型的默认格式"""
        return self._default_formats.get(format_type, self._default_formats["general"]).copy()
    
    def _validate_format_config(self, format_config: Dict[str, Any]) -> bool:
        """验证格式配置结构"""
        try:
            required_fields = ["format_template", "custom_instructions"]
            for field in required_fields:
                if field not in format_config:
                    logger.warning(f"格式配置缺少必需字段: {field}")
                    return False
            
            # 验证format_template是否为有效JSON
            if format_config.get("format_template"):
                try:
                    # 尝试解析JSON模板（移除注释后）
                    template = format_config["format_template"]
                    # 简单验证：检查是否包含基本结构
                    if not any(key in template for key in ["has_violation", "person_count", "conclusion"]):
                        logger.warning("格式模板缺少关键字段")
                        return False
                except Exception as e:
                    logger.warning(f"格式模板JSON验证失败: {e}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"验证格式配置时出错: {e}")
            return False
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """检查缓存是否有效"""
        if cache_key not in self._format_cache:
            return False
        
        cache_time = self._format_cache[cache_key]["timestamp"]
        return (time.time() - cache_time) < self._cache_expire_time
    
    def clear_cache(self, model_config_id: Optional[str] = None):
        """清理格式配置缓存"""
        if model_config_id:
            cache_key = f"format_config_{model_config_id}"
            self._format_cache.pop(cache_key, None)
            logger.info(f"清理格式配置缓存: {model_config_id}")
        else:
            self._format_cache.clear()
            logger.info("清理所有格式配置缓存")
    
    # 以下为格式模板定义（从原AITextGenerator迁移）
    def _get_safety_helmet_format(self) -> str:
        """安全帽检测格式"""
        return '''{
  "has_violation": <boolean>,
  "person_count": <integer>,
  "violation_count": <integer>,
  "conclusion": "<string>",
  "violations": [
    {
      "bbox": {
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>
    }
  ]
}'''

    def _get_smoking_format(self) -> str:
        """吸烟检测格式"""
        return '''{
  "has_violation": <boolean>,
  "person_count": <integer>,
  "violation_count": <integer>,
  "conclusion": "<string>",
  "violations": [
    {
      "bbox": {
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>
    }
  ]
}'''

    def _get_fight_format(self) -> str:
        """打架检测格式"""
        return '''{
  "has_violation": <boolean>,
  "person_count": <integer>,
  "violation_count": <integer>,
  "conclusion": "<string>",
  "violations": [
    {
      "bbox": {
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>
    }
  ]
}'''

    def _get_fire_smoke_format(self) -> str:
        """火灾烟雾检测格式"""
        return '''{
  "has_violation": <boolean>,
  "person_count": <integer>,
  "violation_count": <integer>,
  "conclusion": "<string>",
  "violations": [
    {
      "bbox": {
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>
    }
  ]
}'''

    def _get_general_format(self) -> str:
        """通用检测格式"""
        return '''{
  "has_violation": <boolean>,
  "person_count": <integer>,
  "violation_count": <integer>,
  "conclusion": "<string>",
  "violations": [
    {
      "bbox": {
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>
    }
  ]
}'''


# 全局实例
output_format_manager = OutputFormatManager()