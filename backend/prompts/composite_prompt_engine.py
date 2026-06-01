"""
复合检测提示词模板引擎
动态组装多种检测类型的提示词
"""

import json
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio

from sqlalchemy import text
from database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class PromptTemplateEngine:
    """
    复合检测提示词模板引擎

    职责：
    - 从数据库查询detection_type_templates
    - 动态组装复合提示词
    - 缓存模板减少数据库查询
    - 构建AI响应的JSON Schema
    """

    # 类级别缓存（内存缓存）
    _cache: Dict[str, Dict] = {}
    _cache_timestamp: Optional[datetime] = None
    _cache_ttl = timedelta(minutes=10)  # 缓存10分钟

    # 最大同时检测类型数（防止token超限）
    MAX_DETECTION_TYPES = 5

    def __init__(self):
        """初始化提示词引擎"""
        self._lock = asyncio.Lock()  # 用于缓存更新的锁

    async def build_composite_prompt(
        self,
        type_codes: List[str],
        include_json_schema: bool = True
    ) -> str:
        """
        动态组装复合提示词

        Args:
            type_codes: 检测类型编码列表，如 ['safety_helmet', 'smoking']
            include_json_schema: 是否包含JSON Schema说明

        Returns:
            完整的复合提示词

        Raises:
            ValueError: 当type_codes为空或超过最大限制时
        """
        # 验证输入
        if not type_codes:
            raise ValueError("type_codes不能为空")

        if len(type_codes) > self.MAX_DETECTION_TYPES:
            raise ValueError(
                f"同时检测类型数不能超过{self.MAX_DETECTION_TYPES}个，"
                f"当前请求{len(type_codes)}个"
            )

        try:
            # 获取模板（优先使用缓存）
            templates = await self._get_templates(type_codes)

            if not templates:
                raise ValueError(f"未找到有效的检测类型模板: {type_codes}")

            # 按sort_order排序
            templates.sort(key=lambda x: x['sort_order'])

            # 组装提示词
            prompt = self._assemble_prompt(templates, include_json_schema)

            logger.info(
                f"✅ 成功构建复合提示词，包含{len(templates)}种检测类型: "
                f"{[t['type_code'] for t in templates]}"
            )

            return prompt

        except Exception as e:
            logger.error(f"❌ 构建复合提示词失败: {e}")
            raise

    async def _get_templates(self, type_codes: List[str]) -> List[Dict]:
        """
        获取检测类型模板（优先缓存）

        Args:
            type_codes: 类型编码列表

        Returns:
            模板字典列表
        """
        # 检查缓存是否有效
        if self._is_cache_valid():
            cached_templates = [
                self._cache[code] for code in type_codes
                if code in self._cache
            ]

            # 如果所有请求的模板都在缓存中，直接返回
            if len(cached_templates) == len(type_codes):
                logger.debug(f"✅ 从缓存获取{len(cached_templates)}个模板")
                return cached_templates

        # 缓存未命中或部分命中，从数据库查询
        return await self._load_templates_from_db(type_codes)

    def _is_cache_valid(self) -> bool:
        """检查缓存是否有效"""
        if not self._cache_timestamp:
            return False

        age = datetime.now() - self._cache_timestamp
        return age < self._cache_ttl

    async def _load_templates_from_db(self, type_codes: List[str]) -> List[Dict]:
        """
        从数据库加载模板

        Args:
            type_codes: 类型编码列表

        Returns:
            模板字典列表
        """
        try:
            async with DatabaseManager.get_session() as session:
                # 构建SQL查询
                placeholders = ', '.join([f":code{i}" for i in range(len(type_codes))])
                query = text(f"""
                    SELECT
                        type_code,
                        display_name,
                        category,
                        prompt_template,
                        json_field_name,
                        severity,
                        sort_order,
                        enabled
                    FROM detection_type_templates
                    WHERE type_code IN ({placeholders})
                    AND enabled = TRUE
                    ORDER BY sort_order
                """)

                # 构建参数字典
                params = {f"code{i}": code for i, code in enumerate(type_codes)}

                # 执行查询
                result = await session.execute(query, params)
                rows = result.fetchall()

                # 转换为字典列表
                templates = [
                    {
                        'type_code': row[0],
                        'display_name': row[1],
                        'category': row[2],
                        'prompt_template': row[3],
                        'json_field_name': row[4],
                        'severity': row[5],
                        'sort_order': row[6],
                        'enabled': row[7]
                    }
                    for row in rows
                ]

                # 更新缓存
                await self._update_cache(templates)

                logger.debug(f"✅ 从数据库加载{len(templates)}个模板")
                return templates

        except Exception as e:
            logger.error(f"❌ 从数据库加载模板失败: {e}")
            raise

    async def _update_cache(self, templates: List[Dict]):
        """
        更新缓存

        Args:
            templates: 模板列表
        """
        async with self._lock:
            for template in templates:
                self._cache[template['type_code']] = template

            self._cache_timestamp = datetime.now()
            logger.debug(f"✅ 缓存已更新，当前缓存{len(self._cache)}个模板")

    def _assemble_prompt(
        self,
        templates: List[Dict],
        include_json_schema: bool
    ) -> str:
        """
        组装复合提示词

        Args:
            templates: 模板列表
            include_json_schema: 是否包含JSON Schema

        Returns:
            完整的提示词字符串
        """
        prompt_parts = []

        # 1. 系统角色和任务说明
        prompt_parts.append(
            "你是一个专业的视频监控AI分析助手，负责实时监控视频画面中的违规行为。\n"
            "请仔细观察提供的视频帧图片，同时检测以下多种违规类型：\n"
        )

        # 2. 逐个添加检测类型说明
        for i, template in enumerate(templates, start=1):
            prompt_parts.append(f"\n## {i}. {template['display_name']} ({template['category'].upper()})")
            prompt_parts.append(f"**严重程度**: {template['severity'].upper()}\n")
            prompt_parts.append(f"{template['prompt_template']}\n")

        # 3. 分析要求
        prompt_parts.append("\n---\n")
        prompt_parts.append("## 分析要求\n")
        prompt_parts.append("1. 仔细观察画面中的每一个细节\n")
        prompt_parts.append("2. 对每种违规类型都给出明确的判断\n")
        prompt_parts.append("3. 如果检测到违规，请说明具体位置和人数\n")
        prompt_parts.append("4. 给出合理的置信度评分（0.0-1.0）\n")
        prompt_parts.append("5. 结论要简洁明了，便于生成告警通知\n")

        # 4. JSON格式要求
        if include_json_schema:
            json_schema = self._build_json_schema(templates)
            prompt_parts.append("\n---\n")
            prompt_parts.append("## 输出格式要求\n")
            prompt_parts.append("**请严格按照以下JSON格式返回结果，不要添加任何额外的文字说明**：\n")
            prompt_parts.append("```json\n")
            prompt_parts.append(json_schema)
            prompt_parts.append("\n```\n")

            # 5. 格式说明
            prompt_parts.append("\n**字段说明**：\n")
            prompt_parts.append("- `has_violation`: 布尔值，是否检测到该类型的违规\n")
            prompt_parts.append("- `confidence`: 浮点数（0.0-1.0），检测结果的置信度\n")
            prompt_parts.append("- `violation_count`: 整数，检测到的违规数量（如多少人）\n")
            prompt_parts.append("- `conclusion`: 字符串，简洁的结论说明（50字以内）\n")
            prompt_parts.append("- `details`: 字符串数组，详细的观察细节（可选）\n")

        return "".join(prompt_parts)

    def _build_json_schema(self, templates: List[Dict]) -> str:
        """
        构建AI响应的JSON Schema

        Args:
            templates: 模板列表

        Returns:
            JSON Schema字符串
        """
        violations = {}

        for template in templates:
            violations[template['json_field_name']] = {
                "has_violation": False,
                "confidence": 0.0,
                "violation_count": 0,
                "conclusion": "未检测到违规",
                "details": []
            }

        schema = {
            "violations": violations
        }

        return json.dumps(schema, indent=2, ensure_ascii=False)

    async def clear_cache(self):
        """清空缓存（用于测试或配置更新后）"""
        async with self._lock:
            self._cache.clear()
            self._cache_timestamp = None
            logger.info("✅ 提示词缓存已清空")

    def get_cache_info(self) -> Dict:
        """
        获取缓存信息（用于监控）

        Returns:
            {
                'size': 缓存大小,
                'timestamp': 缓存时间戳,
                'age_seconds': 缓存年龄（秒）,
                'is_valid': 是否有效
            }
        """
        age_seconds = 0
        if self._cache_timestamp:
            age_seconds = (datetime.now() - self._cache_timestamp).total_seconds()

        return {
            'size': len(self._cache),
            'timestamp': self._cache_timestamp.isoformat() if self._cache_timestamp else None,
            'age_seconds': age_seconds,
            'is_valid': self._is_cache_valid(),
            'ttl_seconds': self._cache_ttl.total_seconds()
        }


# 全局单例实例（应用级别共享）
_global_prompt_engine: Optional[PromptTemplateEngine] = None


def get_prompt_engine() -> PromptTemplateEngine:
    """
    获取全局提示词引擎实例（单例模式）

    Returns:
        PromptTemplateEngine实例
    """
    global _global_prompt_engine

    if _global_prompt_engine is None:
        _global_prompt_engine = PromptTemplateEngine()
        logger.info("✅ 创建全局PromptTemplateEngine实例")

    return _global_prompt_engine
