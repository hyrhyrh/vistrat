"""
Agent API端点 - 统一多LLM智能分析接口
支持Claude、DeepSeek等多种LLM模型
架构: LLM + ES工具调用 + 上下文工程
"""
import json
import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from agent.llm.claude_es_client import ClaudeESClient
from agent.llm.deepseek_es_client import DeepSeekESClient
from config.settings import ElasticsearchConfig
from database.connection import get_async_session as get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent", tags=["agent"])


# ========== 请求/响应模型 ==========

class HistoryMessage(BaseModel):
    """历史消息模型"""
    role: str  # 'user' 或 'assistant'
    content: str

class ChatRequest(BaseModel):
    """多轮对话请求模型"""
    question: str
    model: str = "deepseek"  # 默认使用deepseek
    history: Optional[List[HistoryMessage]] = None  # 对话历史(最多保留最近5轮)
    session_id: Optional[str] = None
    user_id: str = "anonymous"


# ========== LLM客户端工厂 ==========

def get_llm_client(model: str):
    """
    根据模型名称获取对应的LLM ES客户端

    Args:
        model: 模型名称 (claude/deepseek)

    Returns:
        对应的LLM ES客户端实例

    Raises:
        ValueError: 不支持的模型名称
    """
    es_url = ElasticsearchConfig.get_es_url()

    if model == "claude":
        return ClaudeESClient(es_url=es_url)
    elif model == "deepseek":
        return DeepSeekESClient(es_url=es_url)
    else:
        raise ValueError(f"不支持的模型: {model}。支持的模型: claude, deepseek")


# ========== API端点 ==========

@router.get("/chat")
async def chat(
    question: str = Query(..., description="用户问题"),
    model: str = Query("deepseek", description="LLM模型选择: claude, deepseek"),
    history: Optional[str] = Query(None, description="对话历史(JSON数组字符串,最多5轮)"),
    session_id: Optional[str] = Query(None, description="会话ID(可选,用于连续对话)"),
    user_id: str = Query("anonymous", description="用户ID(可选,用于记录)"),
    db: AsyncSession = Depends(get_db)
):
    """
    AI智能体对话端点(SSE流式响应) - 统一多LLM接口,支持多轮对话

    支持的模型:
    - deepseek: DeepSeek Chat (默认,经济实惠,性能均衡)
    - claude: Claude Sonnet 4 (高精度,成本较高)

    Args:
        question: 用户问题
        model: LLM模型选择,默认deepseek
        history: 对话历史JSON字符串,格式: [{"role":"user","content":"..."},{"role":"assistant","content":"..."}]
        session_id: 可选的会话ID,用于连续对话
        user_id: 用户ID,默认为anonymous
        db: 数据库会话

    Returns:
        StreamingResponse: SSE流

    示例:
        GET /api/agent/chat?question=今天有多少告警&model=deepseek
        GET /api/agent/chat?question=还有其他问题吗&model=claude&history=[{"role":"user","content":"..."}]
    """

    # 解析对话历史
    history_messages: List[Dict[str, str]] = []
    if history:
        try:
            history_data = json.loads(history)
            # 限制历史消息数量,只保留最近5轮(10条消息)
            max_history = 10
            if len(history_data) > max_history:
                history_data = history_data[-max_history:]

            history_messages = [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in history_data
                if msg.get("content")
            ]
        except json.JSONDecodeError as e:
            logger.warning(f"解析历史消息失败: {e}")
            # 继续执行,忽略无效的历史消息

    # 生成或使用现有session_id
    if not session_id:
        session_uuid = uuid.uuid4()
    else:
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的会话ID")

    logger.info(f"[{user_id}] Agent查询 (model={model}): {question} (session: {session_uuid})")

    async def generate():
        """SSE生成器"""
        try:
            # 获取对应的LLM客户端
            try:
                llm_client = get_llm_client(model)
            except ValueError as e:
                yield f"data: {json.dumps({'stage': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
                return

            # 流式分析(支持多轮对话上下文)
            chunk_count = 0
            async for chunk in llm_client.analyze_stream(
                question=question,
                history=history_messages if history_messages else None
            ):
                chunk_count += 1
                logger.debug(f"收到chunk #{chunk_count}: {chunk[:100] if len(chunk) > 100 else chunk}")

                # ✅ 优先处理正确的工具调用标记（用于折叠框显示）
                if "__TOOL_CALL_START__" in chunk:
                    # 提取JSON数据
                    import re
                    match = re.search(r'__TOOL_CALL_START__(.+?)__TOOL_CALL_START__', chunk, re.DOTALL)
                    if match:
                        try:
                            tool_info = json.loads(match.group(1))
                            # 发送工具调用开始事件
                            yield f"data: {json.dumps({'stage': 'tool_call_start', 'data': tool_info}, ensure_ascii=False)}\n\n"
                            continue
                        except json.JSONDecodeError as e:
                            logger.error(f"解析工具调用开始标记失败: {e}")
                            continue

                elif "__TOOL_CALL_RESULT__" in chunk:
                    # 提取JSON数据
                    import re
                    match = re.search(r'__TOOL_CALL_RESULT__(.+?)__TOOL_CALL_RESULT__', chunk, re.DOTALL)
                    if match:
                        try:
                            tool_result = json.loads(match.group(1))
                            # 发送工具调用结果事件
                            yield f"data: {json.dumps({'stage': 'tool_call_result', 'data': tool_result}, ensure_ascii=False)}\n\n"
                            continue
                        except json.JSONDecodeError as e:
                            logger.error(f"解析工具调用结果标记失败: {e}")
                            continue

                # ✅ 普通内容 - LLM的分析总结，流式显示给用户
                # 统一SSE格式 - 使用 'analyze' 阶段名称
                logger.debug(f"发送analyze chunk #{chunk_count}: {len(chunk)} 字符")
                yield f"data: {json.dumps({'stage': 'analyze', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 分析完成
            yield f"data: {json.dumps({'stage': 'completed', 'message': '分析完成'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[{user_id}] Agent查询失败 (model={model}): {e}", exc_info=True)
            error_msg = {
                "stage": "error",
                "message": f"分析失败: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # 禁用Nginx缓冲
        }
    )


@router.get("/health")
async def health_check():
    """
    Agent服务健康检查

    Returns:
        dict: 健康状态
    """
    return {
        "status": "healthy",
        "service": "agent",
        "version": "1.0.0"
    }
