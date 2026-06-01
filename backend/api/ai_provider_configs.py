"""
AI供应商配置API路由
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from services.ai_provider_service import AIProviderService
from models.ai_provider_config import (
    AIProviderConfigCreate, AIProviderConfigUpdate, AIProviderConfigResponse,
    AIProviderSimple
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai-provider-configs", tags=["AI供应商配置"])


@router.post("/", response_model=AIProviderConfigResponse)
async def create_provider_config(config_data: AIProviderConfigCreate):
    """创建AI供应商配置"""
    try:
        result = await AIProviderService.create_provider(config_data)
        logger.info(f"AI供应商配置创建成功: {result.id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建AI供应商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建配置失败: {str(e)}")


@router.get("/", response_model=List[AIProviderConfigResponse])
async def get_provider_configs(
    active_only: bool = Query(False, description="只返回活跃的供应商"),
    limit: int = Query(100, ge=1, le=100, description="每页数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """获取AI供应商配置列表"""
    try:
        configs = await AIProviderService.get_all_providers(
            active_only=active_only,
            limit=limit,
            offset=offset
        )
        return configs
    except Exception as e:
        logger.error(f"获取AI供应商配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/simple", response_model=List[AIProviderSimple])
async def get_simple_provider_configs(
    active_only: bool = Query(True, description="只返回活跃的供应商")
):
    """获取简化的AI供应商配置列表"""
    try:
        configs = await AIProviderService.get_simple_providers(active_only=active_only)
        return configs
    except Exception as e:
        logger.error(f"获取简化供应商配置列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取列表失败: {str(e)}")


@router.get("/{config_id}", response_model=AIProviderConfigResponse)
async def get_provider_config(config_id: str):
    """获取单个AI供应商配置"""
    try:
        config = await AIProviderService.get_provider_by_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="供应商配置不存在")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI供应商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.put("/{config_id}", response_model=AIProviderConfigResponse)
async def update_provider_config(config_id: str, update_data: AIProviderConfigUpdate):
    """更新AI供应商配置"""
    try:
        result = await AIProviderService.update_provider(config_id, update_data)
        if not result:
            raise HTTPException(status_code=404, detail="供应商配置不存在")
        logger.info(f"AI供应商配置更新成功: {config_id}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新AI供应商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.delete("/{config_id}")
async def delete_provider_config(config_id: str):
    """删除AI供应商配置"""
    try:
        success = await AIProviderService.delete_provider(config_id)
        if not success:
            raise HTTPException(status_code=404, detail="供应商配置不存在")
        logger.info(f"AI供应商配置删除成功: {config_id}")
        return {"message": "供应商配置删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除AI供应商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除配置失败: {str(e)}")


@router.get("/name/{provider_name}", response_model=AIProviderConfigResponse)
async def get_provider_config_by_name(provider_name: str):
    """根据供应商名称获取配置"""
    try:
        config = await AIProviderService.get_provider_by_name(provider_name)
        if not config:
            raise HTTPException(status_code=404, detail=f"供应商 {provider_name} 配置不存在")
        return config
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取AI供应商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/{config_id}/toggle-status")
async def toggle_provider_status(config_id: str):
    """切换供应商启用/禁用状态"""
    try:
        # 获取当前配置
        config = await AIProviderService.get_provider_by_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="供应商配置不存在")
        
        # 切换状态
        update_data = AIProviderConfigUpdate(is_active=not config.is_active)
        result = await AIProviderService.update_provider(config_id, update_data)
        
        logger.info(f"AI供应商状态切换成功: {config_id} -> {result.is_active}")
        return {
            "message": f"供应商已{'启用' if result.is_active else '禁用'}",
            "config": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"切换供应商状态失败: {e}")
        raise HTTPException(status_code=500, detail=f"状态切换失败: {str(e)}")


@router.get("/statistics/summary")
async def get_provider_statistics():
    """获取AI供应商统计信息"""
    try:
        stats = await AIProviderService.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"获取AI供应商统计失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


@router.post("/{config_id}/test-connection")
async def test_provider_connection(config_id: str):
    """测试AI供应商API连接"""
    try:
        # 获取供应商配置
        config = await AIProviderService.get_provider_by_id(config_id)
        if not config:
            raise HTTPException(status_code=404, detail="供应商配置不存在")
        
        # 实际的连接测试逻辑
        test_result = await _test_provider_api(config)
        
        return {
            "message": "连接测试成功" if test_result["success"] else "连接测试失败",
            "provider": config.display_name,
            "status": "ok" if test_result["success"] else "error",
            "details": test_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试供应商连接失败: {e}")
        raise HTTPException(status_code=500, detail=f"连接测试失败: {str(e)}")


@router.post("/test-config")
async def test_provider_config_direct(config_data: dict):
    """直接测试供应商配置（无需保存到数据库）"""
    try:
        # 验证必需字段
        required_fields = ["api_base_url", "default_model"]
        for field in required_fields:
            if field not in config_data or not config_data[field]:
                raise HTTPException(status_code=400, detail=f"缺少必需字段: {field}")
        
        # 创建临时配置对象
        from models.ai_provider_config import AIProviderConfigResponse
        temp_config = AIProviderConfigResponse(
            id="temp",
            provider_name=config_data.get("provider_name", "unknown"),
            display_name=config_data.get("display_name", "测试配置"),
            icon=config_data.get("icon", "🤖"),
            description=config_data.get("description", ""),
            api_base_url=config_data["api_base_url"],
            api_key=config_data.get("api_key", ""),
            api_version=config_data.get("api_version", "v1"),
            available_models=config_data.get("available_models", []),
            default_model=config_data["default_model"],
            max_tokens_limit=config_data.get("max_tokens_limit", {}),
            request_headers=config_data.get("request_headers", {}),
            request_timeout=config_data.get("request_timeout", 60),
            is_active=True,
            sort_order=0,
            extra_config={},
            created_at="",
            updated_at=""
        )
        
        # 执行测试
        test_result = await _test_provider_api(temp_config)
        
        return {
            "message": "配置测试成功" if test_result["success"] else "配置测试失败",
            "provider": temp_config.display_name,
            "status": "ok" if test_result["success"] else "error",
            "details": test_result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"测试供应商配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置测试失败: {str(e)}")


async def _test_provider_api(config: "AIProviderConfigResponse") -> dict:
    """实际测试AI供应商API连接"""
    import httpx
    import time
    
    start_time = time.time()
    
    try:
        # 构建测试消息
        test_messages = [
            {
                "role": "user",
                "content": "Hello, this is a connection test. Please respond with 'OK'."
            }
        ]
        
        # 构建请求数据
        request_data = {
            "model": config.default_model,
            "messages": test_messages,
            "max_tokens": 50,
            "temperature": 0.1
        }
        
        # 专门为蓝翼大模型优化请求参数
        provider_name = getattr(config, 'provider_name', '').lower()
        display_name = getattr(config, 'display_name', '').lower()
        default_model = getattr(config, 'default_model', '').lower()
        api_url = config.api_base_url.lower()
        
        is_lanyi_model = (
            'lanyi' in provider_name or 
            'blue' in provider_name or 
            '蓝翼' in display_name or
            'lanyi' in default_model or
            'blue' in default_model or
            'lanyi' in api_url or 
            'blue' in api_url or
            'lanyi.example.com' in api_url or
            'llm.example.com' in api_url
        )
        
        if is_lanyi_model:
            # 蓝翼大模型需要添加额外参数
            request_data.update({
                "stream": False,
                "top_p": 0.7,
                "presence_penalty": 0,
                "frequency_penalty": 0
            })
        
        # 构建请求头
        headers = {"Content-Type": "application/json"}
        
        if is_lanyi_model:
            # 蓝翼大模型需要的完整请求头
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            headers['Accept'] = '*/*'
            headers['Accept-Encoding'] = 'gzip, deflate, br'
            headers['Connection'] = 'keep-alive'
            # 添加默认Cookie
            headers['Cookie'] = '__jsluid_s=75a13ab091a1822199ee57902f58aacb'
            logger.info(f"为蓝翼大模型添加完整请求头: {config.api_base_url}")
        
        # 处理请求头模板
        if config.request_headers:
            for key, value in config.request_headers.items():
                if '{api_key}' in value and config.api_key:
                    headers[key] = value.format(api_key=config.api_key)
                else:
                    headers[key] = value
        
        # 如果没有配置请求头但有API密钥，使用默认格式
        if config.api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {config.api_key}"
        
        # 发送测试请求
        async with httpx.AsyncClient(timeout=config.request_timeout) as client:
            response = await client.post(
                config.api_base_url,
                headers=headers,
                json=request_data
            )
            
            processing_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    result_data = response.json()
                    
                    # 检查是否是错误响应（蓝翼大模型可能返回成功状态码但包含错误信息）
                    if "code" in result_data and result_data["code"] != 0:
                        # 处理蓝翼大模型的错误格式
                        error_message = result_data.get("message", "未知错误")
                        return {
                            "success": False,
                            "status_code": 200,
                            "response_time": round(processing_time, 2),
                            "error": f"API错误: {error_message} (错误代码: {result_data['code']})",
                            "raw_response": str(result_data)[:200] + "...",
                            "suggestion": "请检查API端点路径是否正确，蓝翼大模型可能需要 /v1/chat/completions 而不是 /compatible/v1"
                        }
                    
                    # 检查标准OpenAI格式
                    elif "choices" in result_data and len(result_data["choices"]) > 0:
                        ai_response = result_data["choices"][0].get("message", {}).get("content", "")
                        
                        return {
                            "success": True,
                            "status_code": 200,
                            "response_time": round(processing_time, 2),
                            "ai_response": ai_response[:100] + "..." if len(ai_response) > 100 else ai_response,
                            "model_used": result_data.get("model", config.default_model),
                            "tokens_used": result_data.get("usage", {}).get("total_tokens", 0)
                        }
                    
                    # 检查是否有success字段（某些API的格式）
                    elif "success" in result_data:
                        if result_data["success"]:
                            # 尝试从data字段获取响应
                            data = result_data.get("data", {})
                            if isinstance(data, dict) and "choices" in data:
                                ai_response = data["choices"][0].get("message", {}).get("content", "")
                                return {
                                    "success": True,
                                    "status_code": 200,
                                    "response_time": round(processing_time, 2),
                                    "ai_response": ai_response[:100] + "..." if len(ai_response) > 100 else ai_response,
                                    "model_used": data.get("model", config.default_model),
                                    "tokens_used": data.get("usage", {}).get("total_tokens", 0)
                                }
                            else:
                                return {
                                    "success": True,
                                    "status_code": 200,
                                    "response_time": round(processing_time, 2),
                                    "ai_response": str(data)[:100] + "..." if len(str(data)) > 100 else str(data),
                                    "note": "非标准响应格式，但API调用成功"
                                }
                        else:
                            return {
                                "success": False,
                                "status_code": 200,
                                "response_time": round(processing_time, 2),
                                "error": f"API返回失败: {result_data.get('message', '未知错误')}",
                                "raw_response": str(result_data)[:200] + "..."
                            }
                    
                    else:
                        return {
                            "success": False,
                            "status_code": 200,
                            "response_time": round(processing_time, 2),
                            "error": "响应格式不正确，缺少choices字段",
                            "raw_response": str(result_data)[:200] + "...",
                            "suggestion": "请检查API端点和请求格式是否正确"
                        }
                        
                except Exception as e:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "response_time": round(processing_time, 2),
                        "error": f"响应解析失败: {str(e)}",
                        "raw_response": response.text[:200] + "..."
                    }
            else:
                # 特殊处理蓝翼大模型的400错误
                if is_lanyi_model and response.status_code == 400 and "模型参数不正确" in response.text:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "response_time": round(processing_time, 2),
                        "error": f"HTTP {response.status_code}: 模型参数不正确，请检查后重试",
                        "raw_response": response.text[:200] + "...",
                        "suggestion": "蓝翼大模型可用模型名称：lanyi-instruct, lanyi-qwen2.5-vl-72b-instruct, lanyi-qwen3-235b-instruct, lanyi-glm-4.5 等。请检查模型名称是否正确。"
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "response_time": round(processing_time, 2),
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "raw_response": response.text[:200] + "..."
                    }
                
    except httpx.TimeoutException:
        return {
            "success": False,
            "status_code": 0,
            "response_time": round(time.time() - start_time, 2),
            "error": f"请求超时（超过{config.request_timeout}秒）"
        }
    except httpx.ConnectError as e:
        return {
            "success": False,
            "status_code": 0,
            "response_time": round(time.time() - start_time, 2),
            "error": f"连接失败: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 0,
            "response_time": round(time.time() - start_time, 2),
            "error": f"测试失败: {str(e)}"
        }