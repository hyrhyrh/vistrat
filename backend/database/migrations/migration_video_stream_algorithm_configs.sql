-- =======================================
-- 视频流算法配置数据库迁移
-- 解决算法配置持久化问题
-- =======================================

-- 创建视频流算法配置表
CREATE TABLE IF NOT EXISTS video_stream_algorithm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL,
    template_id VARCHAR(255) NOT NULL,
    template_name VARCHAR(255),
    priority INTEGER DEFAULT 1,
    confidence_threshold REAL DEFAULT 0.7,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    
    -- 外键约束
    CONSTRAINT fk_stream_algorithm_configs_stream_id 
        FOREIGN KEY (stream_id) REFERENCES video_streams(id) ON DELETE CASCADE,
    
    -- 唯一约束：一个流的同一个算法模板只能配置一次
    CONSTRAINT uk_stream_algorithm_config 
        UNIQUE (stream_id, template_id)
);

-- 创建索引提升查询性能
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_configs_stream_id 
    ON video_stream_algorithm_configs(stream_id);
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_configs_template_id 
    ON video_stream_algorithm_configs(template_id);
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_configs_is_active 
    ON video_stream_algorithm_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_configs_created_at 
    ON video_stream_algorithm_configs(created_at);

-- 为配置表添加更新时间触发器
CREATE TRIGGER update_video_stream_algorithm_configs_updated_at 
    BEFORE UPDATE ON video_stream_algorithm_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 创建视频流算法配置历史表（用于审计）
CREATE TABLE IF NOT EXISTS video_stream_algorithm_config_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID NOT NULL,
    stream_id UUID NOT NULL,
    template_id VARCHAR(255) NOT NULL,
    template_name VARCHAR(255),
    priority INTEGER,
    confidence_threshold REAL,
    is_active BOOLEAN,
    operation VARCHAR(20) NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
    operation_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    operated_by VARCHAR(255),
    old_values JSONB,
    new_values JSONB
);

-- 历史表索引
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_config_history_config_id 
    ON video_stream_algorithm_config_history(config_id);
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_config_history_stream_id 
    ON video_stream_algorithm_config_history(stream_id);
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_config_history_operation_at 
    ON video_stream_algorithm_config_history(operation_at);

-- 创建审计触发器函数
CREATE OR REPLACE FUNCTION audit_video_stream_algorithm_config()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO video_stream_algorithm_config_history (
            config_id, stream_id, template_id, template_name, 
            priority, confidence_threshold, is_active, 
            operation, new_values
        ) VALUES (
            NEW.id, NEW.stream_id, NEW.template_id, NEW.template_name,
            NEW.priority, NEW.confidence_threshold, NEW.is_active,
            'INSERT', to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO video_stream_algorithm_config_history (
            config_id, stream_id, template_id, template_name,
            priority, confidence_threshold, is_active,
            operation, old_values, new_values
        ) VALUES (
            NEW.id, NEW.stream_id, NEW.template_id, NEW.template_name,
            NEW.priority, NEW.confidence_threshold, NEW.is_active,
            'UPDATE', to_jsonb(OLD), to_jsonb(NEW)
        );
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO video_stream_algorithm_config_history (
            config_id, stream_id, template_id, template_name,
            priority, confidence_threshold, is_active,
            operation, old_values
        ) VALUES (
            OLD.id, OLD.stream_id, OLD.template_id, OLD.template_name,
            OLD.priority, OLD.confidence_threshold, OLD.is_active,
            'DELETE', to_jsonb(OLD)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

-- 为配置表添加审计触发器
DROP TRIGGER IF EXISTS audit_video_stream_algorithm_config_trigger ON video_stream_algorithm_configs;
CREATE TRIGGER audit_video_stream_algorithm_config_trigger
    AFTER INSERT OR UPDATE OR DELETE ON video_stream_algorithm_configs
    FOR EACH ROW EXECUTE FUNCTION audit_video_stream_algorithm_config();

-- 插入迁移版本标记
INSERT INTO schema_migrations (version, description) 
VALUES ('v2.2.1', '添加视频流算法配置持久化表结构') 
ON CONFLICT (version) DO NOTHING;

-- 注释说明
COMMENT ON TABLE video_stream_algorithm_configs IS '视频流算法配置表 - 存储每个视频流配置的AI分析算法';
COMMENT ON TABLE video_stream_algorithm_config_history IS '视频流算法配置历史表 - 审计所有配置变更记录';
COMMENT ON COLUMN video_stream_algorithm_configs.stream_id IS '视频流ID，关联video_streams表';
COMMENT ON COLUMN video_stream_algorithm_configs.template_id IS 'AI算法模板ID';
COMMENT ON COLUMN video_stream_algorithm_configs.template_name IS 'AI算法模板名称（冗余字段，便于查询）';
COMMENT ON COLUMN video_stream_algorithm_configs.priority IS '算法执行优先级，数字越大优先级越高';
COMMENT ON COLUMN video_stream_algorithm_configs.confidence_threshold IS '置信度阈值，0.0-1.0之间';
COMMENT ON COLUMN video_stream_algorithm_configs.is_active IS '是否启用该算法配置';