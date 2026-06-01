"""
调试分析队列和预警信息生成
检查分析任务执行状态和日志
"""

import asyncio
import logging
from datetime import datetime, timedelta
from services.ai_analysis_log_service import ai_analysis_log_service
from services.video_file_service import VideoFileService
from services.elasticsearch_service import ElasticsearchService
from database.connection import DatabaseManager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_analysis_status():
    """调试分析状态"""
    try:
        # 初始化数据库连接
        await DatabaseManager.initialize()
        
        print("=" * 60)
        print("AI分析调试报告")
        print("=" * 60)
        
        # 1. 检查最近24小时的分析日志
        print("\n1. 检查最近24小时的AI分析调用日志:")
        recent_logs = await ai_analysis_log_service.get_recent_logs(hours=24, limit=10)
        
        if recent_logs:
            print(f"找到 {len(recent_logs)} 条分析日志:")
            for log in recent_logs:
                print(f"  - 任务: {log.task_id}, 视频: {log.video_id}")
                print(f"    状态: {log.call_status}, 响应时间: {log.response_time_ms}ms")
                print(f"    算法: {log.algorithm_id}, 帧: {log.frame_index}")
                print(f"    时间: {log.call_date}")
                if log.error_message:
                    print(f"    错误: {log.error_message}")
                print()
        else:
            print("  没有找到最近的分析日志")
        
        # 2. 检查分析日志统计
        print("\n2. 最近24小时分析统计:")
        stats = await ai_analysis_log_service.get_log_statistics(hours=24)
        print(f"  总调用次数: {stats.total_calls}")
        print(f"  成功调用: {stats.success_calls}")
        print(f"  失败调用: {stats.failed_calls}")
        print(f"  成功率: {stats.success_rate}%")
        print(f"  平均响应时间: {stats.avg_response_time}ms")
        
        if stats.most_common_errors:
            print("  常见错误:")
            for error in stats.most_common_errors:
                print(f"    {error['error_code']}: {error['count']} 次")
        
        # 3. 检查视频文件状态
        print("\n3. 检查最近的视频文件状态:")
        try:
            videos = await VideoFileService.get_all_videos(limit=5)
            if videos:
                for video in videos:
                    print(f"  视频: {video.get('name', 'N/A')}")
                    print(f"  状态: {video.get('status', 'N/A')}")
                    print(f"  分析进度: {video.get('analysis_progress', 0)}%")
                    print(f"  告警数量: {video.get('total_alerts', 0)}")
                    print(f"  上传时间: {video.get('created_at', 'N/A')}")
                    print()
            else:
                print("  没有找到视频文件")
        except Exception as e:
            print(f"  获取视频文件失败: {e}")
            # 尝试查询数据库获取原始数据
            try:
                from sqlalchemy import select, desc
                from models.video_file import VideoFileDB
                
                async with DatabaseManager.get_session() as session:
                    stmt = select(VideoFileDB).order_by(desc(VideoFileDB.created_at)).limit(5)
                    result = await session.execute(stmt)
                    videos = result.scalars().all()
                    
                    if videos:
                        print(f"  找到 {len(videos)} 个视频文件:")
                        for video in videos:
                            print(f"    视频: {video.name}")
                            print(f"    状态: {video.status}")
                            print(f"    文件路径: {video.file_path}")
                            print(f"    分析进度: {video.analysis_progress}%")
                            print(f"    总告警: {video.total_alerts}")
                            print(f"    上传时间: {video.created_at}")
                            print()
                    else:
                        print("  数据库中没有视频文件")
                        
            except Exception as db_e:
                print(f"  直接查询数据库也失败: {db_e}")
        
        # 4. 检查Elasticsearch中的分析结果
        print("\n4. 检查Elasticsearch中的分析结果:")
        es_service = ElasticsearchService()
        
        if es_service.es_client:
            try:
                # 查询最近的分析结果
                recent_results = await es_service.get_analysis_results(
                    limit=5,
                    hours=24
                )
                
                if recent_results:
                    print(f"找到 {len(recent_results)} 条分析结果:")
                    for result in recent_results:
                        print(f"  任务ID: {result.get('task_id', 'N/A')}")
                        print(f"  视频ID: {result.get('video_id', 'N/A')}")
                        print(f"  状态: {result.get('analysis_status', 'N/A')}")
                        print(f"  处理时间: {result.get('processing_time', 'N/A')}ms")
                        print(f"  创建时间: {result.get('created_at', 'N/A')}")
                        print()
                else:
                    print("  没有找到最近的分析结果")
                
                # 查询最近的预警信息
                recent_alerts = await es_service.get_alerts(
                    limit=5,
                    hours=24
                )
                
                if recent_alerts:
                    print(f"找到 {len(recent_alerts)} 条预警信息:")
                    for alert in recent_alerts:
                        print(f"  预警类型: {alert.get('alert_type', 'N/A')}")
                        print(f"  视频: {alert.get('video_name', 'N/A')}")
                        print(f"  置信度: {alert.get('confidence', 'N/A')}")
                        print(f"  描述: {alert.get('description', 'N/A')}")
                        print(f"  时间: {alert.get('created_at', 'N/A')}")
                        print()
                else:
                    print("  没有找到最近的预警信息")
                    
            except Exception as e:
                print(f"  Elasticsearch查询失败: {e}")
        else:
            print("  Elasticsearch客户端未连接")
        
        # 5. 分析问题诊断
        print("\n5. 问题诊断建议:")
        
        if not recent_logs:
            print("  ❌ 没有AI分析调用日志 - 可能原因:")
            print("     - 没有触发视频分析")
            print("     - 分析服务未启动或有错误")
            print("     - 数据库连接问题")
        elif stats.failed_calls > stats.success_calls:
            print("  ⚠️ AI调用失败率较高 - 可能原因:")
            print("     - AI模型API密钥无效或配额不足")
            print("     - 网络连接问题")
            print("     - 请求格式错误")
        elif stats.success_calls > 0 and not recent_results:
            print("  ⚠️ AI调用成功但无分析结果 - 可能原因:")
            print("     - Elasticsearch存储失败")
            print("     - 结果处理逻辑错误")
        elif recent_results and not recent_alerts:
            print("  ⚠️ 有分析结果但无预警 - 可能原因:")
            print("     - 预警条件未触发")
            print("     - 预警阈值设置过高")
            print("     - AI响应内容未匹配预警关键词")
        else:
            print("  ✅ 系统运行正常")
        
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"调试分析状态失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 关闭数据库连接
        await DatabaseManager.close()


if __name__ == "__main__":
    asyncio.run(debug_analysis_status())