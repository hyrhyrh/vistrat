"""
重建video_frame_results索引脚本
用于修复stream_id字段类型问题（从text改为keyword）
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from config.settings import ElasticsearchConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def reindex_frame_results():
    """重建video_frame_results索引"""

    # 连接ES
    es_url = ElasticsearchConfig.get_es_url()
    es = Elasticsearch(
        hosts=[es_url],
        verify_certs=False,
        ssl_show_warn=False,
        request_timeout=300
    )

    if not es.ping():
        logger.error("无法连接到Elasticsearch")
        return False

    logger.info("✅ 已连接到Elasticsearch")

    old_index = ElasticsearchConfig.FRAME_RESULTS_INDEX
    temp_index = f"{old_index}_temp"

    # 1. 检查旧索引是否存在
    if not es.indices.exists(index=old_index):
        logger.info(f"索引 {old_index} 不存在，无需重建")
        return True

    # 2. 获取旧索引的文档数量
    old_count = es.count(index=old_index)['count']
    logger.info(f"旧索引 {old_index} 包含 {old_count} 个文档")

    # 3. 创建新mapping
    new_mapping = {
        "mappings": {
            "properties": {
                "task_id": {"type": "keyword"},
                "video_id": {"type": "keyword"},
                "stream_id": {"type": "keyword"},  # 修改为keyword类型
                "frame_index": {"type": "integer"},
                "timestamp": {"type": "float"},
                "datetime": {"type": "date"},
                "video_time": {"type": "keyword"},
                "template_id": {"type": "keyword"},
                "template_name": {"type": "text"},
                "category": {"type": "keyword"},
                "priority": {"type": "integer"},
                "ai_response": {"type": "text", "analyzer": "standard"},
                "confidence": {"type": "float"},
                "model_used": {"type": "keyword"},
                "has_alert": {"type": "boolean"},
                "analyzed_at": {"type": "date"},
                "created_at": {"type": "date"},
                "image_url": {"type": "keyword"},
                "data_type": {"type": "keyword"},
                "detection_objects": {
                    "type": "nested",
                    "properties": {
                        "class_name": {"type": "keyword"},
                        "confidence": {"type": "float"},
                        "bbox": {"type": "object"}
                    }
                }
            }
        }
    }

    # 4. 创建临时索引
    logger.info(f"创建临时索引 {temp_index}...")
    if es.indices.exists(index=temp_index):
        es.indices.delete(index=temp_index)
    es.indices.create(index=temp_index, body=new_mapping)
    logger.info(f"✅ 临时索引 {temp_index} 创建成功")

    # 5. 使用reindex API将数据从旧索引复制到新索引
    if old_count > 0:
        logger.info("开始数据迁移...")
        reindex_body = {
            "source": {"index": old_index},
            "dest": {"index": temp_index}
        }

        result = es.reindex(body=reindex_body, wait_for_completion=True, request_timeout=300)

        if result.get('failures'):
            logger.error(f"数据迁移失败: {result['failures']}")
            return False

        migrated_count = result.get('created', 0)
        logger.info(f"✅ 数据迁移完成: {migrated_count}/{old_count} 个文档")
    else:
        logger.info("旧索引没有数据，跳过数据迁移")

    # 6. 删除旧索引
    logger.info(f"删除旧索引 {old_index}...")
    es.indices.delete(index=old_index)
    logger.info(f"✅ 旧索引 {old_index} 已删除")

    # 7. 将临时索引重命名为原索引名
    logger.info(f"重命名临时索引 {temp_index} -> {old_index}...")

    # ES不支持直接重命名，需要使用别名
    # 但这里我们采用reindex到原索引名的方式
    es.indices.create(index=old_index, body=new_mapping)

    if old_count > 0:
        reindex_body = {
            "source": {"index": temp_index},
            "dest": {"index": old_index}
        }
        result = es.reindex(body=reindex_body, wait_for_completion=True, request_timeout=300)
        logger.info(f"✅ 索引重命名完成")

    # 8. 删除临时索引
    es.indices.delete(index=temp_index)
    logger.info(f"✅ 临时索引 {temp_index} 已删除")

    # 9. 验证新索引
    new_count = es.count(index=old_index)['count']
    logger.info(f"新索引 {old_index} 包含 {new_count} 个文档")

    if new_count == old_count:
        logger.info("✅ 索引重建成功，数据完整")
        return True
    else:
        logger.warning(f"⚠️  数据数量不一致: 旧={old_count}, 新={new_count}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("重建 video_frame_results 索引")
    print("修复 stream_id 字段类型（text -> keyword）")
    print("=" * 60)
    print()

    confirm = input("此操作将重建索引，确认继续? (yes/no): ")
    if confirm.lower() != 'yes':
        print("操作已取消")
        sys.exit(0)

    print()
    success = reindex_frame_results()

    if success:
        print()
        print("=" * 60)
        print("✅ 索引重建完成")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ 索引重建失败")
        print("=" * 60)
        sys.exit(1)
