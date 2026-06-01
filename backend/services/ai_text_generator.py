"""
AI文本生成服务
用于生成算法描述、系统提示词和用户提示词
"""

import logging
import httpx
import asyncio
from typing import Dict, Any, Optional
from config.settings import APIConfig
from services.output_format_manager import output_format_manager

logger = logging.getLogger(__name__)


class AITextGenerator:
    """AI文本生成器"""
    
    def __init__(self):
        self.deepseek_api_key = APIConfig.DEEPSEEK_API_KEY
        self.deepseek_base_url = APIConfig.DEEPSEEK_API_URL
        
    async def generate_algorithm_description(self, algorithm_name: str) -> Dict[str, Any]:
        """根据算法名称生成算法描述"""
        try:
            prompt = f"""
请为以下AI视觉算法生成专业的算法描述：

算法名称：{algorithm_name}

要求：
1. 描述应该专业、准确、简洁
2. 包含算法的核心功能和应用场景
3. 字数控制在100-200字之间
4. 语言风格应该是技术性和专业性的

请直接返回算法描述文本，不要包含其他内容。
"""
            
            response = await self._call_deepseek_api(prompt)
            return {
                "success": True,
                "description": response.strip(),
                "algorithm_name": algorithm_name
            }
            
        except Exception as e:
            logger.error(f"生成算法描述失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "algorithm_name": algorithm_name
            }
    
    async def generate_prompts(self, algorithm_name: str, algorithm_description: str = "") -> Dict[str, Any]:
        """根据算法名称和描述生成系统提示词和用户提示词"""
        try:
            # 使用新的输出格式管理器获取格式配置（新增功能）
            format_config = output_format_manager.get_default_format_by_algorithm(algorithm_name)
            output_format = format_config.get('format_template', '')
            
            # 向后兼容：如果新管理器没有找到格式，使用原有方法作为fallback
            if not output_format:
                output_format = self._get_output_format_for_algorithm(algorithm_name)
                logger.warning(f"使用fallback格式配置: {algorithm_name}")
            else:
                logger.info(f"使用OutputFormatManager格式配置: {algorithm_name}")
            
            system_prompt = f"""
请为以下AI视觉算法生成专业的系统提示词：

算法名称：{algorithm_name}
算法描述：{algorithm_description}

要求：
1. 将AI设定为专业的、严谨的、准确的视觉专家
2. 强调清晰度、准确性和交互逻辑
3. 包含角色定位、能力描述、工作方式
4. 确保输出格式严格按照JSON要求
5. 字数控制在200-400字之间

请直接返回系统提示词文本。
"""

            user_prompt = f"""
请为以下AI视觉算法生成专业的用户提示词：

算法名称：{algorithm_name}
算法描述：{algorithm_description}

要求：
1. 明确说明用户需要提供什么样的图片
2. 指导用户如何获得最佳分析结果
3. 说明算法的检测重点和注意事项
4. 包含输出格式要求说明
5. 字数控制在150-300字之间

输出格式要求：
{output_format}

请直接返回用户提示词文本。
"""
            
            # 并发生成两个提示词
            system_task = self._call_deepseek_api(system_prompt)
            user_task = self._call_deepseek_api(user_prompt)
            
            system_response, user_response = await asyncio.gather(system_task, user_task)
            
            return {
                "success": True,
                "system_prompt": system_response.strip(),
                "user_prompt": user_response.strip(),
                "algorithm_name": algorithm_name,
                "algorithm_description": algorithm_description,
                # 新增：返回输出格式配置信息，供前端使用
                "output_format_config": {
                    "format_template": output_format,
                    "custom_instructions": format_config.get('custom_instructions', '请严格按照JSON格式返回检测结果。'),
                    "algorithm_type": format_config.get('algorithm_type', 'general'),
                    "is_custom": False,  # 标识这是系统默认格式
                    "format_version": format_config.get('format_version', '1.0')
                }
            }
            
        except Exception as e:
            logger.error(f"生成提示词失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "algorithm_name": algorithm_name
            }
    
    def _get_output_format_for_algorithm(self, algorithm_name: str) -> str:
        """根据算法名称返回对应的输出格式"""
        
        # 安全帽检测算法的输出格式
        if "安全帽" in algorithm_name or "helmet" in algorithm_name.lower():
            return '''
{
  "has_violation": <boolean>, // 整体结论。如果存在至少一个"未佩戴安全帽"的人员，则为 true；否则为 false。
  "person_count": <integer>,  // 图片中识别到的总人数
  "violation_count": <integer>, // 未佩戴安全帽的人数
  "conclusion": "<string>",   // 简要的文本总结，例如："共检测到5人，其中1人未佩戴安全帽，位于画面左侧脚手架处。"
  "violations": [             // 违规人员详细信息列表。如果 has_violation 为 false，则此数组应为空列表 []。
    {
      "bbox": {               // 违规人员的边界框坐标（像素单位）
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>   // 你对此人未佩戴安全帽这一判断的置信度（0.00 - 1.00之间）
    }
  ]
}'''
        
        # 吸烟检测算法的输出格式
        elif "吸烟" in algorithm_name or "smoking" in algorithm_name.lower():
            return '''
{
  "has_violation": <boolean>, // 整体结论。如果检测到吸烟行为，则为 true；否则为 false。
  "person_count": <integer>,  // 图片中识别到的总人数
  "violation_count": <integer>, // 正在吸烟的人数
  "conclusion": "<string>",   // 简要的文本总结
  "violations": [             // 吸烟人员详细信息列表
    {
      "bbox": {               // 吸烟人员的边界框坐标
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>   // 置信度（0.00 - 1.00之间）
    }
  ]
}'''
        
        # 打架检测算法的输出格式
        elif "打架" in algorithm_name or "fight" in algorithm_name.lower():
            return '''
{
  "has_violation": <boolean>, // 整体结论。如果检测到打架行为，则为 true；否则为 false。
  "person_count": <integer>,  // 图片中识别到的总人数
  "violation_count": <integer>, // 参与打架的人数
  "conclusion": "<string>",   // 简要的文本总结
  "violations": [             // 打架人员详细信息列表
    {
      "bbox": {               // 参与打架人员的边界框坐标
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>   // 置信度（0.00 - 1.00之间）
    }
  ]
}'''
        
        # 火灾烟雾检测算法的输出格式
        elif any(keyword in algorithm_name for keyword in ["火灾", "烟雾", "fire", "smoke"]):
            return '''
{
  "has_violation": <boolean>, // 整体结论。如果检测到火灾或烟雾，则为 true；否则为 false。
  "person_count": <integer>,  // 图片中识别到的总人数
  "violation_count": <integer>, // 检测到的火灾/烟雾区域数量
  "conclusion": "<string>",   // 简要的文本总结
  "violations": [             // 火灾/烟雾区域详细信息列表
    {
      "bbox": {               // 火灾/烟雾区域的边界框坐标
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>   // 置信度（0.00 - 1.00之间）
    }
  ]
}'''
        
        # 通用输出格式
        else:
            return '''
{
  "has_violation": <boolean>, // 整体结论。如果检测到违规行为，则为 true；否则为 false。
  "person_count": <integer>,  // 图片中识别到的总人数
  "violation_count": <integer>, // 违规数量
  "conclusion": "<string>",   // 简要的文本总结
  "violations": [             // 违规详细信息列表
    {
      "bbox": {               // 违规对象的边界框坐标
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>   // 置信度（0.00 - 1.00之间）
    }
  ]
}'''
    
    async def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        if not self.deepseek_api_key:
            raise ValueError("DeepSeek API密钥未配置")
        
        headers = {
            "Authorization": f"Bearer {self.deepseek_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 1500,
            "temperature": 0.1,
            "stream": False
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.deepseek_base_url,
                headers=headers,
                json=data
            )
            
            if response.status_code != 200:
                raise Exception(f"DeepSeek API调用失败: {response.status_code} - {response.text}")
            
            result = response.json()
            
            if "choices" not in result or not result["choices"]:
                raise Exception("DeepSeek API返回格式错误")
            
            return result["choices"][0]["message"]["content"]


# 全局实例
ai_text_generator = AITextGenerator()