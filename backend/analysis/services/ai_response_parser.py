"""
AI响应解析器
专门处理AI模型返回结果的解析和处理
"""

import re
import logging
from typing import List, Dict, Any
import numpy as np

from models.analysis_result import AnnotationObject, BoundingBox, AlertSeverity

logger = logging.getLogger(__name__)


class AIResponseParser:
    """AI响应解析器

    ⚠️ 降级路径专用：
    正常业务链路的 bounding box 由 Vistrat A100 推理服务（DINO）提供，
    见 services.inference_client.InferenceClient.analyze。

    本解析器仅在 A100 不可达（熔断/网络故障）、降级到本地纯 VLM 文字分析时，
    用关键词匹配兜底生成占位 bbox。精度不保证。
    """

    async def parse_ai_response(self, ai_response: str, template) -> List[AnnotationObject]:
        """解析AI模型响应（降级路径 - VLM 纯文本解析，bbox 为占位）"""
        objects = []
        
        try:
            # 根据检测关键词解析结果
            for keyword in template.detection_criteria.detection_keywords:
                if keyword.lower() in ai_response.lower():
                    confidence = self._extract_confidence_from_text(ai_response, keyword)
                    
                    # 创建检测对象
                    obj = AnnotationObject(
                        class_name=keyword,
                        confidence=confidence,
                        # 占位 bbox — 降级路径用（A100 不可达时 VLM 文字解析无 bbox）
                        # 正常路径下 bbox 由 InferenceClient.analyze 的 DINO 结果提供
                        bounding_box=BoundingBox(x=0, y=0, width=100, height=100, confidence=confidence),
                        severity=self._determine_severity(keyword, 
                                                        template.detection_criteria.get('severity_mapping', {}))
                    )
                    objects.append(obj)
                    
            logger.debug(f"解析到 {len(objects)} 个检测对象")
            
        except Exception as e:
            logger.error(f"解析AI响应失败: {e}")
            
        return objects
    
    def _extract_confidence_from_text(self, text: str, keyword: str) -> float:
        """从文本中提取置信度"""
        # 查找置信度相关的表达
        patterns = [
            rf"{keyword}.*?(\d+\.?\d*)%",
            rf"{keyword}.*?置信度.*?(\d+\.?\d*)",
            rf"置信度.*?{keyword}.*?(\d+\.?\d*)",
            rf"概率.*?{keyword}.*?(\d+\.?\d*)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    confidence = float(match.group(1))
                    # 如果是百分比形式，转换为小数
                    if confidence > 1:
                        confidence = confidence / 100
                    return min(max(confidence, 0.0), 1.0)
                except ValueError:
                    continue
        
        # 默认置信度基于关键词出现次数
        keyword_count = text.lower().count(keyword.lower())
        if keyword_count > 0:
            return min(0.5 + (keyword_count - 1) * 0.1, 0.9)
        
        return 0.6  # 默认置信度
    
    def _determine_severity(self, keyword: str, severity_mapping: Dict[str, str]) -> AlertSeverity:
        """确定告警严重程度"""
        severity_str = severity_mapping.get(keyword, 'medium')
        return AlertSeverity(severity_str)
    
    def generate_alert_message(self, violations: List[AnnotationObject], template) -> str:
        """生成告警消息"""
        if not violations:
            return "未检测到异常"
            
        violation_summaries = []
        for violation in violations:
            summary = f"{violation.class_name}(置信度:{violation.confidence:.2f})"
            violation_summaries.append(summary)
        
        alert_message = f"检测到异常: {', '.join(violation_summaries)}"
        
        if hasattr(template, 'alert_template') and template.alert_template:
            # 使用自定义告警模板
            alert_message = template.alert_template.format(
                violations=', '.join(violation_summaries),
                count=len(violations)
            )
        
        return alert_message