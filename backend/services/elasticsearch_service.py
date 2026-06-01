"""
Elasticsearch分析结果存储服务
负责将视频分析结果存储到Elasticsearch中，支持高效的搜索和查询
"""

import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from elasticsearch import Elasticsearch, helpers
import asyncio
from concurrent.futures import ThreadPoolExecutor
from utils.timezone_utils import now, now_isoformat
from config.settings import ElasticsearchConfig
from services.helpers.es_query_builder import create_indices as _create_indices_helper

# 强制ES客户端使用兼容模式
os.environ['ELASTIC_CLIENT_APIVERSIONING'] = 'true'

logger = logging.getLogger(__name__)


class ElasticsearchService:
    """Elasticsearch服务 - 自适应线程池（兼容ARM/Windows）"""

    def __init__(self):
        self.es_client = None
        # 延迟初始化线程池（首次使用时创建）
        self._executor = None
        self._executor_available = None  # None=未测试, True=可用, False=不可用
        self._executor_lock = asyncio.Lock()
        self._initialize_client()

    async def _ensure_executor(self):
        """延迟创建线程池（首次调用时测试是否可用）"""
        if self._executor_available is not None:
            return  # 已经测试过了

        async with self._executor_lock:
            # 双重检查
            if self._executor_available is not None:
                return

            try:
                # 尝试创建小型线程池进行测试
                test_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ESTest")

                # 测试是否能成功执行
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(test_pool, lambda: True),
                    timeout=2.0
                )

                # 测试成功，关闭测试池，创建正式线程池
                test_pool.shutdown(wait=False)
                self._executor = ThreadPoolExecutor(
                    max_workers=3,
                    thread_name_prefix="ESService"
                )
                self._executor_available = True
                logger.info("✅ ES服务线程池创建成功（高性能模式，max_workers=3）")

            except Exception as e:
                # 线程池不可用，使用降级模式
                self._executor = None
                self._executor_available = False
                logger.warning(f"⚠️ ES服务线程池不可用（ARM/Windows限制），使用兼容模式（asyncio.to_thread）: {e}")

    @property
    def executor(self):
        """兼容性属性：返回executor或None"""
        return self._executor

    async def _run_sync(self, func, *args, **kwargs):
        """
        自适应执行同步函数

        - 如果线程池可用：使用线程池（高性能）
        - 如果线程池不可用：使用asyncio.to_thread（兼容）
        """
        # 确保线程池已初始化
        await self._ensure_executor()

        if self._executor_available and self._executor:
            # 高性能模式：使用线程池
            loop = asyncio.get_event_loop()
            # run_in_executor不支持kwargs，需要用lambda包装
            if kwargs:
                return await loop.run_in_executor(
                    self._executor,
                    lambda: func(*args, **kwargs)
                )
            else:
                return await loop.run_in_executor(self._executor, func, *args)
        else:
            # 兼容模式：使用asyncio.to_thread
            return await asyncio.to_thread(func, *args, **kwargs)

    def _initialize_client(self):
        """初始化Elasticsearch客户端"""
        try:
            # 构建连接URL
            if ElasticsearchConfig.ES_USERNAME and ElasticsearchConfig.ES_PASSWORD:
                auth = (ElasticsearchConfig.ES_USERNAME, ElasticsearchConfig.ES_PASSWORD)
            else:
                auth = None

            es_url = ElasticsearchConfig.get_es_url()
            logger.info(f"正在连接 Elasticsearch: {es_url}")

            # 创建客户端 - ES 8.15.0客户端配置，与8.11.0服务端兼容
            self.es_client = Elasticsearch(
                hosts=[es_url],
                basic_auth=auth,  # ES 8.x推荐使用basic_auth
                verify_certs=False,
                ssl_show_warn=False,
                request_timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )

            # 测试连接
            if self.es_client.ping():
                logger.info(f"✅ Elasticsearch 连接成功: {es_url}")
                self._create_indices()
            else:
                logger.error(f"❌ Elasticsearch ping失败: {es_url}，但保留客户端用于懒加载")

        except Exception as e:
            logger.error(f"❌ 初始化Elasticsearch客户端失败: {e}")
            self.es_client = None
    
    def _ensure_connection(self):
        """确保ES连接可用，支持懒加载重连"""
        if not self.es_client:
            self._initialize_client()
            return self.es_client is not None
        
        try:
            if self.es_client.ping():
                return True
            else:
                logger.warning("ES连接已断开，尝试重连")
                self._initialize_client()
                return self.es_client is not None
        except Exception as e:
            logger.warning(f"ES连接检查失败，尝试重连: {e}")
            self._initialize_client()
            return self.es_client is not None
    
    def _create_indices(self):
        """创建必需的索引 - 委托给 helpers.es_query_builder"""
        _create_indices_helper(self.es_client, ElasticsearchConfig)
    
    async def store_analysis_result(self, task_id: str, video_id: str, 
                                  analysis_data: Dict[str, Any]) -> bool:
        """存储分析任务结果"""
        if not self._ensure_connection():
            logger.warning("Elasticsearch连接不可用，跳过存储")
            return False
        
        try:
            # 准备文档数据
            doc = {
                "task_id": task_id,
                "video_id": video_id,
                "video_name": analysis_data.get("video_name", ""),
                "original_filename": analysis_data.get("original_filename", ""),
                "template_ids": analysis_data.get("template_ids", []),
                "analysis_status": analysis_data.get("status", "completed"),
                "total_frames_analyzed": analysis_data.get("frames_analyzed", 0),
                "total_alerts": analysis_data.get("total_alerts", 0),
                "analysis_duration": analysis_data.get("duration", 0.0),
                "created_at": analysis_data.get("created_at", now_isoformat()),
                "started_at": analysis_data.get("started_at"),
                "completed_at": analysis_data.get("completed_at", now_isoformat()),
                "results_summary": analysis_data.get("results_summary", [])
            }

            # 异步存储（自适应线程池）
            await self._run_sync(
                self._store_document,
                ElasticsearchConfig.ANALYSIS_RESULTS_INDEX,
                task_id,
                doc
            )
            
            logger.info(f"分析结果已存储到Elasticsearch: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"存储分析结果失败: {e}")
            return False
    
    async def store_frame_results(self, task_id: str, video_id: str, 
                                frame_results: List[Dict[str, Any]]) -> bool:
        """批量存储帧分析结果"""
        if not frame_results:
            return False
        
        if not self._ensure_connection():
            logger.warning("Elasticsearch连接不可用，跳过帧结果存储")
            return False
        
        try:
            # 准备批量文档
            docs = []
            for result in frame_results:
                doc_id = f"{task_id}_{result.get('frame_index', 0)}"
                doc = {
                    "_index": ElasticsearchConfig.FRAME_RESULTS_INDEX,
                    "_id": doc_id,
                    "_source": {
                        "task_id": task_id,
                        "video_id": video_id,
                        "frame_index": result.get("frame_index", 0),
                        "timestamp": result.get("timestamp", 0.0),
                        "video_time": result.get("video_time", "00:00"),
                        "template_id": result.get("template_id", ""),
                        "template_name": result.get("template_name", ""),
                        "ai_response": result.get("ai_response", ""),
                        "confidence": result.get("confidence", 0.0),
                        "has_alert": result.get("has_alert", False),
                        "analyzed_at": result.get("analyzed_at", now_isoformat()),
                        "image_url": result.get("image_url") or result.get("image_path", ""),  # 支持新旧字段名
                        "detection_objects": result.get("detection_objects", [])
                    }
                }
                docs.append(doc)
            
            # 异步批量存储
            success_count = await self._run_sync(
                self._bulk_store_documents,
                docs
            )
            
            logger.info(f"帧分析结果已存储到Elasticsearch: {success_count}/{len(docs)} 条")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"批量存储帧结果失败: {e}")
            return False
    
    async def store_alert(self, alert_data: Dict[str, Any]) -> bool:
        """存储预警信息"""
        if not self._ensure_connection():
            logger.warning("Elasticsearch连接不可用，跳过告警存储")
            return False

        try:
            # 准备预警文档
            doc = {
                "task_id": alert_data.get("task_id", ""),
                "video_id": alert_data.get("video_id", ""),
                "video_name": alert_data.get("video_name", ""),
                "frame_index": alert_data.get("frame_index", 0),
                "timestamp": alert_data.get("timestamp", 0.0),
                "video_time": alert_data.get("video_time", "00:00"),
                "template_name": alert_data.get("template_name", ""),
                "analysis_type": alert_data.get("analysis_type", "video_analysis"),  # 分析类型
                "confidence": alert_data.get("confidence", 0.0),
                "description": alert_data.get("description", ""),
                "severity": alert_data.get("severity", "medium"),
                "created_at": alert_data.get("created_at", now_isoformat()),
                "location": alert_data.get("location"),
                "metadata": alert_data.get("metadata", {}),
                "image_url": alert_data.get("image_url", ""),  # 添加图片URL字段
                "algorithm_name": alert_data.get("algorithm_name", ""),  # 添加算法名称字段
                "algorithm_category": alert_data.get("algorithm_category", ""),  # 添加算法类别字段
                "ai_response": alert_data.get("ai_response", ""),  # 添加AI响应字段
                "camera_name": alert_data.get("camera_name"),  # 添加摄像头名称字段
                "detection_details": alert_data.get("detection_details", {})  # 添加检测详情字段
            }
            
            # 生成唯一ID
            alert_id = f"{alert_data.get('task_id', '')}_{alert_data.get('frame_index', 0)}_{int(now().timestamp())}"
            
            # 异步存储
            await self._run_sync(
                self._store_document,
                ElasticsearchConfig.ALERTS_INDEX,
                alert_id,
                doc
            )
            
            logger.info(f"预警信息已存储到Elasticsearch: {alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"存储预警信息失败: {e}")
            return False
    
    def _store_document(self, index: str, doc_id: str, doc: Dict[str, Any]):
        """同步存储单个文档"""
        try:
            response = self.es_client.index(
                index=index,
                id=doc_id,
                body=doc,
                refresh='wait_for'
            )
            return response.get('result') == 'created' or response.get('result') == 'updated'
        except Exception as e:
            logger.error(f"存储文档失败 [{index}:{doc_id}]: {e}")
            return False
    
    def _bulk_store_documents(self, docs: List[Dict[str, Any]]) -> int:
        """同步批量存储文档"""
        try:
            # 使用helpers.bulk正确的返回格式处理
            success_count, failed_docs = helpers.bulk(
                self.es_client,
                docs,
                refresh='wait_for',
                request_timeout=60,
                raise_on_error=False  # 不抛出异常，返回失败文档
            )
            
            if failed_docs:
                logger.error(f"批量存储文档失败: {len(failed_docs)} document(s) failed to index.")
                # 打印详细错误信息
                for i, failed_doc in enumerate(failed_docs[:3]):  # 只显示前3个错误
                    error_info = failed_doc.get('index', {}).get('error', {})
                    logger.error(f"失败文档 {i+1}: {error_info}")
                if len(failed_docs) > 3:
                    logger.error(f"还有 {len(failed_docs)-3} 个类似失败文档...")
                
                return success_count
            else:
                return success_count
            
        except Exception as e:
            logger.error(f"批量存储文档失败: {e}")
            return 0
    
    async def bulk_store_frame_results(self, frame_results: List[Dict[str, Any]]) -> bool:
        """批量存储帧分析结果的简化接口"""
        if not frame_results:
            return False
            
        # 提取task_id和video_id
        first_result = frame_results[0]
        task_id = first_result.get('task_id', 'unknown')
        video_id = first_result.get('video_id', 'unknown')
        
        return await self.store_frame_results(task_id, video_id, frame_results)
    
    async def bulk_index_documents(self, index_name: str, documents: List[Dict[str, Any]]) -> bool:
        """通用批量索引文档方法"""
        if not self.es_client or not documents:
            return False
            
        try:
            # 格式化文档用于批量索引
            bulk_docs = []
            for doc in documents:
                bulk_docs.append({
                    '_index': index_name,
                    '_source': doc
                })
            
            success_count = await self._run_sync(
                lambda: self._bulk_store_documents(bulk_docs)
            )
            
            logger.info(f"批量索引到{index_name}: 成功{success_count}条记录")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"批量索引到{index_name}失败: {e}")
            return False
    
    async def search_analysis_results(self, query: Dict[str, Any], 
                                    size: int = 20, from_: int = 0) -> Dict[str, Any]:
        """搜索分析结果"""
        if not self.es_client:
            return {"hits": {"total": {"value": 0}, "hits": []}}
        
        try:
            loop = asyncio.get_event_loop()
            # ES 8.x 兼容性：将分页参数加入查询体
            search_body = dict(query)
            search_body['size'] = size
            search_body['from'] = from_

            # 自适应线程池执行
            response = await self._run_sync(
                lambda: self.es_client.search(
                    index=ElasticsearchConfig.ANALYSIS_RESULTS_INDEX,
                    body=search_body
                )
            )
            
            return response
            
        except Exception as e:
            logger.error(f"搜索分析结果失败: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}}
    
    async def search_alerts(self, query: Dict[str, Any],
                          size: int = 100, from_: int = 0) -> Dict[str, Any]:
        """搜索预警信息"""
        if not self._ensure_connection():
            logger.warning("Elasticsearch连接不可用，返回空结果")
            return {"hits": {"total": {"value": 0}, "hits": []}}

        try:
            loop = asyncio.get_event_loop()
            # ES 8.x 兼容性：将分页参数加入查询体（如果查询体中没有的话）
            search_body = dict(query)
            if 'size' not in search_body:
                search_body['size'] = size
            if 'from' not in search_body:
                search_body['from'] = from_

            response = await self._run_sync(
                lambda: self.es_client.search(
                    index=ElasticsearchConfig.ALERTS_INDEX,
                    body=search_body
                )
            )

            return response

        except Exception as e:
            logger.error(f"搜索预警信息失败: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}}

    async def search_documents(self, index: str, query: Dict[str, Any],
                              size: int = 10, from_: int = 0,
                              sort: Optional[List[Dict[str, Any]]] = None,
                              aggregations: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """通用文档搜索方法

        Args:
            index: 索引名称
            query: 查询条件
            size: 返回文档数量
            from_: 分页偏移量
            sort: 排序规则
            aggregations: 聚合查询

        Returns:
            搜索结果字典
        """
        if not self._ensure_connection():
            logger.warning("Elasticsearch连接不可用，返回空结果")
            return {"hits": {"total": {"value": 0}, "hits": []}, "aggregations": {}}

        try:
            # 构建查询体
            search_body = {
                "query": query,
                "size": size,
                "from": from_
            }

            if sort:
                search_body["sort"] = sort

            if aggregations:
                search_body["aggs"] = aggregations

            loop = asyncio.get_event_loop()
            response = await self._run_sync(
                lambda: self.es_client.search(
                    index=index,
                    body=search_body
                )
            )

            return response

        except Exception as e:
            logger.error(f"搜索文档失败 [{index}]: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}, "aggregations": {}}

    async def count_documents(self, index: str, query: Dict[str, Any]) -> int:
        """统计文档数量

        Args:
            index: 索引名称
            query: 查询条件

        Returns:
            文档数量
        """
        if not self._ensure_connection():
            logger.warning("Elasticsearch连接不可用，返回0")
            return 0

        try:
            loop = asyncio.get_event_loop()
            response = await self._run_sync(
                lambda: self.es_client.count(
                    index=index,
                    body={"query": query}
                )
            )

            return response.get("count", 0)

        except Exception as e:
            logger.error(f"统计文档数量失败 [{index}]: {e}")
            return 0
    
    async def index_alert(self, alert_doc: Dict[str, Any]) -> bool:
        """把 v3 告警双写到 ES video_alerts 索引（best-effort）。

        约定：
        - doc id = alert_doc["id"]（AlertDB.id 的 UUID 字符串），与
          update_alert_fields 的 id 约定一致，保证 clip 字段更新能命中。
        - 存在即覆盖（幂等），refresh=False 避免拖慢主链路。
        - 任何失败只 warning 不抛，保护 PG 主告警链路。
        """
        if not alert_doc:
            return False
        doc_id = alert_doc.get("id")
        if not doc_id:
            logger.warning("index_alert 收到缺 id 的 alert_doc，跳过")
            return False
        if not self._ensure_connection():
            logger.warning("ES 连接不可用，v3 告警跳过双写")
            return False

        try:
            await self._run_sync(
                lambda: self.es_client.index(
                    index=ElasticsearchConfig.ALERTS_INDEX,
                    id=str(doc_id),
                    body=alert_doc,
                    refresh=False,
                )
            )
            return True
        except Exception as e:
            logger.warning(f"v3 告警写 ES 失败 alert_id={doc_id}: {e}")
            return False

    async def update_alert_fields(
        self, alert_id: str, fields: Dict[str, Any]
    ) -> bool:
        """按 doc id 局部更新 video_alerts 索引中的字段（best-effort）。

        用于 v3 告警链路把 clip_url/clip_status 同步到 ES。PG 是权威源，
        本方法任何失败（连接断、doc 不存在等）只返回 False，绝不抛异常。

        约定：ES doc id = AlertDB.id（UUID 字符串）。v3 告警若尚未写入 ES
        （当前阶段可能为真），update 会失败，静默 debug 日志即可。
        """
        if not fields:
            return False
        if not self._ensure_connection():
            return False

        try:
            await self._run_sync(
                lambda: self.es_client.update(
                    index=ElasticsearchConfig.ALERTS_INDEX,
                    id=alert_id,
                    body={"doc": fields},
                    refresh=False,
                )
            )
            return True
        except Exception as e:
            # doc_missing / index_not_found 等均归为非致命
            logger.debug(
                f"ES 告警字段更新未命中或失败 alert_id={alert_id}: {e}"
            )
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """获取Elasticsearch健康状态"""
        try:
            if not self.es_client:
                return {"status": "disconnected", "available": False}
            
            cluster_health = self.es_client.cluster.health()
            return {
                "status": cluster_health.get("status", "unknown"),
                "available": True,
                "cluster_name": cluster_health.get("cluster_name", ""),
                "number_of_nodes": cluster_health.get("number_of_nodes", 0),
                "indices": {
                    "analysis_results": self._get_index_stats(ElasticsearchConfig.ANALYSIS_RESULTS_INDEX),
                    "frame_results": self._get_index_stats(ElasticsearchConfig.FRAME_RESULTS_INDEX),
                    "alerts": self._get_index_stats(ElasticsearchConfig.ALERTS_INDEX)
                }
            }
            
        except Exception as e:
            logger.error(f"获取ES健康状态失败: {e}")
            return {"status": "error", "available": False, "error": str(e)}
    
    def _get_index_stats(self, index: str) -> Dict[str, Any]:
        """获取索引统计信息"""
        try:
            if self.es_client.indices.exists(index=index):
                stats = self.es_client.indices.stats(index=index)
                return {
                    "exists": True,
                    "doc_count": stats["indices"][index]["primaries"]["docs"]["count"],
                    "size": stats["indices"][index]["primaries"]["store"]["size_in_bytes"]
                }
            else:
                return {"exists": False}
        except Exception as e:
            logger.debug(f"获取索引状态失败: {e}")
            return {"exists": False, "error": True}

    async def get_alert_statistics(self) -> Dict[str, Any]:
        """
        从video_alerts索引获取告警统计数据

        Returns:
            包含今日告警数和总告警数的字典
        """
        if not self._ensure_connection():
            logger.warning("Elasticsearch连接不可用，返回默认统计数据")
            return {
                "total_alerts": 0,
                "today_alerts": 0
            }

        try:
            from datetime import datetime, timedelta
            from utils.timezone_utils import now

            # 获取今天开始时间（北京时间）
            beijing_now = now()
            today_start = beijing_now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_start_ms = int(today_start.timestamp() * 1000)

            # 1. 查询总告警数
            total_query = {"match_all": {}}
            total_count = await self.count_documents(
                index=ElasticsearchConfig.ALERTS_INDEX,
                query=total_query
            )

            # 2. 查询今日告警数
            today_query = {
                "range": {
                    "created_at": {
                        "gte": today_start_ms
                    }
                }
            }
            today_count = await self.count_documents(
                index=ElasticsearchConfig.ALERTS_INDEX,
                query=today_query
            )

            logger.info(f"告警统计: 总数={total_count}, 今日={today_count}")

            return {
                "total_alerts": total_count,
                "today_alerts": today_count
            }

        except Exception as e:
            logger.error(f"获取告警统计失败: {e}", exc_info=True)
            return {
                "total_alerts": 0,
                "today_alerts": 0
            }


# 创建全局实例
elasticsearch_service = ElasticsearchService()