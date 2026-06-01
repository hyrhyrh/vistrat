"""v3 系统健康检查 API"""

from fastapi import APIRouter
from services.health_service import HealthService

router = APIRouter(tags=["v3-健康检查"])


@router.get("/health")
async def health_check():
    """系统健康检查"""
    return await HealthService.check()
