-- =====================================================================
-- Migration: 002_restore_missing_tables.sql
--
-- Source:  C:\D\doc\mysql\public.sql  (pg_dump from vision_db_release)
--
-- Purpose: Restore all tables from the reference schema that are missing
--          from the current dev database (container vision_dev_postgres,
--          db vision_db). Schema-only; NO data is loaded.
--
-- Tables SKIPPED (already exist in current DB):
--     users, video_streams, analysis_tasks,
--     alerts, alerts_202604, alerts_202605, alerts_default
--   (Note: analysis_tasks + alerts* are NOT in the reference schema at all;
--    they are partitioned time-series tables owned by the new system.)
--
-- Tables CREATED by this migration (16):
--     ai_agent_history            (log-type, DDL only)
--     ai_agent_sessions           (log-type, DDL only)
--     ai_analysis_logs            (log-type, DDL only)
--     ai_model_configs
--     ai_provider_configs
--     ai_test_results             (log-type, DDL only)
--     detection_type_templates
--     schema_migrations
--     stream_analysis_tasks
--     stream_analysis_templates
--     system_configs
--     video_analysis_results
--     video_analysis_templates
--     video_files
--     video_stream_algorithm_config_history  (log-type, DDL only)
--     video_stream_algorithm_configs
--
-- Log-type tables (structure created, data intentionally skipped per
-- "日志表类的数据清理掉即可"):
--     ai_agent_history, ai_agent_sessions, ai_analysis_logs,
--     ai_test_results, video_stream_algorithm_config_history
--
-- Notes:
--   * All CREATE TABLE statements use IF NOT EXISTS — safe to re-run.
--   * Enum types wrapped in DO blocks to tolerate re-runs.
--   * No INSERT / COPY statements are emitted for ANY table. The current
--     dev DB starts with fresh data.
--   * Foreign keys to existing tables (users, video_streams) are added
--     inside DO blocks to remain idempotent.
--   * Source format detected: PostgreSQL pg_dump (Navicat-style).
--     No type translation was necessary.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. Enum types
-- ---------------------------------------------------------------------
DO $$ BEGIN
    CREATE TYPE "ai_model_type_enum" AS ENUM ('vision', 'text', 'multimodal');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "ai_provider_enum" AS ENUM ('qwen', 'moonshot', 'gpt', 'claude', 'gemini', 'baidu');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "algorithm_status_enum" AS ENUM ('draft', 'testing', 'active', 'deprecated');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "analysis_status_enum" AS ENUM ('not_started', 'queued', 'processing', 'completed', 'failed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "stream_analysis_status_enum" AS ENUM ('NOT_STARTED', 'RUNNING', 'PAUSED', 'STOPPED', 'ERROR');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "stream_status_enum" AS ENUM ('OFFLINE', 'ONLINE', 'CONNECTING', 'ERROR', 'MAINTENANCE');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "stream_type_enum" AS ENUM ('RTSP', 'RTMP', 'HLS', 'WEBRTC', 'HTTP_FLV', 'LOCAL_CAMERA');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "user_role_enum" AS ENUM ('admin', 'user', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE "video_status_enum" AS ENUM ('PENDING', 'UPLOADING', 'READY', 'ANALYZING', 'COMPLETED', 'ERROR', 'DELETED');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- ---------------------------------------------------------------------
-- 2. schema_migrations
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "schema_migrations" (
    "version"     varchar(100) NOT NULL,
    "applied_at"  timestamptz DEFAULT CURRENT_TIMESTAMP,
    "description" text,
    CONSTRAINT "schema_migrations_pkey" PRIMARY KEY ("version")
);
COMMENT ON TABLE "schema_migrations" IS '数据库版本迁移记录表：跟踪所有数据库架构版本';


-- ---------------------------------------------------------------------
-- 3. system_configs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "system_configs" (
    "param_code" varchar(50)   NOT NULL,
    "param_desc" varchar(250)  NOT NULL,
    "param_val"  varchar(1000) NOT NULL,
    "ext_val"    varchar(1000) DEFAULT NULL,
    "created_at" timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at" timestamptz DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "system_configs_pkey" PRIMARY KEY ("param_code")
);
CREATE INDEX IF NOT EXISTS "idx_system_configs_param_desc" ON "system_configs" USING btree ("param_desc");
COMMENT ON TABLE "system_configs" IS '系统配置参数表';


-- ---------------------------------------------------------------------
-- 4. detection_type_templates
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "detection_type_templates" (
    "id"                uuid         NOT NULL DEFAULT gen_random_uuid(),
    "type_code"         varchar(50)  NOT NULL,
    "display_name"      varchar(100) NOT NULL,
    "category"          varchar(50)  NOT NULL,
    "prompt_template"   text         NOT NULL,
    "json_field_name"   varchar(50)  NOT NULL,
    "severity"          varchar(20)  NOT NULL DEFAULT 'medium',
    "sort_order"        int4         NOT NULL DEFAULT 0,
    "enabled"           bool         NOT NULL DEFAULT true,
    "description"       text,
    "example_scenarios" text,
    "usage_count"       int4         DEFAULT 0,
    "detection_count"   int4         DEFAULT 0,
    "avg_confidence"    float4       DEFAULT 0.0,
    "created_at"        timestamptz  DEFAULT CURRENT_TIMESTAMP,
    "updated_at"        timestamptz  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "detection_type_templates_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "detection_type_templates_type_code_key" UNIQUE ("type_code"),
    CONSTRAINT "detection_type_templates_severity_check"
        CHECK (severity::text = ANY (ARRAY['low'::varchar::text, 'medium'::varchar::text, 'high'::varchar::text]))
);
CREATE INDEX IF NOT EXISTS "idx_detection_type_templates_category"   ON "detection_type_templates" USING btree ("category");
CREATE INDEX IF NOT EXISTS "idx_detection_type_templates_enabled"    ON "detection_type_templates" USING btree ("enabled");
CREATE INDEX IF NOT EXISTS "idx_detection_type_templates_sort_order" ON "detection_type_templates" USING btree ("sort_order");
CREATE INDEX IF NOT EXISTS "idx_detection_type_templates_type_code"  ON "detection_type_templates" USING btree ("type_code");
COMMENT ON TABLE "detection_type_templates" IS '检测类型模板表：预定义的AI检测类型和提示词模板，用于复合检测';


-- ---------------------------------------------------------------------
-- 5. ai_provider_configs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "ai_provider_configs" (
    "id"                uuid         NOT NULL DEFAULT gen_random_uuid(),
    "provider_name"     varchar(100) NOT NULL,
    "display_name"      varchar(200) NOT NULL,
    "icon"              varchar(50)  DEFAULT '🤖',
    "description"       text,
    "api_base_url"      varchar(500) NOT NULL,
    "api_key"           varchar(500),
    "api_version"       varchar(50)  DEFAULT 'v1',
    "available_models"  jsonb        DEFAULT '[]'::jsonb,
    "default_model"     varchar(200),
    "max_tokens_limit"  jsonb        DEFAULT '{}'::jsonb,
    "request_headers"   jsonb        DEFAULT '{}'::jsonb,
    "request_timeout"   int4         DEFAULT 60,
    "is_active"         bool,
    "sort_order"        int4         DEFAULT 0,
    "extra_config"      jsonb        DEFAULT '{}'::jsonb,
    "created_at"        timestamptz  DEFAULT CURRENT_TIMESTAMP,
    "updated_at"        timestamptz  DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ai_provider_configs_pkey" PRIMARY KEY ("id")
);
CREATE UNIQUE INDEX IF NOT EXISTS "ai_provider_configs_provider_name_key" ON "ai_provider_configs" USING btree ("provider_name");
CREATE INDEX IF NOT EXISTS "idx_ai_provider_configs_created_at"    ON "ai_provider_configs" USING btree ("created_at");
CREATE INDEX IF NOT EXISTS "idx_ai_provider_configs_is_active"     ON "ai_provider_configs" USING btree ("is_active");
CREATE INDEX IF NOT EXISTS "idx_ai_provider_configs_provider_name" ON "ai_provider_configs" USING btree ("provider_name");
CREATE INDEX IF NOT EXISTS "idx_ai_provider_configs_sort_order"    ON "ai_provider_configs" USING btree ("sort_order");
COMMENT ON TABLE "ai_provider_configs" IS 'AI提供商配置表';


-- ---------------------------------------------------------------------
-- 6. ai_model_configs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "ai_model_configs" (
    "id"                       uuid         NOT NULL DEFAULT gen_random_uuid(),
    "name"                     varchar(255) NOT NULL,
    "description"              text,
    "model_name"               varchar(200) NOT NULL,
    "model_type"               "ai_model_type_enum" DEFAULT 'vision'::ai_model_type_enum,
    "system_prompt"            text,
    "user_prompt"              text,
    "temperature"              float4 DEFAULT 0.7,
    "top_p"                    float4 DEFAULT 0.9,
    "max_tokens"               int4   DEFAULT 1000,
    "confidence_threshold"     float4 DEFAULT 0.7,
    "tags"                     text[] DEFAULT '{}'::text[],
    "status"                   "algorithm_status_enum" DEFAULT 'draft'::algorithm_status_enum,
    "test_count"               int4 DEFAULT 0,
    "success_count"            int4 DEFAULT 0,
    "extra_config"             jsonb DEFAULT '{}'::jsonb,
    "created_at"               timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at"               timestamptz DEFAULT CURRENT_TIMESTAMP,
    "prompt_template"          text DEFAULT ''::text,
    "provider"                 varchar(100) NOT NULL,
    "output_format_config"     jsonb,
    "composite_detection"      bool DEFAULT false,
    "detection_capabilities"   jsonb DEFAULT '[]'::jsonb,
    "prompt_template_strategy" varchar(50) DEFAULT 'single',
    CONSTRAINT "ai_model_configs_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_ai_model_configs_composite_detection"    ON "ai_model_configs" USING btree ("composite_detection");
CREATE INDEX IF NOT EXISTS "idx_ai_model_configs_created_at"             ON "ai_model_configs" USING btree ("created_at");
CREATE INDEX IF NOT EXISTS "idx_ai_model_configs_detection_capabilities" ON "ai_model_configs" USING gin   ("detection_capabilities");
CREATE INDEX IF NOT EXISTS "idx_ai_model_configs_model_type"             ON "ai_model_configs" USING btree ("model_type");
CREATE INDEX IF NOT EXISTS "idx_ai_model_configs_status"                 ON "ai_model_configs" USING btree ("status");
CREATE INDEX IF NOT EXISTS "idx_ai_model_configs_tags"                   ON "ai_model_configs" USING gin   ("tags");
CREATE INDEX IF NOT EXISTS "idx_ai_model_configs_updated_at"             ON "ai_model_configs" USING btree ("updated_at");
COMMENT ON TABLE "ai_model_configs" IS 'AI模型配置表';


-- ---------------------------------------------------------------------
-- 7. ai_test_results  (log-type: DDL only)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "ai_test_results" (
    "id"                uuid NOT NULL DEFAULT gen_random_uuid(),
    "config_id"         uuid NOT NULL,
    "input_image_path"  varchar(1000),
    "input_text"        text,
    "ai_response"       text,
    "confidence_score"  float4,
    "processing_time"   float4 NOT NULL,
    "is_success"        bool,
    "error_message"     text,
    "created_at"        timestamptz DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ai_test_results_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_ai_test_results_config_id"  ON "ai_test_results" USING btree ("config_id");
CREATE INDEX IF NOT EXISTS "idx_ai_test_results_created_at" ON "ai_test_results" USING btree ("created_at");
CREATE INDEX IF NOT EXISTS "idx_ai_test_results_is_success" ON "ai_test_results" USING btree ("is_success");
COMMENT ON TABLE "ai_test_results" IS 'AI测试结果表';


-- ---------------------------------------------------------------------
-- 8. ai_analysis_logs  (log-type: DDL only)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "ai_analysis_logs" (
    "id"                   uuid NOT NULL DEFAULT gen_random_uuid(),
    "task_id"              uuid,
    "video_id"             uuid,
    "algorithm_id"         varchar(255),
    "algorithm_config_id"  uuid,
    "call_status"          varchar(20) DEFAULT 'success',
    "api_endpoint"         varchar(500),
    "model_name"           varchar(100),
    "frame_index"          int4,
    "frame_timestamp"      varchar(20),
    "request_data"         jsonb,
    "response_data"        jsonb,
    "response_time_ms"     int4,
    "confidence_score"     varchar(10),
    "error_message"        text,
    "error_code"           varchar(50),
    "call_date"            timestamptz DEFAULT CURRENT_TIMESTAMP,
    "created_at"           timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at"           timestamptz DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ai_analysis_logs_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_ai_analysis_logs_algorithm_id" ON "ai_analysis_logs" USING btree ("algorithm_id");
CREATE INDEX IF NOT EXISTS "idx_ai_analysis_logs_call_date"    ON "ai_analysis_logs" USING btree ("call_date");
CREATE INDEX IF NOT EXISTS "idx_ai_analysis_logs_call_status"  ON "ai_analysis_logs" USING btree ("call_status");
CREATE INDEX IF NOT EXISTS "idx_ai_analysis_logs_task_id"      ON "ai_analysis_logs" USING btree ("task_id");
CREATE INDEX IF NOT EXISTS "idx_ai_analysis_logs_video_id"     ON "ai_analysis_logs" USING btree ("video_id");
COMMENT ON TABLE "ai_analysis_logs" IS 'AI分析调用日志表';


-- ---------------------------------------------------------------------
-- 9. ai_agent_sessions  (log-type: DDL only)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "ai_agent_sessions" (
    "id"              uuid NOT NULL DEFAULT gen_random_uuid(),
    "user_id"         uuid NOT NULL,
    "title"           text,
    "message_count"   int4 NOT NULL DEFAULT 0,
    "last_message_at" timestamptz,
    "created_at"      timestamptz DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ai_agent_sessions_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_ai_agent_sessions_created_at"      ON "ai_agent_sessions" USING btree ("created_at");
CREATE INDEX IF NOT EXISTS "idx_ai_agent_sessions_last_message_at" ON "ai_agent_sessions" USING btree ("last_message_at");
CREATE INDEX IF NOT EXISTS "idx_ai_agent_sessions_user_id"         ON "ai_agent_sessions" USING btree ("user_id");
COMMENT ON TABLE "ai_agent_sessions" IS 'AI Agent对话会话表';


-- ---------------------------------------------------------------------
-- 10. ai_agent_history  (log-type: DDL only)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "ai_agent_history" (
    "id"              uuid NOT NULL DEFAULT gen_random_uuid(),
    "user_id"         uuid NOT NULL,
    "session_id"      uuid NOT NULL,
    "question"        text NOT NULL,
    "intent"          jsonb NOT NULL,
    "data_summary"    jsonb,
    "insights"        text,
    "report_markdown" text,
    "report_html"     text,
    "extra_metadata"  jsonb,
    "created_at"      timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at"      timestamptz DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT "ai_agent_history_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_ai_agent_history_created_at" ON "ai_agent_history" USING btree ("created_at");
CREATE INDEX IF NOT EXISTS "idx_ai_agent_history_intent"     ON "ai_agent_history" USING gin   ("intent");
CREATE INDEX IF NOT EXISTS "idx_ai_agent_history_session_id" ON "ai_agent_history" USING btree ("session_id");
CREATE INDEX IF NOT EXISTS "idx_ai_agent_history_user_id"    ON "ai_agent_history" USING btree ("user_id");
COMMENT ON TABLE "ai_agent_history" IS 'AI Agent对话历史表';


-- ---------------------------------------------------------------------
-- 11. video_files
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "video_files" (
    "id"                 uuid NOT NULL DEFAULT gen_random_uuid(),
    "name"               varchar(255) NOT NULL,
    "original_filename"  varchar(500) NOT NULL,
    "file_path"          varchar(1000) NOT NULL,
    "thumbnail_path"     varchar(1000),
    "file_size"          int8,
    "duration"           float4,
    "fps"                float4,
    "width"              int4,
    "height"             int4,
    "format"             varchar(50),
    "status"             "video_status_enum" DEFAULT 'PENDING'::video_status_enum,
    "tags"               text[] DEFAULT '{}'::text[],
    "description"        text,
    "analysis_progress"  int4 DEFAULT 0,
    "total_alerts"       int4 DEFAULT 0,
    "created_at"         timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at"         timestamptz DEFAULT CURRENT_TIMESTAMP,
    "analyzed_at"        timestamptz,
    "last_alert_at"      timestamptz,
    "deleted_at"         timestamptz,
    CONSTRAINT "video_files_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_video_files_created_at"        ON "video_files" USING btree ("created_at");
CREATE INDEX IF NOT EXISTS "idx_video_files_original_filename" ON "video_files" USING btree ("original_filename");
CREATE INDEX IF NOT EXISTS "idx_video_files_status"            ON "video_files" USING btree ("status");
CREATE INDEX IF NOT EXISTS "idx_video_files_tags"              ON "video_files" USING gin   ("tags");
COMMENT ON TABLE "video_files" IS '视频文件表';


-- ---------------------------------------------------------------------
-- 12. video_analysis_templates
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "video_analysis_templates" (
    "id"                  uuid NOT NULL DEFAULT gen_random_uuid(),
    "name"                varchar(255) NOT NULL,
    "category"            varchar(100) NOT NULL,
    "description"         text,
    "prompt_content"      text NOT NULL,
    "is_enabled"          bool,
    "created_at"          timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at"          timestamptz DEFAULT CURRENT_TIMESTAMP,
    "video_id"            uuid,
    "template_id"         uuid,
    "template_name"       varchar(255),
    "priority"            int4 DEFAULT 0,
    "enabled"             bool DEFAULT true,
    "analysis_status"     varchar(50) DEFAULT 'not_started',
    "progress"            int4 DEFAULT 0,
    "alerts_count"        int4 DEFAULT 0,
    "confidence_avg"      float4 DEFAULT 0.0,
    "analysis_duration"   int4,
    "error_message"       text,
    "started_at"          timestamptz,
    "completed_at"        timestamptz,
    "detection_type_code" varchar(50),
    CONSTRAINT "video_analysis_templates_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_video_analysis_templates_detection_type" ON "video_analysis_templates" USING btree ("detection_type_code");
COMMENT ON TABLE "video_analysis_templates" IS 'AI分析模板表';


-- ---------------------------------------------------------------------
-- 13. video_analysis_results
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "video_analysis_results" (
    "id"               uuid NOT NULL DEFAULT gen_random_uuid(),
    "video_file_id"    uuid NOT NULL,
    "template_id"      uuid NOT NULL,
    "status"           "analysis_status_enum" DEFAULT 'not_started'::analysis_status_enum,
    "analysis_result"  text,
    "confidence_score" float4,
    "processing_time"  int4,
    "created_at"       timestamptz DEFAULT CURRENT_TIMESTAMP,
    "completed_at"     timestamptz,
    CONSTRAINT "video_analysis_results_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_analysis_results_status"      ON "video_analysis_results" USING btree ("status");
CREATE INDEX IF NOT EXISTS "idx_analysis_results_template_id" ON "video_analysis_results" USING btree ("template_id");
CREATE INDEX IF NOT EXISTS "idx_analysis_results_video_id"    ON "video_analysis_results" USING btree ("video_file_id");
COMMENT ON TABLE "video_analysis_results" IS '视频分析结果表';


-- ---------------------------------------------------------------------
-- 14. stream_analysis_tasks
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "stream_analysis_tasks" (
    "id"                     uuid NOT NULL DEFAULT gen_random_uuid(),
    "stream_id"              uuid NOT NULL,
    "algorithm_config_id"    uuid NOT NULL,
    "task_name"              varchar(255) NOT NULL,
    "status"                 varchar(20) NOT NULL DEFAULT 'enabled',
    "is_active"              bool NOT NULL DEFAULT true,
    "auto_recover"           bool NOT NULL DEFAULT true,
    "time_config"            jsonb NOT NULL DEFAULT '{}'::jsonb,
    "roi_config"             jsonb DEFAULT '{}'::jsonb,
    "priority"               int4 NOT NULL DEFAULT 1,
    "confidence_threshold"   float8 NOT NULL DEFAULT 0.7,
    "analysis_interval"      int4 NOT NULL DEFAULT 10,
    "last_run_at"            timestamptz,
    "next_run_at"            timestamptz,
    "run_count"              int4 NOT NULL DEFAULT 0,
    "error_count"            int4 NOT NULL DEFAULT 0,
    "last_error_message"     text,
    "total_frames_processed" int4 NOT NULL DEFAULT 0,
    "total_alerts_generated" int4 NOT NULL DEFAULT 0,
    "avg_processing_time"    float8 DEFAULT 0,
    "created_at"             timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at"             timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "created_by"             uuid,
    "updated_by"             uuid,
    CONSTRAINT "stream_analysis_tasks_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "chk_confidence_threshold" CHECK (confidence_threshold >= 0::float8 AND confidence_threshold <= 1::float8),
    CONSTRAINT "chk_priority"             CHECK (priority >= 1 AND priority <= 10),
    CONSTRAINT "chk_status"                CHECK (status::text = ANY (ARRAY['enabled'::varchar::text, 'disabled'::varchar::text, 'running'::varchar::text, 'error'::varchar::text, 'scheduled'::varchar::text]))
);
CREATE INDEX IF NOT EXISTS "idx_stream_analysis_tasks_active"       ON "stream_analysis_tasks" USING btree ("is_active");
CREATE INDEX IF NOT EXISTS "idx_stream_analysis_tasks_auto_recover" ON "stream_analysis_tasks" USING btree ("auto_recover");
CREATE INDEX IF NOT EXISTS "idx_stream_analysis_tasks_next_run"     ON "stream_analysis_tasks" USING btree ("next_run_at");
CREATE INDEX IF NOT EXISTS "idx_stream_analysis_tasks_status"       ON "stream_analysis_tasks" USING btree ("status");
CREATE INDEX IF NOT EXISTS "idx_stream_analysis_tasks_stream_id"    ON "stream_analysis_tasks" USING btree ("stream_id");
COMMENT ON TABLE "stream_analysis_tasks" IS '视频流实时分析任务表';


-- ---------------------------------------------------------------------
-- 15. stream_analysis_templates
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "stream_analysis_templates" (
    "id"                   uuid NOT NULL DEFAULT gen_random_uuid(),
    "stream_id"            uuid NOT NULL,
    "template_id"          varchar(100) NOT NULL,
    "template_name"        varchar(255) NOT NULL,
    "priority"             int4 DEFAULT 1,
    "enabled"              bool,
    "confidence_threshold" float4 DEFAULT 0.7,
    "analysis_status"      "stream_analysis_status_enum" DEFAULT 'NOT_STARTED'::stream_analysis_status_enum,
    "alerts_count"         int4 DEFAULT 0,
    "detection_count"      int4 DEFAULT 0,
    "confidence_avg"       float4,
    "created_at"           timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at"           timestamptz DEFAULT CURRENT_TIMESTAMP,
    "last_detection_at"    timestamptz,
    "error_message"        text,
    CONSTRAINT "stream_analysis_templates_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_stream_templates_enabled"   ON "stream_analysis_templates" USING btree ("enabled");
CREATE INDEX IF NOT EXISTS "idx_stream_templates_priority"  ON "stream_analysis_templates" USING btree ("priority");
CREATE INDEX IF NOT EXISTS "idx_stream_templates_stream_id" ON "stream_analysis_templates" USING btree ("stream_id");
CREATE UNIQUE INDEX IF NOT EXISTS "stream_analysis_templates_stream_id_template_id_key"
    ON "stream_analysis_templates" USING btree ("stream_id", "template_id");
COMMENT ON TABLE "stream_analysis_templates" IS '流分析模板表';


-- ---------------------------------------------------------------------
-- 16. video_stream_algorithm_configs
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "video_stream_algorithm_configs" (
    "id"                    uuid NOT NULL DEFAULT gen_random_uuid(),
    "stream_id"             uuid NOT NULL,
    "template_id"           varchar(255) NOT NULL,
    "template_name"         varchar(255),
    "priority"              int4 DEFAULT 1,
    "confidence_threshold"  float4 DEFAULT 0.7,
    "is_active"             bool DEFAULT true,
    "created_at"            timestamptz DEFAULT CURRENT_TIMESTAMP,
    "updated_at"            timestamptz DEFAULT CURRENT_TIMESTAMP,
    "created_by"            varchar(255),
    "detection_type_codes"  jsonb DEFAULT '[]'::jsonb,
    CONSTRAINT "video_stream_algorithm_configs_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "uk_stream_algorithm_config" UNIQUE ("stream_id", "template_id")
);
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_configs_created_at"            ON "video_stream_algorithm_configs" USING btree ("created_at");
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_configs_detection_type_codes"  ON "video_stream_algorithm_configs" USING gin   ("detection_type_codes");
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_configs_is_active"             ON "video_stream_algorithm_configs" USING btree ("is_active");
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_configs_stream_id"             ON "video_stream_algorithm_configs" USING btree ("stream_id");
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_configs_template_id"           ON "video_stream_algorithm_configs" USING btree ("template_id");
COMMENT ON TABLE "video_stream_algorithm_configs" IS '视频流算法配置表';


-- ---------------------------------------------------------------------
-- 17. video_stream_algorithm_config_history  (log-type: DDL only)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "video_stream_algorithm_config_history" (
    "id"                   uuid NOT NULL DEFAULT gen_random_uuid(),
    "config_id"            uuid NOT NULL,
    "stream_id"            uuid NOT NULL,
    "template_id"          varchar(255) NOT NULL,
    "template_name"        varchar(255),
    "priority"             int4,
    "confidence_threshold" float4,
    "is_active"            bool,
    "operation"            varchar(20) NOT NULL,
    "operation_at"         timestamptz DEFAULT CURRENT_TIMESTAMP,
    "operated_by"          varchar(255),
    "old_values"           jsonb,
    "new_values"           jsonb,
    CONSTRAINT "video_stream_algorithm_config_history_pkey" PRIMARY KEY ("id")
);
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_config_history_config_id"    ON "video_stream_algorithm_config_history" USING btree ("config_id");
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_config_history_operation_at" ON "video_stream_algorithm_config_history" USING btree ("operation_at");
CREATE INDEX IF NOT EXISTS "idx_video_stream_algorithm_config_history_stream_id"    ON "video_stream_algorithm_config_history" USING btree ("stream_id");
COMMENT ON TABLE "video_stream_algorithm_config_history" IS '视频流算法配置历史表';


-- ---------------------------------------------------------------------
-- 18. Foreign keys (idempotent)
-- ---------------------------------------------------------------------
DO $$ BEGIN
    ALTER TABLE "ai_agent_history"
        ADD CONSTRAINT "fk_ai_agent_history_user_id"
        FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN undefined_table THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE "ai_agent_sessions"
        ADD CONSTRAINT "fk_ai_agent_sessions_user_id"
        FOREIGN KEY ("user_id") REFERENCES "users" ("id") ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN undefined_table THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE "video_analysis_templates"
        ADD CONSTRAINT "fk_video_analysis_templates_detection_type"
        FOREIGN KEY ("detection_type_code") REFERENCES "detection_type_templates" ("type_code") ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN undefined_table THEN NULL; END $$;

DO $$ BEGIN
    ALTER TABLE "video_stream_algorithm_configs"
        ADD CONSTRAINT "fk_stream_algorithm_configs_stream_id"
        FOREIGN KEY ("stream_id") REFERENCES "video_streams" ("id") ON DELETE CASCADE;
EXCEPTION WHEN duplicate_object THEN NULL; WHEN undefined_table THEN NULL; END $$;


-- ---------------------------------------------------------------------
-- 19. Record migration
-- ---------------------------------------------------------------------
INSERT INTO "schema_migrations" ("version", "description")
VALUES ('002_restore_missing_tables', '从 public.sql 恢复 16 张缺失表（仅结构，日志表不含数据）')
ON CONFLICT ("version") DO NOTHING;

COMMIT;
