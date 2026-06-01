"""
复合检测响应解析器
解析AI返回的多违规JSON响应，支持多层降级策略
"""

import json
import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class CompositeResponseParser:
    """
    复合检测响应解析器

    职责：
    - 解析AI返回的多违规JSON响应
    - 实现3层降级策略
    - 验证响应格式
    - 标准化输出格式
    """

    # 违规关键词（用于降级策略）
    VIOLATION_KEYWORDS = [
        '违规', '违反', '异常', '不规范', '不合规', '发现',
        'violation', 'violate', 'alert', 'warning', 'detected', 'found'
    ]

    def __init__(self):
        """初始化解析器"""
        self._parse_success_count = 0
        self._parse_fail_count = 0
        self._fallback_count = 0

    async def parse_composite_response(
        self,
        ai_response: str,
        expected_types: List[str],
        template_mapping: Optional[Dict[str, Dict]] = None,
        include_full_response: bool = True
    ) -> List[Dict]:
        """
        解析AI的复合检测响应

        Args:
            ai_response: AI的原始响应文本
            expected_types: 期望的检测类型列表，如 ['safety_helmet', 'smoking']
            template_mapping: 类型编码到模板信息的映射（可选，用于补充metadata）

        Returns:
            标准化的违规列表：
            [
                {
                    'type_code': 'safety_helmet',
                    'display_name': '未佩戴安全帽',
                    'has_violation': True,
                    'confidence': 0.92,
                    'violation_count': 1,
                    'conclusion': '发现1人未佩戴安全帽',
                    'details': [...],
                    'severity': 'high',
                    'category': 'safety',
                    'parse_strategy': 'json_block'  # 使用的解析策略
                },
                ...
            ]

        Raises:
            ValueError: 当响应完全无法解析时
        """
        if not ai_response or not ai_response.strip():
            raise ValueError("AI响应为空")

        if not expected_types:
            raise ValueError("expected_types不能为空")

        try:
            # 第1层：尝试解析```json...```代码块
            violations = await self._parse_json_block(ai_response, expected_types)
            if violations:
                self._parse_success_count += 1
                return self._enrich_violations(
                    violations, template_mapping, 'json_block',
                    ai_response if include_full_response else None
                )

            # 第2层：尝试直接JSON解析
            violations = await self._parse_raw_json(ai_response, expected_types)
            if violations:
                self._parse_success_count += 1
                return self._enrich_violations(
                    violations, template_mapping, 'raw_json',
                    ai_response if include_full_response else None
                )

            # 第3层：关键词匹配降级
            logger.warning(
                f"⚠️  JSON解析失败，降级到关键词匹配策略。"
                f"AI响应前100字符: {ai_response[:100]}"
            )
            self._fallback_count += 1
            violations = await self._fallback_keyword_match(ai_response, expected_types)
            return self._enrich_violations(
                violations, template_mapping, 'keyword_fallback',
                ai_response if include_full_response else None
            )

        except Exception as e:
            self._parse_fail_count += 1
            logger.error(f"❌ 解析AI响应失败: {e}")
            logger.debug(f"AI响应内容: {ai_response}")
            raise ValueError(f"无法解析AI响应: {e}")

    async def _parse_json_block(
        self,
        ai_response: str,
        expected_types: List[str]
    ) -> Optional[List[Dict]]:
        """
        第1层：解析```json...```代码块

        Args:
            ai_response: AI响应
            expected_types: 期望的类型列表

        Returns:
            解析成功返回violations列表，失败返回None
        """
        try:
            # 使用正则提取```json...```代码块
            json_pattern = r'```json\s*\n?(.*?)\n?```'
            matches = re.findall(json_pattern, ai_response, re.DOTALL | re.IGNORECASE)

            if not matches:
                logger.debug("未找到```json代码块")
                return None

            # 尝试解析第一个匹配的JSON块
            json_str = matches[0].strip()
            data = json.loads(json_str)

            # 提取violations
            violations = self._extract_violations_from_data(data, expected_types)

            if violations:
                logger.info(f"✅ 成功从JSON代码块解析{len(violations)}个检测结果")
                return violations

            return None

        except json.JSONDecodeError as e:
            logger.debug(f"JSON代码块解析失败: {e}")
            return None
        except Exception as e:
            logger.debug(f"解析JSON代码块时出错: {e}")
            return None

    async def _parse_raw_json(
        self,
        ai_response: str,
        expected_types: List[str]
    ) -> Optional[List[Dict]]:
        """
        第2层：直接JSON解析（处理AI直接返回JSON的情况）

        Args:
            ai_response: AI响应
            expected_types: 期望的类型列表

        Returns:
            解析成功返回violations列表，失败返回None
        """
        try:
            # 去除可能的前后缀文本，提取JSON对象
            # 查找第一个 { 到最后一个 }
            start_idx = ai_response.find('{')
            end_idx = ai_response.rfind('}')

            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                logger.debug("未找到有效的JSON对象边界")
                return None

            json_str = ai_response[start_idx:end_idx+1]
            data = json.loads(json_str)

            # 提取violations
            violations = self._extract_violations_from_data(data, expected_types)

            if violations:
                logger.info(f"✅ 成功从原始JSON解析{len(violations)}个检测结果")
                return violations

            return None

        except json.JSONDecodeError as e:
            logger.debug(f"原始JSON解析失败: {e}")
            return None
        except Exception as e:
            logger.debug(f"解析原始JSON时出错: {e}")
            return None

    def _extract_violations_from_data(
        self,
        data: Dict,
        expected_types: List[str]
    ) -> List[Dict]:
        """
        从解析的JSON数据中提取violations

        Args:
            data: 解析后的JSON数据
            expected_types: 期望的类型列表

        Returns:
            标准化的violations列表
        """
        violations = []

        # 尝试多种JSON结构
        # 结构1: {"violations": {"safety_helmet": {...}, "smoking": {...}}}
        if 'violations' in data and isinstance(data['violations'], dict):
            for type_code in expected_types:
                if type_code in data['violations']:
                    violation_data = data['violations'][type_code]
                    violation = self._normalize_violation(type_code, violation_data)
                    violations.append(violation)

        # 结构2: {"violations": [{"type": "safety_helmet", ...}, ...]}
        elif 'violations' in data and isinstance(data['violations'], list):
            for item in data['violations']:
                type_code = item.get('type') or item.get('type_code')
                if type_code in expected_types:
                    violation = self._normalize_violation(type_code, item)
                    violations.append(violation)

        # 结构3: 直接是type_code字典 {"safety_helmet": {...}, "smoking": {...}}
        else:
            for type_code in expected_types:
                if type_code in data:
                    violation_data = data[type_code]
                    violation = self._normalize_violation(type_code, violation_data)
                    violations.append(violation)

        return violations

    def _normalize_violation(self, type_code: str, data: Dict) -> Dict:
        """
        标准化单个violation数据

        Args:
            type_code: 类型编码
            data: 原始violation数据

        Returns:
            标准化的violation字典
        """
        # 提取has_violation（支持多种字段名）
        has_violation = (
            data.get('has_violation') or
            data.get('is_violation') or
            data.get('detected') or
            False
        )

        # 确保是布尔值
        if isinstance(has_violation, str):
            has_violation = has_violation.lower() in ['true', 'yes', '是', '有']

        # 提取confidence
        confidence = float(data.get('confidence', 0.0))
        confidence = max(0.0, min(1.0, confidence))  # 限制在[0, 1]范围

        # 提取violation_count
        violation_count = int(data.get('violation_count', 0))

        # 提取conclusion
        conclusion = data.get('conclusion') or data.get('summary') or ""

        # 提取details
        details = data.get('details', [])
        if isinstance(details, str):
            details = [details]  # 字符串转为列表

        return {
            'type_code': type_code,
            'has_violation': has_violation,
            'confidence': confidence,
            'violation_count': violation_count,
            'conclusion': str(conclusion),
            'details': list(details) if details else []
        }

    async def _fallback_keyword_match(
        self,
        ai_response: str,
        expected_types: List[str]
    ) -> List[Dict]:
        """
        第3层：关键词匹配降级策略

        当JSON解析完全失败时，使用关键词匹配推断是否有违规

        Args:
            ai_response: AI响应
            expected_types: 期望的类型列表

        Returns:
            推断的violations列表（置信度较低）
        """
        violations = []

        # 将响应转为小写便于匹配
        response_lower = ai_response.lower()

        for type_code in expected_types:
            # 检查是否包含违规关键词
            has_violation_keywords = any(
                keyword in response_lower for keyword in self.VIOLATION_KEYWORDS
            )

            # 检查是否包含类型编码本身（可能AI提到了）
            has_type_mention = type_code.lower() in response_lower

            # 简单推断：如果同时包含违规关键词和类型提及，认为可能有违规
            has_violation = has_violation_keywords and has_type_mention

            # 降级策略的置信度较低
            confidence = 0.5 if has_violation else 0.3

            violations.append({
                'type_code': type_code,
                'has_violation': has_violation,
                'confidence': confidence,
                'violation_count': 1 if has_violation else 0,
                'conclusion': f"关键词匹配推断: {'可能有违规' if has_violation else '未检测到违规'}",
                'details': [f"⚠️  降级策略：JSON解析失败，基于关键词推断"],
                '_is_fallback': True  # 标记为降级结果
            })

        logger.warning(
            f"⚠️  使用关键词降级策略解析，结果可能不准确。"
            f"检测到{sum(1 for v in violations if v['has_violation'])}个可能的违规"
        )

        return violations

    def _enrich_violations(
        self,
        violations: List[Dict],
        template_mapping: Optional[Dict[str, Dict]],
        parse_strategy: str,
        ai_response_full: Optional[str] = None
    ) -> List[Dict]:
        """
        丰富violations数据（添加metadata）

        Args:
            violations: 基础violations列表
            template_mapping: 类型到模板的映射
            parse_strategy: 使用的解析策略名称
            ai_response_full: 完整的AI响应（可选）

        Returns:
            丰富后的violations列表
        """
        enriched = []

        for violation in violations:
            type_code = violation['type_code']

            # 添加解析策略标记
            violation['parse_strategy'] = parse_strategy

            # 添加完整的AI响应（如果提供）
            if ai_response_full:
                violation['ai_response_full'] = ai_response_full

            # 如果有template_mapping，补充额外信息
            if template_mapping and type_code in template_mapping:
                template = template_mapping[type_code]
                display_name = template.get('display_name', type_code)
                logger.info(f"🔍 Parser丰富violation数据: {type_code} -> display_name={display_name}")  # 调试日志
                violation['display_name'] = display_name
                violation['category'] = template.get('category', 'unknown')
                violation['severity'] = template.get('severity', 'medium')
            else:
                # 默认值
                logger.warning(f"⚠️ type_code={type_code} 未在template_mapping中找到")  # 调试日志
                violation.setdefault('display_name', type_code)
                violation.setdefault('category', 'unknown')
                violation.setdefault('severity', 'medium')

            enriched.append(violation)

        return enriched

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取解析器统计信息（用于监控）

        Returns:
            {
                'parse_success_count': 成功解析次数,
                'parse_fail_count': 失败次数,
                'fallback_count': 降级次数,
                'success_rate': 成功率
            }
        """
        total = self._parse_success_count + self._parse_fail_count
        success_rate = (
            self._parse_success_count / total if total > 0 else 0.0
        )

        return {
            'parse_success_count': self._parse_success_count,
            'parse_fail_count': self._parse_fail_count,
            'fallback_count': self._fallback_count,
            'success_rate': round(success_rate, 4),
            'total_attempts': total
        }


# 全局单例实例
_global_response_parser: Optional[CompositeResponseParser] = None


def get_response_parser() -> CompositeResponseParser:
    """
    获取全局响应解析器实例（单例模式）

    Returns:
        CompositeResponseParser实例
    """
    global _global_response_parser

    if _global_response_parser is None:
        _global_response_parser = CompositeResponseParser()
        logger.info("✅ 创建全局CompositeResponseParser实例")

    return _global_response_parser
