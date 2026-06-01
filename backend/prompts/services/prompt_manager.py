"""
AI提示词多维度管理服务
支持分类管理、动态变量、模板继承等高级功能
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import uuid4

from models.prompt import (
    PromptTemplate, PromptCategory
)
from utils.timezone_utils import now, now_isoformat

logger = logging.getLogger(__name__)


class PromptManager:
    """提示词管理器"""
    
    def __init__(self):
        self._templates_cache: Dict[str, PromptTemplate] = {}
        self._category_cache: Dict[PromptCategory, List[PromptTemplate]] = {}
        self.data_dir = Path("data/prompts")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 延迟加载系统模板
        self._system_templates_loaded = False
    
    async def create_template(self, name: str, category: PromptCategory, description: str, content: str, 
                            variables: List[str] = None, detection_criteria: List[str] = None,
                            confidence_threshold: float = 0.7, enabled: bool = True) -> PromptTemplate:
        """创建新的提示词模板"""
        try:
            template = PromptTemplate(
                id=str(uuid4()),
                name=name,
                category=category,
                description=description,
                content=content,
                variables=variables or [],
                detection_criteria=detection_criteria or [],
                confidence_threshold=confidence_threshold,
                enabled=enabled,
                created_at=now(),
                updated_at=now()
            )
            
            # 保存模板
            await self._save_template(template)
            
            # 更新缓存
            self._templates_cache[template.id] = template
            self._update_category_cache(template)
            
            logger.info(f"提示词模板已创建: {template.name}")
            return template
            
        except Exception as e:
            logger.error(f"创建提示词模板失败: {e}")
            raise
    
    async def get_template_by_id(self, template_id: str) -> Optional[PromptTemplate]:
        """根据ID获取模板"""
        try:
            # 从缓存获取
            if template_id in self._templates_cache:
                return self._templates_cache[template_id]
            
            # 从文件加载
            template = await self._load_template(template_id)
            if template:
                self._templates_cache[template_id] = template
            
            return template
            
        except Exception as e:
            logger.error(f"获取提示词模板失败: {e}")
            return None
    
    async def get_templates_by_category(self, category: PromptCategory) -> List[PromptTemplate]:
        """按分类获取模板"""
        try:
            # 从缓存获取
            if category in self._category_cache:
                return self._category_cache[category].copy()
            
            # 重建缓存
            await self._rebuild_category_cache()
            return self._category_cache.get(category, [])
            
        except Exception as e:
            logger.error(f"按分类获取模板失败: {e}")
            return []
    
    async def get_all_templates(self, active_only: bool = False) -> List[PromptTemplate]:
        """获取所有模板"""
        try:
            if not self._templates_cache:
                await self._load_all_templates()
            
            templates = list(self._templates_cache.values())
            
            if active_only:
                templates = [t for t in templates if t.is_active]
            
            # 按优先级和创建时间排序
            templates.sort(key=lambda x: (x.priority.value, x.created_at), reverse=True)
            return templates
            
        except Exception as e:
            logger.error(f"获取所有模板失败: {e}")
            return []
    
    async def update_template(self, template_id: str, updates: Dict[str, Any]) -> Optional[PromptTemplate]:
        """更新提示词模板"""
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                return None
            
            # 更新字段
            for field, value in updates.items():
                if hasattr(template, field):
                    setattr(template, field, value)
            
            template.updated_at = now()
            
            # 保存更新
            await self._save_template(template)
            
            # 更新缓存
            self._templates_cache[template_id] = template
            self._update_category_cache(template)
            
            logger.info(f"提示词模板已更新: {template.name}")
            return template
            
        except Exception as e:
            logger.error(f"更新提示词模板失败: {e}")
            raise
    
    async def delete_template(self, template_id: str) -> bool:
        """删除提示词模板"""
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                return False
            
            # 检查是否为系统模板
            if template.is_system_template:
                raise ValueError("无法删除系统模板")
            
            # 删除文件
            template_file = self.data_dir / f"{template_id}.json"
            if template_file.exists():
                template_file.unlink()
            
            # 从缓存移除
            if template_id in self._templates_cache:
                del self._templates_cache[template_id]
            
            # 重建分类缓存
            await self._rebuild_category_cache()
            
            logger.info(f"提示词模板已删除: {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"删除提示词模板失败: {e}")
            return False
    
    async def activate_template(self, template_id: str, category: PromptCategory) -> bool:
        """激活指定分类的模板（同时取消同分类其他模板）"""
        try:
            # 获取目标模板
            template = await self.get_template_by_id(template_id)
            if not template or template.category != category:
                return False
            
            # 取消同分类其他模板的激活状态
            category_templates = await self.get_templates_by_category(category)
            for t in category_templates:
                if t.is_active:
                    t.is_active = False
                    await self._save_template(t)
                    self._templates_cache[t.id] = t
            
            # 激活目标模板
            template.is_active = True
            template.last_used_at = now()
            await self._save_template(template)
            self._templates_cache[template_id] = template
            
            # 更新缓存
            self._update_category_cache(template)
            
            logger.info(f"模板已激活: {template.name}")
            return True
            
        except Exception as e:
            logger.error(f"激活模板失败: {e}")
            return False
    
    async def render_template(self, template_id: str, variables: Dict[str, Any]) -> Optional[str]:
        """渲染提示词模板"""
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                return None
            
            # 合并系统提示词和用户提示词
            full_prompt = f"{template.system_prompt}\n\n{template.user_prompt}"
            
            # 替换变量
            for var in template.variables:
                var_name = var.name
                var_value = variables.get(var_name, var.default_value)
                
                if var.required and var_value is None:
                    raise ValueError(f"必需变量未提供: {var_name}")
                
                # 进行变量替换
                placeholder = f"{{{var_name}}}"
                if placeholder in full_prompt:
                    full_prompt = full_prompt.replace(placeholder, str(var_value))
            
            # 更新使用统计
            template.usage_count += 1
            template.last_used_at = now()
            await self._save_template(template)
            
            return full_prompt
            
        except Exception as e:
            logger.error(f"渲染模板失败: {e}")
            raise
    
    async def get_template_usage_stats(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板使用统计"""
        try:
            template = await self.get_template_by_id(template_id)
            if not template:
                return None
            
            return {
                "usage_count": template.usage_count,
                "success_rate": template.success_rate,
                "avg_confidence": template.avg_confidence,
                "last_used_at": template.last_used_at.isoformat() if template.last_used_at else None,
                "created_at": template.created_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取模板统计失败: {e}")
            return None
    
    async def search_templates(self, keyword: str, category: Optional[PromptCategory] = None) -> List[PromptTemplate]:
        """搜索提示词模板"""
        try:
            all_templates = await self.get_all_templates()
            
            # 过滤分类
            if category:
                all_templates = [t for t in all_templates if t.category == category]
            
            # 关键词搜索
            keyword_lower = keyword.lower()
            matched_templates = []
            
            for template in all_templates:
                if (keyword_lower in template.name.lower() or
                    keyword_lower in template.description.lower() or
                    any(keyword_lower in tag.lower() for tag in template.tags)):
                    matched_templates.append(template)
            
            return matched_templates
            
        except Exception as e:
            logger.error(f"搜索模板失败: {e}")
            return []
    
    async def _save_template(self, template: PromptTemplate):
        """保存模板到文件"""
        template_file = self.data_dir / f"{template.id}.json"
        with open(template_file, 'w', encoding='utf-8') as f:
            f.write(template.json(ensure_ascii=False, indent=2))
    
    async def _load_template(self, template_id: str) -> Optional[PromptTemplate]:
        """从文件加载模板"""
        try:
            template_file = self.data_dir / f"{template_id}.json"
            if not template_file.exists():
                return None
            
            with open(template_file, 'r', encoding='utf-8') as f:
                data = f.read()
            
            return PromptTemplate.parse_raw(data)
            
        except Exception as e:
            logger.error(f"加载模板失败: {e}")
            return None
    
    async def _load_all_templates(self):
        """加载所有模板到缓存"""
        try:
            self._templates_cache.clear()
            
            for template_file in self.data_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        data = f.read()
                    template = PromptTemplate.parse_raw(data)
                    self._templates_cache[template.id] = template
                except Exception as e:
                    logger.error(f"加载模板文件失败 {template_file}: {e}")
            
            # 重建分类缓存
            await self._rebuild_category_cache()
            
        except Exception as e:
            logger.error(f"加载所有模板失败: {e}")
    
    async def _rebuild_category_cache(self):
        """重建分类缓存"""
        self._category_cache.clear()
        
        for template in self._templates_cache.values():
            self._update_category_cache(template)
    
    def _update_category_cache(self, template: PromptTemplate):
        """更新分类缓存"""
        category = template.category
        if category not in self._category_cache:
            self._category_cache[category] = []
        
        # 移除旧版本
        self._category_cache[category] = [
            t for t in self._category_cache[category] if t.id != template.id
        ]
        
        # 添加新版本
        self._category_cache[category].append(template)
    
    async def _load_system_templates(self):
        """加载系统预置模板"""
        try:
            # 安全帽检测模板
            safety_helmet_template = PromptTemplate(
                name="安全帽佩戴检测",
                category=PromptCategory.SAFETY_DETECTION,
                priority=PromptPriority.HIGH,
                system_prompt="你是一个专业的安全监控AI助手，专门检测工作场所的安全帽佩戴情况。",
                user_prompt="""请仔细检测图像中的人员是否正确佩戴安全帽。重点关注：
1. 每个人员是否佩戴安全帽
2. 安全帽佩戴是否规范（正确位置、固定良好）
3. 安全帽类型是否符合工作环境要求

如果发现人员未佩戴安全帽或佩戴不当，请：
- 明确指出具体的违规行为
- 给出违规行为的置信度值（0-1）
- 描述违规人员的位置和特征
- 评估安全风险等级

当前时间：{current_time}
分析帧时间：{frame_timestamp}""",
                description="检测工作场所人员安全帽佩戴情况，确保作业安全",
                variables=[
                    PromptVariable(
                        name="current_time",
                        type="datetime",
                        description="当前系统时间",
                        required=True,
                        example_value="2024-01-01 12:00:00"
                    ),
                    PromptVariable(
                        name="frame_timestamp",
                        type="datetime", 
                        description="视频帧时间戳",
                        required=True,
                        example_value="2024-01-01 12:00:05"
                    )
                ],
                detection_criteria=DetectionCriteria(
                    confidence_threshold=0.8,
                    detection_keywords=["未佩戴", "佩戴不当", "安全帽", "违规"],
                    exclusion_keywords=["无异常", "正常", "符合要求"],
                    severity_mapping={
                        "未佩戴安全帽": "high",
                        "佩戴不当": "medium",
                        "安全帽松动": "medium"
                    },
                    enable_annotation=True,
                    annotation_style={
                        "box_color": "#FF0000",
                        "text_color": "#FFFFFF", 
                        "font_size": 14
                    }
                ),
                applicable_scenarios=["建筑工地", "工厂车间", "化工区域"],
                supported_models=["qwen-vl", "moonshot"],
                is_system_template=True,
                tags=["安全", "防护", "合规"]
            )
            
            # 人员聚集检测模板
            crowd_detection_template = PromptTemplate(
                name="人员聚集异常检测",
                category=PromptCategory.BEHAVIOR_ANALYSIS,
                priority=PromptPriority.MEDIUM,
                system_prompt="你是一个行为分析AI助手，专门检测视频中的人员聚集和异常行为。",
                user_prompt="""请分析图像中的人员分布和行为模式：
1. 统计画面中的人员数量
2. 分析人员聚集程度和分布
3. 识别是否存在异常聚集行为
4. 评估潜在的安全风险

重点检测：
- 超过{max_people_count}人的异常聚集
- 在{restricted_areas}区域的人员聚集
- 非工作时间的人员聚集
- 紧急出口或通道堵塞

当前时间：{current_time}
区域规则：{area_rules}""",
                description="检测人员聚集异常，预防踩踏和安全事故",
                variables=[
                    PromptVariable(
                        name="max_people_count",
                        type="number",
                        description="最大允许人数",
                        default_value=10,
                        required=True
                    ),
                    PromptVariable(
                        name="restricted_areas",
                        type="string",
                        description="限制区域列表",
                        default_value="设备间,仓库,办公区",
                        required=False
                    ),
                    PromptVariable(
                        name="current_time",
                        type="datetime",
                        description="当前时间",
                        required=True
                    ),
                    PromptVariable(
                        name="area_rules",
                        type="string",
                        description="区域规则说明",
                        default_value="工作区域允许聚集，休息区域限制人数",
                        required=False
                    )
                ],
                detection_criteria=DetectionCriteria(
                    confidence_threshold=0.7,
                    detection_keywords=["人员聚集", "超员", "堵塞", "异常聚集"],
                    exclusion_keywords=["正常", "无异常", "人数合理"],
                    severity_mapping={
                        "严重超员": "critical",
                        "人员聚集": "medium",
                        "通道堵塞": "high"
                    }
                ),
                applicable_scenarios=["商场", "车站", "工厂", "学校"],
                is_system_template=True,
                tags=["行为分析", "人员管理", "安全"]
            )
            
            # 保存系统模板
            system_templates = [safety_helmet_template, crowd_detection_template]
            for template in system_templates:
                await self._save_template(template)
                self._templates_cache[template.id] = template
                self._update_category_cache(template)
            
            logger.info(f"系统模板已加载: {len(system_templates)} 个")
            
        except Exception as e:
            logger.error(f"加载系统模板失败: {e}")
    
    async def get_categories_summary(self) -> Dict[str, Dict[str, Any]]:
        """获取分类汇总信息"""
        try:
            if not self._category_cache:
                await self._rebuild_category_cache()
            
            summary = {}
            for category, templates in self._category_cache.items():
                active_templates = [t for t in templates if t.is_active]
                
                summary[category.value] = {
                    "total_count": len(templates),
                    "active_count": len(active_templates),
                    "active_template": active_templates[0].dict() if active_templates else None,
                    "avg_usage": sum(t.usage_count for t in templates) / len(templates) if templates else 0
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取分类汇总失败: {e}")
            return {}