"""
AI分析结果和图像标注模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
from pydantic import BaseModel, Field, ConfigDict
import uuid
from utils.timezone_utils import now


class DetectionType(str, Enum):
    """检测类型枚举"""
    SAFETY_VIOLATION = "safety_violation"     # 安全违规
    ABNORMAL_BEHAVIOR = "abnormal_behavior"   # 异常行为
    OBJECT_DETECTION = "object_detection"     # 目标检测
    ENVIRONMENT_HAZARD = "environment_hazard" # 环境危险
    QUALITY_ISSUE = "quality_issue"          # 质量问题


class AlertSeverity(str, Enum):
    """告警严重程度"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BoundingBox(BaseModel):
    """边界框模型"""
    x: float = Field(..., description="左上角X坐标")
    y: float = Field(..., description="左上角Y坐标")
    width: float = Field(..., description="宽度")
    height: float = Field(..., description="高度")
    confidence: float = Field(..., description="置信度")


class AnnotationObject(BaseModel):
    """标注对象模型"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="对象ID")
    class_name: str = Field(..., description="对象类别")
    confidence: float = Field(..., description="置信度")
    bounding_box: BoundingBox = Field(..., description="边界框")
    
    # 属性标注
    attributes: Dict[str, Any] = Field(default_factory=dict, description="对象属性")
    label: str = Field(..., description="显示标签")
    color: str = Field(default="#FF0000", description="标注颜色")
    
    # 检测结果
    is_violation: bool = Field(default=False, description="是否违规")
    violation_reason: Optional[str] = Field(None, description="违规原因")
    severity: AlertSeverity = Field(default=AlertSeverity.LOW, description="严重程度")


class FrameAnalysisResult(BaseModel):
    """单帧分析结果模型"""
    model_config = ConfigDict(protected_namespaces=(), use_enum_values=True)
    frame_index: int = Field(..., description="帧索引")
    timestamp: float = Field(..., description="时间戳(秒)")
    
    # AI分析结果
    description: str = Field(..., description="帧描述")
    detected_objects: List[AnnotationObject] = Field(default_factory=list, description="检测到的对象")
    
    # 告警信息
    has_alert: bool = Field(default=False, description="是否有告警")
    alert_message: Optional[str] = Field(None, description="告警消息")
    alert_severity: AlertSeverity = Field(default=AlertSeverity.INFO, description="告警严重程度")
    
    # 图像信息
    original_image_path: Optional[str] = Field(None, description="原图路径")
    annotated_image_path: Optional[str] = Field(None, description="标注图路径")
    thumbnail_path: Optional[str] = Field(None, description="缩略图路径")
    
    # 分析元数据
    analysis_duration: float = Field(..., description="分析耗时(秒)")
    model_used: str = Field(..., description="使用的AI模型")
    prompt_template_id: str = Field(..., description="使用的提示词模板ID")


class VideoAnalysisResult(BaseModel):
    """完整视频分析结果模型"""
    model_config = ConfigDict(protected_namespaces=(), use_enum_values=True)
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="结果ID")
    video_id: str = Field(..., description="视频ID")
    task_id: str = Field(..., description="分析任务ID")
    
    # 分析概况
    total_frames_analyzed: int = Field(..., description="已分析帧数")
    total_detections: int = Field(..., description="总检测数")
    total_alerts: int = Field(..., description="总告警数")
    analysis_duration: float = Field(..., description="总分析时长(秒)")
    
    # 详细结果
    frame_results: List[FrameAnalysisResult] = Field(default_factory=list, description="帧分析结果")
    
    # 汇总信息
    summary: str = Field(..., description="分析总结")
    severity_distribution: Dict[str, int] = Field(default_factory=dict, description="严重程度分布")
    detection_categories: Dict[str, int] = Field(default_factory=dict, description="检测类别统计")
    
    # 关键发现
    critical_alerts: List[FrameAnalysisResult] = Field(default_factory=list, description="关键告警")
    recommendation: Optional[str] = Field(None, description="改进建议")
    
    # 时间属性
    created_at: datetime = Field(default_factory=now, description="创建时间")
    


class MinIOFileInfo(BaseModel):
    """MinIO文件信息模型"""
    bucket_name: str = Field(..., description="存储桶名称")
    object_key: str = Field(..., description="对象键")
    file_size: int = Field(..., description="文件大小")
    content_type: str = Field(..., description="内容类型")
    etag: str = Field(..., description="ETag")
    last_modified: datetime = Field(..., description="最后修改时间")
    metadata: Dict[str, str] = Field(default_factory=dict, description="自定义元数据")
    
    # 访问信息
    url: Optional[str] = Field(None, description="访问URL")
    presigned_url: Optional[str] = Field(None, description="预签名URL")
    expiry: Optional[datetime] = Field(None, description="URL过期时间")