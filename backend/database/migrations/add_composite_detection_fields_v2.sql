-- =====================================================================
-- 复合检测功能数据库迁移脚本
-- 版本: v2.0 (修复版)
-- 创建时间: 2025-10-29
-- 描述: 为视频流分析添加复合检测支持
--       - ai_model_configs添加detection_capabilities字段（已存在，跳过）
--       - video_stream_algorithm_configs添加detection_type_codes字段
-- =====================================================================

-- 开始事务
BEGIN;

-- =====================================================================
-- Step 1: 为ai_model_configs表添加detection_capabilities字段
-- =====================================================================

-- 添加字段（如果不存在）
ALTER TABLE public.ai_model_configs
ADD COLUMN IF NOT EXISTS detection_capabilities jsonb DEFAULT '[]'::jsonb;

-- 添加字段注释
COMMENT ON COLUMN public.ai_model_configs.detection_capabilities IS
'支持的检测能力列表，JSONB数组格式，存储该算法能够检测的违规类型编码。
示例: ["safety_helmet", "smoking", "using_phone", "climbing", "intrusion"]
用途: 定义算法的能力边界，在视频流配置时供用户选择';

-- 创建GIN索引以优化JSONB查询性能
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_detection_capabilities
ON public.ai_model_configs USING gin(detection_capabilities);

COMMENT ON INDEX idx_ai_model_configs_detection_capabilities IS
'GIN索引用于优化detection_capabilities字段的查询性能，支持包含(@>)和相等(=)操作';

-- =====================================================================
-- Step 2: 为video_stream_algorithm_configs表添加detection_type_codes字段
-- =====================================================================

-- 添加字段（如果不存在）
ALTER TABLE public.video_stream_algorithm_configs
ADD COLUMN IF NOT EXISTS detection_type_codes jsonb DEFAULT '[]'::jsonb;

-- 添加字段注释
COMMENT ON COLUMN public.video_stream_algorithm_configs.detection_type_codes IS
'用户选择要启用的检测类型编码列表，JSONB数组格式，从算法的detection_capabilities中选择。
示例: ["smoking", "using_phone"]
用途: 定义用户在该视频流上实际要使用的检测类型，支持从算法能力中灵活选择';

-- 创建GIN索引以优化JSONB查询性能
CREATE INDEX IF NOT EXISTS idx_video_stream_algorithm_configs_detection_type_codes
ON public.video_stream_algorithm_configs USING gin(detection_type_codes);

COMMENT ON INDEX idx_video_stream_algorithm_configs_detection_type_codes IS
'GIN索引用于优化detection_type_codes字段的查询性能，支持包含(@>)和相等(=)操作';

-- =====================================================================
-- Step 3: 验证迁移结果
-- =====================================================================

-- 验证ai_model_configs字段
DO $$
DECLARE
    field_exists boolean;
    index_exists boolean;
BEGIN
    -- 检查detection_capabilities字段是否存在
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'ai_model_configs'
          AND column_name = 'detection_capabilities'
    ) INTO field_exists;

    IF NOT field_exists THEN
        RAISE EXCEPTION '❌ 迁移失败: ai_model_configs.detection_capabilities字段未创建';
    END IF;

    -- 检查索引是否存在
    SELECT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'ai_model_configs'
          AND indexname = 'idx_ai_model_configs_detection_capabilities'
    ) INTO index_exists;

    IF NOT index_exists THEN
        RAISE EXCEPTION '❌ 迁移失败: idx_ai_model_configs_detection_capabilities索引未创建';
    END IF;

    RAISE NOTICE '✅ ai_model_configs表迁移成功';
END $$;

-- 验证video_stream_algorithm_configs字段
DO $$
DECLARE
    field_exists boolean;
    index_exists boolean;
BEGIN
    -- 检查detection_type_codes字段是否存在
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'video_stream_algorithm_configs'
          AND column_name = 'detection_type_codes'
    ) INTO field_exists;

    IF NOT field_exists THEN
        RAISE EXCEPTION '❌ 迁移失败: video_stream_algorithm_configs.detection_type_codes字段未创建';
    END IF;

    -- 检查索引是否存在
    SELECT EXISTS (
        SELECT 1
        FROM pg_indexes
        WHERE schemaname = 'public'
          AND tablename = 'video_stream_algorithm_configs'
          AND indexname = 'idx_video_stream_algorithm_configs_detection_type_codes'
    ) INTO index_exists;

    IF NOT index_exists THEN
        RAISE EXCEPTION '❌ 迁移失败: idx_video_stream_algorithm_configs_detection_type_codes索引未创建';
    END IF;

    RAISE NOTICE '✅ video_stream_algorithm_configs表迁移成功';
END $$;

-- 提交事务
COMMIT;

-- =====================================================================
-- 迁移完成，输出统计信息
-- =====================================================================

SELECT
    '✅ 数据库迁移完成' AS status,
    (SELECT COUNT(*) FROM public.ai_model_configs) AS total_ai_configs,
    (SELECT COUNT(*) FROM public.video_stream_algorithm_configs) AS total_stream_configs;

-- 输出字段信息
SELECT
    '📊 ai_model_configs.detection_capabilities字段信息:' AS info,
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'ai_model_configs'
  AND column_name = 'detection_capabilities';

SELECT
    '📊 video_stream_algorithm_configs.detection_type_codes字段信息:' AS info,
    column_name,
    data_type,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'video_stream_algorithm_configs'
  AND column_name = 'detection_type_codes';
