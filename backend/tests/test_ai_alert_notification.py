#!/usr/bin/env python3
"""
测试AI智能分析告警通知功能
直接调用告警通知服务，验证整个流程：
1. 调用Claude AI分析助手
2. 获取今日告警分析数据
3. 推送到企业微信群
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_file = project_root / '.env'
if env_file.exists():
    load_dotenv(env_file)
    logging.info(f"✅ 已加载环境变量文件: {env_file}")
else:
    logging.warning(f"⚠️ 未找到.env文件: {env_file}")

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,  # 改为DEBUG级别以查看详细信息
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def test_ai_alert_notification():
    """测试AI智能分析告警通知"""
    logger.info("=" * 60)
    logger.info("开始测试AI智能分析告警通知功能")
    logger.info("=" * 60)

    try:
        # 1. 初始化数据库连接
        from database.connection import DatabaseManager

        logger.info("正在初始化数据库连接...")
        db_manager = DatabaseManager()
        await db_manager.initialize()
        logger.info("✅ 数据库连接初始化完成")

        # 2. 导入告警通知服务
        from services.alert_notification_service import AlertNotificationService

        logger.info("✅ 成功导入AlertNotificationService")

        # 3. 创建服务实例
        alert_service = AlertNotificationService()
        logger.info("✅ 创建告警通知服务实例")

        # 4. 加载配置（从数据库加载企业微信webhook等）
        alert_service._load_configuration_sync()
        logger.info("✅ 加载配置完成")

        # 5. 初始化适配器
        alert_service._initialize_adapters_sync()
        logger.info(f"✅ 初始化通知适配器，共 {len(alert_service.adapters)} 个渠道")

        if not alert_service.adapters:
            logger.error("❌ 未配置任何通知适配器！")
            logger.error("请确保在system_config表中配置了qywx_webhook")
            return False

        # 6. 直接调用AI分析汇总通知方法
        logger.info("-" * 60)
        logger.info("开始调用AI分析助手生成告警汇总...")
        logger.info("-" * 60)

        await alert_service._send_scheduled_summary()

        logger.info("-" * 60)
        logger.info("✅ AI分析告警通知测试完成")
        logger.info("-" * 60)

        # 7. 显示统计信息
        logger.info("\n统计信息:")
        logger.info(f"  - 定时通知发送次数: {alert_service.total_scheduled_notifications}")
        logger.info(f"  - 总通知发送次数: {alert_service.total_notifications_sent}")

        # 8. 清理资源
        await db_manager.close()
        logger.info("✅ 数据库连接已关闭")

        return True

    except ImportError as e:
        logger.error(f"❌ 导入模块失败: {e}")
        logger.error("请确保在backend目录下运行此脚本")
        return False

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return False


async def main():
    """主函数"""
    logger.info("\n" + "=" * 60)
    logger.info("AI智能分析告警通知测试脚本")
    logger.info("=" * 60 + "\n")

    # 提示信息
    logger.info("📋 测试流程:")
    logger.info("  1. 初始化告警通知服务")
    logger.info("  2. 加载企业微信webhook配置")
    logger.info("  3. 调用Claude AI分析助手")
    logger.info("  4. 查询今日告警数据")
    logger.info("  5. 生成AI分析报告")
    logger.info("  6. 推送到企业微信群")
    logger.info("")
    logger.info("⏱️  预计耗时: 30-60秒（取决于AI分析速度）")
    logger.info("=" * 60 + "\n")

    # 运行测试
    success = await test_ai_alert_notification()

    # 显示结果
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("✅ 测试成功！")
        logger.info("请检查企业微信群是否收到AI分析报告")
    else:
        logger.info("❌ 测试失败，请查看上方错误日志")
    logger.info("=" * 60 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
