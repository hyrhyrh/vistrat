-- =====================================================================
-- 复合检测功能数据库迁移脚本
-- 版本: v1.0
-- 创建时间: 2025-10-29
-- 描述: 为视频流分析添加复合检测支持
--       - ai_model_configs添加detection_capabilities字段
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
-- Step 3: 数据迁移（向后兼容）
-- =====================================================================

-- 为现有的ai_model_configs记录填充默认的detection_capabilities
-- 从video_analysis_templates表中收集该算法已配置的检测类型
UPDATE public.ai_model_configs amc
SET detection_capabilities = (
    SELECT COALESCE(jsonb_agg(DISTINCT vat.detection_type_code), '[]'::jsonb)
    FROM public.video_analysis_templates vat
    WHERE vat.id = amc.id::text
      AND vat.detection_type_code IS NOT NULL
)
WHERE amc.detection_capabilities = '[]'::jsonb
   OR amc.detection_capabilities IS NULL;

-- 为现有的video_stream_algorithm_configs记录填充默认的detection_type_codes
-- 如果算法有detection_capabilities，则默认选择所有能力
UPDATE public.video_stream_algorithm_configs vsac
SET detection_type_codes = (
    SELECT amc.detection_capabilities
    FROM public.ai_model_configs amc
    WHERE amc.id::text = vsac.template_id
)
WHERE vsac.detection_type_codes = '[]'::jsonb
   OR vsac.detection_type_codes IS NULL;

-- =====================================================================
-- Step 4: 验证迁移结果
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
        RAISE EXCEPTION '迁移失败: ai_model_configs.detection_capabilities字段未创建';
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
        RAISE EXCEPTION '迁移失败: idx_ai_model_configs_detection_capabilities索引未创建';
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
        RAISE EXCEPTION '迁移失败: video_stream_algorithm_configs.detection_type_codes字段未创建';
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
        RAISE EXCEPTION '迁移失败: idx_video_stream_algorithm_configs_detection_type_codes索引未创建';
    END IF;

    RAISE NOTICE '✅ video_stream_algorithm_configs表迁移成功';
END $$;

-- 提交事务
COMMIT;

-- =====================================================================
-- 迁移完成
-- =====================================================================

-- 输出统计信息
SELECT
    '✅ 数据库迁移完成' AS status,
    (SELECT COUNT(*) FROM public.ai_model_configs WHERE detection_capabilities != '[]'::jsonb) AS ai_configs_with_capabilities,
    (SELECT COUNT(*) FROM public.video_stream_algorithm_configs WHERE detection_type_codes != '[]'::jsonb) AS stream_configs_with_types;

-- 输出表结构验证
\d+ public.ai_model_configs
\d+ public.video_stream_algorithm_configs
