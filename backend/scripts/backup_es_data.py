"""
Elasticsearch数据备份脚本
备份video_frame_results和video_alerts索引数据到JSON文件
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from config.settings import ElasticsearchConfig
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_index(es: Elasticsearch, index_name: str, backup_dir: Path) -> bool:
    """备份单个索引"""

    try:
        # 检查索引是否存在
        if not es.indices.exists(index=index_name):
            logger.warning(f"索引 {index_name} 不存在，跳过备份")
            return True

        # 获取文档总数
        total_docs = es.count(index=index_name)['count']
        logger.info(f"索引 {index_name} 包含 {total_docs} 个文档")

        if total_docs == 0:
            logger.info(f"索引 {index_name} 没有数据，跳过备份")
            return True

        # 创建备份文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"{index_name}_{timestamp}.json"

        logger.info(f"开始备份到文件: {backup_file}")

        # 使用scan API获取所有文档
        documents = []
        for doc in scan(
            es,
            index=index_name,
            query={"query": {"match_all": {}}},
            scroll='5m',
            size=1000
        ):
            documents.append({
                "_id": doc["_id"],
                "_source": doc["_source"]
            })

        # 写入备份文件
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump({
                "index": index_name,
                "backup_time": timestamp,
                "total_documents": len(documents),
                "documents": documents
            }, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 备份完成: {len(documents)} 个文档 -> {backup_file}")
        logger.info(f"文件大小: {backup_file.stat().st_size / 1024 / 1024:.2f} MB")

        return True

    except Exception as e:
        logger.error(f"备份索引 {index_name} 失败: {e}")
        return False


def restore_index(es: Elasticsearch, backup_file: Path, target_index: str = None) -> bool:
    """从备份文件恢复索引"""

    try:
        if not backup_file.exists():
            logger.error(f"备份文件不存在: {backup_file}")
            return False

        logger.info(f"从备份文件恢复: {backup_file}")

        # 读取备份文件
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)

        index_name = target_index or backup_data['index']
        documents = backup_data['documents']
        total_docs = backup_data['total_documents']

        logger.info(f"备份文件包含 {total_docs} 个文档")
        logger.info(f"准备恢复到索引: {index_name}")

        # 批量恢复文档
        from elasticsearch.helpers import bulk

        actions = [
            {
                "_index": index_name,
                "_id": doc["_id"],
                "_source": doc["_source"]
            }
            for doc in documents
        ]

        success_count, failed_items = bulk(es, actions, raise_on_error=False)

        if failed_items:
            logger.warning(f"部分文档恢复失败: {len(failed_items)} 个")

        logger.info(f"✅ 恢复完成: {success_count}/{total_docs} 个文档")

        return True

    except Exception as e:
        logger.error(f"恢复索引失败: {e}")
        return False


def main():
    """主函数"""

    print("=" * 60)
    print("Elasticsearch 数据备份工具")
    print("=" * 60)
    print()

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

    logger.info(f"✅ 已连接到Elasticsearch: {es_url}")
    print()

    # 创建备份目录
    backup_dir = Path(__file__).parent.parent / "backups" / "elasticsearch"
    backup_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"备份目录: {backup_dir}")
    print()

    # 备份索引列表
    indices_to_backup = [
        ElasticsearchConfig.FRAME_RESULTS_INDEX,  # video_frame_results
        ElasticsearchConfig.ALERTS_INDEX,         # video_alerts
    ]

    # 执行备份
    all_success = True
    for index_name in indices_to_backup:
        print("-" * 60)
        success = backup_index(es, index_name, backup_dir)
        if not success:
            all_success = False
        print()

    print("=" * 60)
    if all_success:
        print("✅ 所有索引备份完成")
        print(f"备份文件位置: {backup_dir}")
    else:
        print("❌ 部分索引备份失败")
    print("=" * 60)

    return all_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
