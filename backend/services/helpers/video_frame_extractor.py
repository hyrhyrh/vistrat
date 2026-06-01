"""
视频帧提取和分析辅助模块

从 video_analysis_service.py 中提取的视频帧处理相关功能：
- 视频文件下载（MinIO）
- 视频帧抽样和提取
- AI响应违规信息提取
- 复合检测结果转换

这些方法原属于 VideoAnalysisService 类，提取为独立函数以降低主类复杂度。
"""

import json
import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def extract_violation_from_ai_response(ai_response: str) -> bool:
    """
    从AI多模态响应中提取违规信息

    Args:
        ai_response: AI返回的文本响应

    Returns:
        是否检测到违规
    """
    try:
        # 尝试从响应中提取JSON部分
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', ai_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            try:
                response_data = json.loads(json_str)
                if 'has_violation' in response_data:
                    return bool(response_data['has_violation'])
                elif 'violation_count' in response_data:
                    return int(response_data.get('violation_count', 0)) > 0
            except json.JSONDecodeError as e:
                logger.warning(f"解析AI响应JSON失败: {e}")

        # 降级到关键词检查
        response_lower = ai_response.lower()
        violation_keywords = [
            'has_violation": true', '"has_violation":true',
            '违规', '违反', '异常', '不规范', '不合规',
            'violation', 'violate', 'alert', 'warning'
        ]

        return any(keyword in response_lower for keyword in violation_keywords)

    except Exception as e:
        logger.warning(f"提取违规信息失败: {e}")
        return False


def convert_violations_to_results(
    violations: List[Dict],
    templates: List[Dict],
    frame_index: int,
    timestamp: float,
    minio_url: str,
    composite_result: Dict
) -> List[Dict]:
    """
    将violations列表转换为results格式（保持向后兼容）

    Args:
        violations: 来自CompositeResponseParser的violations列表
        templates: 配置的算法模板列表
        frame_index: 帧索引
        timestamp: 时间戳
        minio_url: 图片URL
        composite_result: 完整的复合检测结果

    Returns:
        标准results格式列表
    """
    results = []

    # 构建violation的type_code到数据的映射
    violation_map = {v['type_code']: v for v in violations}

    # 为每个template生成一个result
    for template in templates:
        type_code = template.get('detection_type_code')
        violation = violation_map.get(type_code) if type_code else None

        if violation:
            result = {
                'frame_index': frame_index,
                'timestamp': timestamp,
                'template_id': template['id'],
                'template_name': template['name'],
                'category': violation.get('category', template.get('category', 'unknown')),
                'image_url': minio_url,
                'has_alert': violation.get('has_violation', False),
                'ai_response': violation.get('conclusion', ''),
                'confidence': violation.get('confidence', 0.0),
                'violation_count': violation.get('violation_count', 0),
                'severity': violation.get('severity', 'medium'),
                'details': violation.get('details', []),
                'composite_detection': True,
                'detection_type_code': type_code,
                'parse_strategy': violation.get('parse_strategy', 'unknown')
            }
        else:
            result = {
                'frame_index': frame_index,
                'timestamp': timestamp,
                'template_id': template['id'],
                'template_name': template['name'],
                'category': template.get('category', 'unknown'),
                'image_url': minio_url,
                'has_alert': False,
                'ai_response': '未检测到违规',
                'confidence': 0.0,
                'violation_count': 0,
                'composite_detection': True,
                'detection_type_code': type_code
            }

        results.append(result)

    # 添加元数据
    if results:
        results[0]['_composite_metadata'] = {
            'model_used': composite_result.get('model_used'),
            'provider': composite_result.get('provider'),
            'response_time': composite_result.get('response_time'),
            'total_types': len(templates),
            'violation_types_found': sum(1 for r in results if r.get('has_alert')),
            'detection_summary': composite_result.get('detection_summary', {})
        }

    logger.debug(
        f"转换violations到results: {len(violations)}个violations -> {len(results)}个results, "
        f"{sum(1 for r in results if r.get('has_alert'))}个有告警"
    )

    return results
