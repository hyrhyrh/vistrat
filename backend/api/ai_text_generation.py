"""
AI文本生成API路由
提供算法描述生成、系统提示词生成、用户提示词生成等功能
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
import logging

from services.ai_text_generator import ai_text_generator
from api.auth import get_current_user
from models.auth import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-text", tags=["AI文本生成"])


class GenerateDescriptionRequest(BaseModel):
    """生成算法描述请求"""
    algorithm_name: str = Field(..., description="算法名称", min_length=1, max_length=100)


class GeneratePromptsRequest(BaseModel):
    """生成提示词请求"""
    algorithm_name: str = Field(..., description="算法名称", min_length=1, max_length=100)
    algorithm_description: Optional[str] = Field("", description="算法描述", max_length=1000)


class TextGenerationResponse(BaseModel):
    """文本生成响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[dict] = Field(None, description="生成的内容")
    error: Optional[str] = Field(None, description="错误信息")
    message: str = Field(..., description="响应消息")


@router.post("/generate-description", response_model=TextGenerationResponse)
async def generate_algorithm_description(
    request: GenerateDescriptionRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    根据算法名称生成算法描述
    """
    try:
        logger.info(f"用户 {current_user.username} 请求生成算法描述: {request.algorithm_name}")
        
        result = await ai_text_generator.generate_algorithm_description(request.algorithm_name)
        
        if result["success"]:
            return TextGenerationResponse(
                success=True,
                data={
                    "algorithm_name": result["algorithm_name"],
                    "description": result["description"]
                },
                message="算法描述生成成功"
            )
        else:
            logger.error(f"算法描述生成失败: {result.get('error', '未知错误')}")
            return TextGenerationResponse(
                success=False,
                error=result.get("error", "未知错误"),
                message="算法描述生成失败"
            )
            
    except Exception as e:
        logger.error(f"生成算法描述时发生异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.post("/generate-prompts", response_model=TextGenerationResponse)
async def generate_prompts(
    request: GeneratePromptsRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    根据算法名称和描述生成系统提示词和用户提示词
    """
    try:
        logger.info(f"用户 {current_user.username} 请求生成提示词: {request.algorithm_name}")
        
        result = await ai_text_generator.generate_prompts(
            request.algorithm_name,
            request.algorithm_description
        )
        
        if result["success"]:
            return TextGenerationResponse(
                success=True,
                data={
                    "algorithm_name": result["algorithm_name"],
                    "algorithm_description": result["algorithm_description"],
                    "system_prompt": result["system_prompt"],
                    "user_prompt": result["user_prompt"]
                },
                message="提示词生成成功"
            )
        else:
            logger.error(f"提示词生成失败: {result.get('error', '未知错误')}")
            return TextGenerationResponse(
                success=False,
                error=result.get("error", "未知错误"),
                message="提示词生成失败"
            )
            
    except Exception as e:
        logger.error(f"生成提示词时发生异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"服务器内部错误: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "service": "AI文本生成服务",
        "timestamp": "2025-09-22"
    }