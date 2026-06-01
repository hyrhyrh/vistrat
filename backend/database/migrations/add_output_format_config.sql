-- ===========================================
-- 添加输出格式配置字段迁移脚本
-- 为ai_model_configs表添加output_format_config字段
-- 版本: v2.4.0
-- ===========================================

BEGIN;

-- 检查字段是否已存在，避免重复添加
DO $$ 
BEGIN
    -- 添加输出格式配置字段
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'ai_model_configs' 
        AND column_name = 'output_format_config'
    ) THEN
        ALTER TABLE ai_model_configs 
        ADD COLUMN output_format_config JSONB;
        
        -- 添加字段注释
        COMMENT ON COLUMN ai_model_configs.output_format_config IS '输出格式配置JSON：定义AI模型返回结果的格式要求';
        
        RAISE NOTICE '✅ 成功添加 output_format_config 字段到 ai_model_configs 表';
    ELSE
        RAISE NOTICE '⚠️  output_format_config 字段已存在，跳过添加';
    END IF;
    
    -- 创建输出格式配置的索引（用于快速查找有自定义格式的配置）
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes 
        WHERE tablename = 'ai_model_configs' 
        AND indexname = 'idx_ai_model_configs_output_format'
    ) THEN
        CREATE INDEX idx_ai_model_configs_output_format 
        ON ai_model_configs 
        USING GIN (output_format_config) 
        WHERE output_format_config IS NOT NULL;
        
        RAISE NOTICE '✅ 成功创建 output_format_config 字段索引';
    ELSE
        RAISE NOTICE '⚠️  output_format_config 字段索引已存在，跳过创建';
    END IF;
    
END $$;

-- 插入示例配置数据（可选，演示用）
-- 为现有的模型配置添加默认的输出格式配置
DO $$
BEGIN
    -- 检查是否需要添加示例数据
    IF EXISTS (SELECT 1 FROM ai_model_configs WHERE output_format_config IS NULL LIMIT 1) THEN
        
        -- 为安全帽检测相关的模型添加默认格式配置
        UPDATE ai_model_configs 
        SET output_format_config = jsonb_build_object(
            'format_version', '1.0',
            'algorithm_type', 'safety_helmet',
            'format_template', '{
  "has_violation": "<boolean>",
  "person_count": "<integer>", 
  "violation_count": "<integer>",
  "conclusion": "<string>",
  "violations": [
    {
      "bbox": {
        "top_left_x": "<integer>",
        "top_left_y": "<integer>",
        "bottom_right_x": "<integer>",
        "bottom_right_y": "<integer>"
      },
      "confidence": "<float>"
    }
  ]
}',
            'custom_instructions', '请严格按照JSON格式返回安全帽检测结果，确保所有字段都存在且类型正确。',
            'is_custom', false,
            'created_at', CURRENT_TIMESTAMP::text
        )
        WHERE (
            LOWER(model_name) LIKE '%安全帽%' 
            OR LOWER(model_name) LIKE '%helmet%'
            OR LOWER(model_name) LIKE '%safety%'
        ) AND output_format_config IS NULL;
        
        RAISE NOTICE '✅ 为安全帽检测模型添加了默认输出格式配置';
        
        -- 为通用检测模型添加通用格式配置
        UPDATE ai_model_configs 
        SET output_format_config = jsonb_build_object(
            'format_version', '1.0',
            'algorithm_type', 'general',
            'format_template', '{
  "has_violation": "<boolean>",
  "person_count": "<integer>",
  "violation_count": "<integer>", 
  "conclusion": "<string>",
  "violations": [
    {
      "bbox": {
        "top_left_x": "<integer>",
        "top_left_y": "<integer>",
        "bottom_right_x": "<integer>",
        "bottom_right_y": "<integer>"
      },
      "confidence": "<float>"
    }
  ]
}',
            'custom_instructions', '请严格按照JSON格式返回检测结果。',
            'is_custom', false,
            'created_at', CURRENT_TIMESTAMP::text
        )
        WHERE output_format_config IS NULL;
        
        RAISE NOTICE '✅ 为其他模型添加了通用输出格式配置';
    ELSE
        RAISE NOTICE '⚠️  所有模型配置都已有输出格式配置，跳过添加示例数据';
    END IF;
END $$;

COMMIT;

-- 验证迁移结果
DO $$
DECLARE
    config_count INTEGER;
    format_count INTEGER;
BEGIN
    -- 统计总配置数
    SELECT COUNT(*) INTO config_count FROM ai_model_configs;
    
    -- 统计有输出格式配置的数量
    SELECT COUNT(*) INTO format_count FROM ai_model_configs WHERE output_format_config IS NOT NULL;
    
    RAISE NOTICE '===========================================';
    RAISE NOTICE '📊 迁移结果统计:';
    RAISE NOTICE '   总模型配置数: %', config_count;
    RAISE NOTICE '   已配置输出格式数: %', format_count;
    RAISE NOTICE '   配置覆盖率: %%%', ROUND((format_count::DECIMAL / NULLIF(config_count, 0)) * 100, 2);
    RAISE NOTICE '===========================================';
END $$;