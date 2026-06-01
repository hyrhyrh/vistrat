"""
重构后的AI模型智能选择服务
使用模块化设计，分离关注点
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from models.ai_model_types import (
    ModelType, TaskComplexity, ModelCapabilities, PromptCategory, 
    PromptPriority, PromptTemplate
)
from services.ai_model_performance import ModelPerformanceTracker

logger = logging.getLogger(__name__)


class ModelCapabilityProvider:
    """模型能力提供者"""
    
    def __init__(self):
        self.model_capabilities = {
            ModelType.QWEN_VL: ModelCapabilities(
                model_type=ModelType.QWEN_VL,
                vision_quality=0.85,
                text_understanding=0.9,
                reasoning_ability=0.8,
                speed=0.8,
                cost_efficiency=0.9,
                max_image_size=2048
            ),
            ModelType.MOONSHOT: ModelCapabilities(
                model_type=ModelType.MOONSHOT,
                vision_quality=0.7,
                text_understanding=0.85,
                reasoning_ability=0.75,
                speed=0.85,
                cost_efficiency=0.8,
                max_image_size=1536
            ),
            ModelType.GPT4_VISION: ModelCapabilities(
                model_type=ModelType.GPT4_VISION,
                vision_quality=0.95,
                text_understanding=0.95,
                reasoning_ability=0.9,
                speed=0.6,
                cost_efficiency=0.5,
                max_image_size=4096
            ),
            ModelType.CLAUDE_VISION: ModelCapabilities(
                model_type=ModelType.CLAUDE_VISION,
                vision_quality=0.9,
                text_understanding=0.95,
                reasoning_ability=0.85,
                speed=0.7,
                cost_efficiency=0.6,
                max_image_size=3072
            )
        }
    
    def get_capability(self, model_type: ModelType) -> Optional[ModelCapabilities]:
        """获取模型能力"""
        return self.model_capabilities.get(model_type)
    
    def get_all_capabilities(self) -> Dict[ModelType, ModelCapabilities]:
        """获取所有模型能力"""
        return self.model_capabilities.copy()


class TaskAnalyzer:
    """任务分析器"""
    
    def analyze_task_complexity(self, prompt_template: PromptTemplate) -> TaskComplexity:
        """分析任务复杂度"""
        try:
            content = prompt_template.content.lower()
            priority = prompt_template.priority
            category = prompt_template.category
            
            # 基于优先级判断
            if priority == PromptPriority.CRITICAL:
                return TaskComplexity.CRITICAL
            
            # 基于内容复杂度判断
            complex_keywords = [
                '推理', '分析', '理解', '判断', '综合', '评估',
                'reasoning', 'analysis', 'understanding', 'judgment'
            ]
            
            simple_keywords = [
                '识别', '检测', '发现', '计数', '定位',
                'identify', 'detect', 'find', 'count', 'locate'
            ]
            
            complex_count = sum(1 for word in complex_keywords if word in content)
            simple_count = sum(1 for word in simple_keywords if word in content)
            
            if complex_count > simple_count and complex_count >= 2:
                return TaskComplexity.COMPLEX
            elif simple_count > 0 and complex_count == 0:
                return TaskComplexity.SIMPLE
            else:
                return TaskComplexity.MEDIUM
                
        except Exception as e:
            logger.warning(f"分析任务复杂度失败: {e}")
            return TaskComplexity.MEDIUM
    
    def get_category_requirements(self, category: PromptCategory) -> Dict[str, float]:
        """获取不同类别的能力要求权重"""
        requirements = {
            PromptCategory.SAFETY_DETECTION: {
                'vision_quality': 0.9,
                'reasoning_ability': 0.7,
                'speed': 0.8,
                'text_understanding': 0.6
            },
            PromptCategory.BEHAVIOR_ANALYSIS: {
                'vision_quality': 0.8,
                'reasoning_ability': 0.9,
                'speed': 0.6,
                'text_understanding': 0.8
            },
            PromptCategory.OBJECT_DETECTION: {
                'vision_quality': 0.95,
                'reasoning_ability': 0.5,
                'speed': 0.8,
                'text_understanding': 0.5
            },
            PromptCategory.SCENE_UNDERSTANDING: {
                'vision_quality': 0.8,
                'reasoning_ability': 0.85,
                'speed': 0.6,
                'text_understanding': 0.9
            }
        }
        
        return requirements.get(category, {
            'vision_quality': 0.8,
            'reasoning_ability': 0.7,
            'speed': 0.7,
            'text_understanding': 0.7
        })


class AIModelSelector:
    """重构后的AI模型选择器"""
    
    def __init__(self):
        self.capability_provider = ModelCapabilityProvider()
        self.task_analyzer = TaskAnalyzer()
        self.performance_tracker = ModelPerformanceTracker()
        
        # 可用模型列表
        self.available_models = [
            ModelType.QWEN_VL,
            ModelType.MOONSHOT,
            ModelType.GPT4_VISION,
            ModelType.CLAUDE_VISION
        ]
    
    def select_model(self, task_type: str = "视觉分析", 
                    prompt_template: Optional[PromptTemplate] = None,
                    context: Optional[Dict[str, Any]] = None) -> str:
        """智能选择最适合的模型"""
        try:
            # 如果提供了模板，进行详细分析
            if prompt_template:
                return self._select_by_template(prompt_template, context)
            
            # 否则基于任务类型选择
            return self._select_by_task_type(task_type, context)
            
        except Exception as e:
            logger.error(f"模型选择失败: {e}")
            return self._get_fallback_model()
    
    def _select_by_template(self, template: PromptTemplate, 
                           context: Optional[Dict[str, Any]] = None) -> str:
        """基于模板选择模型"""
        # 分析任务特征
        complexity = self.task_analyzer.analyze_task_complexity(template)
        category_requirements = self.task_analyzer.get_category_requirements(template.category)
        
        # 计算每个模型的适配分数
        model_scores = {}
        
        for model_type in self.available_models:
            capability = self.capability_provider.get_capability(model_type)
            if not capability:
                continue
            
            # 基础能力分数
            base_score = self._calculate_capability_score(capability, category_requirements)
            
            # 性能历史分数
            performance_score = self._calculate_performance_score(model_type, template.category)
            
            # 复杂度适配分数
            complexity_score = self._calculate_complexity_score(capability, complexity)
            
            # 优先级权重
            priority_weight = self._get_priority_weight(template.priority)
            
            # 综合分数
            total_score = (base_score * 0.4 + 
                          performance_score * 0.3 + 
                          complexity_score * 0.2 + 
                          priority_weight * 0.1)
            
            model_scores[model_type] = total_score
            
            logger.debug(f"模型 {model_type.value} 分数: {total_score:.3f} "
                        f"(基础:{base_score:.3f}, 性能:{performance_score:.3f}, "
                        f"复杂度:{complexity_score:.3f})")
        
        # 选择最高分模型
        if model_scores:
            best_model = max(model_scores.items(), key=lambda x: x[1])
            logger.info(f"为模板 {template.name} 选择模型: {best_model[0].value} "
                       f"(分数: {best_model[1]:.3f})")
            return best_model[0].value
        
        return self._get_fallback_model()
    
    def _select_by_task_type(self, task_type: str, 
                           context: Optional[Dict[str, Any]] = None) -> str:
        """基于任务类型选择模型"""
        # 简化的任务类型映射
        task_model_mapping = {
            "视觉分析": ModelType.QWEN_VL.value,
            "安全检测": ModelType.GPT4_VISION.value,
            "行为分析": ModelType.CLAUDE_VISION.value,
            "物体识别": ModelType.QWEN_VL.value,
            "文本理解": ModelType.MOONSHOT.value
        }
        
        selected = task_model_mapping.get(task_type, ModelType.QWEN_VL.value)
        logger.info(f"基于任务类型 '{task_type}' 选择模型: {selected}")
        return selected
    
    def _calculate_capability_score(self, capability: ModelCapabilities, 
                                  requirements: Dict[str, float]) -> float:
        """计算能力匹配分数"""
        score = 0.0
        total_weight = 0.0
        
        for req_key, req_weight in requirements.items():
            if hasattr(capability, req_key):
                capability_value = getattr(capability, req_key)
                score += capability_value * req_weight
                total_weight += req_weight
        
        return score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_performance_score(self, model_type: ModelType, 
                                   category: PromptCategory) -> float:
        """计算性能历史分数"""
        performance = self.performance_tracker.get_model_performance(model_type)
        if not performance:
            return 0.5  # 默认中等分数
        
        # 整体成功率
        base_score = performance.success_rate
        
        # 分类特定性能
        category_score = performance.category_performance.get(category, base_score)
        
        # 综合评分
        return (base_score * 0.6 + category_score * 0.4)
    
    def _calculate_complexity_score(self, capability: ModelCapabilities, 
                                  complexity: TaskComplexity) -> float:
        """计算复杂度适配分数"""
        complexity_requirements = {
            TaskComplexity.SIMPLE: {'speed': 0.8, 'cost_efficiency': 0.9},
            TaskComplexity.MEDIUM: {'reasoning_ability': 0.7, 'speed': 0.7},
            TaskComplexity.COMPLEX: {'reasoning_ability': 0.9, 'vision_quality': 0.8},
            TaskComplexity.CRITICAL: {'reasoning_ability': 0.95, 'vision_quality': 0.9}
        }
        
        requirements = complexity_requirements.get(complexity, {})
        return self._calculate_capability_score(capability, requirements)
    
    def _get_priority_weight(self, priority: PromptPriority) -> float:
        """获取优先级权重"""
        weights = {
            PromptPriority.LOW: 0.3,
            PromptPriority.MEDIUM: 0.5,
            PromptPriority.HIGH: 0.8,
            PromptPriority.CRITICAL: 1.0
        }
        return weights.get(priority, 0.5)
    
    def _get_fallback_model(self) -> str:
        """获取默认后备模型"""
        return ModelType.QWEN_VL.value
    
    def record_model_performance(self, model: str, success: bool, 
                               response_time: float, confidence: float,
                               category: PromptCategory):
        """记录模型性能"""
        try:
            model_type = ModelType(model)
            self.performance_tracker.record_model_usage(
                model_type, success, response_time, confidence, category
            )
        except ValueError:
            logger.warning(f"未知的模型类型: {model}")
    
    def get_model_statistics(self) -> Dict:
        """获取模型统计信息"""
        return self.performance_tracker.get_performance_summary()


# 全局单例
ai_model_selector = AIModelSelector()