"""
AI模型管理API端点
提供模型性能监控、选择策略配置等功能
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

from services.ai_model_selector import ai_model_selector, ModelType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-models", tags=["AI模型管理"])


class ModelSelectionRequest(BaseModel):
    """模型选择请求"""
    template_name: str = Field(..., description="模板名称")
    template_content: str = Field(..., description="模板内容")
    category: str = Field("safety_detection", description="任务类别")
    priority: str = Field("balanced", description="优化目标")
    image_width: Optional[int] = Field(None, description="图像宽度")
    image_height: Optional[int] = Field(None, description="图像高度")


class ModelPerformanceUpdate(BaseModel):
    """模型性能更新"""
    model_config = ConfigDict(protected_namespaces=())
    
    model_type: str = Field(..., description="模型类型")
    success: bool = Field(..., description="是否成功")
    response_time: float = Field(..., description="响应时间(秒)")
    confidence: float = Field(0.0, description="置信度")
    error: Optional[str] = Field(None, description="错误信息")


@router.get("/performance-report", summary="获取模型性能报告")
async def get_performance_report():
    """
    获取所有AI模型的性能统计报告
    包括成功率、响应时间、置信度等指标
    """
    try:
        report = ai_model_selector.get_performance_report()
        return {
            "success": True,
            "data": report
        }
    except Exception as e:
        logger.error(f"获取性能报告失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取报告失败: {str(e)}")


@router.post("/select-model", summary="智能选择AI模型")
async def select_model(request: ModelSelectionRequest):
    """
    基于任务需求智能选择最适合的AI模型
    """
    try:
        from services.ai_model_selector import PromptTemplate, PromptCategory, PromptPriority
        
        # 创建简化模板
        category_map = {
            "safety_detection": PromptCategory.SAFETY_DETECTION,
            "behavior_analysis": PromptCategory.BEHAVIOR_ANALYSIS,
            "object_detection": PromptCategory.OBJECT_DETECTION,
            "scene_understanding": PromptCategory.SCENE_UNDERSTANDING
        }
        
        template = PromptTemplate(
            id="api_request",
            name=request.template_name,
            category=category_map.get(request.category, PromptCategory.SAFETY_DETECTION),
            content=request.template_content,
            priority=PromptPriority.MEDIUM
        )
        
        # 智能选择模型
        image_size = None
        if request.image_width and request.image_height:
            image_size = (request.image_width, request.image_height)
        
        selected_model = await ai_model_selector.select_best_model(
            template=template,
            image_size=image_size,
            priority=request.priority
        )
        
        # 获取预期性能
        expected_performance = ai_model_selector._predict_performance(template, selected_model)
        
        # 获取选择理由
        selection_reason = ai_model_selector._get_selection_reason(template, selected_model)
        
        return {
            "success": True,
            "data": {
                "recommended_model": selected_model.value,
                "expected_performance": expected_performance,
                "selection_reason": selection_reason,
                "template_info": {
                    "name": request.template_name,
                    "category": request.category,
                    "priority": request.priority
                }
            }
        }
        
    except Exception as e:
        logger.error(f"模型选择失败: {e}")
        raise HTTPException(status_code=500, detail=f"模型选择失败: {str(e)}")


@router.post("/update-performance", summary="更新模型性能数据")
async def update_performance(update: ModelPerformanceUpdate):
    """
    手动更新模型性能统计数据
    用于外部系统上报性能指标
    """
    try:
        # 验证模型类型
        try:
            model_type = ModelType(update.model_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"不支持的模型类型: {update.model_type}")
        
        # 记录性能数据
        await ai_model_selector.record_model_performance(
            model_type=model_type,
            success=update.success,
            response_time=update.response_time,
            confidence=update.confidence,
            error=update.error
        )
        
        return {
            "success": True,
            "message": "性能数据已更新",
            "model_type": update.model_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新性能数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@router.get("/model-capabilities", summary="获取模型能力信息")
async def get_model_capabilities():
    """
    获取所有支持的AI模型的能力描述
    """
    try:
        capabilities = {}
        
        for model_type, capability in ai_model_selector.model_capabilities.items():
            capabilities[model_type.value] = {
                "vision_quality": capability.vision_quality,
                "text_reasoning": capability.text_reasoning,
                "response_speed": capability.response_speed,
                "reliability": capability.reliability,
                "cost_efficiency": capability.cost_efficiency,
                "supported_languages": capability.supported_languages,
                "max_image_size": capability.max_image_size,
                "context_window": capability.context_window,
                "specialized_tasks": capability.specialized_tasks
            }
        
        return {
            "success": True,
            "data": {
                "supported_models": list(capabilities.keys()),
                "capabilities": capabilities,
                "total_models": len(capabilities)
            }
        }
        
    except Exception as e:
        logger.error(f"获取模型能力失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取能力信息失败: {str(e)}")


@router.get("/recommendations", summary="获取批量模型推荐")
async def get_model_recommendations(
    template_names: str = Query(..., description="模板名称列表，逗号分隔"),
    category: str = Query("safety_detection", description="任务类别")
):
    """
    为多个模板批量推荐最适合的AI模型
    """
    try:
        from services.ai_model_selector import PromptTemplate, PromptCategory, PromptPriority
        
        # 解析模板名称
        template_name_list = [name.strip() for name in template_names.split(",")]
        
        # 创建模板列表
        category_map = {
            "safety_detection": PromptCategory.SAFETY_DETECTION,
            "behavior_analysis": PromptCategory.BEHAVIOR_ANALYSIS,
            "object_detection": PromptCategory.OBJECT_DETECTION,
            "scene_understanding": PromptCategory.SCENE_UNDERSTANDING
        }
        
        templates = []
        for i, name in enumerate(template_name_list):
            template = PromptTemplate(
                id=f"batch_{i}",
                name=name,
                category=category_map.get(category, PromptCategory.SAFETY_DETECTION),
                content=f"Template for {name}",
                priority=PromptPriority.MEDIUM
            )
            templates.append(template)
        
        # 获取批量推荐
        recommendations = await ai_model_selector.get_model_recommendations(templates)
        
        return {
            "success": True,
            "data": {
                "recommendations": recommendations,
                "total_templates": len(templates),
                "category": category
            }
        }
        
    except Exception as e:
        logger.error(f"获取批量推荐失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量推荐失败: {str(e)}")


@router.post("/optimize-assignments", summary="优化模型分配")
async def optimize_model_assignments(
    template_count: int = Query(10, description="模板数量"),
    category: str = Query("safety_detection", description="任务类别")
):
    """
    优化多个模板的模型分配，考虑负载均衡和资源约束
    """
    try:
        from services.ai_model_selector import PromptTemplate, PromptCategory, PromptPriority
        
        # 创建测试模板列表
        category_map = {
            "safety_detection": PromptCategory.SAFETY_DETECTION,
            "behavior_analysis": PromptCategory.BEHAVIOR_ANALYSIS,
            "object_detection": PromptCategory.OBJECT_DETECTION,
            "scene_understanding": PromptCategory.SCENE_UNDERSTANDING
        }
        
        templates = []
        for i in range(template_count):
            template = PromptTemplate(
                id=f"optimize_{i}",
                name=f"Template {i+1}",
                category=category_map.get(category, PromptCategory.SAFETY_DETECTION),
                content=f"Optimization template {i+1}",
                priority=PromptPriority.MEDIUM
            )
            templates.append(template)
        
        # 执行优化分配
        assignments = await ai_model_selector.optimize_model_assignment(templates)
        
        # 统计分配结果
        model_counts = {}
        for template_id, model_type in assignments.items():
            model_name = model_type.value
            model_counts[model_name] = model_counts.get(model_name, 0) + 1
        
        return {
            "success": True,
            "data": {
                "assignments": {k: v.value for k, v in assignments.items()},
                "load_distribution": model_counts,
                "total_templates": len(assignments),
                "optimization_category": category
            }
        }
        
    except Exception as e:
        logger.error(f"模型分配优化失败: {e}")
        raise HTTPException(status_code=500, detail=f"优化失败: {str(e)}")


@router.get("/health", summary="模型服务健康检查")
async def check_model_health():
    """
    检查AI模型选择服务的健康状态
    """
    try:
        # 获取性能统计
        performance_stats = ai_model_selector.performance_stats
        
        # 统计活跃模型
        active_models = [
            model.value for model, stats in performance_stats.items()
            if stats.total_calls > 0
        ]
        
        # 计算整体健康度
        total_calls = sum(stats.total_calls for stats in performance_stats.values())
        total_success = sum(stats.success_calls for stats in performance_stats.values())
        overall_success_rate = total_success / total_calls if total_calls > 0 else 0
        
        health_status = "healthy" if overall_success_rate > 0.8 else "degraded" if overall_success_rate > 0.5 else "unhealthy"
        
        return {
            "success": True,
            "data": {
                "status": health_status,
                "active_models": active_models,
                "total_models": len(ai_model_selector.model_capabilities),
                "overall_success_rate": overall_success_rate,
                "total_api_calls": total_calls,
                "last_check": now_isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "success": False,
            "data": {
                "status": "error",
                "error": str(e),
                "last_check": now_isoformat()
            }
        }