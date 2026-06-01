"""
服务辅助模块 (helpers)

从超长的 service 文件中提取的辅助功能模块，遵循单一职责原则。
每个 helper 文件包含从对应 service 中提取的独立功能组。

模块列表:
- frame_selection_helper: 帧选择和质量评估逻辑 (来源: stream_frame_analyzer.py)
- stream_connection_helper: AI响应违规提取逻辑 (来源: stream_frame_analyzer.py)
- task_recovery_helper: 任务恢复和自动重启逻辑 (来源: stream_task_manager.py)
- task_statistics_helper: 任务统计和报告方法 (来源: stream_task_manager.py)
- buffer_manager: 缓冲区管理和数据刷新逻辑 (来源: stream_analysis_service.py)
- video_frame_extractor: 视频帧提取和抽样逻辑 (来源: video_analysis_service.py)
- es_query_builder: ES查询构建和索引映射逻辑 (来源: elasticsearch_service.py)
- mjpeg_frame_processor: 帧处理、质量检测、编码逻辑 (来源: api/mjpeg_stream.py)
"""
