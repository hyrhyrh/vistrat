-- 数据库迁移脚本：v2.1.0 -> v2.2.0
-- 添加AI分析调用日志表

-- AI分析调用日志表
CREATE TABLE IF NOT EXISTS ai_analysis_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID,
    video_id UUID,
    algorithm_id VARCHAR(255),
    algorithm_config_id UUID,
    call_status VARCHAR(20) DEFAULT 'success',
    api_endpoint VARCHAR(500),
    model_name VARCHAR(100),
    frame_index INTEGER,
    frame_timestamp VARCHAR(20),
    request_data JSONB,
    response_data JSONB,
    response_time_ms INTEGER,
    confidence_score VARCHAR(10),
    error_message TEXT,
    error_code VARCHAR(50),
    call_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- AI分析日志表索引
CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_task_id ON ai_analysis_logs(task_id);
CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_video_id ON ai_analysis_logs(video_id);
CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_call_status ON ai_analysis_logs(call_status);
CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_call_date ON ai_analysis_logs(call_date);
CREATE INDEX IF NOT EXISTS idx_ai_analysis_logs_algorithm_id ON ai_analysis_logs(algorithm_id);

-- AI分析日志表触发器
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger 
        WHERE tgname = 'update_ai_analysis_logs_updated_at'
    ) THEN
        CREATE TRIGGER update_ai_analysis_logs_updated_at 
            BEFORE UPDATE ON ai_analysis_logs 
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- 更新版本标记
INSERT INTO schema_migrations (version, description) 
VALUES ('v2.2.0', 'AI视频监控系统 - 添加AI分析调用日志表') 
ON CONFLICT (version) DO NOTHING;