"""
Vistrat 推理服务（A100 Tier 2）响应模型
与 vistrat-inference 服务契约对齐
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class InferenceBoundingBox(BaseModel):
    """DINO 检测框（像素坐标，整数）"""
    x: int = Field(..., description="左上角 X")
    y: int = Field(..., description="左上角 Y")
    width: int = Field(..., description="宽度")
    height: int = Field(..., description="高度")


class InferenceDetectionObject(BaseModel):
    """DINO 单个检测对象"""
    label: str = Field(..., description="英文 label，如 worker without helmet")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    bbox: InferenceBoundingBox = Field(..., description="检测框")
    severity: str = Field(default="medium", description="严重程度 critical/high/medium/low/info")


class InferenceVlmResult(BaseModel):
    """VLM 文字分析结果"""
    has_violation: bool = Field(default=False)
    violations: List[str] = Field(default_factory=list, description="命中的违规类型中文名")
    scene_description: str = Field(default="")
    raw_text: str = Field(default="")
    latency_ms: int = Field(default=0)
    error: Optional[str] = Field(default=None)


class InferenceResult(BaseModel):
    """A100 /v1/analyze 完整响应"""
    request_id: str
    vlm_result: InferenceVlmResult
    detection_objects: List[InferenceDetectionObject] = Field(default_factory=list)
    image_size: Dict[str, int] = Field(default_factory=lambda: {"width": 0, "height": 0})
    total_latency_ms: int = 0
