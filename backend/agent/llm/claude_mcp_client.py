"""
Claude + MCP Agent客户端
结合Claude API和Elasticsearch MCP服务器实现智能数据分析
"""

import asyncio
import json
import logging
import subprocess
from typing import Optional, Dict, Any, AsyncGenerator
import anthropic

from config.settings import APIConfig

logger = logging.getLogger(__name__)


class ClaudeMCPClient:
    """
    Claude + MCP Agent客户端

    通过Claude API调用MCP工具(Elasticsearch)实现智能数据分析
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化Claude MCP客户端

        Args:
            api_key: Claude API密钥,如果不提供则从配置读取
        """
        self.api_key = api_key or APIConfig.ANTHROPIC_API_KEY
        if not self.api_key:
            raise ValueError("Claude API密钥未配置,请设置ANTHROPIC_API_KEY环境变量")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = "claude-sonnet-4-20250514"  # 使用Claude Sonnet 4

        # Elasticsearch连接信息
        self.es_url = "http://localhost:9200"

        logger.info(f"✅ Claude MCP客户端初始化完成 (model: {self.model})")

    def _get_elasticsearch_tools(self) -> list:
        """
        获取Elasticsearch MCP工具定义

        Returns:
            工具列表
        """
        return [
            {
                "name": "elasticsearch_search",
                "description": """在Elasticsearch中搜索数据。支持多种查询方式:
                - 简单查询字符串(query_string)
                - 完整的Query DSL(query_dsl)
                - ES|QL查询(esql)

                参数:
                - index: 索引名称(必需),如"video_alerts"
                - query: 查询内容(必需),可以是:
                  * 简单查询字符串,如"alert_type:未佩戴安全帽"
                  * JSON格式的Query DSL查询
                  * ES|QL查询语句
                - query_type: 查询类型,可选值:
                  * "query_string"(默认): 简单查询字符串
                  * "query_dsl": 完整Query DSL
                  * "esql": ES|QL查询
                - size: 返回结果数量(可选),默认10
                - from: 分页起始位置(可选),默认0
                - sort: 排序字段(可选),如"datetime:desc"
                - _source: 返回字段列表(可选),如["alert_type","datetime","confidence"]
                - track_total_hits: 是否精确计算总数(可选),默认true

                示例:
                1. 简单查询:
                   index="video_alerts", query="alert_level:critical", query_type="query_string"

                2. Query DSL查询:
                   index="video_alerts", query='{"range": {"datetime": {"gte": "now-1d"}}}', query_type="query_dsl"

                3. ES|QL查询:
                   query="FROM video_alerts | WHERE datetime >= NOW() - 1 day | STATS count = COUNT(*) BY alert_type", query_type="esql"
                """,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "string",
                            "description": "索引名称"
                        },
                        "query": {
                            "type": "string",
                            "description": "查询内容"
                        },
                        "query_type": {
                            "type": "string",
                            "enum": ["query_string", "query_dsl", "esql"],
                            "description": "查询类型",
                            "default": "query_string"
                        },
                        "size": {
                            "type": "integer",
                            "description": "返回结果数量",
                            "default": 10
                        },
                        "from": {
                            "type": "integer",
                            "description": "分页起始位置",
                            "default": 0
                        },
                        "sort": {
                            "type": "string",
                            "description": "排序字段,格式: field:order"
                        },
                        "_source": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "返回字段列表"
                        },
                        "track_total_hits": {
                            "type": "boolean",
                            "description": "是否精确计算总数",
                            "default": True
                        }
                    },
                    "required": ["index", "query"]
                }
            },
            {
                "name": "elasticsearch_aggregate",
                "description": """在Elasticsearch中执行聚合分析。支持多种聚合类型:
                - terms: 分组统计
                - date_histogram: 时间分布
                - stats: 数值统计(平均值、最大最小值等)
                - cardinality: 去重计数

                参数:
                - index: 索引名称(必需)
                - query: 过滤条件(可选),Query DSL格式
                - aggregations: 聚合配置(必需),JSON格式的aggregations定义
                - size: 返回文档数量(可选),默认0(只返回聚合结果)

                示例:
                1. 按告警类型分组统计:
                   aggregations='{"alert_types": {"terms": {"field": "alert_type", "size": 10}}}'

                2. 按时间分布:
                   aggregations='{"alerts_over_time": {"date_histogram": {"field": "datetime", "calendar_interval": "hour"}}}'

                3. 置信度统计:
                   aggregations='{"confidence_stats": {"stats": {"field": "confidence"}}}'
                """,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "index": {
                            "type": "string",
                            "description": "索引名称"
                        },
                        "query": {
                            "type": "string",
                            "description": "过滤条件(Query DSL JSON字符串)"
                        },
                        "aggregations": {
                            "type": "string",
                            "description": "聚合配置(JSON字符串)"
                        },
                        "size": {
                            "type": "integer",
                            "description": "返回文档数量",
                            "default": 0
                        }
                    },
                    "required": ["index", "aggregations"]
                }
            }
        ]

    def _execute_mcp_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行MCP工具调用(通过Docker容器)

        Args:
            tool_name: 工具名称
            tool_input: 工具输入参数

        Returns:
            工具执行结果
        """
        try:
            logger.info(f"执行MCP工具: {tool_name}, 参数: {json.dumps(tool_input, ensure_ascii=False)}")

            # 构建MCP请求
            mcp_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tool_input
                }
            }

            # 通过Docker exec调用MCP服务器
            docker_cmd = [
                "docker", "exec", "-i", "bold_darwin",  # MCP容器名称
                "node", "/app/build/index.js"  # MCP服务器入口
            ]

            # NOTE(async): subprocess.run 在此处合理 — 通过 Docker exec 调用 MCP 服务器，
            # 调用方应通过 asyncio.to_thread 包装此同步方法
            process = subprocess.run(
                docker_cmd,
                input=json.dumps(mcp_request).encode(),
                capture_output=True,
                timeout=30
            )

            if process.returncode != 0:
                error_msg = process.stderr.decode()
                logger.error(f"MCP工具执行失败: {error_msg}")
                return {"error": error_msg}

            # 解析响应
            response = json.loads(process.stdout.decode())

            if "error" in response:
                logger.error(f"MCP返回错误: {response['error']}")
                return {"error": response["error"]}

            result = response.get("result", {})
            logger.info(f"MCP工具执行成功,返回数据: {len(str(result))} 字符")

            return result

        except subprocess.TimeoutExpired:
            logger.error("MCP工具执行超时")
            return {"error": "执行超时"}
        except Exception as e:
            logger.error(f"MCP工具执行异常: {e}", exc_info=True)
            return {"error": str(e)}

    async def analyze_stream(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式分析查询(SSE方式)

        Args:
            question: 用户问题
            context: 上下文信息(可选)

        Yields:
            分析结果片段(SSE格式)
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
            system_prompt = f"""你是一个专业的视频监控告警数据分析助手。

## 你的能力

1. **数据查询**: 可以使用Elasticsearch工具查询告警数据
2. **数据分析**: 对查询结果进行深入分析和洞察
3. **可视化建议**: 提供数据可视化的建议
4. **趋势预测**: 基于历史数据分析趋势

## 数据索引说明

{es_schema}

## 分析流程

1. **理解问题**: 分析用户的问题意图
2. **构建查询**: 根据问题生成合适的Elasticsearch查询
3. **执行查询**: 调用工具获取数据
4. **数据分析**: 对结果进行统计分析和洞察提取
5. **生成报告**: 以结构化、易读的方式呈现分析结果

## 注意事项

- 优先使用ES|QL查询语言,语法更简洁
- 对于复杂查询,可以分步骤执行多个查询
- 统计数据时要提供具体数字和百分比
- 发现异常或趋势时要明确指出
- 提供可操作的建议和洞察

## 输出格式

使用Markdown格式输出,包括:
- ## 标题分节
- 表格展示数据
- **加粗**重点内容
- 列表呈现要点
- 📊📈等emoji增强可读性

现在,请回答用户的问题。"""

            # 构建消息
            messages = [
                {"role": "user", "content": question}
            ]

            # 添加上下文
            if context:
                context_text = f"\n\n**上下文信息**:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
                messages[0]["content"] += context_text

            # 创建Claude对话(启用工具使用)
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=self._get_elasticsearch_tools(),
                messages=messages,
                stream=True
            )

            # 流式处理响应
            current_tool_use = None
            tool_input_buffer = ""

            for event in response:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        current_tool_use = {
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input": ""
                        }
                        tool_input_buffer = ""

                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        # 文本内容,直接返回
                        yield event.delta.text

                    elif event.delta.type == "input_json_delta":
                        # 工具输入参数
                        tool_input_buffer += event.delta.partial_json

                elif event.type == "content_block_stop":
                    if current_tool_use:
                        # 工具使用完成,执行工具调用
                        try:
                            tool_input = json.loads(tool_input_buffer)
                            yield f"\n\n🔍 **正在查询数据**: {current_tool_use['name']}...\n\n"

                            # 执行MCP工具
                            tool_result = self._execute_mcp_tool(
                                current_tool_use["name"],
                                tool_input
                            )

                            # 继续对话,让Claude分析工具结果
                            messages.append({
                                "role": "assistant",
                                "content": [
                                    {
                                        "type": "tool_use",
                                        "id": current_tool_use["id"],
                                        "name": current_tool_use["name"],
                                        "input": tool_input
                                    }
                                ]
                            })

                            messages.append({
                                "role": "user",
                                "content": [
                                    {
                                        "type": "tool_result",
                                        "tool_use_id": current_tool_use["id"],
                                        "content": json.dumps(tool_result, ensure_ascii=False)
                                    }
                                ]
                            })

                            # 继续流式处理
                            continue_response = self.client.messages.create(
                                model=self.model,
                                max_tokens=4096,
                                system=system_prompt,
                                tools=self._get_elasticsearch_tools(),
                                messages=messages,
                                stream=True
                            )

                            for continue_event in continue_response:
                                if continue_event.type == "content_block_delta":
                                    if continue_event.delta.type == "text_delta":
                                        yield continue_event.delta.text

                        except Exception as e:
                            logger.error(f"工具执行失败: {e}", exc_info=True)
                            yield f"\n\n❌ **查询失败**: {str(e)}\n\n"

                        finally:
                            current_tool_use = None
                            tool_input_buffer = ""

        except Exception as e:
            logger.error(f"Claude MCP分析失败: {e}", exc_info=True)
            yield f"\n\n❌ **分析失败**: {str(e)}\n\n"

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
