-- ===========================================
-- 视频流实时分析任务表迁移脚本
-- 支持任务级别管理、时间配置、ROI配置
-- 版本: v2.5.0
-- ===========================================

BEGIN;

-- 创建实时分析任务表
CREATE TABLE IF NOT EXISTS stream_analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL,
    algorithm_config_id UUID NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    
    -- 任务状态管理
    status VARCHAR(20) NOT NULL DEFAULT 'enabled', -- enabled, disabled, running, error
    is_active BOOLEAN NOT NULL DEFAULT true, -- 用户控制的启用/停用
    auto_recover BOOLEAN NOT NULL DEFAULT true, -- 系统重启后是否自动恢复
    
    -- 时间配置 - 支持多时间段
    time_config JSONB NOT NULL DEFAULT '{}', -- 存储时间配置
    /*
    时间配置结构：
    {
        "enabled": true,
        "time_ranges": [
            {
                "start_time": "07:00",
                "end_time": "18:00", 
                "days": [1,2,3,4,5] // 周一到周五
            }
        ],
        "timezone": "Asia/Shanghai"
    }
    */
    
    -- ROI配置 - 支持多种形状
    roi_config JSONB DEFAULT '{}', -- 存储ROI配置
    /*
    ROI配置结构：
    {
        "enabled": true,
        "regions": [
            {
                "id": "region_1",
                "type": "rectangle|polygon", 
                "name": "监控区域1",
                "data": {...}, // 具体坐标数据
                "active": true
            }
        ],
        "image_info": {
            "width": 1920,
            "height": 1080,
            "snapshot_url": "..."
        }
    }
    */
    
    -- 任务配置
    priority INTEGER NOT NULL DEFAULT 1,
    confidence_threshold FLOAT NOT NULL DEFAULT 0.7,
    analysis_interval INTEGER NOT NULL DEFAULT 10, -- 分析间隔(秒)
    
    -- 运行状态跟踪
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    run_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error_message TEXT,
    
    -- 统计信息
    total_frames_processed INTEGER NOT NULL DEFAULT 0,
    total_alerts_generated INTEGER NOT NULL DEFAULT 0,
    avg_processing_time FLOAT DEFAULT 0, -- 平均处理时间(秒)
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID
);

-- 创建索引优化查询性能
CREATE INDEX idx_stream_analysis_tasks_stream_id ON stream_analysis_tasks(stream_id);
CREATE INDEX idx_stream_analysis_tasks_status ON stream_analysis_tasks(status);
CREATE INDEX idx_stream_analysis_tasks_active ON stream_analysis_tasks(is_active);
CREATE INDEX idx_stream_analysis_tasks_auto_recover ON stream_analysis_tasks(auto_recover);
CREATE INDEX idx_stream_analysis_tasks_next_run ON stream_analysis_tasks(next_run_at) WHERE status = 'enabled';

-- 创建GIN索引支持JSON查询
CREATE INDEX idx_stream_analysis_tasks_time_config ON stream_analysis_tasks USING GIN(time_config);
CREATE INDEX idx_stream_analysis_tasks_roi_config ON stream_analysis_tasks USING GIN(roi_config);

-- 添加外键约束
ALTER TABLE stream_analysis_tasks 
ADD CONSTRAINT fk_stream_analysis_tasks_stream_id 
FOREIGN KEY (stream_id) REFERENCES video_streams(id) ON DELETE CASCADE;

ALTER TABLE stream_analysis_tasks 
ADD CONSTRAINT fk_stream_analysis_tasks_algorithm_config_id 
FOREIGN KEY (algorithm_config_id) REFERENCES ai_model_configs(id) ON DELETE CASCADE;

-- 添加检查约束
ALTER TABLE stream_analysis_tasks 
ADD CONSTRAINT chk_status 
CHECK (status IN ('enabled', 'disabled', 'running', 'error', 'scheduled'));

ALTER TABLE stream_analysis_tasks 
ADD CONSTRAINT chk_priority 
CHECK (priority >= 1 AND priority <= 10);

ALTER TABLE stream_analysis_tasks 
ADD CONSTRAINT chk_confidence_threshold 
CHECK (confidence_threshold >= 0 AND confidence_threshold <= 1);

-- 创建更新时间自动触发器
CREATE OR REPLACE FUNCTION update_stream_analysis_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_update_stream_analysis_tasks_updated_at
    BEFORE UPDATE ON stream_analysis_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_stream_analysis_tasks_updated_at();

-- 插入示例数据（可选）
DO $$
BEGIN
    -- 检查是否有video_streams数据
    IF EXISTS (SELECT 1 FROM video_streams LIMIT 1) THEN
        -- 为每个视频流创建示例分析任务
        INSERT INTO stream_analysis_tasks (
            stream_id, algorithm_config_id, task_name, 
            time_config, roi_config, priority, confidence_threshold
        ) 
        SELECT 
            vs.id as stream_id,
            (SELECT id FROM ai_model_configs WHERE status = 'active' LIMIT 1) as algorithm_config_id,
            vs.name || '_默认分析任务' as task_name,
            jsonb_build_object(
                'enabled', true,
                'time_ranges', jsonb_build_array(
                    jsonb_build_object(
                        'start_time', '07:00',
                        'end_time', '18:00',
                        'days', jsonb_build_array(1,2,3,4,5,6,0)
                    )
                ),
                'timezone', 'Asia/Shanghai'
            ) as time_config,
            jsonb_build_object(
                'enabled', false,
                'regions', jsonb_build_array()
            ) as roi_config,
            1 as priority,
            0.7 as confidence_threshold
        FROM video_streams vs
        WHERE NOT EXISTS (
            SELECT 1 FROM stream_analysis_tasks sat 
            WHERE sat.stream_id = vs.id
        );
        
        RAISE NOTICE '✅ 成功为现有视频流创建示例分析任务';
    END IF;
END $$;

COMMIT;

-- 验证迁移结果
DO $$
DECLARE
    task_count INTEGER;
    stream_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO task_count FROM stream_analysis_tasks;
    SELECT COUNT(*) INTO stream_count FROM video_streams;
    
    RAISE NOTICE '=========================================';
    RAISE NOTICE '📊 实时分析任务表创建完成:';
    RAISE NOTICE '   视频流数量: %', stream_count;
    RAISE NOTICE '   分析任务数量: %', task_count;
    RAISE NOTICE '   数据表结构: stream_analysis_tasks';
    RAISE NOTICE '   支持功能: 时间配置、ROI配置、任务管理';
    RAISE NOTICE '=========================================';
END $$;