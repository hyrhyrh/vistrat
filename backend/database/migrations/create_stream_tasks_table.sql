
-- ===========================================
-- 视频流实时分析任务表创建脚本
-- 手动执行版本
-- ===========================================

-- 创建实时分析任务表
CREATE TABLE IF NOT EXISTS stream_analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL,
    algorithm_config_id UUID NOT NULL,
    task_name VARCHAR(255) NOT NULL,
    
    -- 任务状态管理
    status VARCHAR(20) NOT NULL DEFAULT 'enabled',
    is_active BOOLEAN NOT NULL DEFAULT true,
    auto_recover BOOLEAN NOT NULL DEFAULT true,
    
    -- 时间配置（支持多时间段、跨天、星期选择）
    time_config JSONB NOT NULL DEFAULT '{}',
    
    -- ROI配置（支持矩形和多边形区域）
    roi_config JSONB DEFAULT '{}',
    
    -- 任务配置参数
    priority INTEGER NOT NULL DEFAULT 1,
    confidence_threshold FLOAT NOT NULL DEFAULT 0.7,
    analysis_interval INTEGER NOT NULL DEFAULT 10,
    
    -- 运行状态跟踪
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    run_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    last_error_message TEXT,
    
    -- 性能统计
    total_frames_processed INTEGER NOT NULL DEFAULT 0,
    total_alerts_generated INTEGER NOT NULL DEFAULT 0,
    avg_processing_time FLOAT DEFAULT 0,
    
    -- 审计字段
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    updated_by UUID,
    
    -- 约束
    CONSTRAINT chk_status CHECK (status IN ('enabled', 'disabled', 'running', 'error', 'scheduled')),
    CONSTRAINT chk_priority CHECK (priority >= 1 AND priority <= 10),
    CONSTRAINT chk_confidence_threshold CHECK (confidence_threshold >= 0 AND confidence_threshold <= 1)
);

-- 创建索引优化查询性能
CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_stream_id ON stream_analysis_tasks(stream_id);
CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_status ON stream_analysis_tasks(status);
CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_active ON stream_analysis_tasks(is_active);
CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_auto_recover ON stream_analysis_tasks(auto_recover);
CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_next_run ON stream_analysis_tasks(next_run_at) WHERE status = 'enabled';

-- 创建GIN索引支持JSON查询（如果PostgreSQL版本支持）
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'btree_gin') THEN
        CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_time_config ON stream_analysis_tasks USING GIN(time_config);
        CREATE INDEX IF NOT EXISTS idx_stream_analysis_tasks_roi_config ON stream_analysis_tasks USING GIN(roi_config);
    END IF;
EXCEPTION WHEN OTHERS THEN
    -- 忽略索引创建失败
    NULL;
END $$;

-- 创建更新时间自动触发器
CREATE OR REPLACE FUNCTION update_stream_analysis_tasks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE 'plpgsql';

-- 创建触发器
DROP TRIGGER IF EXISTS trigger_update_stream_analysis_tasks_updated_at ON stream_analysis_tasks;
CREATE TRIGGER trigger_update_stream_analysis_tasks_updated_at
    BEFORE UPDATE ON stream_analysis_tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_stream_analysis_tasks_updated_at();

-- 添加表注释
COMMENT ON TABLE stream_analysis_tasks IS '视频流实时分析任务表 - 支持任务级别管理、时间调度、ROI配置';
COMMENT ON COLUMN stream_analysis_tasks.time_config IS '时间配置JSON：支持多时间段、跨天时间、星期选择';
COMMENT ON COLUMN stream_analysis_tasks.roi_config IS 'ROI区域配置JSON：支持矩形和多边形感兴趣区域';

-- 插入示例数据（可选）
DO $$
BEGIN
    -- 只有当表为空时才插入示例数据
    IF NOT EXISTS (SELECT 1 FROM stream_analysis_tasks LIMIT 1) THEN
        INSERT INTO stream_analysis_tasks (
            stream_id,
            algorithm_config_id, 
            task_name,
            time_config,
            roi_config,
            priority,
            confidence_threshold,
            analysis_interval
        ) VALUES (
            gen_random_uuid(),
            gen_random_uuid(),
            '示例分析任务 - 工作日安全帽检测',
            '{"enabled": true, "time_ranges": [{"start_time": "07:00", "end_time": "18:00", "days": [1,2,3,4,5]}], "timezone": "Asia/Shanghai"}',
            '{"enabled": false, "regions": []}',
            1,
            0.7,
            10
        );
        
        RAISE NOTICE '✅ 插入示例数据成功';
    END IF;
END $$;

-- 验证表创建
DO $$
DECLARE
    table_exists BOOLEAN;
    record_count INTEGER;
    column_count INTEGER;
BEGIN
    -- 检查表是否存在
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_name = 'stream_analysis_tasks'
    ) INTO table_exists;
    
    IF table_exists THEN
        -- 统计记录数
        SELECT COUNT(*) INTO record_count FROM stream_analysis_tasks;
        
        -- 统计字段数
        SELECT COUNT(*) INTO column_count 
        FROM information_schema.columns 
        WHERE table_name = 'stream_analysis_tasks';
        
        RAISE NOTICE '=========================================';
        RAISE NOTICE '✅ 表创建验证成功:';
        RAISE NOTICE '   表名: stream_analysis_tasks';
        RAISE NOTICE '   字段数: %', column_count;
        RAISE NOTICE '   记录数: %', record_count;
        RAISE NOTICE '   状态: 可用';
        RAISE NOTICE '=========================================';
    ELSE
        RAISE EXCEPTION '❌ 表创建失败: stream_analysis_tasks 不存在';
    END IF;
END $$;
