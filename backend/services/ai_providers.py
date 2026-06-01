"""
AI提供商服务
支持多厂商AI模型调用，根据数据库配置动态选择
"""

import base64
import logging
import httpx
import json
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from config.settings import APIConfig

logger = logging.getLogger(__name__)


class BaseAIProvider(ABC):
    """AI提供商基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', '')
        self.model_name = config.get('model_name', '')
        
    @abstractmethod
    async def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """
        分析图像（向后兼容接口）

        Returns:
            AI响应文本
        """
        pass

    async def analyze_image_detailed(self, image_path: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        分析图像并返回完整的请求/响应信息（默认实现，子类应覆盖）

        Returns:
            包含完整信息的字典：
            {
                'ai_response': str,  # AI响应文本
                'raw_request': dict,  # 完整的请求体
                'raw_response': dict,  # 完整的响应体
                'api_endpoint': str,  # API端点URL
                'status_code': int,  # HTTP状态码
                'headers': dict,  # 请求headers（敏感信息已脱敏）
                'usage': dict,  # Token使用信息（如果有）
            }
        """
        # 默认实现：调用简化方法并返回基本信息
        ai_response = await self.analyze_image(image_path, prompt, **kwargs)
        return {
            'ai_response': ai_response,
            'raw_request': {
                'prompt': prompt,
                'image_path': image_path,
                'kwargs': kwargs
            },
            'raw_response': {'content': ai_response},
            'api_endpoint': self.base_url,
            'status_code': 200,
            'headers': self._sanitize_headers(self._get_headers()),
            'usage': {}
        }
        
    def _prepare_image_data(self, image_path: str) -> str:
        """
        准备图像数据：支持HTTP URL和本地文件路径

        Args:
            image_path: 图片路径或URL

        Returns:
            如果是HTTP/HTTPS URL则直接返回，否则读取文件转base64
        """
        try:
            # 如果是HTTP/HTTPS URL，直接返回（节省token）
            if image_path.startswith('http://') or image_path.startswith('https://'):
                logger.debug(f"使用图片URL (节省token): {image_path[:80]}...")
                return image_path

            # 否则读取本地文件转base64
            logger.debug(f"读取本地文件转base64: {image_path}")
            with open(image_path, 'rb') as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            return f"data:image/jpeg;base64,{image_base64}"
        except Exception as e:
            logger.error(f"准备图像数据失败 {image_path}: {e}")
            raise

    def _prepare_image_base64(self, image_path: str) -> str:
        """准备图像的base64编码（向后兼容，调用新方法）"""
        return self._prepare_image_data(image_path)
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """脱敏headers（隐藏API Key）"""
        safe_headers = headers.copy()
        if 'Authorization' in safe_headers and self.api_key:
            safe_headers['Authorization'] = 'Bearer ****' + (self.api_key[-8:] if len(self.api_key) > 8 else '****')
        return safe_headers

    def _sanitize_request_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """移除请求体中的base64图片数据，保留大小信息"""
        safe_request = request_data.copy()
        if 'messages' in safe_request and safe_request['messages']:
            safe_request['messages'] = []
            for msg in request_data['messages']:
                safe_msg = msg.copy()
                if isinstance(safe_msg.get('content'), list):
                    safe_content = []
                    for item in safe_msg['content']:
                        if item.get('type') == 'image_url':
                            img_url = item.get('image_url', {}).get('url', '')
                            safe_content.append({
                                'type': 'image_url',
                                'image_url': {
                                    'url': f"<base64_image_data_size: {len(img_url)} bytes>"
                                }
                            })
                        elif item.get('type') == 'image' and item.get('source', {}).get('type') == 'base64':
                            # Claude格式
                            img_data = item.get('source', {}).get('data', '')
                            safe_content.append({
                                'type': 'image',
                                'source': {
                                    'type': 'base64',
                                    'media_type': item.get('source', {}).get('media_type', 'image/jpeg'),
                                    'data': f"<base64_image_data_size: {len(img_data)} bytes>"
                                }
                            })
                        else:
                            safe_content.append(item)
                    safe_msg['content'] = safe_content
                safe_request['messages'].append(safe_msg)
        return safe_request

    def _get_headers(self) -> Dict[str, str]:
        """获取默认请求头"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 专门为蓝翼大模型添加User-Agent请求头
        provider_type = self.config.get('provider', '').lower()
        model_name = self.config.get('model_name', '').lower()
        api_url = self.base_url.lower()
        
        # 只针对蓝翼大模型进行特殊处理
        is_lanyi_model = (
            'lanyi' in provider_type or 
            'blue' in provider_type or 
            'lanyi' in model_name or
            'blue' in model_name or
            'lanyi' in api_url or 
            'blue' in api_url or
            'lanyi.example.com' in api_url or  # 蓝翼的具体域名
            'llm.example.com' in api_url
        )
        
        if is_lanyi_model:
            # 蓝翼大模型需要的完整请求头
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
            headers['Accept'] = '*/*'
            headers['Accept-Encoding'] = 'gzip, deflate, br'
            headers['Connection'] = 'keep-alive'
            # 添加Cookie（如果配置中提供）
            cookie = self.config.get('cookie', '__jsluid_s=75a13ab091a1822199ee57902f58aacb')
            if cookie:
                headers['Cookie'] = cookie
            logger.debug(f"为蓝翼大模型添加完整请求头: {self.base_url}")
        
        return headers


class QwenProvider(BaseAIProvider):
    """通义千问提供商"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', APIConfig.QWEN_API_URL)

    async def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """使用通义千问分析图像"""
        try:
            image_data = self._prepare_image_base64(image_path)

            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]

            data = {
                "model": self.model_name or APIConfig.QWEN_MODEL,
                "vl_high_resolution_images": False,
                "messages": [{"role": "user", "content": content}]
            }

            headers = self._get_headers()

            async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
                response = await client.post(self.base_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']

        except Exception as e:
            logger.error(f"通义千问API调用失败: {e}")
            raise

    async def analyze_image_detailed(self, image_path: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """使用通义千问分析图像，返回完整信息"""
        try:
            image_data = self._prepare_image_base64(image_path)

            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]

            # 构建完整请求体
            request_data = {
                "model": self.model_name or APIConfig.QWEN_MODEL,
                "vl_high_resolution_images": False,
                "messages": [{"role": "user", "content": content}],
                **kwargs  # 包含temperature, top_p, max_tokens等参数
            }

            headers = self._get_headers()

            # 执行API调用
            async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
                response = await client.post(self.base_url, headers=headers, json=request_data)
                response.raise_for_status()
                result = response.json()

                return {
                    'ai_response': result['choices'][0]['message']['content'],
                    'raw_request': self._sanitize_request_data(request_data),
                    'raw_response': result,
                    'api_endpoint': self.base_url,
                    'status_code': response.status_code,
                    'headers': self._sanitize_headers(headers),
                    'usage': result.get('usage', {})
                }

        except Exception as e:
            logger.error(f"通义千问API调用失败: {e}")
            raise


class OpenAIProvider(BaseAIProvider):
    """OpenAI GPT提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.openai.com/v1/chat/completions')
        
    async def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """使用OpenAI GPT分析图像"""
        try:
            image_data = self._prepare_image_base64(image_path)
            
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
            
            data = {
                "model": self.model_name or "gpt-4-vision-preview",
                "messages": [{"role": "user", "content": content}],
                "max_tokens": kwargs.get('max_tokens', 1000)
            }
            
            headers = self._get_headers()
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
                response = await client.post(self.base_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']

        except httpx.HTTPStatusError as e:
            # 记录详细的HTTP错误信息
            error_detail = f"HTTP {e.response.status_code}"
            try:
                error_body = e.response.json()
                logger.error(f"OpenAI API调用失败: {error_detail}, 错误详情: {error_body}")
            except Exception:
                error_text = e.response.text[:500]
                logger.error(f"OpenAI API调用失败: {error_detail}, 响应体: {error_text}")
            raise
        except Exception as e:
            logger.error(f"OpenAI API调用失败: {e}")
            raise


class MoonshotProvider(BaseAIProvider):
    """Moonshot提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', APIConfig.MOONSHOT_API_URL)
        
    async def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """使用Moonshot分析图像"""
        try:
            image_data = self._prepare_image_base64(image_path)
            
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
            
            data = {
                "model": self.model_name or APIConfig.MOONSHOT_MODEL,
                "messages": [{"role": "user", "content": content}],
                "temperature": kwargs.get('temperature', APIConfig.TEMPERATURE),
                "top_p": kwargs.get('top_p', APIConfig.TOP_P)
            }
            
            headers = self._get_headers()
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
                response = await client.post(self.base_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
                
        except Exception as e:
            logger.error(f"Moonshot API调用失败: {e}")
            raise


class ClaudeProvider(BaseAIProvider):
    """Claude提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.anthropic.com/v1/messages')
        
    async def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """使用Claude分析图像"""
        try:
            image_data = self._prepare_image_base64(image_path)
            # Claude需要不同的图像格式
            image_data = image_data.replace('data:image/jpeg;base64,', '')
            
            content = [
                {"type": "text", "text": prompt},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": image_data
                    }
                }
            ]
            
            data = {
                "model": self.model_name or "claude-3-vision",
                "max_tokens": kwargs.get('max_tokens', 1000),
                "messages": [{"role": "user", "content": content}]
            }
            
            headers = self._get_headers()
            headers["anthropic-version"] = "2023-06-01"
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
                response = await client.post(self.base_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result['content'][0]['text']
                
        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            raise


class LanyiProvider(BaseAIProvider):
    """蓝翼大模型提供商"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 蓝翼模型需要特殊的User-Agent处理
        
    async def analyze_image(self, image_path: str, prompt: str, **kwargs) -> str:
        """使用蓝翼大模型分析图像"""
        try:
            image_data = self._prepare_image_base64(image_path)
            
            # 根据蓝翼API格式构建请求
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]
            
            data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": content}],
                "temperature": kwargs.get('temperature', 0.2),
                "top_p": kwargs.get('top_p', 0.7),
                "max_tokens": kwargs.get('max_tokens', 1000),
                "stream": False,
                "presence_penalty": 0,
                "frequency_penalty": 0
            }
            
            headers = self._get_headers()  # 已包含User-Agent
            
            async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
                response = await client.post(self.base_url, headers=headers, json=data)
                response.raise_for_status()
                result = response.json()
                return result['choices'][0]['message']['content']
                
        except Exception as e:
            logger.error(f"蓝翼大模型API调用失败: {e}")
            raise

    async def analyze_image_detailed(self, image_path: str, prompt: str, **kwargs) -> Dict[str, Any]:
        """使用蓝翼大模型分析图像，返回完整信息"""
        try:
            image_data = self._prepare_image_base64(image_path)

            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]

            # 构建完整请求体
            request_data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": content}],
                "temperature": kwargs.get('temperature', 0.2),
                "top_p": kwargs.get('top_p', 0.7),
                "max_tokens": kwargs.get('max_tokens', 1000),
                "stream": False,
                "presence_penalty": 0,
                "frequency_penalty": 0
            }

            headers = self._get_headers()

            # 执行API调用
            async with httpx.AsyncClient(timeout=httpx.Timeout(APIConfig.REQUEST_TIMEOUT)) as client:
                response = await client.post(self.base_url, headers=headers, json=request_data)
                response.raise_for_status()
                result = response.json()

                return {
                    'ai_response': result['choices'][0]['message']['content'],
                    'raw_request': self._sanitize_request_data(request_data),
                    'raw_response': result,
                    'api_endpoint': self.base_url,
                    'status_code': response.status_code,
                    'headers': self._sanitize_headers(headers),
                    'usage': result.get('usage', {})
                }

        except Exception as e:
            logger.error(f"蓝翼大模型API调用失败: {e}")
            raise


class AIProviderFactory:
    """AI提供商工厂"""
    
    PROVIDERS = {
        'qwen': QwenProvider,
        'qwen-vl': QwenProvider,
        'openai': OpenAIProvider,
        'gpt': OpenAIProvider,
        'gpt-4': OpenAIProvider,
        'gpt-4-vision': OpenAIProvider,
        'gpt-4-vision-preview': OpenAIProvider,
        'moonshot': MoonshotProvider,
        'claude': ClaudeProvider,
        'claude-vision': ClaudeProvider,
        'claude-3': ClaudeProvider,
        'lanyi': LanyiProvider,
        'blue': LanyiProvider,
        'vllm': OpenAIProvider,
        'vllm-local': OpenAIProvider
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> BaseAIProvider:
        """创建AI提供商实例"""
        provider_type_lower = provider_type.lower()
        
        # 查找匹配的提供商
        for key, provider_class in cls.PROVIDERS.items():
            if key in provider_type_lower:
                logger.info(f"创建AI提供商: {provider_class.__name__} for {provider_type}")
                return provider_class(config)
        
        # 默认使用通义千问
        logger.warning(f"未找到匹配的提供商 {provider_type}，使用默认的QwenProvider")
        return QwenProvider(config)
    
    @classmethod
    def get_supported_providers(cls) -> list:
        """获取支持的提供商列表"""
        return list(set(cls.PROVIDERS.values()))