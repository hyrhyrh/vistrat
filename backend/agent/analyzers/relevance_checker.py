"""
基于DeepSeek大模型的问题相关性判断器
利用LLM强大的语义理解能力,精准判断问题是否与告警分析相关
"""
import logging
from typing import Tuple
import httpx
import json

from ..exceptions import IntentAnalysisException
from config.settings import APIConfig

logger = logging.getLogger(__name__)


# Elasticsearch索引字段完整注释
ES_SCHEMA_DESCRIPTION = """
# 告警分析系统 Elasticsearch 索引字段说明

## 1. video_alerts (告警索引)
存储视频分析产生的所有告警记录,是告警分析的核心数据源。

### 核心字段:
- **task_id** (任务ID): 分析任务的唯一标识符
- **video_id** (视频ID): 视频文件的唯一标识符
- **stream_id** (视频流ID): RTSP视频流的唯一标识符
- **video_name** (视频名称): 视频文件或视频流的名称
- **camera_name** (摄像头名称): 产生告警的摄像头名称

### 时间相关字段:
- **frame_index** (帧索引): 告警发生的视频帧编号
- **timestamp** (时间戳): 告警发生的Unix时间戳(秒)
- **video_time** (视频时间点): 告警在视频中的时间位置(HH:MM:SS格式)
- **datetime** (日期时间): 告警创建的完整日期时间
- **created_at** (创建时间): 告警记录的创建时间

### 算法相关字段:
- **template_name** (模板名称): 触发告警的AI分析模板名称,这就是告警类型
- **algorithm_name** (算法名称): 使用的AI算法名称(如未戴安全帽检测、吸烟检测等),这就是告警类型
- **algorithm_category** (算法类别): 算法所属的大类(如安全检测、行为分析等)
- **analysis_type** (分析类型): 数据来源类型,video_analysis(离线分析)或stream_analysis(实时分析)
- **ai_response** (AI响应): AI模型返回的原始分析结果文本

### 告警内容字段:
- **confidence** (置信度): 告警的置信度分数(0.0-1.0)
- **description** (描述): 告警的文字描述
- **alert_content** (告警内容): 告警的详细内容信息
- **detection_details** (检测详情): 检测到的具体对象和细节(嵌套对象)

### 严重程度字段:
- **severity** (严重程度): 告警严重等级(如low、medium、high、critical)
- **alert_level** (告警级别): 告警的级别分类
- **priority** (优先级): 告警处理优先级(数值型,越大越优先)
- **category** (类别): 告警所属的业务类别

### 位置和状态字段:
- **location** (位置): 告警发生的物理位置或区域
- **resolved** (已解决): 告警是否已被解决(true/false)
- **image_url** (图片URL): 告警截图的访问地址
- **metadata** (元数据): 其他扩展信息(嵌套对象)
- **data_type** (数据类型): 数据来源类型标识

---

## 2. video_frame_results (视频帧分析结果索引)
存储每一帧视频的AI分析结果,包括有告警和无告警的帧。

### 核心字段:
- **task_id** (任务ID): 所属分析任务的ID
- **video_id** (视频ID): 所属视频的ID
- **frame_index** (帧索引): 视频帧的序号
- **timestamp** (时间戳): 该帧的Unix时间戳
- **video_time** (视频时间点): 该帧在视频中的时间位置

### 分析结果字段:
- **template_id** (模板ID): 使用的分析模板ID
- **template_name** (模板名称): 使用的分析模板名称
- **ai_response** (AI响应): AI模型对该帧的完整分析结果
- **confidence** (置信度): 分析结果的置信度
- **has_alert** (有告警): 该帧是否产生了告警(true/false)

### 辅助字段:
- **analyzed_at** (分析时间): 该帧被分析的时间
- **image_url** (图片URL): 该帧图片的访问地址
- **detection_objects** (检测对象): 检测到的所有对象列表(嵌套数组)
  - class_name (类别名称): 检测对象的类别
  - confidence (置信度): 检测的置信度
  - bbox (边界框): 对象的位置坐标

---

## 业务场景说明

### ✅ 与告警分析相关的问题类型:
1. **统计类**: "今天有多少告警?"、"本周告警总数"、"每天的告警数量"
2. **趋势类**: "告警趋势如何?"、"告警是增加还是减少?"、"最近告警变化"
3. **分类类**: "哪种类型的告警最多?"、"未戴安全帽的告警有多少?"
4. **位置类**: "哪个区域告警最多?"、"某摄像头的告警情况"
5. **时间类**: "上午和下午哪个时段告警多?"、"工作日和周末的告警对比"
6. **严重程度**: "高危告警有多少?"、"紧急告警的分布"
7. **处理状态**: "未处理的告警有多少?"、"已解决的告警占比"
8. **算法效果**: "某算法的准确率"、"平均置信度是多少"
9. **异常分析**: "异常的告警模式"、"突发告警事件"
10. **对比分析**: "今天vs昨天"、"本周vs上周"的告警对比

### ❌ 与告警分析无关的问题类型:
1. **问候语**: "你好"、"您好"、"hi"
2. **闲聊**: "今天吃饭了吗"、"天气怎么样"、"你是谁"
3. **通用知识**: "什么是人工智能"、"如何编程"
4. **其他业务**: 与视频监控告警分析完全无关的业务问题
"""


class RelevanceChecker:
    """
    基于DeepSeek的问题相关性判断器

    职责:
    1. 接收用户问题
    2. 调用DeepSeek大模型进行语义理解
    3. 判断问题是否与告警分析相关
    4. 返回判断结果和理由
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化相关性判断器

        Args:
            api_key: DeepSeek API密钥(可选,默认从配置读取)
            model: 模型名称(可选,默认从配置读取)
        """
        self.api_key = api_key or APIConfig.DEEPSEEK_API_KEY
        self.model = model or APIConfig.DEEPSEEK_MODEL
        self.base_url = APIConfig.DEEPSEEK_API_URL

        if not self.api_key:
            logger.warning("未配置DEEPSEEK_API_KEY,相关性检查将使用规则引擎降级方案")

    async def check_relevance(self, question: str) -> Tuple[bool, str]:
        """
        检查问题是否与告警分析相关

        Args:
            question: 用户问题

        Returns:
            Tuple[bool, str]: (是否相关, 判断理由)
        """
        if not self.api_key:
            # 降级到规则引擎
            return self._rule_based_check(question)

        try:
            # 调用DeepSeek进行语义判断
            prompt = self._build_relevance_check_prompt(question)

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": """你是一个告警分析系统的问题分类专家。

【核心任务】
判断用户问题是否与视频监控告警分析相关。

【判断标准】
基于提供的Elasticsearch索引字段说明,判断问题是否涉及:
- 告警数据的查询、统计、分析
- 视频帧分析结果的查询
- 告警趋势、分布、类型、严重程度等
- 摄像头、位置、时间维度的告警分析
- 算法效果、置信度等技术指标

【输出格式】
严格按照JSON格式输出,不要包含任何其他文字:
{
  "relevant": true/false,
  "reason": "判断理由(简短,一句话)"
}

【示例】
问题: "今天有多少告警?"
输出: {"relevant": true, "reason": "查询今天的告警数量,属于告警统计分析"}

问题: "你好"
输出: {"relevant": false, "reason": "问候语,与告警分析无关"}

问题: "今天天气怎么样"
输出: {"relevant": false, "reason": "询问天气,与告警分析无关"}"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.1,  # 使用较低温度确保稳定输出
                "max_tokens": 200
            }

            logger.info(f"调用DeepSeek判断问题相关性: {question}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.base_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                result = response.json()

            # 解析LLM响应
            choices = result.get("choices", [])
            if not choices:
                logger.warning("DeepSeek返回空响应,使用规则引擎降级")
                return self._rule_based_check(question)

            content = choices[0].get("message", {}).get("content", "")
            logger.debug(f"DeepSeek相关性判断响应: {content}")

            # 解析JSON响应
            try:
                judgment = json.loads(content)
                is_relevant = judgment.get("relevant", False)
                reason = judgment.get("reason", "未知原因")

                logger.info(f"相关性判断结果: {is_relevant}, 理由: {reason}")
                return is_relevant, reason

            except json.JSONDecodeError as e:
                logger.warning(f"解析DeepSeek响应失败: {e}, 内容: {content}")
                # 尝试从文本中提取判断结果
                if "relevant" in content.lower():
                    if "true" in content.lower() or "是" in content:
                        return True, "LLM判断为相关(文本解析)"
                    else:
                        return False, "LLM判断为不相关(文本解析)"

                # 降级到规则引擎
                return self._rule_based_check(question)

        except httpx.TimeoutException:
            logger.warning("DeepSeek API调用超时,使用规则引擎降级")
            return self._rule_based_check(question)

        except Exception as e:
            logger.error(f"DeepSeek相关性判断失败: {e}, 使用规则引擎降级")
            return self._rule_based_check(question)

    def _build_relevance_check_prompt(self, question: str) -> str:
        """
        构建相关性检查的提示词

        Args:
            question: 用户问题

        Returns:
            str: 完整提示词
        """
        return f"""{ES_SCHEMA_DESCRIPTION}

---

# 用户问题
{question}

# 任务
请判断上述问题是否与告警分析相关,严格按照JSON格式输出判断结果。"""

    def _rule_based_check(self, question: str) -> Tuple[bool, str]:
        """
        规则引擎降级方案

        Args:
            question: 用户问题

        Returns:
            Tuple[bool, str]: (是否相关, 判断理由)
        """
        import re

        # 核心业务关键词
        core_keywords = [
            r"告警", r"预警", r"警报", r"报警", r"alert",
            r"帧", r"frame", r"视频", r"video", r"监控", r"stream"
        ]

        # 领域关键词
        domain_keywords = [
            r"类型", r"算法", r"模板", r"置信度", r"严重",
            r"位置", r"区域", r"摄像头", r"camera",
            r"时间", r"今天", r"昨天", r"本周", r"最近",
            r"多少", r"数量", r"统计", r"分析", r"趋势",
            r"安全帽", r"吸烟", r"违规", r"异常"
        ]

        # 检查核心关键词
        for keyword in core_keywords:
            if re.search(keyword, question, re.IGNORECASE):
                return True, f"匹配核心关键词: {keyword}"

        # 检查领域关键词组合(至少2个)
        matches = []
        for keyword in domain_keywords:
            if re.search(keyword, question, re.IGNORECASE):
                matches.append(keyword)

        if len(matches) >= 2:
            return True, f"匹配多个领域关键词: {', '.join(matches[:3])}"

        # 问候语检测
        greetings = [r"你好", r"您好", r"hi", r"hello", r"嗨"]
        for greeting in greetings:
            if re.search(greeting, question.lower()):
                return False, "识别为问候语"

        # 默认判断为不相关
        if len(question) < 3:
            return False, "问题过短,无法判断"

        return False, "未匹配到告警分析相关关键词"
