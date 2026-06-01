"""
DeepSeek + Elasticsearch 智能分析客户端
使用DeepSeek API（OpenAI兼容格式）结合Elasticsearch直接查询实现智能数据分析
"""

import json
import logging
from typing import Optional, Dict, Any, AsyncGenerator, List
from elasticsearch import AsyncElasticsearch
from openai import AsyncOpenAI

from config.settings import APIConfig

logger = logging.getLogger(__name__)


class DeepSeekESClient:
    """
    DeepSeek + Elasticsearch 智能分析客户端

    通过DeepSeek API（OpenAI兼容格式）直接调用Elasticsearch实现智能数据分析
    架构：LLM + ES工具调用 + 上下文工程
    """

    def __init__(self, api_key: Optional[str] = None, es_url: str = "http://localhost:9200"):
        """
        初始化DeepSeek ES客户端

        Args:
            api_key: DeepSeek API密钥,如果不提供则从配置读取
            es_url: Elasticsearch URL
        """
        self.api_key = api_key or APIConfig.DEEPSEEK_API_KEY
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未配置,请设置DEEPSEEK_API_KEY环境变量")

        # 使用AsyncOpenAI客户端（DeepSeek API兼容OpenAI格式）
        self.deepseek_client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=APIConfig.DEEPSEEK_API_URL.replace("/chat/completions", "")  # 确保base_url格式正确
        )
        self.model = APIConfig.DEEPSEEK_MODEL

        # Elasticsearch客户端
        self.es_url = es_url
        self.es_client = None

        logger.info(f"✅ DeepSeek ES客户端初始化完成 (model: {self.model}, base_url: {APIConfig.DEEPSEEK_API_URL}, es: {es_url})")

    async def _get_es_client(self) -> AsyncElasticsearch:
        """获取ES客户端(懒加载)"""
        if not self.es_client:
            self.es_client = AsyncElasticsearch([self.es_url])
        return self.es_client

    async def _execute_es_query(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Elasticsearch查询

        Args:
            index: 索引名称
            body: 查询体

        Returns:
            查询结果（字典格式）
        """
        try:
            # 🔧 修复：检测并修正对_id字段的聚合（ES不允许对_id进行聚合）
            if 'aggs' in body or 'aggregations' in body:
                aggs_key = 'aggs' if 'aggs' in body else 'aggregations'
                body = self._fix_id_field_aggregation(body, aggs_key)

            es = await self._get_es_client()
            result = await es.search(index=index, body=body)
            # 将ObjectApiResponse转换为dict
            return dict(result)
        except Exception as e:
            logger.error(f"ES查询失败: {e}", exc_info=True)
            return {"error": str(e)}

    def _fix_id_field_aggregation(self, body: Dict[str, Any], aggs_key: str) -> Dict[str, Any]:
        """
        修正对_id字段的聚合（ES不允许）

        将对_id的聚合替换为其他等效方式：
        - value_count/_id → 使用hits.total.value或者不设置聚合
        - cardinality/_id → 使用其他唯一字段如task_id.keyword
        """
        try:
            aggs = body.get(aggs_key, {})
            modified = False

            for agg_name, agg_def in aggs.items():
                # 检查所有聚合类型
                for agg_type in ['value_count', 'cardinality', 'terms', 'stats', 'sum', 'avg', 'min', 'max']:
                    if agg_type in agg_def and isinstance(agg_def[agg_type], dict):
                        field = agg_def[agg_type].get('field')
                        if field == '_id':
                            logger.warning(f"检测到对_id字段的{agg_type}聚合，已自动移除")
                            # 对于统计文档数量的场景，直接移除聚合（使用hits.total.value代替）
                            if agg_type in ['value_count', 'cardinality']:
                                del aggs[agg_name]
                                modified = True
                                logger.info(f"已移除{agg_name}聚合，请使用hits.total.value获取文档数量")

            if modified:
                body[aggs_key] = aggs
                # 如果所有聚合都被移除了，删除整个aggs键
                if not aggs:
                    del body[aggs_key]

            return body
        except Exception as e:
            logger.warning(f"修正_id聚合时出错: {e}，使用原始查询")
            return body

    async def _execute_es_esql(self, query: str) -> Dict[str, Any]:
        """
        执行ES|QL查询

        Args:
            query: ES|QL查询语句

        Returns:
            查询结果（字典格式）
        """
        try:
            es = await self._get_es_client()
            result = await es.esql.query(query=query, format="json")
            # 将ObjectApiResponse转换为dict
            return dict(result)
        except Exception as e:
            logger.error(f"ES|QL查询失败: {e}", exc_info=True)
            return {"error": str(e)}

    def _get_elasticsearch_tools(self) -> list:
        """
        获取Elasticsearch工具定义(给DeepSeek使用)

        Returns:
            工具列表
        """
        return [
            {
                "name": "elasticsearch_search",
                "description": """在Elasticsearch中执行搜索查询。

支持的索引:
- video_alerts: 告警数据(最常用)
- video_analysis_results: 视频分析任务结果
- video_frame_results: 帧分析结果

参数说明:
- index: 索引名称(必需)
- query: Query DSL查询对象(必需),完整的JSON对象
  * 可以包含query、aggs、sort等ES DSL字段
  * 支持复杂的bool query、range query、terms aggregation等
- size: 返回结果数量(可选),默认10
- from_: 分页起始位置(可选),默认0
- _source: 返回字段列表(可选),如["alert_type","datetime"]

常用查询模式:
1. 统计文档数量(⭐️ 推荐方式):
   {
     "query": {
       "range": {"datetime": {"gte": "now-1d", "lte": "now"}}
     },
     "size": 0
   }
   # 结果在 hits.total.value 字段中
   # ⚠️ 不要使用aggs对_id做value_count，直接用hits.total.value！

2. 时间范围查询:
   {
     "query": {
       "range": {
         "datetime": {
           "gte": "now-1d",
           "lte": "now"
         }
       }
     }
   }

3. 按字段聚合(⚠️ text字段必须用.keyword后缀):
   {
     "size": 0,
     "aggs": {
       "by_algorithm": {
         "terms": {
           "field": "algorithm_name.keyword",
           "size": 10
         }
       }
     }
   }

   注意:
   - algorithm_name、template_name、location、camera_name等text类型字段聚合时必须用.keyword后缀
   - ⚠️ 禁止对_id字段进行聚合或统计,使用其他字段如task_id.keyword代替

4. 时间分布:
   {
     "size": 0,
     "aggs": {
       "alerts_over_time": {
         "date_histogram": {
           "field": "datetime",
           "calendar_interval": "hour"
         }
       }
     }
   }
""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "string",
                            "description": "索引名称,如video_alerts"
                        },
                        "query": {
                            "type": "object",
                            "description": "Query DSL查询对象(JSON)"
                        },
                        "size": {
                            "type": "integer",
                            "description": "返回结果数量",
                            "default": 10
                        },
                        "from_": {
                            "type": "integer",
                            "description": "分页起始位置",
                            "default": 0
                        },
                        "_source": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "返回字段列表"
                        }
                    },
                    "required": ["index", "query"]
                }
            }
        ]

    async def _process_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理工具调用

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            工具执行结果
        """
        try:
            logger.info(f"执行工具: {tool_name}, 参数: {json.dumps(tool_input, ensure_ascii=False)[:200]}")

            if tool_name == "elasticsearch_search":
                # 构建ES查询
                index = tool_input["index"]
                query_body = tool_input["query"]

                # 添加其他参数
                if "size" in tool_input:
                    query_body["size"] = tool_input["size"]
                if "from_" in tool_input:
                    query_body["from"] = tool_input["from_"]
                if "_source" in tool_input:
                    query_body["_source"] = tool_input["_source"]

                # 执行查询
                result = await self._execute_es_query(index, query_body)
                return result

            elif tool_name == "elasticsearch_esql":
                # 执行ES|QL查询
                query = tool_input["query"]
                result = await self._execute_es_esql(query)
                return result

            else:
                return {"error": f"未知工具: {tool_name}"}

        except Exception as e:
            logger.error(f"工具执行失败: {e}", exc_info=True)
            return {"error": str(e)}

    def _convert_tools_to_openai_format(self) -> list:
        """
        将工具定义转换为OpenAI Function Calling格式

        Returns:
            OpenAI格式的工具列表
        """
        tools = []
        for tool in self._get_elasticsearch_tools():
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })
        return tools

    async def analyze_stream(
        self,
        question: str,
        history: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式分析查询(SSE方式),支持多轮对话

        Args:
            question: 用户问题
            history: 对话历史,格式: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            context: 额外上下文信息(可选)

        Yields:
            分析结果片段
        """
        try:
            # 读取Elasticsearch schema文档
            try:
                with open("/root/project/vistrat/backend/agent/docs/elasticsearch_schema.md", "r", encoding="utf-8") as f:
                    es_schema = f.read()
            except Exception as e:
                logger.warning(f"无法读取ES schema文档: {e}")
                es_schema = "无法加载Elasticsearch schema文档"

            # 构建系统提示词
            system_prompt = f"""你是一个专业的视频监控告警数据分析助手,精通Elasticsearch数据查询和分析。

## 核心能力

1. **数据查询**: 使用Elasticsearch工具精确查询告警数据
2. **深度分析**: 对查询结果进行统计分析、趋势识别、异常检测
3. **洞察提取**: 从数据中提取有价值的业务洞察
4. **可视化建议**: 提供数据可视化方案

## 数据索引结构

{es_schema}

## 分析流程

1. **理解问题**: 准确理解用户的分析需求
2. **规划查询**: 设计合适的Elasticsearch查询策略
   - 优先使用Query DSL
   - 可以执行多个查询进行对比分析
3. **执行查询**: 调用elasticsearch_search工具获取数据
4. **数据处理**: 整理、计算、聚合查询结果
5. **生成报告**: 结构化呈现分析结果和洞察

## 查询技巧

- 时间范围: 使用`now-1d`、`now-1w`等相对时间
- 分组统计: 使用terms aggregation,注意text字段需要用.keyword
- 时间趋势: 使用date_histogram
- 多维分析: 结合bool query和多字段聚合
- 数值统计: 使用AVG、MAX、MIN、SUM等聚合函数

## 输出格式

使用结构化Markdown格式:

### 📊 分析标题

**数据分析**:
- 关键指标统计
- 趋势变化描述
- 异常情况识别

**洞察与发现**:
- 📈 重要发现
- ⚠️ 风险提示
- 💡 改进建议

## 注意事项

- 数字要准确,提供百分比和绝对值
- 发现趋势时要明确说明上升/下降幅度
- 对比分析时要给出具体差异
- 提供可操作的业务建议
- 适当使用emoji增强可读性(📊📈📉⚠️💡🔍等)

现在,请分析用户的问题。"""

            # 构建消息 - 支持多轮对话
            messages = [
                {"role": "system", "content": system_prompt}
            ]

            # 添加历史对话(如果有)
            if history:
                messages.extend(history)
                logger.info(f"添加了{len(history)}条历史消息到上下文")

            # 添加当前问题
            current_message = {"role": "user", "content": question}

            # 添加额外上下文(如果有)
            if context:
                context_text = f"\n\n**补充上下文**:\n```json\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```"
                current_message["content"] += context_text

            messages.append(current_message)

            # 第一轮调用: 让模型决定是否需要调用工具
            response = await self.deepseek_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._convert_tools_to_openai_format(),
                tool_choice="auto",
                temperature=0.1,
                stream=False  # 先不流式,简化处理
            )

            message = response.choices[0].message

            # 检查是否有工具调用
            if message.tool_calls:
                # 有工具调用,执行它们
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name

                    # ✅ 清理tool_call.function.arguments中的工具标记(DeepSeek API bug)
                    import re
                    raw_arguments = tool_call.function.arguments
                    # 匹配DeepSeek返回的工具标记（包括Unicode和普通字符变体）
                    tool_marker_pattern = r'<\s*[\|｜]\s*tool[_▁]+call[s]?[_▁]*(begin|end|sep)\s*[\|｜]\s*>'
                    cleaned_arguments = re.sub(tool_marker_pattern, '', raw_arguments, flags=re.IGNORECASE)
                    logger.debug(f"原始arguments长度: {len(raw_arguments)}, 清理后: {len(cleaned_arguments)}")

                    tool_args = json.loads(cleaned_arguments)

                    # 发送工具调用开始标记(使用特殊JSON格式)
                    tool_call_info = {
                        "_type": "tool_call_start",
                        "tool_name": tool_name,
                        "tool_display_name": "Elasticsearch search DSL query" if tool_name == "elasticsearch_search" else tool_name,
                        "parameters": tool_args
                    }
                    yield f"\n\n__TOOL_CALL_START__{json.dumps(tool_call_info, ensure_ascii=False)}__TOOL_CALL_START__\n\n"
                    logger.info(f"执行工具调用: {tool_name}, 参数: {json.dumps(tool_args, ensure_ascii=False)[:200]}")

                    # 执行工具
                    tool_result = await self._process_tool_call(tool_name, tool_args)

                    # 发送工具调用结果标记
                    tool_result_info = {
                        "_type": "tool_call_result",
                        "tool_name": tool_name,
                        "result": tool_result,
                        "success": "error" not in tool_result
                    }
                    yield f"\n\n__TOOL_CALL_RESULT__{json.dumps(tool_result_info, ensure_ascii=False)}__TOOL_CALL_RESULT__\n\n"

                    # 添加助手的工具调用消息
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })

                    # 添加工具结果
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result, ensure_ascii=False)
                    })

                # 第二轮调用: 让模型分析工具结果 (流式)
                # 添加明确的分析指令
                messages.append({
                    "role": "user",
                    "content": "请根据以上查询结果,生成完整的数据分析报告。使用结构化Markdown格式,包含标题、列表、emoji等,直接输出分析内容。"
                })

                logger.info(f"开始第二轮调用: 分析工具结果 (共{len(messages)}条消息)")
                final_response = await self.deepseek_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    stream=True
                )

                logger.info("第二轮调用返回，开始流式处理...")
                chunk_count = 0
                async for chunk in final_response:
                    chunk_count += 1
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content

                        # 过滤DeepSeek内部工具标记
                        import re
                        # 匹配DeepSeek API返回的工具调用标记（包括Unicode和普通字符变体）
                        tool_marker_pattern = r'<\s*[\|｜]\s*tool[_▁]+call[s]?[_▁]*(begin|end|sep)\s*[\|｜]\s*>'
                        cleaned_content = re.sub(tool_marker_pattern, '', content, flags=re.IGNORECASE)

                        # ✅ 修复：只要清理后有任何字符（包括换行符）就yield，不用strip()
                        # strip()会把换行符也删掉，导致前端渲染时缺少换行
                        if cleaned_content:  # 只检查是否为空字符串，保留换行符
                            logger.debug(f"收到第二轮chunk #{chunk_count}: {len(cleaned_content)} 字符")
                            yield cleaned_content
                        else:
                            logger.debug(f"过滤掉纯工具标记chunk #{chunk_count}")
                    else:
                        logger.debug(f"收到空chunk #{chunk_count}: {chunk}")

                logger.info(f"第二轮调用完成，共{chunk_count}个chunks")

            else:
                # 没有工具调用,直接返回回复 (流式)
                messages_copy = messages.copy()
                stream_response = await self.deepseek_client.chat.completions.create(
                    model=self.model,
                    messages=messages_copy,
                    temperature=0.3,
                    stream=True
                )

                async for chunk in stream_response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"DeepSeek分析失败: {e}", exc_info=True)
            yield f"\n\n❌ **分析失败**: {str(e)}\n\n"

        finally:
            # 关闭ES连接
            if self.es_client:
                await self.es_client.close()

    async def analyze(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        非流式分析查询

        Args:
            question: 用户问题
            context: 上下文信息(可选)

        Returns:
            完整的分析结果
        """
        result_parts = []
        async for chunk in self.analyze_stream(question, context):
            result_parts.append(chunk)

        return "".join(result_parts)
