"""
复合检测服务
编排复合检测的完整流程：提示词构建 → AI调用 → 响应解析
"""

import logging
import time
from typing import Dict, List, Optional
from datetime import datetime

from prompts.composite_prompt_engine import get_prompt_engine
from parsers.composite_response_parser import get_response_parser
from services.unified_ai_client import UnifiedAIClient

logger = logging.getLogger(__name__)


class CompositeDetectionService:
    """
    复合检测服务 - 单一职责：编排复合检测流程

    职责：
    - 协调PromptTemplateEngine、UnifiedAIClient、CompositeResponseParser
    - 实现完整的复合检测流程
    - 错误处理和降级
    - 性能监控
    """

    def __init__(self, ai_client: Optional[UnifiedAIClient] = None):
        """
        初始化复合检测服务

        Args:
            ai_client: UnifiedAIClient实例（可选，用于依赖注入）
        """
        self.prompt_engine = get_prompt_engine()
        self.response_parser = get_response_parser()
        self.ai_client = ai_client or UnifiedAIClient()

        # 统计信息
        self._total_calls = 0
        self._success_calls = 0
        self._failed_calls = 0
        self._total_response_time = 0.0

    async def analyze_frame_composite(
        self,
        image_path: str,
        template_configs: List[Dict],
        model_config_id: str
    ) -> Dict:
        """
        复合检测分析一帧

        Args:
            image_path: 图片文件路径
            template_configs: 算法模板配置列表，每个元素包含：
                {
                    'id': 'tpl-001',
                    'name': '未佩戴安全帽',
                    'detection_type_code': 'safety_helmet',
                    'category': 'safety',
                    'severity': 'high'
                }
            model_config_id: AI模型配置ID

        Returns:
            {
                'success': True/False,
                'violations': [
                    {
                        'type_code': 'safety_helmet',
                        'display_name': '未佩戴安全帽',
                        'has_violation': True,
                        'confidence': 0.92,
                        'violation_count': 1,
                        'conclusion': '发现1人未佩戴',
                        'severity': 'high',
                        'category': 'safety'
                    },
                    ...
                ],
                'raw_response': 'AI完整响应',
                'model_used': 'gpt-4-vision',
                'provider': 'gpt',
                'response_time': 5.2,
                'detection_summary': {
                    'total_types': 3,
                    'violation_types_found': 1,
                    'total_violations': 1,
                    'avg_confidence': 0.85
                }
            }

        Raises:
            ValueError: 当输入参数无效时
            RuntimeError: 当复合检测流程失败时
        """
        start_time = time.time()
        self._total_calls += 1

        try:
            # 1. 验证输入
            self._validate_inputs(image_path, template_configs, model_config_id)

            # 2. 提取detection_type_codes
            type_codes = self._extract_type_codes(template_configs)

            if not type_codes:
                raise ValueError(
                    "template_configs中没有有效的detection_type_code字段，"
                    "无法执行复合检测"
                )

            logger.info(
                f"🚀 开始复合检测分析: image={image_path}, "
                f"types={type_codes}, model={model_config_id}"
            )

            # 3. 构建复合提示词
            composite_prompt = await self.prompt_engine.build_composite_prompt(
                type_codes=type_codes,
                include_json_schema=True
            )

            logger.debug(f"复合提示词长度: {len(composite_prompt)}字符")

            # 4. 调用AI（一次调用）
            ai_result = await self.ai_client.analyze_image_with_config(
                image_path=image_path,
                model_config_id=model_config_id,
                custom_prompt=composite_prompt
            )

            # 检查AI调用是否成功
            if not ai_result.get('success'):
                raise RuntimeError(
                    f"AI调用失败: {ai_result.get('error', 'Unknown error')}"
                )

            # 5. 解析AI响应
            template_mapping = self._build_template_mapping(template_configs)
            logger.info(f"🔍 template_mapping构建完成: {template_mapping}")  # 调试日志

            violations = await self.response_parser.parse_composite_response(
                ai_response=ai_result['ai_response'],
                expected_types=type_codes,
                template_mapping=template_mapping
            )

            # 6. 计算统计信息
            detection_summary = self._calculate_summary(violations)

            # 7. 组装最终结果
            response_time = time.time() - start_time
            self._total_response_time += response_time
            self._success_calls += 1

            result = {
                'success': True,
                'violations': violations,
                'raw_response': ai_result['ai_response'],
                'model_used': ai_result.get('model_name', 'unknown'),
                'provider': ai_result.get('provider', 'unknown'),
                'model_config_id': model_config_id,
                'response_time': round(response_time, 2),
                'detection_summary': detection_summary,
                'prompt_length': len(composite_prompt),
                'parse_strategy': violations[0].get('parse_strategy', 'unknown') if violations else None,
                # ✅ 传递完整的API调用详情
                'api_call_details': ai_result.get('api_call_details', {}),
                'prompt_used': ai_result.get('prompt_used', composite_prompt)
            }

            logger.info(
                f"✅ 复合检测完成: 耗时{response_time:.2f}s, "
                f"检测到{detection_summary['violation_types_found']}种违规"
            )

            return result

        except Exception as e:
            self._failed_calls += 1
            response_time = time.time() - start_time
            logger.error(f"❌ 复合检测失败: {e}, 耗时{response_time:.2f}s")

            # 返回失败结果（而不是抛出异常，提供降级）
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
                'violations': [],  # 空列表表示未检测到
                'raw_response': None,
                'model_used': None,
                'provider': None,
                'model_config_id': model_config_id,
                'response_time': round(response_time, 2),
                'detection_summary': {
                    'total_types': len(template_configs),
                    'violation_types_found': 0,
                    'total_violations': 0,
                    'avg_confidence': 0.0
                }
            }

    def _validate_inputs(
        self,
        image_path: str,
        template_configs: List[Dict],
        model_config_id: str
    ):
        """验证输入参数"""
        if not image_path or not isinstance(image_path, str):
            raise ValueError("image_path必须是非空字符串")

        if not template_configs or not isinstance(template_configs, list):
            raise ValueError("template_configs必须是非空列表")

        if not model_config_id or not isinstance(model_config_id, str):
            raise ValueError("model_config_id必须是非空字符串")

    def _extract_type_codes(self, template_configs: List[Dict]) -> List[str]:
        """
        从template_configs中提取detection_type_codes

        Args:
            template_configs: 模板配置列表

        Returns:
            type_code列表，去重
        """
        type_codes = []

        for config in template_configs:
            type_code = config.get('detection_type_code')
            if type_code and type_code not in type_codes:
                type_codes.append(type_code)

        return type_codes

    def _build_template_mapping(
        self,
        template_configs: List[Dict]
    ) -> Dict[str, Dict]:
        """
        构建type_code到template信息的映射

        Args:
            template_configs: 模板配置列表

        Returns:
            {
                'safety_helmet': {
                    'id': 'tpl-001',
                    'display_name': '未佩戴安全帽',
                    'category': 'safety',
                    'severity': 'high'
                },
                ...
            }
        """
        mapping = {}

        for config in template_configs:
            type_code = config.get('detection_type_code')
            if type_code:
                mapping[type_code] = {
                    'id': config.get('id'),
                    'display_name': config.get('display_name', type_code),  # 🔧 修复：使用display_name字段（与数据库字段一致）
                    'category': config.get('category', 'unknown'),
                    'severity': config.get('severity', 'medium'),
                    'priority': config.get('priority', 0)
                }

        return mapping

    def _calculate_summary(self, violations: List[Dict]) -> Dict:
        """
        计算检测摘要统计

        Args:
            violations: 违规列表

        Returns:
            {
                'total_types': 总检测类型数,
                'violation_types_found': 发现违规的类型数,
                'total_violations': 总违规数量,
                'avg_confidence': 平均置信度
            }
        """
        total_types = len(violations)

        # 统计有违规的类型
        violations_found = [v for v in violations if v.get('has_violation')]
        violation_types_found = len(violations_found)

        # 统计总违规数量
        total_violations = sum(
            v.get('violation_count', 0) for v in violations_found
        )

        # 计算平均置信度（所有类型，不仅是有违规的）
        if violations:
            avg_confidence = sum(v.get('confidence', 0.0) for v in violations) / len(violations)
        else:
            avg_confidence = 0.0

        return {
            'total_types': total_types,
            'violation_types_found': violation_types_found,
            'total_violations': total_violations,
            'avg_confidence': round(avg_confidence, 4),
            'violation_rate': round(violation_types_found / total_types, 4) if total_types > 0 else 0.0
        }

    def get_statistics(self) -> Dict:
        """
        获取服务统计信息（用于监控）

        Returns:
            {
                'total_calls': 总调用次数,
                'success_calls': 成功次数,
                'failed_calls': 失败次数,
                'success_rate': 成功率,
                'avg_response_time': 平均响应时间
            }
        """
        success_rate = (
            self._success_calls / self._total_calls
            if self._total_calls > 0 else 0.0
        )

        avg_response_time = (
            self._total_response_time / self._total_calls
            if self._total_calls > 0 else 0.0
        )

        return {
            'total_calls': self._total_calls,
            'success_calls': self._success_calls,
            'failed_calls': self._failed_calls,
            'success_rate': round(success_rate, 4),
            'avg_response_time': round(avg_response_time, 2),
            'prompt_engine_cache': self.prompt_engine.get_cache_info(),
            'parser_stats': self.response_parser.get_statistics()
        }


# 全局单例实例（应用级别共享）
_global_composite_detection_service: Optional[CompositeDetectionService] = None


def get_composite_detection_service() -> CompositeDetectionService:
    """
    获取全局复合检测服务实例（单例模式）

    Returns:
        CompositeDetectionService实例
    """
    global _global_composite_detection_service

    if _global_composite_detection_service is None:
        _global_composite_detection_service = CompositeDetectionService()
        logger.info("✅ 创建全局CompositeDetectionService实例")

    return _global_composite_detection_service
