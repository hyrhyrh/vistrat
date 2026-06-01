-- 系统配置表迁移脚本
-- 从MySQL dc_system_param 转换为 PostgreSQL system_configs

-- 创建系统配置表
CREATE TABLE IF NOT EXISTS system_configs (
    param_code VARCHAR(50) NOT NULL,
    param_desc VARCHAR(250) NOT NULL,
    param_val VARCHAR(1000) NOT NULL,
    ext_val VARCHAR(1000) DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_system_configs PRIMARY KEY (param_code)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_system_configs_param_desc 
ON system_configs(param_desc);

-- 创建更新时间触发器
CREATE TRIGGER update_system_configs_updated_at
    BEFORE UPDATE ON system_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 添加表注释
COMMENT ON TABLE system_configs IS '系统配置参数表';

-- 添加字段注释
COMMENT ON COLUMN system_configs.param_code IS '配置参数编码(主键)';
COMMENT ON COLUMN system_configs.param_desc IS '配置参数描述';
COMMENT ON COLUMN system_configs.param_val IS '配置参数值';
COMMENT ON COLUMN system_configs.ext_val IS '扩展配置值';
COMMENT ON COLUMN system_configs.created_at IS '创建时间';
COMMENT ON COLUMN system_configs.updated_at IS '更新时间';

-- 插入一些默认系统配置
INSERT INTO system_configs (param_code, param_desc, param_val, ext_val) VALUES
('video_max_size', '视频文件最大大小(MB)', '500', NULL),
('ai_request_timeout', 'AI请求超时时间(秒)', '30', NULL),
('stream_analysis_interval', '流分析间隔时间(秒)', '10', NULL),
('max_concurrent_analysis', '最大并发分析任务数', '5', NULL),
('alert_retention_days', '告警记录保留天数', '30', NULL)
ON CONFLICT (param_code) DO NOTHING;

-- 记录迁移版本
INSERT INTO schema_migrations (version, description)
VALUES ('20250922_004', '创建系统配置表system_configs')
ON CONFLICT (version) DO NOTHING;