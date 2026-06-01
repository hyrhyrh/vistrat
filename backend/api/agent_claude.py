"""
Claude Agent API端点
基于Claude + ES工具调用的简洁架构
"""
import json
import logging
import uuid
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional

from agent.llm.claude_es_client import ClaudeESClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent-claude", tags=["agent-claude"])


@router.get("/chat")
async def chat(
    question: str = Query(..., description="用户问题"),
    session_id: Optional[str] = Query(None, description="会话ID"),
    user_id: str = Query("anonymous", description="用户ID")
):
    """
    Claude Agent 对话端点(SSE流式响应)

    架构: 大模型(Claude) + ES工具调用 + 上下文工程

    Args:
        question: 用户问题
        session_id: 会话ID(可选)
        user_id: 用户ID(可选)

    Returns:
        StreamingResponse: SSE流
    """

    # 生成或使用现有session_id
    if not session_id:
        session_uuid = uuid.uuid4()
    else:
        try:
            session_uuid = uuid.UUID(session_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="无效的会话ID")

    logger.info(f"[{user_id}] Claude Agent查询: {question} (session: {session_uuid})")

    async def generate():
        """SSE生成器"""
        try:
            # 创建Claude客户端
            claude_client = ClaudeESClient()

            # 流式分析
            async for chunk in claude_client.analyze_stream(question=question):
                # SSE格式: data: {json}\n\n
                yield f"data: {json.dumps({'stage': 'analyzing', 'content': chunk}, ensure_ascii=False)}\n\n"

            # 发送完成信号
            yield f"data: {json.dumps({'stage': 'completed', 'message': '分析完成'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"[{user_id}] Claude分析失败: {e}", exc_info=True)
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
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/health")
async def health_check():
    """
    Claude Agent健康检查

    Returns:
        dict: 健康状态
    """
    return {
        "status": "healthy",
        "service": "claude-agent",
        "version": "MVP-1.0.0",
        "architecture": "LLM + ES Tools + Context Engineering"
    }
