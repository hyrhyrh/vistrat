"""
增强的提示词模板模型
支持多维度分类和动态变量系统
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from utils.timezone_utils import now
import uuid


class PromptCategory(str, Enum):
    """提示词分类枚举"""
    SAFETY_DETECTION = "safety_detection"       # 安全检测
    BEHAVIOR_ANALYSIS = "behavior_analysis"     # 行为分析
    OBJECT_RECOGNITION = "object_recognition"   # 目标识别
    ENVIRONMENT_MONITOR = "environment_monitor" # 环境监控
    QUALITY_CONTROL = "quality_control"        # 质量控制
    CUSTOM = "custom"                          # 自定义


class PromptPriority(str, Enum):
    """提示词优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromptVariable(BaseModel):
    """提示词动态变量"""
    name: str = Field(..., description="变量名")
    type: str = Field(..., description="变量类型: string|number|boolean|datetime")
    description: str = Field(..., description="变量描述")
    default_value: Optional[Any] = Field(None, description="默认值")
    required: bool = Field(default=False, description="是否必需")
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="验证规则")
    example_value: Optional[str] = Field(None, description="示例值")


class DetectionCriteria(BaseModel):
    """检测条件配置"""
    confidence_threshold: float = Field(default=0.7, description="置信度阈值")
    detection_keywords: List[str] = Field(default_factory=list, description="检测关键词")
    exclusion_keywords: List[str] = Field(default_factory=list, description="排除关键词")
    severity_mapping: Dict[str, str] = Field(default_factory=dict, description="严重程度映射")
    enable_annotation: bool = Field(default=True, description="是否启用图像标注")
    annotation_style: Optional[Dict[str, Any]] = Field(None, description="标注样式配置")


class PromptTemplate(BaseModel):
    """增强的提示词模板模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="模板ID")
    name: str = Field(..., description="模板名称")
    category: PromptCategory = Field(..., description="模板分类")
    priority: PromptPriority = Field(default=PromptPriority.MEDIUM, description="优先级")
    
    # 提示词内容
    system_prompt: str = Field(..., description="系统提示词")
    user_prompt: str = Field(..., description="用户提示词")
    example_input: Optional[str] = Field(None, description="输入示例")
    example_output: Optional[str] = Field(None, description="输出示例")
    
    # 模板属性
    description: str = Field(..., description="模板描述")
    variables: List[PromptVariable] = Field(default_factory=list, description="动态变量列表")
    detection_criteria: DetectionCriteria = Field(default_factory=DetectionCriteria, description="检测条件")
    
    # 应用场景
    applicable_scenarios: List[str] = Field(default_factory=list, description="适用场景")
    supported_models: List[str] = Field(default_factory=list, description="支持的AI模型")
    
    # 状态管理
    is_active: bool = Field(default=False, description="是否激活")
    is_system_template: bool = Field(default=False, description="是否系统模板")
    version: str = Field(default="1.0", description="模板版本")
    
    # 使用统计
    usage_count: int = Field(default=0, description="使用次数")
    success_rate: float = Field(default=0.0, description="成功率")
    avg_confidence: float = Field(default=0.0, description="平均置信度")
    
    # 时间属性
    created_at: datetime = Field(default_factory=now, description="创建时间")
    updated_at: datetime = Field(default_factory=now, description="更新时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    
    # 作者信息
    created_by: Optional[str] = Field(None, description="创建者")
    tags: List[str] = Field(default_factory=list, description="标签")
    
    class Config:
        use_enum_values = True


class PromptTemplateRequest(BaseModel):
    """提示词模板请求模型"""
    name: str = Field(..., description="模板名称")
    category: PromptCategory = Field(..., description="模板分类")
    priority: PromptPriority = Field(default=PromptPriority.MEDIUM, description="优先级")
    system_prompt: str = Field(..., description="系统提示词")
    user_prompt: str = Field(..., description="用户提示词")
    description: str = Field(..., description="模板描述")
    variables: List[PromptVariable] = Field(default_factory=list, description="动态变量")
    detection_criteria: DetectionCriteria = Field(default_factory=DetectionCriteria, description="检测条件")
    applicable_scenarios: List[str] = Field(default_factory=list, description="适用场景")
    tags: List[str] = Field(default_factory=list, description="标签")
    
    class Config:
        use_enum_values = True


class PromptTemplateUpdate(BaseModel):
    """提示词模板更新模型"""
    name: Optional[str] = Field(None, description="模板名称")
    category: Optional[PromptCategory] = Field(None, description="模板分类")
    priority: Optional[PromptPriority] = Field(None, description="优先级")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    user_prompt: Optional[str] = Field(None, description="用户提示词")
    description: Optional[str] = Field(None, description="模板描述")
    variables: Optional[List[PromptVariable]] = Field(None, description="动态变量")
    detection_criteria: Optional[DetectionCriteria] = Field(None, description="检测条件")
    applicable_scenarios: Optional[List[str]] = Field(None, description="适用场景")
    tags: Optional[List[str]] = Field(None, description="标签")
    is_active: Optional[bool] = Field(None, description="是否激活")
    
    class Config:
        use_enum_values = True