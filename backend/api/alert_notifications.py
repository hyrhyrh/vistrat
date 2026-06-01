"""
告警通知API端点
提供告警通知服务的管理和查询接口
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel

from services.alert_notification_service import alert_notification_service

router = APIRouter(prefix="/alert-notifications", tags=["alert_notifications"])


class DailyReportRequest(BaseModel):
    """每日报表请求"""
    report_content: str
    title: str = "每日告警统计报表"


@router.get("/statistics")
async def get_notification_statistics() -> Dict[str, Any]:
    """
    获取告警通知统计信息

    Returns:
        统计信息字典
    """
    return alert_notification_service.get_statistics()


@router.post("/test")
async def send_test_notification() -> Dict[str, Any]:
    """
    发送测试通知

    Returns:
        发送结果
    """
    success = await alert_notification_service.send_test_notification()

    return {
        'success': success,
        'message': '测试通知已发送' if success else '测试通知发送失败'
    }


@router.post("/send-daily-report")
async def send_daily_report(request: DailyReportRequest) -> Dict[str, Any]:
    """
    发送每日告警统计报表到企业微信

    Args:
        request: 报表请求,包含报表内容和标题

    Returns:
        发送结果
    """
    try:
        success = await alert_notification_service.send_daily_report(
            report_content=request.report_content,
            title=request.title
        )

        return {
            'success': success,
            'message': '告警统计报表已发送' if success else '告警统计报表发送失败'
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送报表失败: {str(e)}")


@router.get("/health")
async def get_notification_health() -> Dict[str, Any]:
    """
    获取告警通知服务健康状态

    Returns:
        健康状态信息
    """
    stats = alert_notification_service.get_statistics()

    if stats['service_status'] != 'running':
        return {
            'status': 'stopped',
            'message': '告警通知服务未运行'
        }

    if stats['adapters_count'] == 0:
        return {
            'status': 'degraded',
            'message': '未配置通知适配器'
        }

    return {
        'status': 'healthy',
        'message': '告警通知服务运行正常',
        'adapters_count': stats['adapters_count'],
        'total_notifications_sent': stats['total_notifications_sent']
    }


@router.post("/test-daily-report")
async def test_daily_report_generation() -> Dict[str, Any]:
    """
    手动测试AI日报生成和发送功能

    这个接口会立即触发日报生成,无需等待定时任务
    适用于测试和调试

    Returns:
        生成和发送结果
    """
    try:
        # 直接调用内部方法生成日报
        await alert_notification_service._send_scheduled_summary()

        return {
            'success': True,
            'message': 'AI视频分析预警日报已生成并发送到企业微信',
            'tip': '请检查企业微信群消息'
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"日报生成失败: {str(e)}"
        )
