"""
AI提示词模板管理API路由
处理多维度提示词模板的CRUD操作
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.prompt import PromptTemplate, PromptCategory
from prompts.services.prompt_manager import PromptManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/prompts/templates", tags=["prompt_templates"])

# 初始化服务
prompt_manager = PromptManager()


class PromptTemplateCreateRequest(BaseModel):
    """创建提示词模板请求"""
    name: str
    category: PromptCategory
    description: str
    content: str
    variables: Optional[List[str]] = []
    detection_criteria: Optional[List[str]] = []
    confidence_threshold: Optional[float] = 0.7
    enabled: bool = True


class PromptTemplateUpdateRequest(BaseModel):
    """更新提示词模板请求"""
    name: Optional[str] = None
    category: Optional[PromptCategory] = None
    description: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    detection_criteria: Optional[List[str]] = None
    confidence_threshold: Optional[float] = None
    enabled: Optional[bool] = None


@router.get("/list")
async def list_templates(
    category: Optional[PromptCategory] = None,
    enabled: Optional[bool] = None
):
    """获取提示词模板列表"""
    try:
        templates = await prompt_manager.get_all_templates()
        return {
            "status": "success",
            "data": [template.model_dump() for template in templates],
            "total": len(templates)
        }
    except Exception as e:
        logger.error(f"获取提示词模板列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取提示词模板列表失败: {str(e)}")


@router.post("/create")
async def create_template(request: PromptTemplateCreateRequest):
    """创建提示词模板"""
    try:
        template = await prompt_manager.create_template(
            name=request.name,
            category=request.category,
            description=request.description,
            content=request.content,
            variables=request.variables,
            detection_criteria=request.detection_criteria,
            confidence_threshold=request.confidence_threshold,
            enabled=request.enabled
        )
        
        return {
            "status": "success",
            "message": "提示词模板创建成功",
            "data": template.model_dump()
        }
    except Exception as e:
        logger.error(f"创建提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建提示词模板失败: {str(e)}")


@router.get("/{template_id}")
async def get_template(template_id: str):
    """获取提示词模板详情"""
    try:
        template = await prompt_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="提示词模板不存在")
        
        return {
            "status": "success",
            "data": template.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取提示词模板详情失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取提示词模板详情失败: {str(e)}")


@router.put("/{template_id}")
async def update_template(template_id: str, request: PromptTemplateUpdateRequest):
    """更新提示词模板"""
    try:
        template = await prompt_manager.update_template(template_id, request.model_dump(exclude_unset=True))
        if not template:
            raise HTTPException(status_code=404, detail="提示词模板不存在")
        
        return {
            "status": "success",
            "message": "提示词模板更新成功",
            "data": template.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新提示词模板失败: {str(e)}")


@router.delete("/{template_id}")
async def delete_template(template_id: str):
    """删除提示词模板"""
    try:
        success = await prompt_manager.delete_template(template_id)
        if not success:
            raise HTTPException(status_code=404, detail="提示词模板不存在")
        
        return {
            "status": "success",
            "message": "提示词模板删除成功"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除提示词模板失败: {str(e)}")


@router.post("/{template_id}/test")
async def test_template(template_id: str, test_data: dict):
    """测试提示词模板"""
    try:
        template = await prompt_manager.get_template(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="提示词模板不存在")
        
        # 渲染提示词模板
        rendered_prompt = await prompt_manager.render_template(template_id, test_data)
        
        return {
            "status": "success",
            "data": {
                "template_id": template_id,
                "rendered_prompt": rendered_prompt,
                "test_data": test_data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试提示词模板失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试提示词模板失败: {str(e)}")


@router.get("/categories/list")
async def list_categories():
    """获取提示词类别列表"""
    try:
        categories = [
            {
                "value": category.value,
                "label": category.value,
                "description": _get_category_description(category)
            }
            for category in PromptCategory
        ]
        
        return {
            "status": "success",
            "data": categories
        }
    except Exception as e:
        logger.error(f"获取类别列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取类别列表失败: {str(e)}")


def _get_category_description(category: PromptCategory) -> str:
    """获取类别描述"""
    descriptions = {
        PromptCategory.SAFETY_DETECTION: "用于检测安全相关的违规行为，如未佩戴安全帽、违规操作等",
        PromptCategory.BEHAVIOR_ANALYSIS: "用于分析人员行为模式，如聚集、冲突、异常行为等",
        PromptCategory.OBJECT_RECOGNITION: "用于识别和检测特定物品、设备或环境要素",
        PromptCategory.ENVIRONMENT_MONITOR: "用于监控环境变化，如天气、光线、清洁状况等"
    }
    return descriptions.get(category, "未知类别")