"""
视频分析模板服务
从数据库获取视频配置的AI分析算法
纯异步版本


"""

import logging
from typing import List, Optional, Dict, Any
from sqlalchemy import select

from database.connection import DatabaseManager
from models.video_analysis_template import VideoAnalysisTemplateDB

logger = logging.getLogger(__name__)


# Detection Type Templates的数据模型（用于类型提示）
# 注意：这些数据来自detection_type_templates表，不是ORM模型
DetectionTypeTemplate = Dict[str, Any]


class VideoAnalysisTemplateService:
    """视频分析模板服务（纯异步版本）"""

    @staticmethod
    async def get_video_analysis_templates(video_id: str) -> List[Dict[str, Any]]:
        """获取指定视频的分析模板配置（包含detection_type_templates的display_name）"""
        async with DatabaseManager.get_session() as session:
            try:
                # 使用原生SQL查询，JOIN detection_type_templates表获取display_name
                from sqlalchemy import text

                query = text("""
                    SELECT
                        vat.id,
                        vat.template_id,
                        vat.template_name,
                        vat.name,
                        vat.category,
                        vat.description,
                        vat.prompt_content,
                        vat.priority,
                        vat.enabled,
                        vat.analysis_status,
                        vat.progress,
                        vat.confidence_avg,
                        vat.created_at,
                        vat.updated_at,
                        vat.detection_type_code,
                        dtt.display_name,
                        dtt.severity
                    FROM video_analysis_templates vat
                    LEFT JOIN detection_type_templates dtt
                        ON vat.detection_type_code = dtt.type_code
                    WHERE vat.video_id = :video_id
                        AND vat.enabled = TRUE
                    ORDER BY vat.priority DESC
                """)

                result = await session.execute(query, {"video_id": video_id})
                rows = result.fetchall()

                if not rows:
                    logger.warning(f"未找到视频 {video_id} 的分析模板配置")
                    return []

                # 转换为字典格式
                template_list = []
                for row in rows:
                    # 优先使用detection_type_templates的display_name（全中文）
                    # 如果没有关联到detection_type_templates，则使用video_analysis_templates.name
                    display_name = row[15] if row[15] else row[3]  # row[15]是dtt.display_name, row[3]是vat.name

                    template_dict = {
                        'id': str(row[0]),
                        'template_id': str(row[1]) if row[1] else None,
                        'template_name': row[2],
                        'name': display_name,  # 使用display_name（全中文）
                        'category': row[4],
                        'description': row[5],
                        'prompt_content': row[6],
                        'priority': row[7],
                        'enabled': row[8],
                        'analysis_status': row[9],
                        'progress': row[10],
                        'confidence_avg': row[11],
                        'created_at': row[12],
                        'updated_at': row[13],
                        # 复合检测关键字段
                        'detection_type_code': row[14],
                        'display_name': display_name,  # 新增字段，确保有display_name
                        'severity': row[16] if row[16] else 'medium'  # 从detection_type_templates获取severity
                    }
                    template_list.append(template_dict)

                logger.info(f"找到 {len(template_list)} 个分析模板用于视频 {video_id}")
                return template_list
            except Exception as e:
                logger.error(f"获取视频分析模板失败 {video_id}: {e}")
                return []

    @staticmethod
    async def create_default_templates_for_video(video_id: str) -> List[Dict[str, Any]]:
        """为视频创建默认的分析模板配置"""
        async with DatabaseManager.get_session() as session:
            try:
                # 定义默认的分析算法
                default_algorithms = [
                    {
                        'name': '通用视频内容分析',
                        'category': 'general_analysis',
                        'description': '对视频内容进行全面分析，识别对象、行为和异常情况',
                        'prompt_content': '''请仔细分析这张图片，描述图片中的内容，包括：
1. 主要对象和人物
2. 场景环境
3. 正在进行的活动或行为
4. 任何异常或需要注意的情况
5. 整体安全状况评估

请以客观、详细的方式描述，如果发现任何安全隐患或异常情况，请特别标注。''',
                        'priority': 1,
                        'enabled': True
                    },
                    {
                        'name': '安全监控分析',
                        'category': 'security_monitoring',
                        'description': '专注于安全相关的分析，检测潜在风险',
                        'prompt_content': '''请从安全监控的角度分析这张图片：
1. 是否存在安全隐患？
2. 人员行为是否正常？
3. 设备设施状态如何？
4. 环境是否安全？
5. 是否需要立即关注？

如果发现任何安全问题或异常情况，请明确指出并评估严重程度。置信度请用数字表示(0.0-1.0)。''',
                        'priority': 2,
                        'enabled': True
                    },
                    {
                        'name': '行为模式识别',
                        'category': 'behavior_analysis',
                        'description': '识别和分析人员行为模式',
                        'prompt_content': '''请分析图片中的人员行为：
1. 识别所有可见人员
2. 分析每个人的动作和姿态
3. 判断行为是否符合场景预期
4. 识别任何异常行为模式
5. 评估行为的合理性

重点关注：聚集、奔跑、争执、摔倒等异常行为。如发现异常请详细描述。''',
                        'priority': 3,
                        'enabled': True
                    }
                ]

                created_templates = []

                for i, algo in enumerate(default_algorithms):
                    template = VideoAnalysisTemplateDB(
                        video_id=video_id,
                        template_name=algo['name'],
                        name=algo['name'],
                        category=algo['category'],
                        description=algo['description'],
                        prompt_content=algo['prompt_content'],
                        priority=algo['priority'],
                        enabled=algo['enabled'],
                        analysis_status='ready'
                    )

                    session.add(template)
                    created_templates.append({
                        'id': str(template.id),
                        'name': template.name,
                        'category': template.category,
                        'prompt_content': template.prompt_content,
                        'priority': template.priority,
                        'enabled': template.enabled
                    })

                await session.commit()

                logger.info(f"为视频 {video_id} 创建了 {len(created_templates)} 个默认分析模板")
                return created_templates
            except Exception as e:
                logger.error(f"创建默认分析模板失败 {video_id}: {e}")
                return []

    @staticmethod
    async def get_or_create_video_templates(video_id: str) -> List[Dict[str, Any]]:
        """获取或创建视频的分析模板"""
        templates = await VideoAnalysisTemplateService.get_video_analysis_templates(video_id)

        if not templates:
            logger.info(f"视频 {video_id} 没有分析模板配置，创建默认模板")
            templates = await VideoAnalysisTemplateService.create_default_templates_for_video(video_id)

        return templates

    @staticmethod
    async def get_detection_type_templates() -> List[DetectionTypeTemplate]:
        """
        获取所有可用的检测类型模板（用于复合检测）

        Returns:
            检测类型模板列表，包含type_code, name, category等信息
        """
        async with DatabaseManager.get_session() as session:
            try:
                # 使用原始SQL查询detection_type_templates表
                from sqlalchemy import text

                query = text("""
                    SELECT
                        type_code,
                        display_name,
                        category,
                        severity,
                        description,
                        prompt_template,
                        json_field_name,
                        sort_order,
                        enabled,
                        created_at,
                        updated_at
                    FROM detection_type_templates
                    WHERE enabled = true
                    ORDER BY sort_order ASC, type_code ASC
                """)

                result = await session.execute(query)
                rows = result.fetchall()

                templates = []
                for row in rows:
                    template = {
                        'type_code': row[0],
                        'display_name': row[1],  # 🔧 修复：改为display_name，与数据库字段一致
                        'category': row[2],
                        'severity': row[3],
                        'description': row[4],
                        'prompt_template': row[5],
                        'json_schema': row[6],
                        'sort_order': row[7],
                        'enabled': row[8],
                        'created_at': row[9],
                        'updated_at': row[10]
                    }
                    templates.append(template)

                logger.info(f"获取到 {len(templates)} 个检测类型模板")
                return templates

            except Exception as e:
                logger.error(f"获取检测类型模板失败: {e}")
                import traceback
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                return []

    @staticmethod
    async def get_detection_type_by_code(type_code: str) -> Optional[DetectionTypeTemplate]:
        """
        根据type_code获取单个检测类型模板

        Args:
            type_code: 检测类型编码（如safety_helmet, smoking等）

        Returns:
            检测类型模板，如果不存在则返回None
        """
        async with DatabaseManager.get_session() as session:
            try:
                from sqlalchemy import text

                query = text("""
                    SELECT
                        type_code,
                        display_name,
                        category,
                        severity,
                        description,
                        prompt_template,
                        json_field_name,
                        sort_order,
                        enabled,
                        created_at,
                        updated_at
                    FROM detection_type_templates
                    WHERE type_code = :type_code AND enabled = true
                """)

                result = await session.execute(query, {'type_code': type_code})
                row = result.fetchone()

                if not row:
                    logger.warning(f"未找到检测类型: {type_code}")
                    return None

                template = {
                    'type_code': row[0],
                    'display_name': row[1],  # 🔧 关键修复：字段名从'name'改为'display_name'，与数据库列名一致
                    'category': row[2],
                    'severity': row[3],
                    'description': row[4],
                    'prompt_template': row[5],
                    'json_schema': row[6],
                    'sort_order': row[7],
                    'enabled': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }

                return template

            except Exception as e:
                logger.error(f"获取检测类型模板失败 {type_code}: {e}")
                return None

    @staticmethod
    async def create_detection_type_template(template_data: Dict[str, Any]) -> Optional[DetectionTypeTemplate]:
        """
        创建新的检测类型模板

        Args:
            template_data: 模板数据，包含type_code, display_name, category等字段

        Returns:
            创建的模板数据，如果失败返回None
        """
        async with DatabaseManager.get_session() as session:
            try:
                from sqlalchemy import text

                # 检查type_code是否已存在
                check_query = text("""
                    SELECT COUNT(*) FROM detection_type_templates WHERE type_code = :type_code
                """)
                result = await session.execute(check_query, {'type_code': template_data.get('type_code')})
                count = result.scalar()

                if count > 0:
                    logger.warning(f"检测类型编码已存在: {template_data.get('type_code')}")
                    raise ValueError(f"检测类型编码已存在: {template_data.get('type_code')}")

                # 插入新模板
                insert_query = text("""
                    INSERT INTO detection_type_templates
                        (type_code, display_name, category, prompt_template, json_field_name,
                         severity, sort_order, enabled, description, example_scenarios)
                    VALUES
                        (:type_code, :display_name, :category, :prompt_template, :json_field_name,
                         :severity, :sort_order, :enabled, :description, :example_scenarios)
                    RETURNING
                        type_code, display_name, category, severity, description,
                        prompt_template, json_field_name, sort_order, enabled,
                        created_at, updated_at
                """)

                result = await session.execute(insert_query, {
                    'type_code': template_data.get('type_code'),
                    'display_name': template_data.get('display_name'),
                    'category': template_data.get('category'),
                    'prompt_template': template_data.get('prompt_template', ''),
                    'json_field_name': template_data.get('json_field_name', template_data.get('type_code')),
                    'severity': template_data.get('severity', 'medium'),
                    'sort_order': template_data.get('sort_order', 0),
                    'enabled': template_data.get('enabled', True),
                    'description': template_data.get('description', ''),
                    'example_scenarios': template_data.get('example_scenarios', '')
                })

                row = result.fetchone()
                await session.commit()

                template = {
                    'type_code': row[0],
                    'display_name': row[1],  # 🔧 关键修复：字段名从'name'改为'display_name'，与数据库列名一致
                    'category': row[2],
                    'severity': row[3],
                    'description': row[4],
                    'prompt_template': row[5],
                    'json_schema': row[6],
                    'sort_order': row[7],
                    'enabled': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }

                logger.info(f"成功创建检测类型模板: {template['type_code']}")
                return template

            except ValueError as ve:
                logger.error(f"创建检测类型模板失败: {ve}")
                raise
            except Exception as e:
                logger.error(f"创建检测类型模板失败: {e}")
                import traceback
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                await session.rollback()
                return None

    @staticmethod
    async def update_detection_type_template(type_code: str, template_data: Dict[str, Any]) -> Optional[DetectionTypeTemplate]:
        """
        更新检测类型模板

        Args:
            type_code: 要更新的模板编码
            template_data: 更新的数据

        Returns:
            更新后的模板数据，如果失败返回None
        """
        async with DatabaseManager.get_session() as session:
            try:
                from sqlalchemy import text

                # 检查模板是否存在
                check_query = text("""
                    SELECT COUNT(*) FROM detection_type_templates WHERE type_code = :type_code
                """)
                result = await session.execute(check_query, {'type_code': type_code})
                count = result.scalar()

                if count == 0:
                    logger.warning(f"检测类型不存在: {type_code}")
                    raise ValueError(f"检测类型不存在: {type_code}")

                # 构建更新语句
                update_fields = []
                params = {'type_code': type_code}

                if 'display_name' in template_data:
                    update_fields.append("display_name = :display_name")
                    params['display_name'] = template_data['display_name']
                if 'category' in template_data:
                    update_fields.append("category = :category")
                    params['category'] = template_data['category']
                if 'prompt_template' in template_data:
                    update_fields.append("prompt_template = :prompt_template")
                    params['prompt_template'] = template_data['prompt_template']
                if 'json_field_name' in template_data:
                    update_fields.append("json_field_name = :json_field_name")
                    params['json_field_name'] = template_data['json_field_name']
                if 'severity' in template_data:
                    update_fields.append("severity = :severity")
                    params['severity'] = template_data['severity']
                if 'sort_order' in template_data:
                    update_fields.append("sort_order = :sort_order")
                    params['sort_order'] = template_data['sort_order']
                if 'enabled' in template_data:
                    update_fields.append("enabled = :enabled")
                    params['enabled'] = template_data['enabled']
                if 'description' in template_data:
                    update_fields.append("description = :description")
                    params['description'] = template_data['description']
                if 'example_scenarios' in template_data:
                    update_fields.append("example_scenarios = :example_scenarios")
                    params['example_scenarios'] = template_data['example_scenarios']

                if not update_fields:
                    logger.warning("没有要更新的字段")
                    return await VideoAnalysisTemplateService.get_detection_type_by_code(type_code)

                # 执行更新
                update_query = text(f"""
                    UPDATE detection_type_templates
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE type_code = :type_code
                    RETURNING
                        type_code, display_name, category, severity, description,
                        prompt_template, json_field_name, sort_order, enabled,
                        created_at, updated_at
                """)

                result = await session.execute(update_query, params)
                row = result.fetchone()
                await session.commit()

                template = {
                    'type_code': row[0],
                    'display_name': row[1],  # 🔧 关键修复：字段名从'name'改为'display_name'，与数据库列名一致
                    'category': row[2],
                    'severity': row[3],
                    'description': row[4],
                    'prompt_template': row[5],
                    'json_schema': row[6],
                    'sort_order': row[7],
                    'enabled': row[8],
                    'created_at': row[9],
                    'updated_at': row[10]
                }

                logger.info(f"成功更新检测类型模板: {type_code}")
                return template

            except ValueError as ve:
                logger.error(f"更新检测类型模板失败: {ve}")
                raise
            except Exception as e:
                logger.error(f"更新检测类型模板失败: {e}")
                import traceback
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                await session.rollback()
                return None

    @staticmethod
    async def delete_detection_type_template(type_code: str) -> bool:
        """
        删除检测类型模板（软删除：设置enabled=false）

        Args:
            type_code: 要删除的模板编码

        Returns:
            成功返回True，失败返回False
        """
        async with DatabaseManager.get_session() as session:
            try:
                from sqlalchemy import text

                # 检查模板是否存在
                check_query = text("""
                    SELECT COUNT(*) FROM detection_type_templates WHERE type_code = :type_code
                """)
                result = await session.execute(check_query, {'type_code': type_code})
                count = result.scalar()

                if count == 0:
                    logger.warning(f"检测类型不存在: {type_code}")
                    raise ValueError(f"检测类型不存在: {type_code}")

                # 软删除：设置enabled=false
                delete_query = text("""
                    UPDATE detection_type_templates
                    SET enabled = false, updated_at = CURRENT_TIMESTAMP
                    WHERE type_code = :type_code
                """)

                await session.execute(delete_query, {'type_code': type_code})
                await session.commit()

                logger.info(f"成功删除检测类型模板: {type_code}")
                return True

            except ValueError as ve:
                logger.error(f"删除检测类型模板失败: {ve}")
                raise
            except Exception as e:
                logger.error(f"删除检测类型模板失败: {e}")
                import traceback
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                await session.rollback()
                return False

    @staticmethod
    async def batch_import_detection_types(templates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        批量导入检测类型模板

        Args:
            templates: 模板列表

        Returns:
            导入结果统计
        """
        async with DatabaseManager.get_session() as session:
            try:
                success_count = 0
                fail_count = 0
                errors = []

                for template_data in templates:
                    try:
                        # 检查type_code是否已存在
                        from sqlalchemy import text
                        check_query = text("""
                            SELECT COUNT(*) FROM detection_type_templates WHERE type_code = :type_code
                        """)
                        result = await session.execute(check_query, {'type_code': template_data.get('type_code')})
                        count = result.scalar()

                        if count > 0:
                            # 如果已存在，跳过
                            errors.append(f"跳过重复的type_code: {template_data.get('type_code')}")
                            fail_count += 1
                            continue

                        # 插入新模板
                        insert_query = text("""
                            INSERT INTO detection_type_templates
                                (type_code, display_name, category, prompt_template, json_field_name,
                                 severity, sort_order, enabled, description, example_scenarios)
                            VALUES
                                (:type_code, :display_name, :category, :prompt_template, :json_field_name,
                                 :severity, :sort_order, :enabled, :description, :example_scenarios)
                        """)

                        await session.execute(insert_query, {
                            'type_code': template_data.get('type_code'),
                            'display_name': template_data.get('display_name'),
                            'category': template_data.get('category'),
                            'prompt_template': template_data.get('prompt_template', ''),
                            'json_field_name': template_data.get('json_field_name', template_data.get('type_code')),
                            'severity': template_data.get('severity', 'medium'),
                            'sort_order': template_data.get('sort_order', 0),
                            'enabled': template_data.get('enabled', True),
                            'description': template_data.get('description', ''),
                            'example_scenarios': template_data.get('example_scenarios', '')
                        })

                        success_count += 1

                    except Exception as e:
                        fail_count += 1
                        errors.append(f"导入失败 {template_data.get('type_code', 'unknown')}: {str(e)}")
                        logger.error(f"导入模板失败: {e}")

                await session.commit()

                result = {
                    'success_count': success_count,
                    'fail_count': fail_count,
                    'total': len(templates),
                    'errors': errors
                }

                logger.info(f"批量导入完成: 成功{success_count}个，失败{fail_count}个")
                return result

            except Exception as e:
                logger.error(f"批量导入失败: {e}")
                import traceback
                logger.error(f"异常堆栈: {traceback.format_exc()}")
                await session.rollback()
                return {
                    'success_count': 0,
                    'fail_count': len(templates),
                    'total': len(templates),
                    'errors': [str(e)]
                }


# 创建全局实例
video_analysis_template_service = VideoAnalysisTemplateService()
