-- 修复置信度字段长度问题
-- 将confidence_score字段从VARCHAR(10)扩展到VARCHAR(50)以支持完整的浮点数值

-- 修改ai_analysis_logs表的confidence_score字段长度
ALTER TABLE ai_analysis_logs ALTER COLUMN confidence_score TYPE VARCHAR(50);

-- 添加注释说明修复
COMMENT ON COLUMN ai_analysis_logs.confidence_score IS '置信度分数：结果可信度(修复字段长度)';

-- 记录修复日志
INSERT INTO schema_versions (version, description, applied_at)
VALUES ('fix_confidence_field_20250925', '修复ai_analysis_logs.confidence_score字段长度问题', CURRENT_TIMESTAMP)
ON CONFLICT (version) DO NOTHING;