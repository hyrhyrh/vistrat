"""
AI模型相关的类型定义和枚举
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from utils.timezone_utils import now


class PromptCategory(Enum):
    """提示词类别"""
    SAFETY_DETECTION = "safety_detection"
    BEHAVIOR_ANALYSIS = "behavior_analysis"
    OBJECT_DETECTION = "object_detection"
    SCENE_UNDERSTANDING = "scene_understanding"


class PromptPriority(Enum):
    """提示词优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ModelType(Enum):
    """支持的AI模型类型"""
    QWEN_VL = "qwen-vl"
    MOONSHOT = "moonshot"
    GPT4_VISION = "gpt4-vision"
    CLAUDE_VISION = "claude-vision"
    GEMINI_PRO = "gemini-pro"


class TaskComplexity(Enum):
    """任务复杂度级别"""
    SIMPLE = "simple"      # 简单识别任务
    MEDIUM = "medium"      # 中等复杂度
    COMPLEX = "complex"    # 复杂分析任务
    CRITICAL = "critical"  # 关键任务


@dataclass
class PromptTemplate:
    """简化版提示词模板"""
    id: str
    name: str
    category: PromptCategory
    content: str
    priority: PromptPriority = PromptPriority.MEDIUM


@dataclass
class ModelCapabilities:
    """模型能力描述"""
    model_type: ModelType
    vision_quality: float = 0.8  # 视觉分析质量 (0-1)
    text_understanding: float = 0.8  # 文本理解能力
    reasoning_ability: float = 0.7  # 推理能力
    speed: float = 0.7  # 响应速度
    cost_efficiency: float = 0.8  # 成本效率
    multilingual: bool = True  # 多语言支持
    max_image_size: int = 2048  # 支持的最大图片尺寸
    supported_formats: List[str] = field(default_factory=lambda: ["jpg", "png", "webp"])
    
    def get_overall_score(self) -> float:
        """计算综合评分"""
        return (self.vision_quality + self.text_understanding + 
                self.reasoning_ability + self.speed + self.cost_efficiency) / 5


@dataclass
class ModelPerformance:
    """模型性能统计"""
    model_type: ModelType
    success_count: int = 0
    total_count: int = 0
    avg_response_time: float = 0.0
    avg_confidence: float = 0.0
    category_performance: Dict[PromptCategory, float] = field(default_factory=dict)
    last_updated: Optional[str] = None
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        return self.success_count / self.total_count if self.total_count > 0 else 0.0
    
    def update_performance(self, success: bool, response_time: float, 
                         confidence: float, category: PromptCategory):
        """更新性能统计"""
        self.total_count += 1
        if success:
            self.success_count += 1
        
        # 更新平均响应时间
        self.avg_response_time = ((self.avg_response_time * (self.total_count - 1) + 
                                 response_time) / self.total_count)
        
        # 更新平均置信度
        self.avg_confidence = ((self.avg_confidence * (self.total_count - 1) + 
                              confidence) / self.total_count)
        
        # 更新分类性能
        if category not in self.category_performance:
            self.category_performance[category] = confidence
        else:
            current_avg = self.category_performance[category]
            self.category_performance[category] = (current_avg + confidence) / 2
        
        from datetime import datetime
        self.last_updated = str(now())