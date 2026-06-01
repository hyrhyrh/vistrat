-- AI视频监控系统数据库导出
-- 生成时间: 14346.710203492
-- 数据库: vistrat

-- ===========================================
-- 枚举类型定义
-- ===========================================

-- 创建枚举类型 ai_model_type_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ai_model_type_enum') THEN
        CREATE TYPE ai_model_type_enum AS ENUM ('vision', 'text', 'multimodal');
    END IF;
END $$;

-- 创建枚举类型 ai_provider_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'ai_provider_enum') THEN
        CREATE TYPE ai_provider_enum AS ENUM ('qwen', 'moonshot', 'gpt', 'claude', 'gemini', 'baidu');
    END IF;
END $$;

-- 创建枚举类型 algorithm_status_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'algorithm_status_enum') THEN
        CREATE TYPE algorithm_status_enum AS ENUM ('draft', 'testing', 'active', 'deprecated');
    END IF;
END $$;

-- 创建枚举类型 analysis_status_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'analysis_status_enum') THEN
        CREATE TYPE analysis_status_enum AS ENUM ('not_started', 'queued', 'processing', 'completed', 'failed', 'cancelled');
    END IF;
END $$;

-- 创建枚举类型 stream_analysis_status_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stream_analysis_status_enum') THEN
        CREATE TYPE stream_analysis_status_enum AS ENUM ('NOT_STARTED', 'RUNNING', 'PAUSED', 'STOPPED', 'ERROR');
    END IF;
END $$;

-- 创建枚举类型 stream_status_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stream_status_enum') THEN
        CREATE TYPE stream_status_enum AS ENUM ('OFFLINE', 'ONLINE', 'CONNECTING', 'ERROR', 'MAINTENANCE');
    END IF;
END $$;

-- 创建枚举类型 stream_type_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'stream_type_enum') THEN
        CREATE TYPE stream_type_enum AS ENUM ('RTSP', 'RTMP', 'HLS', 'WEBRTC', 'HTTP_FLV', 'LOCAL_CAMERA');
    END IF;
END $$;

-- 创建枚举类型 user_role_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'user_role_enum') THEN
        CREATE TYPE user_role_enum AS ENUM ('admin', 'user', 'viewer');
    END IF;
END $$;

-- 创建枚举类型 video_status_enum
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'video_status_enum') THEN
        CREATE TYPE video_status_enum AS ENUM ('PENDING', 'UPLOADING', 'READY', 'ANALYZING', 'COMPLETED', 'ERROR', 'DELETED');
    END IF;
END $$;

-- ===========================================
-- 表结构定义
-- ===========================================

-- ai_model_configs表
CREATE TABLE IF NOT EXISTS ai_model_configs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    provider ai_provider_enum NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    model_type ai_model_type_enum DEFAULT 'vision',
    system_prompt TEXT,
    user_prompt TEXT,
    temperature REAL DEFAULT 0.7,
    top_p REAL DEFAULT 0.9,
    max_tokens INTEGER DEFAULT 1000,
    confidence_threshold REAL DEFAULT 0.7,
    tags TEXT[] DEFAULT '{}',
    status algorithm_status_enum DEFAULT 'draft',
    test_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    extra_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ai_provider_configs表
CREATE TABLE IF NOT EXISTS ai_provider_configs (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    provider_name VARCHAR(100) NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    icon VARCHAR(50) DEFAULT '🤖',
    description TEXT,
    api_base_url VARCHAR(500) NOT NULL,
    api_key VARCHAR(500),
    api_version VARCHAR(50) DEFAULT 'v1',
    available_models JSONB DEFAULT '[]',
    default_model VARCHAR(200),
    max_tokens_limit JSONB DEFAULT '{}',
    request_headers JSONB DEFAULT '{}',
    request_timeout INTEGER DEFAULT 60,
    is_active BOOLEAN,
    sort_order INTEGER DEFAULT 0,
    extra_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ai_test_results表
CREATE TABLE IF NOT EXISTS ai_test_results (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    config_id UUID NOT NULL,
    input_image_path VARCHAR(1000),
    input_text TEXT,
    ai_response TEXT,
    confidence_score REAL,
    processing_time REAL NOT NULL,
    is_success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- schema_migrations表
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) NOT NULL,
    applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

-- stream_analysis_templates表
CREATE TABLE IF NOT EXISTS stream_analysis_templates (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL,
    template_id VARCHAR(100) NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    priority INTEGER DEFAULT 1,
    enabled BOOLEAN,
    confidence_threshold REAL DEFAULT 0.7,
    analysis_status stream_analysis_status_enum DEFAULT 'NOT_STARTED',
    alerts_count INTEGER DEFAULT 0,
    detection_count INTEGER DEFAULT 0,
    confidence_avg REAL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_detection_at TIMESTAMPTZ,
    error_message TEXT
);

-- users表
CREATE TABLE IF NOT EXISTS users (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone VARCHAR(20),
    department VARCHAR(100),
    role user_role_enum DEFAULT 'user',
    is_active BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ
);

-- video_analysis_results表
CREATE TABLE IF NOT EXISTS video_analysis_results (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    video_file_id UUID NOT NULL,
    template_id UUID NOT NULL,
    status analysis_status_enum DEFAULT 'not_started',
    analysis_result TEXT,
    confidence_score REAL,
    processing_time INTEGER,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

-- video_analysis_templates表
CREATE TABLE IF NOT EXISTS video_analysis_templates (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    description TEXT,
    prompt_content TEXT NOT NULL,
    is_enabled BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- video_files表
CREATE TABLE IF NOT EXISTS video_files (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    thumbnail_path VARCHAR(1000),
    file_size BIGINT,
    duration REAL,
    fps REAL,
    width INTEGER,
    height INTEGER,
    format VARCHAR(50),
    status video_status_enum DEFAULT 'PENDING',
    tags TEXT[] DEFAULT '{}',
    description TEXT,
    analysis_progress INTEGER DEFAULT 0,
    total_alerts INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    analyzed_at TIMESTAMPTZ,
    last_alert_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- video_streams表
CREATE TABLE IF NOT EXISTS video_streams (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    stream_url VARCHAR(1000) NOT NULL,
    stream_type stream_type_enum NOT NULL DEFAULT 'RTSP',
    username VARCHAR(100),
    password VARCHAR(100),
    status stream_status_enum NOT NULL DEFAULT 'OFFLINE',
    last_online_at TIMESTAMPTZ,
    connection_error TEXT,
    fps REAL,
    width INTEGER,
    height INTEGER,
    codec VARCHAR(50),
    thumbnail_path VARCHAR(1000),
    latest_frame_path VARCHAR(1000),
    analysis_status stream_analysis_status_enum NOT NULL DEFAULT 'NOT_STARTED',
    analysis_interval INTEGER DEFAULT 10,
    enable_recording BOOLEAN,
    total_analysis_count INTEGER DEFAULT 0,
    total_alerts INTEGER DEFAULT 0,
    last_analysis_at TIMESTAMPTZ,
    last_alert_at TIMESTAMPTZ,
    location VARCHAR(255),
    group_name VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ===========================================
-- 主键约束
-- ===========================================

ALTER TABLE ai_model_configs ADD CONSTRAINT ai_model_configs_pkey PRIMARY KEY (id);
ALTER TABLE ai_provider_configs ADD CONSTRAINT ai_provider_configs_pkey PRIMARY KEY (id);
ALTER TABLE ai_test_results ADD CONSTRAINT ai_test_results_pkey PRIMARY KEY (id);
ALTER TABLE schema_migrations ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);
ALTER TABLE stream_analysis_templates ADD CONSTRAINT stream_analysis_templates_pkey PRIMARY KEY (id);
ALTER TABLE users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
ALTER TABLE video_analysis_results ADD CONSTRAINT video_analysis_results_pkey PRIMARY KEY (id);
ALTER TABLE video_analysis_templates ADD CONSTRAINT video_analysis_templates_pkey PRIMARY KEY (id);
ALTER TABLE video_files ADD CONSTRAINT video_files_pkey PRIMARY KEY (id);
ALTER TABLE video_streams ADD CONSTRAINT video_streams_pkey PRIMARY KEY (id);

-- ===========================================
-- 索引定义
-- ===========================================

CREATE INDEX IF NOT EXISTS idx_ai_model_configs_created_at ON public.ai_model_configs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_model_type ON public.ai_model_configs USING btree (model_type);
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_provider ON public.ai_model_configs USING btree (provider);
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_status ON public.ai_model_configs USING btree (status);
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_tags ON public.ai_model_configs USING gin (tags);
CREATE INDEX IF NOT EXISTS idx_ai_model_configs_updated_at ON public.ai_model_configs USING btree (updated_at DESC);
CREATE UNIQUE INDEX ai_provider_configs_provider_name_key ON public.ai_provider_configs USING btree (provider_name);
CREATE INDEX IF NOT EXISTS idx_ai_provider_configs_created_at ON public.ai_provider_configs USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_provider_configs_is_active ON public.ai_provider_configs USING btree (is_active);
CREATE INDEX IF NOT EXISTS idx_ai_provider_configs_provider_name ON public.ai_provider_configs USING btree (provider_name);
CREATE INDEX IF NOT EXISTS idx_ai_provider_configs_sort_order ON public.ai_provider_configs USING btree (sort_order);
CREATE INDEX IF NOT EXISTS idx_ai_test_results_config_id ON public.ai_test_results USING btree (config_id);
CREATE INDEX IF NOT EXISTS idx_ai_test_results_created_at ON public.ai_test_results USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_test_results_is_success ON public.ai_test_results USING btree (is_success);
CREATE INDEX IF NOT EXISTS idx_stream_templates_enabled ON public.stream_analysis_templates USING btree (enabled);
CREATE INDEX IF NOT EXISTS idx_stream_templates_priority ON public.stream_analysis_templates USING btree (priority DESC);
CREATE INDEX IF NOT EXISTS idx_stream_templates_stream_id ON public.stream_analysis_templates USING btree (stream_id);
CREATE UNIQUE INDEX stream_analysis_templates_stream_id_template_id_key ON public.stream_analysis_templates USING btree (stream_id, template_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users USING btree (email);
CREATE INDEX IF NOT EXISTS idx_users_role ON public.users USING btree (role);
CREATE INDEX IF NOT EXISTS idx_users_username ON public.users USING btree (username);
CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email);
CREATE UNIQUE INDEX users_username_key ON public.users USING btree (username);
CREATE INDEX IF NOT EXISTS idx_analysis_results_status ON public.video_analysis_results USING btree (status);
CREATE INDEX IF NOT EXISTS idx_analysis_results_template_id ON public.video_analysis_results USING btree (template_id);
CREATE INDEX IF NOT EXISTS idx_analysis_results_video_id ON public.video_analysis_results USING btree (video_file_id);
CREATE INDEX IF NOT EXISTS idx_video_files_created_at ON public.video_files USING btree (created_at);
CREATE INDEX IF NOT EXISTS idx_video_files_original_filename ON public.video_files USING btree (original_filename);
CREATE INDEX IF NOT EXISTS idx_video_files_status ON public.video_files USING btree (status);
CREATE INDEX IF NOT EXISTS idx_video_files_tags ON public.video_files USING gin (tags);
CREATE INDEX IF NOT EXISTS idx_video_streams_created_at ON public.video_streams USING btree (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_video_streams_group ON public.video_streams USING btree (group_name);
CREATE INDEX IF NOT EXISTS idx_video_streams_location ON public.video_streams USING btree (location);
CREATE INDEX IF NOT EXISTS idx_video_streams_name ON public.video_streams USING btree (name);
CREATE INDEX IF NOT EXISTS idx_video_streams_status ON public.video_streams USING btree (status);

-- ===========================================
-- users表数据
-- ===========================================

INSERT INTO users (id, username, email, password_hash, full_name, phone, department, role, is_active, created_at, updated_at, last_login_at) VALUES (e84d7361-80b4-457e-b836-b78ccffeb7fb, 'admin', 'admin@example.com', '$2b$12$03qLb6lAHdVoOfGQRNrVYuhK0Kg.I8aTbf5eOpswL8m4zGvSm30WC', '系统管理员', NULL, NULL, 'admin', True, '2025-09-07T02:49:34.980485+00:00', '2025-09-07T06:53:28.724686+00:00', '2025-09-06T22:53:29.017323+00:00') ON CONFLICT (id) DO NOTHING;