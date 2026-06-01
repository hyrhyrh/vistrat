--
-- AI智能视频监控系统 - 数据库初始化脚本
-- PostgreSQL Database Schema v2.3.0
--
-- 包含完整的表结构、枚举类型、函数、触发器、索引、外键约束和初始数据
--

-- ==================== PostgreSQL基础配置 ====================
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


-- ==================== 枚举类型定义 ====================

-- AI模型类型枚举
DROP TYPE IF EXISTS public.ai_model_type_enum CASCADE;
CREATE TYPE public.ai_model_type_enum AS ENUM (
    'vision',      -- 视觉模型
    'text',        -- 文本模型
    'multimodal'   -- 多模态模型
);

-- AI服务提供商枚举
DROP TYPE IF EXISTS public.ai_provider_enum CASCADE;
CREATE TYPE public.ai_provider_enum AS ENUM (
    'qwen',        -- 通义千问
    'moonshot',    -- Moonshot AI
    'gpt',         -- OpenAI GPT
    'claude',      -- Anthropic Claude
    'gemini',      -- Google Gemini
    'baidu'        -- 百度文心
);

-- 算法状态枚举
DROP TYPE IF EXISTS public.algorithm_status_enum CASCADE;
CREATE TYPE public.algorithm_status_enum AS ENUM (
    'draft',       -- 草稿
    'testing',     -- 测试中
    'active',      -- 已激活
    'deprecated'   -- 已废弃
);

-- 分析状态枚举
DROP TYPE IF EXISTS public.analysis_status_enum CASCADE;
CREATE TYPE public.analysis_status_enum AS ENUM (
    'not_started', -- 未开始
    'queued',      -- 已排队
    'processing',  -- 处理中
    'completed',   -- 已完成
    'failed',      -- 失败
    'cancelled'    -- 已取消
);

-- 流分析状态枚举
DROP TYPE IF EXISTS public.stream_analysis_status_enum CASCADE;
CREATE TYPE public.stream_analysis_status_enum AS ENUM (
    'NOT_STARTED', -- 未开始
    'RUNNING',     -- 运行中
    'PAUSED',      -- 已暂停
    'STOPPED',     -- 已停止
    'ERROR'        -- 错误
);

-- 流状态枚举
DROP TYPE IF EXISTS public.stream_status_enum CASCADE;
CREATE TYPE public.stream_status_enum AS ENUM (
    'OFFLINE',     -- 离线
    'ONLINE',      -- 在线
    'CONNECTING',  -- 连接中
    'ERROR',       -- 错误
    'MAINTENANCE'  -- 维护中
);

-- 流类型枚举
DROP TYPE IF EXISTS public.stream_type_enum CASCADE;
CREATE TYPE public.stream_type_enum AS ENUM (
    'RTSP',        -- RTSP流
    'RTMP',        -- RTMP流
    'HLS',         -- HLS流
    'WEBRTC',      -- WebRTC流
    'HTTP_FLV',    -- HTTP-FLV流
    'LOCAL_CAMERA' -- 本地摄像头
);

-- 用户角色枚举
DROP TYPE IF EXISTS public.user_role_enum CASCADE;
CREATE TYPE public.user_role_enum AS ENUM (
    'admin',       -- 管理员
    'user',        -- 普通用户
    'viewer'       -- 只读用户
);

-- 视频状态枚举
DROP TYPE IF EXISTS public.video_status_enum CASCADE;
CREATE TYPE public.video_status_enum AS ENUM (
    'PENDING',     -- 待处理
    'UPLOADING',   -- 上传中
    'READY',       -- 就绪
    'ANALYZING',   -- 分析中
    'COMPLETED',   -- 已完成
    'ERROR',       -- 错误
    'DELETED'      -- 已删除
);


-- ==================== 函数定义 ====================

-- 函数: 审计视频流算法配置变更
DROP FUNCTION IF EXISTS public.audit_video_stream_algorithm_config() CASCADE;
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

-- 函数: 更新流分析任务的updated_at时间戳
DROP FUNCTION IF EXISTS public.update_stream_analysis_tasks_updated_at() CASCADE;
CREATE FUNCTION public.update_stream_analysis_tasks_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

-- 函数: 通用更新updated_at列
DROP FUNCTION IF EXISTS public.update_updated_at_column() CASCADE;
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


-- ==================== 表结构定义 ====================

-- 表: AI分析调用日志
DROP TABLE IF EXISTS public.ai_analysis_logs CASCADE;
CREATE TABLE public.ai_analysis_logs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    task_id uuid,                                           -- 关联的任务ID
    video_id uuid,                                          -- 关联的视频ID
    algorithm_id character varying(255),                    -- 算法ID
    algorithm_config_id uuid,                               -- 算法配置ID
    call_status character varying(20) DEFAULT 'success'::character varying, -- 调用状态
    api_endpoint character varying(500),                    -- API端点
    model_name character varying(100),                      -- 模型名称
    frame_index integer,                                    -- 帧索引
    frame_timestamp character varying(20),                  -- 帧时间戳
    request_data jsonb,                                     -- 请求数据
    response_data jsonb,                                    -- 响应数据
    response_time_ms integer,                               -- 响应时间(毫秒)
    confidence_score character varying(10),                 -- 置信度分数
    error_message text,                                     -- 错误信息
    error_code character varying(50),                       -- 错误代码
    call_date timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,  -- 调用日期
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.ai_analysis_logs IS 'AI分析调用日志表：记录所有AI API调用的详细日志和性能数据';


-- 表: AI模型配置
DROP TABLE IF EXISTS public.ai_model_configs CASCADE;
CREATE TABLE public.ai_model_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    name character varying(255) NOT NULL,                   -- 模型配置名称
    description text,                                       -- 描述
    model_name character varying(200) NOT NULL,             -- 模型名称
    model_type public.ai_model_type_enum DEFAULT 'vision'::public.ai_model_type_enum,  -- 模型类型
    system_prompt text,                                     -- 系统提示词
    user_prompt text,                                       -- 用户提示词
    temperature real DEFAULT 0.7,                           -- 温度参数
    top_p real DEFAULT 0.9,                                 -- Top-P参数
    max_tokens integer DEFAULT 1000,                        -- 最大token数
    confidence_threshold real DEFAULT 0.7,                  -- 置信度阈值
    tags text[] DEFAULT '{}'::text[],                       -- 标签数组
    status public.algorithm_status_enum DEFAULT 'draft'::public.algorithm_status_enum,  -- 状态
    test_count integer DEFAULT 0,                           -- 测试次数
    success_count integer DEFAULT 0,                        -- 成功次数
    extra_config jsonb DEFAULT '{}'::jsonb,                 -- 额外配置
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    prompt_template text DEFAULT ''::text,                  -- 提示词模板
    provider character varying(100) NOT NULL,               -- AI提供商(引用ai_provider_configs.provider_name)
    output_format_config jsonb                              -- 输出格式配置
);

COMMENT ON TABLE public.ai_model_configs IS 'AI模型配置表：管理各AI模型的参数、提示词和性能统计';
COMMENT ON COLUMN public.ai_model_configs.provider IS 'AI模型供应商名称(引用ai_provider_configs.provider_name)';


-- 表: AI服务提供商配置
DROP TABLE IF EXISTS public.ai_provider_configs CASCADE;
CREATE TABLE public.ai_provider_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    provider_name character varying(100) NOT NULL,          -- 提供商名称(唯一)
    display_name character varying(200) NOT NULL,           -- 显示名称
    icon character varying(50) DEFAULT '🤖'::character varying,  -- 图标
    description text,                                       -- 描述
    api_base_url character varying(500) NOT NULL,           -- API基础URL
    api_key character varying(500),                         -- API密钥
    api_version character varying(50) DEFAULT 'v1'::character varying,  -- API版本
    available_models jsonb DEFAULT '[]'::jsonb,             -- 可用模型列表
    default_model character varying(200),                   -- 默认模型
    max_tokens_limit jsonb DEFAULT '{}'::jsonb,             -- Token限制配置
    request_headers jsonb DEFAULT '{}'::jsonb,              -- 请求头配置
    request_timeout integer DEFAULT 60,                     -- 请求超时(秒)
    is_active boolean,                                      -- 是否激活
    sort_order integer DEFAULT 0,                           -- 排序顺序
    extra_config jsonb DEFAULT '{}'::jsonb,                 -- 额外配置
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.ai_provider_configs IS 'AI提供商配置表：管理各大AI服务商的API配置和连接信息';


-- 表: AI测试结果
DROP TABLE IF EXISTS public.ai_test_results CASCADE;
CREATE TABLE public.ai_test_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    config_id uuid NOT NULL,                                -- 关联的配置ID
    input_image_path character varying(1000),               -- 输入图片路径
    input_text text,                                        -- 输入文本
    ai_response text,                                       -- AI响应
    confidence_score real,                                  -- 置信度分数
    processing_time real NOT NULL,                          -- 处理时间(秒)
    is_success boolean,                                     -- 是否成功
    error_message text,                                     -- 错误信息
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.ai_test_results IS 'AI测试结果表：存储模型性能测试和评估的结果数据';


-- 表: 数据库版本迁移记录
DROP TABLE IF EXISTS public.schema_migrations CASCADE;
CREATE TABLE public.schema_migrations (
    version character varying(100) NOT NULL PRIMARY KEY,    -- 版本号
    applied_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,  -- 应用时间
    description text                                        -- 版本描述
);

COMMENT ON TABLE public.schema_migrations IS '数据库版本迁移记录表：跟踪所有数据库架构版本';


-- 表: 流分析任务(支持任务级别管理、时间调度、ROI配置)
DROP TABLE IF EXISTS public.stream_analysis_tasks CASCADE;
CREATE TABLE public.stream_analysis_tasks (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    stream_id uuid NOT NULL,                                -- 视频流ID
    algorithm_config_id uuid NOT NULL,                      -- 算法配置ID
    task_name character varying(255) NOT NULL,              -- 任务名称
    status character varying(20) DEFAULT 'enabled'::character varying NOT NULL,  -- 任务状态
    is_active boolean DEFAULT true NOT NULL,                -- 是否激活
    auto_recover boolean DEFAULT true NOT NULL,             -- 是否自动恢复
    time_config jsonb DEFAULT '{}'::jsonb NOT NULL,         -- 时间配置JSON(支持多时间段、跨天时间、星期选择)
    roi_config jsonb DEFAULT '{}'::jsonb,                   -- ROI区域配置JSON(支持矩形和多边形感兴趣区域)
    priority integer DEFAULT 1 NOT NULL,                    -- 优先级(1-10)
    confidence_threshold double precision DEFAULT 0.7 NOT NULL,  -- 置信度阈值
    analysis_interval integer DEFAULT 10 NOT NULL,          -- 分析间隔(秒)
    last_run_at timestamp with time zone,                   -- 上次运行时间
    next_run_at timestamp with time zone,                   -- 下次运行时间
    run_count integer DEFAULT 0 NOT NULL,                   -- 运行次数
    error_count integer DEFAULT 0 NOT NULL,                 -- 错误次数
    last_error_message text,                                -- 最后错误信息
    total_frames_processed integer DEFAULT 0 NOT NULL,      -- 总处理帧数
    total_alerts_generated integer DEFAULT 0 NOT NULL,      -- 总告警数
    avg_processing_time double precision DEFAULT 0,         -- 平均处理时间
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by uuid,                                        -- 创建人
    updated_by uuid,                                        -- 更新人
    CONSTRAINT chk_confidence_threshold CHECK (((confidence_threshold >= (0)::double precision) AND (confidence_threshold <= (1)::double precision))),
    CONSTRAINT chk_priority CHECK (((priority >= 1) AND (priority <= 10))),
    CONSTRAINT chk_status CHECK (((status)::text = ANY ((ARRAY['enabled'::character varying, 'disabled'::character varying, 'running'::character varying, 'error'::character varying, 'scheduled'::character varying])::text[])))
);

COMMENT ON TABLE public.stream_analysis_tasks IS '视频流实时分析任务表 - 支持任务级别管理、时间调度、ROI配置';
COMMENT ON COLUMN public.stream_analysis_tasks.time_config IS '时间配置JSON：支持多时间段、跨天时间、星期选择';
COMMENT ON COLUMN public.stream_analysis_tasks.roi_config IS 'ROI区域配置JSON：支持矩形和多边形感兴趣区域';


-- 表: 流分析模板
DROP TABLE IF EXISTS public.stream_analysis_templates CASCADE;
CREATE TABLE public.stream_analysis_templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    stream_id uuid NOT NULL,                                -- 视频流ID
    template_id character varying(100) NOT NULL,            -- 模板ID
    template_name character varying(255) NOT NULL,          -- 模板名称
    priority integer DEFAULT 1,                             -- 优先级
    enabled boolean,                                        -- 是否启用
    confidence_threshold real DEFAULT 0.7,                  -- 置信度阈值
    analysis_status public.stream_analysis_status_enum DEFAULT 'NOT_STARTED'::public.stream_analysis_status_enum,  -- 分析状态
    alerts_count integer DEFAULT 0,                         -- 告警数量
    detection_count integer DEFAULT 0,                      -- 检测数量
    confidence_avg real,                                    -- 平均置信度
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    last_detection_at timestamp(6) with time zone,          -- 最后检测时间
    error_message text                                      -- 错误信息
);

COMMENT ON TABLE public.stream_analysis_templates IS '流分析模板表：视频流AI分析配置模板';


-- 表: 系统配置参数表
DROP TABLE IF EXISTS public.system_configs CASCADE;
CREATE TABLE public.system_configs (
    param_code character varying(50) NOT NULL PRIMARY KEY,  -- 配置参数编码(主键)
    param_desc character varying(250) NOT NULL,             -- 配置参数描述
    param_val character varying(1000) NOT NULL,             -- 配置参数值
    ext_val character varying(1000) DEFAULT NULL::character varying,  -- 扩展配置值
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,  -- 创建时间
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP   -- 更新时间
);

COMMENT ON TABLE public.system_configs IS '系统配置参数表';
COMMENT ON COLUMN public.system_configs.param_code IS '配置参数编码(主键)';
COMMENT ON COLUMN public.system_configs.param_desc IS '配置参数描述';
COMMENT ON COLUMN public.system_configs.param_val IS '配置参数值';
COMMENT ON COLUMN public.system_configs.ext_val IS '扩展配置值';
COMMENT ON COLUMN public.system_configs.created_at IS '创建时间';
COMMENT ON COLUMN public.system_configs.updated_at IS '更新时间';


-- 表: 用户表
DROP TABLE IF EXISTS public.users CASCADE;
CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    username character varying(50) NOT NULL UNIQUE,         -- 用户名(唯一)
    email character varying(255) UNIQUE,                    -- 邮箱(唯一)
    password_hash character varying(255) NOT NULL,          -- 密码哈希
    full_name character varying(255),                       -- 全名
    phone character varying(20),                            -- 电话
    department character varying(100),                      -- 部门
    role public.user_role_enum DEFAULT 'user'::public.user_role_enum,  -- 角色
    is_active boolean,                                      -- 是否激活
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    last_login_at timestamp(6) with time zone               -- 最后登录时间
);

COMMENT ON TABLE public.users IS '系统用户表：管理所有用户账户信息和权限';


-- 表: 视频分析结果
DROP TABLE IF EXISTS public.video_analysis_results CASCADE;
CREATE TABLE public.video_analysis_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    video_file_id uuid NOT NULL,                            -- 视频文件ID
    template_id uuid NOT NULL,                              -- 模板ID
    status public.analysis_status_enum DEFAULT 'not_started'::public.analysis_status_enum,  -- 分析状态
    analysis_result text,                                   -- 分析结果
    confidence_score real,                                  -- 置信度分数
    processing_time integer,                                -- 处理时间(毫秒)
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    completed_at timestamp(6) with time zone                -- 完成时间
);

COMMENT ON TABLE public.video_analysis_results IS '视频分析结果表：存储AI分析的详细结果和性能指标';


-- 表: 视频分析模板
DROP TABLE IF EXISTS public.video_analysis_templates CASCADE;
CREATE TABLE public.video_analysis_templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    name character varying(255) NOT NULL,                   -- 模板名称
    category character varying(100) NOT NULL,               -- 分类
    description text,                                       -- 描述
    prompt_content text NOT NULL,                           -- 提示词内容
    is_enabled boolean,                                     -- 是否启用
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    video_id uuid,                                          -- 关联视频ID
    template_id uuid,                                       -- 模板ID
    template_name character varying(255),                   -- 模板名称
    priority integer DEFAULT 0,                             -- 优先级
    enabled boolean DEFAULT true,                           -- 是否启用
    analysis_status character varying(50) DEFAULT 'not_started'::character varying,  -- 分析状态
    progress integer DEFAULT 0,                             -- 进度百分比
    alerts_count integer DEFAULT 0,                         -- 告警数量
    confidence_avg real DEFAULT 0.0,                        -- 平均置信度
    analysis_duration integer,                              -- 分析时长(秒)
    error_message text,                                     -- 错误信息
    started_at timestamp(6) with time zone,                 -- 开始时间
    completed_at timestamp(6) with time zone                -- 完成时间
);

COMMENT ON TABLE public.video_analysis_templates IS 'AI分析模板表：存储视频分析的提示词模板和配置';


-- 表: 视频文件
DROP TABLE IF EXISTS public.video_files CASCADE;
CREATE TABLE public.video_files (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    name character varying(255) NOT NULL,                   -- 文件名称
    original_filename character varying(500) NOT NULL,      -- 原始文件名
    file_path character varying(1000) NOT NULL,             -- 文件路径
    thumbnail_path character varying(1000),                 -- 缩略图路径
    file_size bigint,                                       -- 文件大小(字节)
    duration real,                                          -- 时长(秒)
    fps real,                                               -- 帧率
    width integer,                                          -- 宽度
    height integer,                                         -- 高度
    format character varying(50),                           -- 格式
    status public.video_status_enum DEFAULT 'PENDING'::public.video_status_enum,  -- 状态
    tags text[] DEFAULT '{}'::text[],                       -- 标签数组
    description text,                                       -- 描述
    analysis_progress integer DEFAULT 0,                    -- 分析进度百分比
    total_alerts integer DEFAULT 0,                         -- 总告警数
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    analyzed_at timestamp(6) with time zone,                -- 分析完成时间
    last_alert_at timestamp(6) with time zone,              -- 最后告警时间
    deleted_at timestamp(6) with time zone                  -- 删除时间(软删除)
);

COMMENT ON TABLE public.video_files IS '视频文件表：管理所有上传的视频文件信息和分析状态';


-- 表: 视频流算法配置变更历史(审计所有配置变更记录)
DROP TABLE IF EXISTS public.video_stream_algorithm_config_history CASCADE;
CREATE TABLE public.video_stream_algorithm_config_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    config_id uuid NOT NULL,                                -- 配置ID
    stream_id uuid NOT NULL,                                -- 视频流ID
    template_id character varying(255) NOT NULL,            -- 模板ID
    template_name character varying(255),                   -- 模板名称
    priority integer,                                       -- 优先级
    confidence_threshold real,                              -- 置信度阈值
    is_active boolean,                                      -- 是否激活
    operation character varying(20) NOT NULL,               -- 操作类型(INSERT/UPDATE/DELETE)
    operation_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,  -- 操作时间
    operated_by character varying(255),                     -- 操作人
    old_values jsonb,                                       -- 旧值
    new_values jsonb                                        -- 新值
);

COMMENT ON TABLE public.video_stream_algorithm_config_history IS '视频流算法配置历史表 - 审计所有配置变更记录';


-- 表: 视频流算法配置(存储每个视频流配置的AI分析算法)
DROP TABLE IF EXISTS public.video_stream_algorithm_configs CASCADE;
CREATE TABLE public.video_stream_algorithm_configs (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    stream_id uuid NOT NULL,                                -- 视频流ID，关联video_streams表
    template_id character varying(255) NOT NULL,            -- AI算法模板ID
    template_name character varying(255),                   -- AI算法模板名称（冗余字段，便于查询）
    priority integer DEFAULT 1,                             -- 算法执行优先级，数字越大优先级越高
    confidence_threshold real DEFAULT 0.7,                  -- 置信度阈值，0.0-1.0之间
    is_active boolean DEFAULT true,                         -- 是否启用该算法配置
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    created_by character varying(255),                      -- 创建人
    CONSTRAINT uk_stream_algorithm_config UNIQUE (stream_id, template_id)  -- 确保同一个流不会重复配置同一个算法
);

COMMENT ON TABLE public.video_stream_algorithm_configs IS '视频流算法配置表 - 存储每个视频流配置的AI分析算法';
COMMENT ON COLUMN public.video_stream_algorithm_configs.stream_id IS '视频流ID，关联video_streams表';
COMMENT ON COLUMN public.video_stream_algorithm_configs.template_id IS 'AI算法模板ID';
COMMENT ON COLUMN public.video_stream_algorithm_configs.template_name IS 'AI算法模板名称（冗余字段，便于查询）';
COMMENT ON COLUMN public.video_stream_algorithm_configs.priority IS '算法执行优先级，数字越大优先级越高';
COMMENT ON COLUMN public.video_stream_algorithm_configs.confidence_threshold IS '置信度阈值，0.0-1.0之间';
COMMENT ON COLUMN public.video_stream_algorithm_configs.is_active IS '是否启用该算法配置';


-- 表: 视频流
DROP TABLE IF EXISTS public.video_streams CASCADE;
CREATE TABLE public.video_streams (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    name character varying(255) NOT NULL,                   -- 流名称
    description text,                                       -- 描述
    stream_url character varying(1000) NOT NULL,            -- 流URL
    stream_type public.stream_type_enum DEFAULT 'RTSP'::public.stream_type_enum NOT NULL,  -- 流类型
    username character varying(100),                        -- 认证用户名
    password character varying(100),                        -- 认证密码
    status public.stream_status_enum DEFAULT 'OFFLINE'::public.stream_status_enum NOT NULL,  -- 流状态
    last_online_at timestamp(6) with time zone,             -- 最后在线时间
    connection_error text,                                  -- 连接错误信息
    fps real,                                               -- 帧率
    width integer,                                          -- 宽度
    height integer,                                         -- 高度
    codec character varying(50),                            -- 编码格式
    thumbnail_path character varying(1000),                 -- 缩略图路径
    latest_frame_path character varying(1000),              -- 最新帧路径
    analysis_status public.stream_analysis_status_enum DEFAULT 'NOT_STARTED'::public.stream_analysis_status_enum NOT NULL,  -- 分析状态
    analysis_interval integer DEFAULT 10,                   -- 分析间隔(秒)
    enable_recording boolean,                               -- 是否启用录制
    total_analysis_count integer DEFAULT 0,                 -- 总分析次数
    total_alerts integer DEFAULT 0,                         -- 总告警数
    last_analysis_at timestamp(6) with time zone,           -- 最后分析时间
    last_alert_at timestamp(6) with time zone,              -- 最后告警时间
    location character varying(255),                        -- 位置
    group_name character varying(100),                      -- 分组名称
    tags text[] DEFAULT '{}'::text[],                       -- 标签数组
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE public.video_streams IS '视频流表：管理RTSP等实时视频流的配置和状态';


-- ==================== 索引定义 ====================

-- AI分析日志索引
DROP INDEX IF EXISTS public.idx_ai_analysis_logs_algorithm_id CASCADE;
CREATE INDEX idx_ai_analysis_logs_algorithm_id ON public.ai_analysis_logs USING btree (algorithm_id);
DROP INDEX IF EXISTS public.idx_ai_analysis_logs_call_date CASCADE;
CREATE INDEX idx_ai_analysis_logs_call_date ON public.ai_analysis_logs USING btree (call_date);
DROP INDEX IF EXISTS public.idx_ai_analysis_logs_call_status CASCADE;
CREATE INDEX idx_ai_analysis_logs_call_status ON public.ai_analysis_logs USING btree (call_status);
DROP INDEX IF EXISTS public.idx_ai_analysis_logs_task_id CASCADE;
CREATE INDEX idx_ai_analysis_logs_task_id ON public.ai_analysis_logs USING btree (task_id);
DROP INDEX IF EXISTS public.idx_ai_analysis_logs_video_id CASCADE;
CREATE INDEX idx_ai_analysis_logs_video_id ON public.ai_analysis_logs USING btree (video_id);

-- AI模型配置索引
DROP INDEX IF EXISTS public.idx_ai_model_configs_created_at CASCADE;
CREATE INDEX idx_ai_model_configs_created_at ON public.ai_model_configs USING btree (created_at DESC);
DROP INDEX IF EXISTS public.idx_ai_model_configs_model_type CASCADE;
CREATE INDEX idx_ai_model_configs_model_type ON public.ai_model_configs USING btree (model_type);
DROP INDEX IF EXISTS public.idx_ai_model_configs_status CASCADE;
CREATE INDEX idx_ai_model_configs_status ON public.ai_model_configs USING btree (status);
DROP INDEX IF EXISTS public.idx_ai_model_configs_tags CASCADE;
CREATE INDEX idx_ai_model_configs_tags ON public.ai_model_configs USING gin (tags);
DROP INDEX IF EXISTS public.idx_ai_model_configs_updated_at CASCADE;
CREATE INDEX idx_ai_model_configs_updated_at ON public.ai_model_configs USING btree (updated_at DESC);

-- AI服务提供商索引
DROP INDEX IF EXISTS public.ai_provider_configs_provider_name_key CASCADE;
CREATE UNIQUE INDEX ai_provider_configs_provider_name_key ON public.ai_provider_configs USING btree (provider_name);
DROP INDEX IF EXISTS public.idx_ai_provider_configs_created_at CASCADE;
CREATE INDEX idx_ai_provider_configs_created_at ON public.ai_provider_configs USING btree (created_at DESC);
DROP INDEX IF EXISTS public.idx_ai_provider_configs_is_active CASCADE;
CREATE INDEX idx_ai_provider_configs_is_active ON public.ai_provider_configs USING btree (is_active);
DROP INDEX IF EXISTS public.idx_ai_provider_configs_provider_name CASCADE;
CREATE INDEX idx_ai_provider_configs_provider_name ON public.ai_provider_configs USING btree (provider_name);
DROP INDEX IF EXISTS public.idx_ai_provider_configs_sort_order CASCADE;
CREATE INDEX idx_ai_provider_configs_sort_order ON public.ai_provider_configs USING btree (sort_order);

-- AI测试结果索引
DROP INDEX IF EXISTS public.idx_ai_test_results_config_id CASCADE;
CREATE INDEX idx_ai_test_results_config_id ON public.ai_test_results USING btree (config_id);
DROP INDEX IF EXISTS public.idx_ai_test_results_created_at CASCADE;
CREATE INDEX idx_ai_test_results_created_at ON public.ai_test_results USING btree (created_at DESC);
DROP INDEX IF EXISTS public.idx_ai_test_results_is_success CASCADE;
CREATE INDEX idx_ai_test_results_is_success ON public.ai_test_results USING btree (is_success);

-- 视频分析结果索引
DROP INDEX IF EXISTS public.idx_analysis_results_status CASCADE;
CREATE INDEX idx_analysis_results_status ON public.video_analysis_results USING btree (status);
DROP INDEX IF EXISTS public.idx_analysis_results_template_id CASCADE;
CREATE INDEX idx_analysis_results_template_id ON public.video_analysis_results USING btree (template_id);
DROP INDEX IF EXISTS public.idx_analysis_results_video_id CASCADE;
CREATE INDEX idx_analysis_results_video_id ON public.video_analysis_results USING btree (video_file_id);

-- 流分析任务索引
DROP INDEX IF EXISTS public.idx_stream_analysis_tasks_active CASCADE;
CREATE INDEX idx_stream_analysis_tasks_active ON public.stream_analysis_tasks USING btree (is_active);
DROP INDEX IF EXISTS public.idx_stream_analysis_tasks_auto_recover CASCADE;
CREATE INDEX idx_stream_analysis_tasks_auto_recover ON public.stream_analysis_tasks USING btree (auto_recover);
DROP INDEX IF EXISTS public.idx_stream_analysis_tasks_next_run CASCADE;
CREATE INDEX idx_stream_analysis_tasks_next_run ON public.stream_analysis_tasks USING btree (next_run_at) WHERE ((status)::text = 'enabled'::text);
DROP INDEX IF EXISTS public.idx_stream_analysis_tasks_status CASCADE;
CREATE INDEX idx_stream_analysis_tasks_status ON public.stream_analysis_tasks USING btree (status);
DROP INDEX IF EXISTS public.idx_stream_analysis_tasks_stream_id CASCADE;
CREATE INDEX idx_stream_analysis_tasks_stream_id ON public.stream_analysis_tasks USING btree (stream_id);

-- 流分析模板索引
DROP INDEX IF EXISTS public.idx_stream_templates_enabled CASCADE;
CREATE INDEX idx_stream_templates_enabled ON public.stream_analysis_templates USING btree (enabled);
DROP INDEX IF EXISTS public.idx_stream_templates_priority CASCADE;
CREATE INDEX idx_stream_templates_priority ON public.stream_analysis_templates USING btree (priority DESC);
DROP INDEX IF EXISTS public.idx_stream_templates_stream_id CASCADE;
CREATE INDEX idx_stream_templates_stream_id ON public.stream_analysis_templates USING btree (stream_id);
DROP INDEX IF EXISTS public.stream_analysis_templates_stream_id_template_id_key CASCADE;
CREATE UNIQUE INDEX stream_analysis_templates_stream_id_template_id_key ON public.stream_analysis_templates USING btree (stream_id, template_id);

-- 系统配置索引
DROP INDEX IF EXISTS public.idx_system_configs_param_desc CASCADE;
CREATE INDEX idx_system_configs_param_desc ON public.system_configs USING btree (param_desc);

-- 用户索引
DROP INDEX IF EXISTS public.idx_users_email CASCADE;
CREATE INDEX idx_users_email ON public.users USING btree (email);
DROP INDEX IF EXISTS public.idx_users_role CASCADE;
CREATE INDEX idx_users_role ON public.users USING btree (role);
DROP INDEX IF EXISTS public.idx_users_username CASCADE;
CREATE INDEX idx_users_username ON public.users USING btree (username);
-- 注意: users_email_key 和 users_username_key 由表的UNIQUE约束自动创建,不需要单独创建

-- 视频文件索引
DROP INDEX IF EXISTS public.idx_video_files_created_at CASCADE;
CREATE INDEX idx_video_files_created_at ON public.video_files USING btree (created_at);
DROP INDEX IF EXISTS public.idx_video_files_original_filename CASCADE;
CREATE INDEX idx_video_files_original_filename ON public.video_files USING btree (original_filename);
DROP INDEX IF EXISTS public.idx_video_files_status CASCADE;
CREATE INDEX idx_video_files_status ON public.video_files USING btree (status);
DROP INDEX IF EXISTS public.idx_video_files_tags CASCADE;
CREATE INDEX idx_video_files_tags ON public.video_files USING gin (tags);

-- 视频流算法配置历史索引
DROP INDEX IF EXISTS public.idx_video_stream_algorithm_config_history_config_id CASCADE;
CREATE INDEX idx_video_stream_algorithm_config_history_config_id ON public.video_stream_algorithm_config_history USING btree (config_id);
DROP INDEX IF EXISTS public.idx_video_stream_algorithm_config_history_operation_at CASCADE;
CREATE INDEX idx_video_stream_algorithm_config_history_operation_at ON public.video_stream_algorithm_config_history USING btree (operation_at);
DROP INDEX IF EXISTS public.idx_video_stream_algorithm_config_history_stream_id CASCADE;
CREATE INDEX idx_video_stream_algorithm_config_history_stream_id ON public.video_stream_algorithm_config_history USING btree (stream_id);

-- 视频流算法配置索引
DROP INDEX IF EXISTS public.idx_video_stream_algorithm_configs_created_at CASCADE;
CREATE INDEX idx_video_stream_algorithm_configs_created_at ON public.video_stream_algorithm_configs USING btree (created_at);
DROP INDEX IF EXISTS public.idx_video_stream_algorithm_configs_is_active CASCADE;
CREATE INDEX idx_video_stream_algorithm_configs_is_active ON public.video_stream_algorithm_configs USING btree (is_active);
DROP INDEX IF EXISTS public.idx_video_stream_algorithm_configs_stream_id CASCADE;
CREATE INDEX idx_video_stream_algorithm_configs_stream_id ON public.video_stream_algorithm_configs USING btree (stream_id);
DROP INDEX IF EXISTS public.idx_video_stream_algorithm_configs_template_id CASCADE;
CREATE INDEX idx_video_stream_algorithm_configs_template_id ON public.video_stream_algorithm_configs USING btree (template_id);

-- 视频流索引
DROP INDEX IF EXISTS public.idx_video_streams_created_at CASCADE;
CREATE INDEX idx_video_streams_created_at ON public.video_streams USING btree (created_at DESC);
DROP INDEX IF EXISTS public.idx_video_streams_group CASCADE;
CREATE INDEX idx_video_streams_group ON public.video_streams USING btree (group_name);
DROP INDEX IF EXISTS public.idx_video_streams_location CASCADE;
CREATE INDEX idx_video_streams_location ON public.video_streams USING btree (location);
DROP INDEX IF EXISTS public.idx_video_streams_name CASCADE;
CREATE INDEX idx_video_streams_name ON public.video_streams USING btree (name);
DROP INDEX IF EXISTS public.idx_video_streams_status CASCADE;
CREATE INDEX idx_video_streams_status ON public.video_streams USING btree (status);


-- ==================== 触发器定义 ====================

-- 视频流算法配置审计触发器
CREATE TRIGGER audit_video_stream_algorithm_config_trigger
    AFTER INSERT OR DELETE OR UPDATE ON public.video_stream_algorithm_configs
    FOR EACH ROW EXECUTE FUNCTION public.audit_video_stream_algorithm_config();

-- 流分析任务更新时间触发器
CREATE TRIGGER trigger_update_stream_analysis_tasks_updated_at
    BEFORE UPDATE ON public.stream_analysis_tasks
    FOR EACH ROW EXECUTE FUNCTION public.update_stream_analysis_tasks_updated_at();

-- 各表updated_at自动更新触发器
CREATE TRIGGER update_ai_analysis_logs_updated_at
    BEFORE UPDATE ON public.ai_analysis_logs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_ai_model_configs_updated_at
    BEFORE UPDATE ON public.ai_model_configs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_ai_provider_configs_updated_at
    BEFORE UPDATE ON public.ai_provider_configs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_stream_analysis_templates_updated_at
    BEFORE UPDATE ON public.stream_analysis_templates
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_system_configs_updated_at
    BEFORE UPDATE ON public.system_configs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_video_analysis_templates_updated_at
    BEFORE UPDATE ON public.video_analysis_templates
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_video_files_updated_at
    BEFORE UPDATE ON public.video_files
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_video_stream_algorithm_configs_updated_at
    BEFORE UPDATE ON public.video_stream_algorithm_configs
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_video_streams_updated_at
    BEFORE UPDATE ON public.video_streams
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


-- ==================== 外键约束 ====================

-- 视频流算法配置的流ID外键约束(级联删除)
ALTER TABLE ONLY public.video_stream_algorithm_configs
    ADD CONSTRAINT fk_stream_algorithm_configs_stream_id
    FOREIGN KEY (stream_id) REFERENCES public.video_streams(id) ON DELETE CASCADE;


-- ==================== 初始数据 ====================

-- 插入AI服务提供商配置（仅在不存在时插入）
INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES
('5de3f7bc-0053-4f65-9cd2-487f1db3f3c6', 'qwen', '通义千问', '🟡', '阿里云通义千问大模型，支持文本和视觉理解', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', '', 'v1', '["qwen-vl-plus", "qwen-vl-max", "qwen-turbo", "qwen-plus", "qwen-max"]', 'qwen-vl-plus', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 90, false, 1, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b7102feb-646c-4425-91c6-a62fe2f5bc6a', 'moonshot', 'Moonshot', '🌙', 'Moonshot AI大模型，专注于长上下文理解', 'https://api.moonshot.cn/v1/chat/completions', '', 'v1', '["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]', 'moonshot-v1-8k', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 60, false, 2, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('68071e9f-9274-4a26-82db-89104a6dcb3a', 'gpt', 'OpenAI GPT', '🤖', 'OpenAI GPT系列模型，支持文本和视觉理解', 'https://api.openai.com/v1/chat/completions', '', 'v1', '["gpt-4-vision-preview", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]', 'gpt-4-vision-preview', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 60, false, 3, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('a196fa76-189e-4e17-8a73-9a27e45ab917', 'claude', 'Claude', '🎭', 'Anthropic Claude大模型，擅长理解和推理', 'https://api.anthropic.com/v1/messages', '', 'v1', '["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]', 'claude-3-sonnet', '{}', '{"x-api-key": "{api_key}", "Content-Type": "application/json", "anthropic-version": "2023-06-01"}', 60, false, 4, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('6e1823ec-e19d-4e86-ae44-c09d08aaba4f', 'gemini', 'Google Gemini', '💎', 'Google Gemini多模态大模型', 'https://generativelanguage.googleapis.com/v1/models', '', 'v1', '["gemini-1.5-pro", "gemini-1.0-pro-vision", "gemini-1.0-pro"]', 'gemini-1.5-pro', '{}', '{"Content-Type": "application/json"}', 60, false, 5, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('b2a59c44-997f-4d42-9b87-ad31439fa4df', 'baidu', '百度文心', '🐻', '百度文心一言大模型', 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat', '', 'v1', '["ernie-4.0-turbo", "ernie-3.5-turbo", "ernie-bot-4"]', 'ernie-4.0-turbo', '{}', '{"Content-Type": "application/json"}', 60, false, 6, '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (id) DO NOTHING;

-- 插入系统配置参数（仅在不存在时插入）
INSERT INTO public.system_configs (param_code, param_desc, param_val, ext_val, created_at, updated_at) VALUES
('video_max_size', '视频文件最大大小(MB)', '500', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('ai_request_timeout', 'AI请求超时时间(秒)', '30', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('stream_analysis_interval', '流分析间隔时间(秒)', '10', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('max_concurrent_analysis', '最大并发分析任务数', '5', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
('alert_retention_days', '告警记录保留天数', '30', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT (param_code) DO NOTHING;

-- 插入版本迁移记录（仅在不存在时插入）
INSERT INTO public.schema_migrations (version, applied_at, description) VALUES
('v2.3.0', CURRENT_TIMESTAMP, '首次数据库初始化 - 完整架构')
ON CONFLICT (version) DO NOTHING;

-- ==================== 完成 ====================
-- 数据库初始化完成
-- 注意: 管理员用户将由应用程序的 init_admin_user() 函数自动创建
