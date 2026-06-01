--
-- PostgreSQL database dump
--

\restrict C3GnB5VrycpbHHOXehp5qKRKeIcWViJLNDzOlIbmIjDZl5VfnaCr1U8AHLSqQu5

-- Dumped from database version 16.10 (Debian 16.10-1.pgdg13+1)
-- Dumped by pg_dump version 16.10 (Debian 16.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: ai_model_type_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ai_model_type_enum AS ENUM (
    'vision',
    'text',
    'multimodal'
);


--
-- Name: ai_provider_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ai_provider_enum AS ENUM (
    'qwen',
    'moonshot',
    'gpt',
    'claude',
    'gemini',
    'baidu'
);


--
-- Name: algorithm_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.algorithm_status_enum AS ENUM (
    'draft',
    'testing',
    'active',
    'deprecated'
);


--
-- Name: analysis_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.analysis_status_enum AS ENUM (
    'not_started',
    'queued',
    'processing',
    'completed',
    'failed',
    'cancelled'
);


--
-- Name: stream_analysis_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.stream_analysis_status_enum AS ENUM (
    'NOT_STARTED',
    'RUNNING',
    'PAUSED',
    'STOPPED',
    'ERROR'
);


--
-- Name: stream_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.stream_status_enum AS ENUM (
    'OFFLINE',
    'ONLINE',
    'CONNECTING',
    'ERROR',
    'MAINTENANCE'
);


--
-- Name: stream_type_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.stream_type_enum AS ENUM (
    'RTSP',
    'RTMP',
    'HLS',
    'WEBRTC',
    'HTTP_FLV',
    'LOCAL_CAMERA'
);


--
-- Name: user_role_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.user_role_enum AS ENUM (
    'admin',
    'user',
    'viewer'
);


--
-- Name: video_status_enum; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.video_status_enum AS ENUM (
    'PENDING',
    'UPLOADING',
    'READY',
    'ANALYZING',
    'COMPLETED',
    'ERROR',
    'DELETED'
);


--
-- Name: audit_video_stream_algorithm_config(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.audit_video_stream_algorithm_config() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
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
$$;


--
-- Name: update_stream_analysis_tasks_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_stream_analysis_tasks_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ai_analysis_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_analysis_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    task_id uuid,
    video_id uuid,
    algorithm_id character varying(255),
    algorithm_config_id uuid,
    call_status character varying(20) DEFAULT 'success'::character varying,
    api_endpoint character varying(500),
    model_name character varying(100),
    frame_index integer,
    frame_timestamp character varying(20),
    request_data jsonb,
    response_data jsonb,
    response_time_ms integer,
    confidence_score character varying(10),
    error_message text,
    error_code character varying(50),
    call_date timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ai_model_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_model_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    model_name character varying(200) NOT NULL,
    model_type public.ai_model_type_enum DEFAULT 'vision'::public.ai_model_type_enum,
    system_prompt text,
    user_prompt text,
    temperature real DEFAULT 0.7,
    top_p real DEFAULT 0.9,
    max_tokens integer DEFAULT 1000,
    confidence_threshold real DEFAULT 0.7,
    tags text[] DEFAULT '{}'::text[],
    status public.algorithm_status_enum DEFAULT 'draft'::public.algorithm_status_enum,
    test_count integer DEFAULT 0,
    success_count integer DEFAULT 0,
    extra_config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    prompt_template text DEFAULT ''::text,
    provider character varying(100) NOT NULL,
    output_format_config jsonb
);


--
-- Name: COLUMN ai_model_configs.provider; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ai_model_configs.provider IS 'AI模型供应商名称(引用ai_provider_configs.provider_name)';


--
-- Name: ai_provider_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_provider_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    provider_name character varying(100) NOT NULL,
    display_name character varying(200) NOT NULL,
    icon character varying(50) DEFAULT '🤖'::character varying,
    description text,
    api_base_url character varying(500) NOT NULL,
    api_key character varying(500),
    api_version character varying(50) DEFAULT 'v1'::character varying,
    available_models jsonb DEFAULT '[]'::jsonb,
    default_model character varying(200),
    max_tokens_limit jsonb DEFAULT '{}'::jsonb,
    request_headers jsonb DEFAULT '{}'::jsonb,
    request_timeout integer DEFAULT 60,
    is_active boolean,
    sort_order integer DEFAULT 0,
    extra_config jsonb DEFAULT '{}'::jsonb,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ai_test_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ai_test_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    config_id uuid NOT NULL,
    input_image_path character varying(1000),
    input_text text,
    ai_response text,
    confidence_score real,
    processing_time real NOT NULL,
    is_success boolean,
    error_message text,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying(100) NOT NULL,
    applied_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    description text
);


--
-- Name: stream_analysis_tasks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stream_analysis_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    stream_id uuid NOT NULL,
    algorithm_config_id uuid NOT NULL,
    task_name character varying(255) NOT NULL,
    status character varying(20) DEFAULT 'enabled'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    auto_recover boolean DEFAULT true NOT NULL,
    time_config jsonb DEFAULT '{}'::jsonb NOT NULL,
    roi_config jsonb DEFAULT '{}'::jsonb,
    priority integer DEFAULT 1 NOT NULL,
    confidence_threshold double precision DEFAULT 0.7 NOT NULL,
    analysis_interval integer DEFAULT 10 NOT NULL,
    last_run_at timestamp with time zone,
    next_run_at timestamp with time zone,
    run_count integer DEFAULT 0 NOT NULL,
    error_count integer DEFAULT 0 NOT NULL,
    last_error_message text,
    total_frames_processed integer DEFAULT 0 NOT NULL,
    total_alerts_generated integer DEFAULT 0 NOT NULL,
    avg_processing_time double precision DEFAULT 0,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by uuid,
    updated_by uuid,
    CONSTRAINT chk_confidence_threshold CHECK (((confidence_threshold >= (0)::double precision) AND (confidence_threshold <= (1)::double precision))),
    CONSTRAINT chk_priority CHECK (((priority >= 1) AND (priority <= 10))),
    CONSTRAINT chk_status CHECK (((status)::text = ANY ((ARRAY['enabled'::character varying, 'disabled'::character varying, 'running'::character varying, 'error'::character varying, 'scheduled'::character varying])::text[])))
);


--
-- Name: TABLE stream_analysis_tasks; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.stream_analysis_tasks IS '视频流实时分析任务表 - 支持任务级别管理、时间调度、ROI配置';


--
-- Name: COLUMN stream_analysis_tasks.time_config; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.stream_analysis_tasks.time_config IS '时间配置JSON：支持多时间段、跨天时间、星期选择';


--
-- Name: COLUMN stream_analysis_tasks.roi_config; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.stream_analysis_tasks.roi_config IS 'ROI区域配置JSON：支持矩形和多边形感兴趣区域';


--
-- Name: stream_analysis_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.stream_analysis_templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    stream_id uuid NOT NULL,
    template_id character varying(100) NOT NULL,
    template_name character varying(255) NOT NULL,
    priority integer DEFAULT 1,
    enabled boolean,
    confidence_threshold real DEFAULT 0.7,
    analysis_status public.stream_analysis_status_enum DEFAULT 'NOT_STARTED'::public.stream_analysis_status_enum,
    alerts_count integer DEFAULT 0,
    detection_count integer DEFAULT 0,
    confidence_avg real,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    last_detection_at timestamp(6) with time zone,
    error_message text
);


--
-- Name: system_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_configs (
    param_code character varying(50) NOT NULL,
    param_desc character varying(250) NOT NULL,
    param_val character varying(1000) NOT NULL,
    ext_val character varying(1000) DEFAULT NULL::character varying,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: TABLE system_configs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.system_configs IS '系统配置参数表';


--
-- Name: COLUMN system_configs.param_code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.system_configs.param_code IS '配置参数编码(主键)';


--
-- Name: COLUMN system_configs.param_desc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.system_configs.param_desc IS '配置参数描述';


--
-- Name: COLUMN system_configs.param_val; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.system_configs.param_val IS '配置参数值';


--
-- Name: COLUMN system_configs.ext_val; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.system_configs.ext_val IS '扩展配置值';


--
-- Name: COLUMN system_configs.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.system_configs.created_at IS '创建时间';


--
-- Name: COLUMN system_configs.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.system_configs.updated_at IS '更新时间';


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    username character varying(50) NOT NULL,
    email character varying(255),
    password_hash character varying(255) NOT NULL,
    full_name character varying(255),
    phone character varying(20),
    department character varying(100),
    role public.user_role_enum DEFAULT 'user'::public.user_role_enum,
    is_active boolean,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    last_login_at timestamp(6) with time zone
);


--
-- Name: video_analysis_results; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_analysis_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    video_file_id uuid NOT NULL,
    template_id uuid NOT NULL,
    status public.analysis_status_enum DEFAULT 'not_started'::public.analysis_status_enum,
    analysis_result text,
    confidence_score real,
    processing_time integer,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp(6) with time zone
);


--
-- Name: video_analysis_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_analysis_templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    category character varying(100) NOT NULL,
    description text,
    prompt_content text NOT NULL,
    is_enabled boolean,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    video_id uuid,
    template_id uuid,
    template_name character varying(255),
    priority integer DEFAULT 0,
    enabled boolean DEFAULT true,
    analysis_status character varying(50) DEFAULT 'not_started'::character varying,
    progress integer DEFAULT 0,
    alerts_count integer DEFAULT 0,
    confidence_avg real DEFAULT 0.0,
    analysis_duration integer,
    error_message text,
    started_at timestamp(6) with time zone,
    completed_at timestamp(6) with time zone
);


--
-- Name: video_files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    original_filename character varying(500) NOT NULL,
    file_path character varying(1000) NOT NULL,
    thumbnail_path character varying(1000),
    file_size bigint,
    duration real,
    fps real,
    width integer,
    height integer,
    format character varying(50),
    status public.video_status_enum DEFAULT 'PENDING'::public.video_status_enum,
    tags text[] DEFAULT '{}'::text[],
    description text,
    analysis_progress integer DEFAULT 0,
    total_alerts integer DEFAULT 0,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    analyzed_at timestamp(6) with time zone,
    last_alert_at timestamp(6) with time zone,
    deleted_at timestamp(6) with time zone
);


--
-- Name: video_stream_algorithm_config_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_stream_algorithm_config_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    config_id uuid NOT NULL,
    stream_id uuid NOT NULL,
    template_id character varying(255) NOT NULL,
    template_name character varying(255),
    priority integer,
    confidence_threshold real,
    is_active boolean,
    operation character varying(20) NOT NULL,
    operation_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    operated_by character varying(255),
    old_values jsonb,
    new_values jsonb
);


--
-- Name: TABLE video_stream_algorithm_config_history; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.video_stream_algorithm_config_history IS '视频流算法配置历史表 - 审计所有配置变更记录';


--
-- Name: video_stream_algorithm_configs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_stream_algorithm_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    stream_id uuid NOT NULL,
    template_id character varying(255) NOT NULL,
    template_name character varying(255),
    priority integer DEFAULT 1,
    confidence_threshold real DEFAULT 0.7,
    is_active boolean DEFAULT true,
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    created_by character varying(255)
);


--
-- Name: TABLE video_stream_algorithm_configs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.video_stream_algorithm_configs IS '视频流算法配置表 - 存储每个视频流配置的AI分析算法';


--
-- Name: COLUMN video_stream_algorithm_configs.stream_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.video_stream_algorithm_configs.stream_id IS '视频流ID，关联video_streams表';


--
-- Name: COLUMN video_stream_algorithm_configs.template_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.video_stream_algorithm_configs.template_id IS 'AI算法模板ID';


--
-- Name: COLUMN video_stream_algorithm_configs.template_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.video_stream_algorithm_configs.template_name IS 'AI算法模板名称（冗余字段，便于查询）';


--
-- Name: COLUMN video_stream_algorithm_configs.priority; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.video_stream_algorithm_configs.priority IS '算法执行优先级，数字越大优先级越高';


--
-- Name: COLUMN video_stream_algorithm_configs.confidence_threshold; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.video_stream_algorithm_configs.confidence_threshold IS '置信度阈值，0.0-1.0之间';


--
-- Name: COLUMN video_stream_algorithm_configs.is_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.video_stream_algorithm_configs.is_active IS '是否启用该算法配置';


--
-- Name: video_streams; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.video_streams (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    stream_url character varying(1000) NOT NULL,
    stream_type public.stream_type_enum DEFAULT 'RTSP'::public.stream_type_enum NOT NULL,
    username character varying(100),
    password character varying(100),
    status public.stream_status_enum DEFAULT 'OFFLINE'::public.stream_status_enum NOT NULL,
    last_online_at timestamp(6) with time zone,
    connection_error text,
    fps real,
    width integer,
    height integer,
    codec character varying(50),
    thumbnail_path character varying(1000),
    latest_frame_path character varying(1000),
    analysis_status public.stream_analysis_status_enum DEFAULT 'NOT_STARTED'::public.stream_analysis_status_enum NOT NULL,
    analysis_interval integer DEFAULT 10,
    enable_recording boolean,
    total_analysis_count integer DEFAULT 0,
    total_alerts integer DEFAULT 0,
    last_analysis_at timestamp(6) with time zone,
    last_alert_at timestamp(6) with time zone,
    location character varying(255),
    group_name character varying(100),
    tags text[] DEFAULT '{}'::text[],
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: ai_analysis_logs ai_analysis_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_analysis_logs
    ADD CONSTRAINT ai_analysis_logs_pkey PRIMARY KEY (id);


--
-- Name: ai_model_configs ai_model_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_model_configs
    ADD CONSTRAINT ai_model_configs_pkey PRIMARY KEY (id);


--
-- Name: ai_provider_configs ai_provider_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_provider_configs
    ADD CONSTRAINT ai_provider_configs_pkey PRIMARY KEY (id);


--
-- Name: ai_test_results ai_test_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ai_test_results
    ADD CONSTRAINT ai_test_results_pkey PRIMARY KEY (id);


--
-- Name: system_configs pk_system_configs; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_configs
    ADD CONSTRAINT pk_system_configs PRIMARY KEY (param_code);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: stream_analysis_tasks stream_analysis_tasks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stream_analysis_tasks
    ADD CONSTRAINT stream_analysis_tasks_pkey PRIMARY KEY (id);


--
-- Name: stream_analysis_templates stream_analysis_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.stream_analysis_templates
    ADD CONSTRAINT stream_analysis_templates_pkey PRIMARY KEY (id);


--
-- Name: video_stream_algorithm_configs uk_stream_algorithm_config; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stream_algorithm_configs
    ADD CONSTRAINT uk_stream_algorithm_config UNIQUE (stream_id, template_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: video_analysis_results video_analysis_results_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_analysis_results
    ADD CONSTRAINT video_analysis_results_pkey PRIMARY KEY (id);


--
-- Name: video_analysis_templates video_analysis_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_analysis_templates
    ADD CONSTRAINT video_analysis_templates_pkey PRIMARY KEY (id);


--
-- Name: video_files video_files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_files
    ADD CONSTRAINT video_files_pkey PRIMARY KEY (id);


--
-- Name: video_stream_algorithm_config_history video_stream_algorithm_config_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stream_algorithm_config_history
    ADD CONSTRAINT video_stream_algorithm_config_history_pkey PRIMARY KEY (id);


--
-- Name: video_stream_algorithm_configs video_stream_algorithm_configs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stream_algorithm_configs
    ADD CONSTRAINT video_stream_algorithm_configs_pkey PRIMARY KEY (id);


--
-- Name: video_streams video_streams_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_streams
    ADD CONSTRAINT video_streams_pkey PRIMARY KEY (id);


--
-- Name: ai_provider_configs_provider_name_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ai_provider_configs_provider_name_key ON public.ai_provider_configs USING btree (provider_name);


--
-- Name: idx_ai_analysis_logs_algorithm_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_analysis_logs_algorithm_id ON public.ai_analysis_logs USING btree (algorithm_id);


--
-- Name: idx_ai_analysis_logs_call_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_analysis_logs_call_date ON public.ai_analysis_logs USING btree (call_date);


--
-- Name: idx_ai_analysis_logs_call_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_analysis_logs_call_status ON public.ai_analysis_logs USING btree (call_status);


--
-- Name: idx_ai_analysis_logs_task_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_analysis_logs_task_id ON public.ai_analysis_logs USING btree (task_id);


--
-- Name: idx_ai_analysis_logs_video_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_analysis_logs_video_id ON public.ai_analysis_logs USING btree (video_id);


--
-- Name: idx_ai_model_configs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_model_configs_created_at ON public.ai_model_configs USING btree (created_at DESC);


--
-- Name: idx_ai_model_configs_model_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_model_configs_model_type ON public.ai_model_configs USING btree (model_type);


--
-- Name: idx_ai_model_configs_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_model_configs_status ON public.ai_model_configs USING btree (status);


--
-- Name: idx_ai_model_configs_tags; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_model_configs_tags ON public.ai_model_configs USING gin (tags);


--
-- Name: idx_ai_model_configs_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_model_configs_updated_at ON public.ai_model_configs USING btree (updated_at DESC);


--
-- Name: idx_ai_provider_configs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_provider_configs_created_at ON public.ai_provider_configs USING btree (created_at DESC);


--
-- Name: idx_ai_provider_configs_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_provider_configs_is_active ON public.ai_provider_configs USING btree (is_active);


--
-- Name: idx_ai_provider_configs_provider_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_provider_configs_provider_name ON public.ai_provider_configs USING btree (provider_name);


--
-- Name: idx_ai_provider_configs_sort_order; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_provider_configs_sort_order ON public.ai_provider_configs USING btree (sort_order);


--
-- Name: idx_ai_test_results_config_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_test_results_config_id ON public.ai_test_results USING btree (config_id);


--
-- Name: idx_ai_test_results_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_test_results_created_at ON public.ai_test_results USING btree (created_at DESC);


--
-- Name: idx_ai_test_results_is_success; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ai_test_results_is_success ON public.ai_test_results USING btree (is_success);


--
-- Name: idx_analysis_results_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_results_status ON public.video_analysis_results USING btree (status);


--
-- Name: idx_analysis_results_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_results_template_id ON public.video_analysis_results USING btree (template_id);


--
-- Name: idx_analysis_results_video_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analysis_results_video_id ON public.video_analysis_results USING btree (video_file_id);


--
-- Name: idx_stream_analysis_tasks_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_analysis_tasks_active ON public.stream_analysis_tasks USING btree (is_active);


--
-- Name: idx_stream_analysis_tasks_auto_recover; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_analysis_tasks_auto_recover ON public.stream_analysis_tasks USING btree (auto_recover);


--
-- Name: idx_stream_analysis_tasks_next_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_analysis_tasks_next_run ON public.stream_analysis_tasks USING btree (next_run_at) WHERE ((status)::text = 'enabled'::text);


--
-- Name: idx_stream_analysis_tasks_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_analysis_tasks_status ON public.stream_analysis_tasks USING btree (status);


--
-- Name: idx_stream_analysis_tasks_stream_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_analysis_tasks_stream_id ON public.stream_analysis_tasks USING btree (stream_id);


--
-- Name: idx_stream_templates_enabled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_templates_enabled ON public.stream_analysis_templates USING btree (enabled);


--
-- Name: idx_stream_templates_priority; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_templates_priority ON public.stream_analysis_templates USING btree (priority DESC);


--
-- Name: idx_stream_templates_stream_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_stream_templates_stream_id ON public.stream_analysis_templates USING btree (stream_id);


--
-- Name: idx_system_configs_param_desc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_system_configs_param_desc ON public.system_configs USING btree (param_desc);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_username ON public.users USING btree (username);


--
-- Name: idx_video_files_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_files_created_at ON public.video_files USING btree (created_at);


--
-- Name: idx_video_files_original_filename; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_files_original_filename ON public.video_files USING btree (original_filename);


--
-- Name: idx_video_files_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_files_status ON public.video_files USING btree (status);


--
-- Name: idx_video_files_tags; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_files_tags ON public.video_files USING gin (tags);


--
-- Name: idx_video_stream_algorithm_config_history_config_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_stream_algorithm_config_history_config_id ON public.video_stream_algorithm_config_history USING btree (config_id);


--
-- Name: idx_video_stream_algorithm_config_history_operation_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_stream_algorithm_config_history_operation_at ON public.video_stream_algorithm_config_history USING btree (operation_at);


--
-- Name: idx_video_stream_algorithm_config_history_stream_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_stream_algorithm_config_history_stream_id ON public.video_stream_algorithm_config_history USING btree (stream_id);


--
-- Name: idx_video_stream_algorithm_configs_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_stream_algorithm_configs_created_at ON public.video_stream_algorithm_configs USING btree (created_at);


--
-- Name: idx_video_stream_algorithm_configs_is_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_stream_algorithm_configs_is_active ON public.video_stream_algorithm_configs USING btree (is_active);


--
-- Name: idx_video_stream_algorithm_configs_stream_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_stream_algorithm_configs_stream_id ON public.video_stream_algorithm_configs USING btree (stream_id);


--
-- Name: idx_video_stream_algorithm_configs_template_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_stream_algorithm_configs_template_id ON public.video_stream_algorithm_configs USING btree (template_id);


--
-- Name: idx_video_streams_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_streams_created_at ON public.video_streams USING btree (created_at DESC);


--
-- Name: idx_video_streams_group; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_streams_group ON public.video_streams USING btree (group_name);


--
-- Name: idx_video_streams_location; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_streams_location ON public.video_streams USING btree (location);


--
-- Name: idx_video_streams_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_streams_name ON public.video_streams USING btree (name);


--
-- Name: idx_video_streams_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_video_streams_status ON public.video_streams USING btree (status);


--
-- Name: stream_analysis_templates_stream_id_template_id_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX stream_analysis_templates_stream_id_template_id_key ON public.stream_analysis_templates USING btree (stream_id, template_id);


--
-- Name: users_email_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email);


--
-- Name: users_username_key; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX users_username_key ON public.users USING btree (username);


--
-- Name: video_stream_algorithm_configs audit_video_stream_algorithm_config_trigger; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER audit_video_stream_algorithm_config_trigger AFTER INSERT OR DELETE OR UPDATE ON public.video_stream_algorithm_configs FOR EACH ROW EXECUTE FUNCTION public.audit_video_stream_algorithm_config();


--
-- Name: stream_analysis_tasks trigger_update_stream_analysis_tasks_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trigger_update_stream_analysis_tasks_updated_at BEFORE UPDATE ON public.stream_analysis_tasks FOR EACH ROW EXECUTE FUNCTION public.update_stream_analysis_tasks_updated_at();


--
-- Name: ai_analysis_logs update_ai_analysis_logs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_ai_analysis_logs_updated_at BEFORE UPDATE ON public.ai_analysis_logs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: ai_model_configs update_ai_model_configs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_ai_model_configs_updated_at BEFORE UPDATE ON public.ai_model_configs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: ai_provider_configs update_ai_provider_configs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_ai_provider_configs_updated_at BEFORE UPDATE ON public.ai_provider_configs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: stream_analysis_templates update_stream_analysis_templates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_stream_analysis_templates_updated_at BEFORE UPDATE ON public.stream_analysis_templates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: system_configs update_system_configs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_system_configs_updated_at BEFORE UPDATE ON public.system_configs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: video_analysis_templates update_video_analysis_templates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_video_analysis_templates_updated_at BEFORE UPDATE ON public.video_analysis_templates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: video_files update_video_files_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_video_files_updated_at BEFORE UPDATE ON public.video_files FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: video_stream_algorithm_configs update_video_stream_algorithm_configs_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_video_stream_algorithm_configs_updated_at BEFORE UPDATE ON public.video_stream_algorithm_configs FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: video_streams update_video_streams_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_video_streams_updated_at BEFORE UPDATE ON public.video_streams FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: video_stream_algorithm_configs fk_stream_algorithm_configs_stream_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.video_stream_algorithm_configs
    ADD CONSTRAINT fk_stream_algorithm_configs_stream_id FOREIGN KEY (stream_id) REFERENCES public.video_streams(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict C3GnB5VrycpbHHOXehp5qKRKeIcWViJLNDzOlIbmIjDZl5VfnaCr1U8AHLSqQu5

