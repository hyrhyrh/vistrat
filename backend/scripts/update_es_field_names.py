"""
更新Elasticsearch索引中的字段名
将 alert_type 重命名为 analysis_type
"""
import asyncio
from elasticsearch import AsyncElasticsearch, helpers
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import ElasticsearchConfig


async def update_field_names():
    """更新ES中的字段名称"""

    # 连接ES
    es = AsyncElasticsearch(
        [f"http://{ElasticsearchConfig.ES_HOST}:{ElasticsearchConfig.ES_PORT}"],
        verify_certs=False,
        ssl_show_warn=False
    )

    try:
        print("连接到Elasticsearch...")

        # 检查连接
        if not await es.ping():
            print("无法连接到Elasticsearch!")
            return

        print("成功连接到Elasticsearch")

        # 更新 video_alerts 索引
        print("\n开始更新 video_alerts 索引...")

        # 使用 update_by_query 更新字段
        update_script = {
            "script": {
                "source": """
                    if (ctx._source.containsKey('alert_type')) {
                        ctx._source.analysis_type = ctx._source.alert_type;
                        ctx._source.remove('alert_type');
                    }
                """,
                "lang": "painless"
            },
            "query": {
                "exists": {
                    "field": "alert_type"
                }
            }
        }

        try:
            response = await es.update_by_query(
                index="video_alerts",
                body=update_script,
                conflicts="proceed",  # 忽略版本冲突
                wait_for_completion=True
            )

            updated_count = response.get("updated", 0)
            print(f"✅ video_alerts 索引更新完成! 更新了 {updated_count} 条记录")

        except Exception as e:
            if "index_not_found_exception" in str(e):
                print("⚠️  video_alerts 索引不存在,跳过")
            else:
                print(f"❌ 更新 video_alerts 索引失败: {e}")

        # 刷新索引
        try:
            await es.indices.refresh(index="video_alerts")
            print("✅ video_alerts 索引已刷新")
        except Exception:
            pass  # 索引刷新失败不影响主流程

        print("\n所有索引更新完成!")

    finally:
        await es.close()


if __name__ == "__main__":
    print("=" * 60)
    print("ES索引字段重命名工具")
    print("将 alert_type 字段重命名为 analysis_type")
    print("=" * 60)

    asyncio.run(update_field_names())
