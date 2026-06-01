"""v3 API router -- prefix /api/v3/, coexists with old API"""
from fastapi import APIRouter
from api.v3.streams import router as streams_router
from api.v3.analysis import router as analysis_router
from api.v3.health import router as health_router
from api.v3.alerts import router as alerts_router
from api.v3.callbacks import router as callbacks_router

v3_router = APIRouter(prefix="/api/v3", tags=["v3"])
v3_router.include_router(streams_router)
v3_router.include_router(analysis_router)
v3_router.include_router(health_router)
v3_router.include_router(alerts_router)
v3_router.include_router(callbacks_router)
