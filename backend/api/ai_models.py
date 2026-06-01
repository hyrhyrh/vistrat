"""
AI大模型编排API路由
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse

from services.ai_model_service import AIModelService
from services.ai_provider_service import AIProviderService
from models.ai_model import (
    AIModelConfigCreate, AIModelConfigUpdate, AIModelConfigResponse,
    AITestRequest, AITestResponse,
    AIProviderEnum, AIModelTypeEnum, AlgorithmStatusEnum
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-models", tags=["AI模型编排"])


@router.post("/configs/", response_model=AIModelConfigResponse)
async def create_ai_config(config_data: AIModelConfigCreate):
    """创建AI模型配置"""
    try:
        result = await AIModelService.create_config(config_data)
        logger.info(f"AI配置创建成功: {result.id}")
        return result
    except Exception as e:
        logger.error(f"创建AI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")


@router.get("/configs/", response_model=List[AIModelConfigResponse])
async def get_ai_configs(
    search_name: Optional[str] = Query(None, description="按名称搜索"),
    provider: Optional[AIProviderEnum] = Query(None, description="供应商筛选"),
    status: Optional[AlgorithmStatusEnum] = Query(None, description="状态筛选"),
    tags: Optional[str] = Query(None, description="标签筛选，逗号分隔"),
    limit: int = Query(50, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取AI模型配置列表"""
    try:
        tag_list = tags.split(",") if tags else None
        configs = await AIModelService.get_configs_with_search(
            search_name=search_name,
            provider=provider,
            status=status,
            tags=tag_list,
            limit=limit,
            offset=offset
        )
        return configs
    except Exception as e:
        logger.error(f"获取AI配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/configs/{config_id}", response_model=AIModelConfigResponse)
async def get_ai_config(config_id: str):
    """获取单个AI模型配置"""
    try:
        config = await AIModelService.get_config_by_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="配置不存在")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/configs/{config_id}", response_model=AIModelConfigResponse)
async def update_ai_config(config_id: str, update_data: AIModelConfigUpdate):
    """更新AI模型配置"""
    try:
        result = await AIModelService.update_config(config_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="配置不存在")
        logger.info(f"AI配置更新成功: {config_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新AI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.delete("/configs/{config_id}")
async def delete_ai_config(config_id: str):
    """删除AI模型配置"""
    try:
        success = await AIModelService.delete_config(config_id)
        if not success:
            raise HTTPException(status_code=404, detail="配置不存在")
        logger.info(f"AI配置删除成功: {config_id}")
        return {"message": "配置删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除AI配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")


@router.post("/test", response_model=AITestResponse)
async def test_ai_model(
    config_id: str = Form(...),
    input_text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    """测试AI模型"""
    try:
        # 处理图片上传
        image_data = None
        if image:
            # 验证文件类型
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="只支持图片文件")
            
            # 读取图片并转换为base64
            import base64
            content = await image.read()
            image_data = base64.b64encode(content).decode('utf-8')
        
        # 创建测试请求
        test_request = AITestRequest(
            config_id=config_id,
            image_data=image_data,
            input_text=input_text
        )
        
        result = await AIModelService.test_ai_model(test_request)
        logger.info(f"AI模型测试完成: {config_id}")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI模型测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.post("/test-config", response_model=AITestResponse)
async def test_ai_config_direct(
    provider: str = Form(...),
    model_name: str = Form(...),
    system_prompt: Optional[str] = Form(None),
    user_prompt: Optional[str] = Form(None),
    temperature: float = Form(0.7),
    top_p: float = Form(0.9),
    max_tokens: int = Form(1000),
    confidence_threshold: float = Form(0.7),
    detection_capabilities: Optional[str] = Form(None, description="检测能力列表，JSON数组字符串，如：[\"safety_helmet\", \"smoking\"]"),
    image: Optional[UploadFile] = File(None)
):
    """
    直接测试AI配置（无需保存到数据库）

    支持两种模式：
    1. 复合检测模式：传入detection_capabilities参数（推荐）
    2. 传统模式：传入system_prompt和user_prompt（不推荐，用于兼容）
    """
    try:
        import json
        import base64
        import os
        import tempfile
        from pathlib import Path

        # 处理图片上传
        image_path = None
        if image:
            # 验证文件类型
            if not image.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail="只支持图片文件")

            # 保存图片到临时文件（复合检测需要文件路径）
            content = await image.read()
            temp_dir = Path(tempfile.gettempdir()) / "vistrat_test"
            temp_dir.mkdir(exist_ok=True)

            image_path = temp_dir / f"test_{os.urandom(8).hex()}.jpg"
            with open(image_path, 'wb') as f:
                f.write(content)

        # 判断使用哪种模式
        use_composite_mode = False
        detection_types = []

        if detection_capabilities:
            try:
                detection_types = json.loads(detection_capabilities)
                if isinstance(detection_types, list) and len(detection_types) > 0:
                    use_composite_mode = True
                    logger.info(f"🎯 使用复合检测模式，检测类型: {detection_types}")
            except json.JSONDecodeError:
                logger.warning(f"detection_capabilities格式错误，降级为传统模式: {detection_capabilities}")

        # ============ 模式1: 复合检测模式 ============
        if use_composite_mode and image_path:
            from prompts.composite_prompt_engine import get_prompt_engine
            from parsers.composite_response_parser import get_response_parser
            from services.ai_provider_service import AIProviderService
            import httpx

            start_time = __import__('time').time()

            try:
                # 1. 构建复合提示词
                prompt_engine = get_prompt_engine()
                composite_prompt = await prompt_engine.build_composite_prompt(
                    type_codes=detection_types,
                    include_json_schema=True
                )

                logger.info(f"🎯 复合提示词构建完成，长度: {len(composite_prompt)} 字符")

                # 2. 获取AI供应商配置
                provider_config = await AIProviderService.get_provider_by_name(provider)
                if not provider_config or not provider_config.is_active:
                    raise ValueError(f"供应商 {provider} 不存在或未激活")

                # 3. 读取图片为base64
                import base64
                with open(image_path, 'rb') as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')

                # 4. 构建AI请求
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": composite_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                        ]
                    }
                ]

                request_data = {
                    "model": model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_tokens": max_tokens,
                    "stream": False,
                    "presence_penalty": 0,
                    "frequency_penalty": 0
                }

                # 5. 构建请求头
                headers = {"Content-Type": "application/json"}
                if provider_config.request_headers:
                    for key, value in provider_config.request_headers.items():
                        if '{api_key}' in value and provider_config.api_key:
                            headers[key] = value.format(api_key=provider_config.api_key)
                        else:
                            headers[key] = value

                logger.info(f"🚀 调用AI API: {provider_config.api_base_url}")

                # 6. 调用AI
                async with httpx.AsyncClient(timeout=provider_config.request_timeout) as client:
                    response = await client.post(
                        provider_config.api_base_url,
                        headers=headers,
                        json=request_data
                    )
                    response.raise_for_status()
                    api_result = response.json()

                # 7. 提取AI响应
                ai_response = ""
                if 'choices' in api_result and len(api_result['choices']) > 0:
                    ai_response = api_result['choices'][0]['message']['content']

                logger.info(f"✅ AI响应成功，长度: {len(ai_response)} 字符")

                # 8. 解析响应
                response_parser = get_response_parser()

                # 构建template_mapping
                template_mapping = {}
                for type_code in detection_types:
                    template_mapping[type_code] = {
                        'id': f'template_{type_code}',
                        'display_name': type_code,
                        'category': 'test',
                        'severity': 'medium',
                        'priority': 0
                    }

                violations = await response_parser.parse_composite_response(
                    ai_response=ai_response,
                    expected_types=detection_types,
                    template_mapping=template_mapping
                )

                logger.info(f"✅ 响应解析成功，检测到 {len(violations)} 种类型")

                # 9. 计算统计信息
                total_violations = sum(1 for v in violations if v.get('has_violation'))
                avg_confidence = sum(v.get('confidence', 0.0) for v in violations) / len(violations) if violations else 0.0

                processing_time = __import__('time').time() - start_time

                # 10. 格式化复合检测结果
                violation_summary = []
                for v in violations:
                    status = "✅ 检测到违规" if v.get('has_violation') else "✅ 未检测到违规"
                    violation_summary.append(
                        f"【{v.get('display_name', v.get('type_code'))}】{status}\n"
                        f"  置信度: {v.get('confidence', 0):.2%}\n"
                        f"  结论: {v.get('conclusion', '无')}\n"
                    )

                formatted_response = (
                    f"🎯 复合检测结果\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"检测类型数: {len(violations)}\n"
                    f"发现违规: {total_violations} 种\n"
                    f"平均置信度: {avg_confidence:.2%}\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    + "\n".join(violation_summary) +
                    f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📊 统计信息:\n"
                    f"  - 模型: {model_name}\n"
                    f"  - 提示词长度: {len(composite_prompt)} 字符\n"
                    f"  - 处理耗时: {processing_time:.2f} 秒\n"
                    f"\n💡 提示: 如需查看完整AI响应，请查看日志\n"
                    f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ 测试成功，可直接保存配置使用！\n"
                )

                # 清理临时文件
                if image_path and image_path.exists():
                    image_path.unlink()

                return AITestResponse(
                    id=f"composite_test_{os.urandom(4).hex()}",
                    ai_response=formatted_response,
                    confidence_score=avg_confidence,
                    processing_time=processing_time,
                    is_success=True,
                    error_message=None,
                    created_at=__import__('time').strftime("%Y-%m-%dT%H:%M:%S")
                )

            except Exception as e:
                logger.error(f"复合检测异常: {e}")
                # 清理临时文件
                if image_path and image_path.exists():
                    image_path.unlink()
                raise

        # ============ 模式2: 传统模式（兼容旧版本） ============
        # 读取图片为base64
        image_data = None
        if image_path and image_path.exists():
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            # 清理临时文件
            image_path.unlink()

        # 创建临时配置
        temp_config = AIModelConfigCreate(
            provider=AIProviderEnum(provider),
            model_name=model_name,
            name="临时测试配置",
            description="用于测试的临时配置",
            system_prompt=system_prompt or "",
            user_prompt=user_prompt or "",
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            confidence_threshold=confidence_threshold,
            detection_capabilities=detection_types  # 保存检测能力（即使是传统模式）
        )

        result = await AIModelService.test_ai_config_direct(
            config=temp_config,
            image_data=image_data
        )
        logger.info(f"AI配置直接测试完成: {provider}-{model_name}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI配置测试失败: {e}")
        raise HTTPException(status_code=500, detail=f"测试失败: {str(e)}")


@router.get("/model-options")
async def get_model_options():
    """获取可用的模型选项（从数据库动态获取）"""
    try:
        options = await AIModelService.get_model_options()
        return {"model_options": options}
    except Exception as e:
        logger.error(f"获取模型选项失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取选项失败: {str(e)}")


@router.get("/statistics")
async def get_ai_statistics():
    """获取AI模型统计信息"""
    try:
        stats = await AIModelService.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"获取AI统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.post("/configs/{config_id}/activate")
async def activate_config(config_id: str):
    """激活配置（设为active状态）"""
    try:
        update_data = AIModelConfigUpdate(status=AlgorithmStatusEnum.ACTIVE)
        result = await AIModelService.update_config(config_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="配置不存在")
        logger.info(f"AI配置已激活: {config_id}")
        return {"message": "配置已激活", "config": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"激活配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"激活失败: {str(e)}")


@router.post("/configs/{config_id}/deactivate")
async def deactivate_config(config_id: str):
    """停用配置（设为draft状态）"""
    try:
        update_data = AIModelConfigUpdate(status=AlgorithmStatusEnum.DRAFT)
        result = await AIModelService.update_config(config_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="配置不存在")
        logger.info(f"AI配置已停用: {config_id}")
        return {"message": "配置已停用", "config": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停用配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"停用失败: {str(e)}")


@router.get("/providers")
async def get_providers():
    """获取AI供应商列表"""
    try:
        providers = await AIProviderService.get_simple_providers(active_only=True)
        return {
            "providers": [
                {
                    "value": provider.provider_name,
                    "label": provider.display_name, 
                    "icon": provider.icon,
                    "id": provider.id
                }
                for provider in providers
            ]
        }
    except Exception as e:
        logger.error(f"获取AI供应商列表失败: {e}")
        # 如果数据库查询失败，返回默认配置
        return {
            "providers": [
                {"value": "qwen", "label": "通义千问", "icon": "🟡"},
                {"value": "moonshot", "label": "Moonshot", "icon": "🌙"},
                {"value": "gpt", "label": "OpenAI GPT", "icon": "🤖"},
                {"value": "claude", "label": "Claude", "icon": "🎭"},
                {"value": "gemini", "label": "Google Gemini", "icon": "💎"},
                {"value": "baidu", "label": "百度文心", "icon": "🐻"}
            ]
        }


@router.get("/model-types")
async def get_model_types():
    """获取模型类型列表"""
    return {
        "types": [
            {"value": "vision", "label": "视觉模型", "description": "支持图像分析"},
            {"value": "text", "label": "文本模型", "description": "仅支持文本处理"},
            {"value": "multimodal", "label": "多模态模型", "description": "支持图像和文本"}
        ]
    }