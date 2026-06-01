"""
增强的AI大模型编排服务
支持动态供应商配置和优化的API调用


"""

import logging
import time
import httpx
import re
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func, or_

from database.connection import DatabaseManager
from models.ai_model import (
    AIModelConfigDB, AITestResultDB,
    AIModelConfigCreate, AIModelConfigUpdate, AIModelConfigResponse,
    AITestRequest, AITestResponse,
    AIProviderEnum, AIModelTypeEnum, AlgorithmStatusEnum,
    AI_MODEL_OPTIONS
)
from services.ai_provider_service import AIProviderService
from models.ai_provider_config import AIProviderConfigResponse, AIProviderConfigDB

logger = logging.getLogger(__name__)


class AIModelService:
    """增强的AI模型服务（纯异步版本）"""

    @staticmethod
    def _db_to_response(db_config: AIModelConfigDB) -> AIModelConfigResponse:
        """将数据库对象转换为响应模型"""
        return AIModelConfigResponse(
            id=str(db_config.id),
            name=db_config.name,
            description=db_config.description,
            provider=db_config.provider,
            model_name=db_config.model_name,
            model_type=db_config.model_type,
            system_prompt=db_config.system_prompt,
            user_prompt=db_config.user_prompt,
            temperature=db_config.temperature,
            top_p=db_config.top_p,
            max_tokens=db_config.max_tokens,
            confidence_threshold=db_config.confidence_threshold,
            tags=db_config.tags or [],
            detection_capabilities=db_config.detection_capabilities or [],  # ✅ 添加检测能力字段
            status=db_config.status,
            test_count=db_config.test_count,
            success_count=db_config.success_count,
            extra_config=db_config.extra_config or {},
            created_at=db_config.created_at.isoformat(),
            updated_at=db_config.updated_at.isoformat()
        )

    @staticmethod
    async def create_config(config_data: AIModelConfigCreate) -> AIModelConfigResponse:
        """创建AI模型配置"""
        # 验证供应商是否存在并激活
        provider_config = await AIProviderService.get_provider_by_name(config_data.provider)
        if not provider_config or not provider_config.is_active:
            raise ValueError(f"供应商 {config_data.provider} 不存在或未激活")

        async with DatabaseManager.get_session() as session:
            # 处理枚举字段转换
            config_dict = config_data.model_dump()
            if isinstance(config_dict.get('model_type'), AIModelTypeEnum):
                config_dict['model_type'] = config_dict['model_type'].value
            if isinstance(config_dict.get('status'), AlgorithmStatusEnum):
                config_dict['status'] = config_dict['status'].value

            db_config = AIModelConfigDB(**config_dict)
            session.add(db_config)
            await session.flush()
            await session.refresh(db_config)

            return AIModelService._db_to_response(db_config)

    @staticmethod
    async def get_config_by_id(config_id: str) -> Optional[AIModelConfigResponse]:
        """根据ID获取AI模型配置"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AIModelConfigDB).where(AIModelConfigDB.id == config_id)
            result = await session.execute(stmt)
            db_config = result.scalar_one_or_none()

            if not db_config:
                return None

            return AIModelService._db_to_response(db_config)

    @staticmethod
    async def get_configs_with_search(
        search_name: Optional[str] = None,
        provider: Optional[str] = None,
        status: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[AIModelConfigResponse]:
        """搜索AI模型配置"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AIModelConfigDB)

            # 添加搜索条件
            if search_name:
                stmt = stmt.where(
                    or_(
                        AIModelConfigDB.name.ilike(f"%{search_name}%"),
                        AIModelConfigDB.description.ilike(f"%{search_name}%")
                    )
                )

            if provider:
                stmt = stmt.where(AIModelConfigDB.provider == provider)

            if status:
                stmt = stmt.where(AIModelConfigDB.status == status)

            if tags:
                stmt = stmt.where(AIModelConfigDB.tags.overlap(tags))

            stmt = stmt.order_by(AIModelConfigDB.updated_at.desc())
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            db_configs = result.scalars().all()

            return [
                AIModelService._db_to_response(config)
                for config in db_configs
            ]

    @staticmethod
    async def update_config(config_id: str, update_data: AIModelConfigUpdate) -> Optional[AIModelConfigResponse]:
        """更新AI模型配置"""
        async with DatabaseManager.get_session() as session:
            stmt = select(AIModelConfigDB).where(AIModelConfigDB.id == config_id)
            result = await session.execute(stmt)
            db_config = result.scalar_one_or_none()

            if not db_config:
                return None

            # 验证provider字段（如果要更新）
            if update_data.provider is not None:
                provider_config = await AIProviderService.get_provider_by_name(update_data.provider)
                if not provider_config or not provider_config.is_active:
                    raise ValueError(f"供应商 {update_data.provider} 不存在或未激活")

            # 更新字段
            update_dict = update_data.model_dump(exclude_unset=True)
            if update_dict:
                # 处理枚举字段转换
                if 'model_type' in update_dict and isinstance(update_dict['model_type'], AIModelTypeEnum):
                    update_dict['model_type'] = update_dict['model_type'].value
                if 'status' in update_dict and isinstance(update_dict['status'], AlgorithmStatusEnum):
                    update_dict['status'] = update_dict['status'].value

                stmt = update(AIModelConfigDB).where(
                    AIModelConfigDB.id == config_id
                ).values(**update_dict)
                await session.execute(stmt)
                await session.flush()
                await session.refresh(db_config)

            return AIModelService._db_to_response(db_config)

    @staticmethod
    async def delete_config(config_id: str) -> bool:
        """删除AI模型配置"""
        async with DatabaseManager.get_session() as session:
            stmt = delete(AIModelConfigDB).where(AIModelConfigDB.id == config_id)
            result = await session.execute(stmt)
            return result.rowcount > 0

    @staticmethod
    async def _call_ai_api_with_provider_config(
        provider_config: AIProviderConfigResponse,
        model_config: AIModelConfigResponse,
        image_data: Optional[str] = None,
        input_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """使用供应商配置调用AI API"""

        # 构建请求数据
        messages = []

        # 添加系统提示词
        if model_config.system_prompt:
            messages.append({
                "role": "system",
                "content": model_config.system_prompt
            })

        # 构建用户消息
        user_content = []

        # 添加文本内容
        text_content = []
        if model_config.user_prompt:
            text_content.append(model_config.user_prompt)
        if input_text:
            text_content.append(f"输入文本：{input_text}")

        # 如果没有任何文本内容但有图片，添加默认分析指令
        if not text_content and image_data:
            text_content.append("请分析这张图片，根据系统提示词中的要求给出详细的分析结果。")

        # 构建用户消息内容
        if provider_config.provider_name == 'qwen':
            # 通义千问格式
            if image_data and text_content:
                user_content = [
                    {"type": "text", "text": "\n".join(text_content)},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            elif image_data:
                user_content = [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            elif text_content:
                user_content = "\n".join(text_content)
            else:
                user_content = "Hello, please provide a simple greeting response."
        else:
            # 其他供应商格式
            if image_data and text_content:
                user_content = [
                    {"type": "text", "text": "\n".join(text_content)},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            elif image_data:
                user_content = [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                ]
            elif text_content:
                user_content = "\n".join(text_content)
            else:
                user_content = "Hello, please provide a simple greeting response."

        messages.append({
            "role": "user",
            "content": user_content
        })

        # 构建请求体
        request_data = {
            "model": model_config.model_name,
            "messages": messages,
            "temperature": model_config.temperature,
            "top_p": model_config.top_p,
            "max_tokens": model_config.max_tokens
        }

        # 专门为蓝翼大模型优化请求参数
        provider_name = getattr(provider_config, 'provider_name', '').lower()
        display_name = getattr(provider_config, 'display_name', '').lower()
        default_model = getattr(model_config, 'model_name', '').lower()
        api_url = provider_config.api_base_url.lower()

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
                "presence_penalty": 0,
                "frequency_penalty": 0
            })
            logger.info(f"检测到蓝翼大模型，添加额外参数: {provider_config.api_base_url}")

        # 构建请求头
        headers = {"Content-Type": "application/json"}

        if is_lanyi_model:
            # 蓝翼大模型需要的完整请求头
            headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cookie': '__jsluid_s=75a13ab091a1822199ee57902f58aacb'
            })
            logger.info(f"为蓝翼大模型添加完整请求头: {provider_config.api_base_url}")

        # 处理供应商配置的请求头模板
        if provider_config.request_headers:
            for key, value in provider_config.request_headers.items():
                if '{api_key}' in value and provider_config.api_key:
                    headers[key] = value.format(api_key=provider_config.api_key)
                else:
                    headers[key] = value

        # 如果没有配置请求头但有API密钥，使用默认格式
        if provider_config.api_key and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {provider_config.api_key}"

        logger.info(f"调用AI API: {provider_config.api_base_url}")
        logger.info(f"请求头: {headers}")

        # 发送请求
        async with httpx.AsyncClient(timeout=provider_config.request_timeout) as client:
            response = await client.post(
                provider_config.api_base_url,
                headers=headers,
                json=request_data
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"API响应成功，状态码: {response.status_code}")

            return result

    @staticmethod
    def _extract_confidence_score(ai_response: str) -> Optional[float]:
        """从AI响应中提取置信度分数"""
        try:
            # 尝试多种置信度格式
            patterns = [
                r'置信度[：:]\s*(\d+(?:\.\d+)?)%?',
                r'confidence[：:]\s*(\d+(?:\.\d+)?)%?',
                r'可信度[：:]\s*(\d+(?:\.\d+)?)%?',
                r'准确度[：:]\s*(\d+(?:\.\d+)?)%?',
                r'(\d+(?:\.\d+)?)%\s*置信度',
                r'(\d+(?:\.\d+)?)\s*分(?:的置信度)?'
            ]

            for pattern in patterns:
                matches = re.findall(pattern, ai_response, re.IGNORECASE)
                if matches:
                    score = float(matches[0])
                    # 如果分数大于1，假设是百分比格式
                    if score > 1:
                        score = score / 100
                    return min(max(score, 0.0), 1.0)

            return None

        except Exception:
            return None

    @staticmethod
    async def _save_test_result(
        config_id: str,
        input_text: Optional[str],
        ai_response: str,
        confidence_score: Optional[float],
        processing_time: float,
        is_success: bool,
        error_message: Optional[str]
    ) -> str:
        """保存测试结果"""
        async with DatabaseManager.get_session() as session:
            test_result = AITestResultDB(
                config_id=config_id,
                input_text=input_text,
                ai_response=ai_response,
                confidence_score=confidence_score,
                processing_time=processing_time,
                is_success=is_success,
                error_message=error_message
            )

            session.add(test_result)

            # 更新配置统计
            if is_success:
                stmt = update(AIModelConfigDB).where(
                    AIModelConfigDB.id == config_id
                ).values(
                    test_count=AIModelConfigDB.test_count + 1,
                    success_count=AIModelConfigDB.success_count + 1
                )
            else:
                stmt = update(AIModelConfigDB).where(
                    AIModelConfigDB.id == config_id
                ).values(test_count=AIModelConfigDB.test_count + 1)

            await session.execute(stmt)
            await session.flush()
            await session.refresh(test_result)

            return str(test_result.id)

    @staticmethod
    async def test_ai_model(test_request: AITestRequest) -> AITestResponse:
        """测试AI模型"""
        start_time = time.time()

        try:
            # 获取模型配置
            model_config = await AIModelService.get_config_by_id(test_request.config_id)
            if not model_config:
                raise ValueError("AI模型配置不存在")

            # 获取供应商配置
            provider_name = model_config.provider if isinstance(model_config.provider, str) else model_config.provider.value
            provider_config = await AIProviderService.get_provider_by_name(provider_name)
            if not provider_config:
                raise ValueError(f"供应商配置不存在: {model_config.provider}")

            if not provider_config.is_active:
                raise ValueError(f"供应商未激活: {model_config.provider}")

            # 调用AI API
            api_result = await AIModelService._call_ai_api_with_provider_config(
                provider_config=provider_config,
                model_config=model_config,
                image_data=test_request.image_data,
                input_text=test_request.input_text
            )

            # 提取AI响应内容
            ai_response = ""
            # 标准OpenAI格式（通义千问现在也用这个格式）
            if 'choices' in api_result and len(api_result['choices']) > 0:
                ai_response = api_result['choices'][0]['message']['content']

            # 提取置信度
            confidence_score = AIModelService._extract_confidence_score(ai_response)

            processing_time = time.time() - start_time

            # 保存测试结果
            test_result_id = await AIModelService._save_test_result(
                test_request.config_id,
                test_request.input_text,
                ai_response,
                confidence_score,
                processing_time,
                True,
                None
            )

            return AITestResponse(
                id=test_result_id,
                ai_response=ai_response,
                confidence_score=confidence_score,
                processing_time=processing_time,
                is_success=True,
                error_message=None,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%S")
            )

        except httpx.HTTPStatusError as e:
            error_message = f"API请求失败 ({e.response.status_code}): {e.response.text}"
            logger.error(error_message)

        except Exception as e:
            error_message = str(e)
            logger.error(f"AI模型测试失败: {error_message}")

        # 保存失败结果
        processing_time = time.time() - start_time
        test_result_id = await AIModelService._save_test_result(
            test_request.config_id,
            test_request.input_text,
            "",
            None,
            processing_time,
            False,
            error_message
        )

        return AITestResponse(
            id=test_result_id,
            ai_response="",
            confidence_score=None,
            processing_time=processing_time,
            is_success=False,
            error_message=error_message,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S")
        )

    @staticmethod
    async def get_model_options() -> Dict[str, List[str]]:
        """获取可用模型选项"""
        try:
            async with DatabaseManager.get_session() as session:
                # 查询所有激活的AI提供商配置
                result = await session.execute(
                    select(AIProviderConfigDB)
                    .where(AIProviderConfigDB.is_active == True)
                )
                configs = result.scalars().all()

                # 构建模型选项字典
                model_options = {}
                for config in configs:
                    provider_name = config.provider_name
                    available_models = config.available_models or []

                    # 如果可用模型列表为空，使用默认模型
                    if not available_models and config.default_model:
                        available_models = [config.default_model]

                    # 合并相同提供商的模型
                    if provider_name in model_options:
                        # 去重合并
                        existing_models = set(model_options[provider_name])
                        new_models = set(available_models)
                        model_options[provider_name] = list(existing_models | new_models)
                    else:
                        model_options[provider_name] = available_models

                # 如果数据库没有配置，返回默认选项作为备选
                if not model_options:
                    logger.warning("数据库中没有找到AI提供商配置，使用默认模型选项")
                    return AI_MODEL_OPTIONS

                logger.info(f"从数据库动态加载模型选项: {list(model_options.keys())}")
                return model_options
        except Exception as e:
            logger.error(f"从数据库获取模型选项失败: {e}")
            logger.info("使用默认模型选项作为后备")
            return AI_MODEL_OPTIONS

    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """获取AI模型统计信息"""
        async with DatabaseManager.get_session() as session:
            # 配置总数
            total_configs = await session.execute(
                select(func.count(AIModelConfigDB.id))
            )

            # 活跃配置数
            active_configs = await session.execute(
                select(func.count(AIModelConfigDB.id)).where(
                    AIModelConfigDB.status == 'active'
                )
            )

            # 总测试次数
            total_tests = await session.execute(
                select(func.sum(AIModelConfigDB.test_count))
            )

            # 成功测试次数
            success_tests = await session.execute(
                select(func.sum(AIModelConfigDB.success_count))
            )

            total_count = total_configs.scalar() or 0
            active_count = active_configs.scalar() or 0
            total_test_count = total_tests.scalar() or 0
            success_test_count = success_tests.scalar() or 0

            return {
                "total_configs": total_count,
                "active_configs": active_count,
                "total_tests": total_test_count,
                "success_tests": success_test_count,
                "success_rate": success_test_count / total_test_count if total_test_count > 0 else 0
            }

    @staticmethod
    async def test_ai_config_direct(config: AIModelConfigCreate, image_data: Optional[str] = None) -> AITestResponse:
        """直接测试AI配置（无需保存到数据库）"""
        start_time = time.time()

        try:
            # 获取供应商配置
            provider_name = config.provider if isinstance(config.provider, str) else config.provider.value
            provider_config = await AIProviderService.get_provider_by_name(provider_name)
            if not provider_config:
                raise ValueError(f"供应商配置不存在: {config.provider}")

            if not provider_config.is_active:
                raise ValueError(f"供应商未激活: {config.provider}")

            # 创建临时配置对象用于API调用
            temp_config = AIModelConfigResponse(
                id="temp",
                name=config.name,
                description=config.description,
                provider=config.provider,
                model_name=config.model_name,
                model_type=config.model_type or "vision",
                system_prompt=config.system_prompt,
                user_prompt=config.user_prompt,
                temperature=config.temperature,
                top_p=config.top_p,
                max_tokens=config.max_tokens,
                confidence_threshold=config.confidence_threshold,
                tags=config.tags or [],
                status="draft",
                test_count=0,
                success_count=0,
                extra_config={},
                created_at="",
                updated_at=""
            )

            # 调用AI API
            api_result = await AIModelService._call_ai_api_with_provider_config(
                provider_config=provider_config,
                model_config=temp_config,
                image_data=image_data,
                input_text=None
            )

            # 提取AI响应内容
            ai_response = ""
            # 标准OpenAI格式（通义千问现在也用这个格式）
            if 'choices' in api_result and len(api_result['choices']) > 0:
                choice = api_result['choices'][0]
                if 'message' in choice and 'content' in choice['message']:
                    ai_response = choice['message']['content']
                elif 'text' in choice:  # 兼容其他格式
                    ai_response = choice['text']

            processing_time = time.time() - start_time

            # 计算置信度（简单实现）
            confidence_score = len([word for word in ai_response.split() if word]) / 100.0
            confidence_score = min(confidence_score, 1.0)

            return AITestResponse(
                id="temp_test",
                ai_response=ai_response,
                confidence_score=confidence_score,
                processing_time=processing_time,
                is_success=True,
                error_message=None,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%S")
            )

        except Exception as e:
            processing_time = time.time() - start_time
            error_message = str(e)
            logger.error(f"AI配置直接测试失败: {error_message}")

            return AITestResponse(
                id="temp_test_error",
                ai_response="",
                confidence_score=None,
                processing_time=processing_time,
                is_success=False,
                error_message=error_message,
                created_at=time.strftime("%Y-%m-%dT%H:%M:%S")
            )
