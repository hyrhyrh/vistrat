-- 数据库表结构修复脚本
-- 修复 ai_provider_configs 和 video_analysis_templates 表结构

-- 修复 ai_provider_configs 表
DO $$
BEGIN
    -- 添加缺失的字段
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'display_name') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN display_name VARCHAR(200) DEFAULT '';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'icon') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN icon VARCHAR(50) DEFAULT '🤖';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'description') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN description TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'api_base_url') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN api_base_url VARCHAR(500);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'api_version') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN api_version VARCHAR(50) DEFAULT 'v1';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'available_models') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN available_models JSONB DEFAULT '[]';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'default_model') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN default_model VARCHAR(200);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'max_tokens_limit') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN max_tokens_limit JSONB DEFAULT '{}';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'request_headers') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN request_headers JSONB DEFAULT '{}';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'request_timeout') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN request_timeout INTEGER DEFAULT 60;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'sort_order') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN sort_order INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_provider_configs' AND column_name = 'extra_config') THEN
        ALTER TABLE ai_provider_configs ADD COLUMN extra_config JSONB DEFAULT '{}';
    END IF;

    -- 修复 ai_model_configs 表
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_model_configs' AND column_name = 'name') THEN
        ALTER TABLE ai_model_configs ADD COLUMN name VARCHAR(255) DEFAULT '';
        UPDATE ai_model_configs SET name = COALESCE(model_name, 'Unnamed Model') WHERE name = '';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'ai_model_configs' AND column_name = 'prompt_template') THEN
        ALTER TABLE ai_model_configs ADD COLUMN prompt_template TEXT DEFAULT '';
        UPDATE ai_model_configs SET prompt_template = COALESCE(user_prompt, system_prompt, '请分析这张图片的内容。') WHERE prompt_template = '';
    END IF;

    -- 修复 video_analysis_templates 表
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'video_id') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN video_id UUID;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'template_id') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN template_id UUID;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'template_name') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN template_name VARCHAR(255);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'priority') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN priority INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'enabled') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN enabled BOOLEAN DEFAULT true;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'analysis_status') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN analysis_status VARCHAR(50) DEFAULT 'not_started';
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'progress') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN progress INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'alerts_count') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN alerts_count INTEGER DEFAULT 0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'confidence_avg') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN confidence_avg REAL DEFAULT 0.0;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'analysis_duration') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN analysis_duration INTEGER;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'error_message') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN error_message TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'started_at') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN started_at TIMESTAMPTZ;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'video_analysis_templates' AND column_name = 'completed_at') THEN
        ALTER TABLE video_analysis_templates ADD COLUMN completed_at TIMESTAMPTZ;
    END IF;
    
    RAISE NOTICE '数据库表结构修复完成';
END $$;