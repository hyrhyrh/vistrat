"""
Agent核心数据类型定义
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class AgentState(str, Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    ANALYZING_INTENT = "analyzing_intent"
    QUERYING_DATA = "querying_data"
    PROCESSING_DATA = "processing_data"
    GENERATING_INSIGHTS = "generating_insights"
    BUILDING_REPORT = "building_report"
    COMPLETED = "completed"
    ERROR = "error"


class StreamMessageStage(str, Enum):
    """流式消息阶段"""
    INTENT = "intent"
    QUERY = "query"
    PROCESS = "process"
    ANALYZE = "analyze"
    REPORT = "report"
    COMPLETED = "completed"
    ERROR = "error"


class StreamMessage(BaseModel):
    """流式消息"""
    stage: str = Field(..., description="当前阶段")
    message: str = Field(default="", description="提示文本")
    content: str = Field(default="", description="内容(用于analyze阶段的流式输出)")
    data: Dict[str, Any] = Field(default_factory=dict, description="附加数据")

    class Config:
        json_schema_extra = {
            "example": {
                "stage": "intent",
                "message": "✓ 已识别: 时间:今天 | 指标:count",
                "content": "",
                "data": {"intent": {}}
            }
        }


class TimeWindow(BaseModel):
    """时间窗口"""
    start: datetime = Field(..., description="开始时间")
    end: datetime = Field(..., description="结束时间")
    label: str = Field(..., description="时间窗口标签,如'今天'、'最近一周'")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "start": "2025-10-10T00:00:00",
                "end": "2025-10-10T23:59:59",
                "label": "今天"
            }
        }


class Intent(BaseModel):
    """用户意图"""
    time_window: Optional[TimeWindow] = Field(None, description="时间窗口")
    entities: List[str] = Field(default_factory=list, description="实体列表(区域、设备、告警类型等)")
    metrics: List[str] = Field(default_factory=list, description="指标列表(count、severity、trend等)")
    query_type: str = Field(default="statistics", description="查询类型: statistics/trend/comparison/anomaly")
    aggregation_level: str = Field(default="day", description="聚合级别: hour/day/week/month")
    filters: Dict[str, Any] = Field(default_factory=dict, description="其他过滤条件")

    def summary(self) -> str:
        """生成意图摘要"""
        parts = []
        if self.time_window:
            parts.append(f"时间:{self.time_window.label}")
        if self.entities:
            parts.append(f"实体:{','.join(self.entities)}")
        if self.metrics:
            parts.append(f"指标:{','.join(self.metrics)}")
        return " | ".join(parts) if parts else "统计查询"

    class Config:
        json_schema_extra = {
            "example": {
                "time_window": {
                    "start": "2025-10-03T00:00:00",
                    "end": "2025-10-10T23:59:59",
                    "label": "最近一周"
                },
                "entities": ["区域A"],
                "metrics": ["count", "trend"],
                "query_type": "trend",
                "aggregation_level": "day",
                "filters": {}
            }
        }


class AgentContext(BaseModel):
    """对话上下文"""
    question: str = Field(..., description="用户问题")
    user_id: str = Field(..., description="用户ID")
    intent: Dict[str, Any] = Field(default_factory=dict, description="意图数据")
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="ES原始数据")
    processed_data: Dict[str, Any] = Field(default_factory=dict, description="处理后的数据")
    insights: str = Field(default="", description="AI分析结果")
    report: str = Field(default="", description="报告内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "最近一周有多少告警?",
                "user_id": "user123",
                "intent": {},
                "raw_data": {},
                "processed_data": {},
                "insights": "",
                "report": "",
                "metadata": {}
            }
        }


class ProcessedData(BaseModel):
    """处理后的数据"""
    summary: Dict[str, Any] = Field(default_factory=dict, description="数据摘要")
    table_data: List[Dict[str, Any]] = Field(default_factory=list, description="表格数据")
    statistics: Dict[str, float] = Field(default_factory=dict, description="统计数据")
    charts: List[Dict[str, Any]] = Field(default_factory=list, description="图表建议")

    class Config:
        json_schema_extra = {
            "example": {
                "summary": {
                    "total_count": 42
                },
                "table_data": [
                    {
                        "timestamp": "2025-10-10T14:30:00",
                        "type": "未戴安全帽",
                        "stream": "摄像头001",
                        "confidence": 0.95
                    }
                ],
                "statistics": {
                    "mean_confidence": 0.87,
                    "median_confidence": 0.89
                },
                "charts": [
                    {
                        "type": "line",
                        "title": "告警趋势",
                        "data": []
                    }
                ]
            }
        }


class ReportOutput(BaseModel):
    """报告输出"""
    markdown: str = Field(..., description="Markdown格式报告")
    html: str = Field(default="", description="HTML格式报告")
    json_data: Dict[str, Any] = Field(default_factory=dict, description="JSON数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    class Config:
        json_schema_extra = {
            "example": {
                "markdown": "# 分析报告\n\n## 核心结论\n...",
                "html": "<!DOCTYPE html>...",
                "json_data": {},
                "metadata": {
                    "timestamp": "2025-10-10T15:00:00",
                    "question": "最近一周有多少告警?",
                    "data_count": 42
                }
            }
        }
