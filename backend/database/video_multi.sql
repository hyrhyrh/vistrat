/*
 Navicat Premium Dump SQL

 Source Server         : 工控机
 Source Server Type    : PostgreSQL
 Source Server Version : 160011 (160011)
 Source Host           : localhost:5432
 Source Catalog        : video_multi
 Source Schema         : public

 Target Server Type    : PostgreSQL
 Target Server Version : 160011 (160011)
 File Encoding         : 65001

 Date: 24/11/2025 15:01:08
*/


-- ----------------------------
-- Type structure for ai_model_type_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."ai_model_type_enum";
CREATE TYPE "public"."ai_model_type_enum" AS ENUM (
  'vision',
  'text',
  'multimodal'
);

-- ----------------------------
-- Type structure for ai_provider_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."ai_provider_enum";
CREATE TYPE "public"."ai_provider_enum" AS ENUM (
  'qwen',
  'moonshot',
  'gpt',
  'claude',
  'gemini',
  'baidu'
);

-- ----------------------------
-- Type structure for algorithm_status_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."algorithm_status_enum";
CREATE TYPE "public"."algorithm_status_enum" AS ENUM (
  'draft',
  'testing',
  'active',
  'deprecated'
);

-- ----------------------------
-- Type structure for analysis_status_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."analysis_status_enum";
CREATE TYPE "public"."analysis_status_enum" AS ENUM (
  'not_started',
  'queued',
  'processing',
  'completed',
  'failed',
  'cancelled'
);

-- ----------------------------
-- Type structure for stream_analysis_status_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."stream_analysis_status_enum";
CREATE TYPE "public"."stream_analysis_status_enum" AS ENUM (
  'NOT_STARTED',
  'RUNNING',
  'PAUSED',
  'STOPPED',
  'ERROR'
);

-- ----------------------------
-- Type structure for stream_status_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."stream_status_enum";
CREATE TYPE "public"."stream_status_enum" AS ENUM (
  'OFFLINE',
  'ONLINE',
  'CONNECTING',
  'ERROR',
  'MAINTENANCE'
);

-- ----------------------------
-- Type structure for stream_type_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."stream_type_enum";
CREATE TYPE "public"."stream_type_enum" AS ENUM (
  'RTSP',
  'RTMP',
  'HLS',
  'WEBRTC',
  'HTTP_FLV',
  'LOCAL_CAMERA'
);

-- ----------------------------
-- Type structure for user_role_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."user_role_enum";
CREATE TYPE "public"."user_role_enum" AS ENUM (
  'admin',
  'user',
  'viewer'
);

-- ----------------------------
-- Type structure for video_status_enum
-- ----------------------------
DROP TYPE IF EXISTS "public"."video_status_enum";
CREATE TYPE "public"."video_status_enum" AS ENUM (
  'PENDING',
  'UPLOADING',
  'READY',
  'ANALYZING',
  'COMPLETED',
  'ERROR',
  'DELETED'
);

-- ----------------------------
-- Table structure for ai_agent_history
-- ----------------------------
DROP TABLE IF EXISTS "public"."ai_agent_history";
CREATE TABLE "public"."ai_agent_history" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "session_id" uuid NOT NULL,
  "question" text COLLATE "pg_catalog"."default" NOT NULL,
  "intent" jsonb NOT NULL,
  "data_summary" jsonb,
  "insights" text COLLATE "pg_catalog"."default",
  "report_markdown" text COLLATE "pg_catalog"."default",
  "report_html" text COLLATE "pg_catalog"."default",
  "extra_metadata" jsonb,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON COLUMN "public"."ai_agent_history"."user_id" IS '用户ID，关联users表';
COMMENT ON COLUMN "public"."ai_agent_history"."session_id" IS '对话会话ID，相同session_id表示同一次对话';
COMMENT ON COLUMN "public"."ai_agent_history"."question" IS '用户提出的问题';
COMMENT ON COLUMN "public"."ai_agent_history"."intent" IS '意图分析结果JSON：包含time_window, entities, metrics等';
COMMENT ON COLUMN "public"."ai_agent_history"."data_summary" IS '数据摘要JSON：包含total_count, took_ms等统计信息';
COMMENT ON COLUMN "public"."ai_agent_history"."insights" IS 'AI分析结果Markdown格式文本';
COMMENT ON COLUMN "public"."ai_agent_history"."report_markdown" IS '完整Markdown格式报告';
COMMENT ON COLUMN "public"."ai_agent_history"."report_html" IS '完整HTML格式报告';
COMMENT ON COLUMN "public"."ai_agent_history"."extra_metadata" IS '元数据JSON：包含timestamp, query_time_ms, data_count等';
COMMENT ON TABLE "public"."ai_agent_history" IS 'AI Agent对话历史表：保存所有AI分析对话记录';

-- ----------------------------
-- Records of ai_agent_history
-- ----------------------------

-- ----------------------------
-- Table structure for ai_agent_sessions
-- ----------------------------
DROP TABLE IF EXISTS "public"."ai_agent_sessions";
CREATE TABLE "public"."ai_agent_sessions" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "user_id" uuid NOT NULL,
  "title" text COLLATE "pg_catalog"."default",
  "message_count" int4 NOT NULL DEFAULT 0,
  "last_message_at" timestamptz(6),
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON COLUMN "public"."ai_agent_sessions"."title" IS '会话标题，通常由首个问题生成';
COMMENT ON COLUMN "public"."ai_agent_sessions"."message_count" IS '会话中的消息数量';
COMMENT ON COLUMN "public"."ai_agent_sessions"."last_message_at" IS '最后一条消息的时间';
COMMENT ON TABLE "public"."ai_agent_sessions" IS 'AI Agent对话会话表：管理用户的对话会话';

-- ----------------------------
-- Records of ai_agent_sessions
-- ----------------------------

-- ----------------------------
-- Table structure for ai_analysis_logs
-- ----------------------------
DROP TABLE IF EXISTS "public"."ai_analysis_logs";
CREATE TABLE "public"."ai_analysis_logs" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "task_id" uuid,
  "video_id" uuid,
  "algorithm_id" varchar(255) COLLATE "pg_catalog"."default",
  "algorithm_config_id" uuid,
  "call_status" varchar(20) COLLATE "pg_catalog"."default" DEFAULT 'success'::character varying,
  "api_endpoint" varchar(500) COLLATE "pg_catalog"."default",
  "model_name" varchar(100) COLLATE "pg_catalog"."default",
  "frame_index" int4,
  "frame_timestamp" varchar(20) COLLATE "pg_catalog"."default",
  "request_data" jsonb,
  "response_data" jsonb,
  "response_time_ms" int4,
  "confidence_score" varchar(10) COLLATE "pg_catalog"."default",
  "error_message" text COLLATE "pg_catalog"."default",
  "error_code" varchar(50) COLLATE "pg_catalog"."default",
  "call_date" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON TABLE "public"."ai_analysis_logs" IS 'AI分析调用日志表：记录所有AI API调用的详细日志和性能数据';

-- ----------------------------
-- Records of ai_analysis_logs
-- ----------------------------

-- ----------------------------
-- Table structure for ai_model_configs
-- ----------------------------
DROP TABLE IF EXISTS "public"."ai_model_configs";
CREATE TABLE "public"."ai_model_configs" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "model_name" varchar(200) COLLATE "pg_catalog"."default" NOT NULL,
  "model_type" "public"."ai_model_type_enum" DEFAULT 'vision'::ai_model_type_enum,
  "system_prompt" text COLLATE "pg_catalog"."default",
  "user_prompt" text COLLATE "pg_catalog"."default",
  "temperature" float4 DEFAULT 0.7,
  "top_p" float4 DEFAULT 0.9,
  "max_tokens" int4 DEFAULT 1000,
  "confidence_threshold" float4 DEFAULT 0.7,
  "tags" text[] COLLATE "pg_catalog"."default" DEFAULT '{}'::text[],
  "status" "public"."algorithm_status_enum" DEFAULT 'draft'::algorithm_status_enum,
  "test_count" int4 DEFAULT 0,
  "success_count" int4 DEFAULT 0,
  "extra_config" jsonb DEFAULT '{}'::jsonb,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "prompt_template" text COLLATE "pg_catalog"."default" DEFAULT ''::text,
  "provider" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "output_format_config" jsonb,
  "composite_detection" bool DEFAULT false,
  "detection_capabilities" jsonb DEFAULT '[]'::jsonb,
  "prompt_template_strategy" varchar(50) COLLATE "pg_catalog"."default" DEFAULT 'single'::character varying
)
;
COMMENT ON COLUMN "public"."ai_model_configs"."provider" IS 'AI模型供应商名称(引用ai_provider_configs.provider_name)';
COMMENT ON COLUMN "public"."ai_model_configs"."composite_detection" IS '是否为复合检测算法(可同时检测多种违规类型)';
COMMENT ON COLUMN "public"."ai_model_configs"."detection_capabilities" IS '支持的检测能力列表，JSONB数组格式，存储该算法能够检测的违规类型编码。
示例: ["safety_helmet", "smoking", "using_phone", "climbing", "intrusion"]
用途: 定义算法的能力边界，在视频流配置时供用户选择';
COMMENT ON COLUMN "public"."ai_model_configs"."prompt_template_strategy" IS '提示词策略: single(单违规)、composite(复合检测)';
COMMENT ON TABLE "public"."ai_model_configs" IS 'AI模型配置表：管理各AI模型的参数、提示词和性能统计';

-- ----------------------------
-- Records of ai_model_configs
-- ----------------------------
INSERT INTO "public"."ai_model_configs" VALUES ('5ffdc79a-f8cc-4f10-ba8d-0db561c1d611', '测试配置_092712', '复合检测测试配置 - safety_helmet, reflective_vest, smoking', 'lanyi-qwen2.5-vl-72b-instruct', 'vision', '', '', 0.1, 0.1, 1000, 0.6, '{}', 'draft', 0, 0, '{}', '2025-11-09 01:27:12.277266+00', '2025-11-09 01:27:12.277266+00', '', 'lanyi', NULL, 'f', '["safety_helmet", "reflective_vest", "smoking"]', 'single');
INSERT INTO "public"."ai_model_configs" VALUES ('35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', '违规行为分析', 'lanyi-qwen2.5-vl-72b-instruct', 'vision', NULL, NULL, 0.1, 0.1, 1000, 0.6, '{}', 'active', 1016, 903, '{}', '2025-11-09 01:42:25.000038+00', '2025-11-21 01:33:43.794878+00', '', 'lanyi', NULL, 'f', '["safety_helmet", "reflective_vest", "smoking"]', 'single');
INSERT INTO "public"."ai_model_configs" VALUES ('7e3a256c-4bfb-4f20-9b91-581ae9d1202c', '烟雾检测', '烟雾测试', 'qwen3-vl-4b', 'vision', NULL, NULL, 0.1, 0.1, 200, 0.6, '{烟雾}', 'active', 0, 0, '{}', '2025-11-21 06:38:08.691374+00', '2025-11-24 02:12:50.5109+00', '', 'vllm-local', NULL, 'f', '["fire_smoke"]', 'single');
INSERT INTO "public"."ai_model_configs" VALUES ('69cdb856-fc7b-4146-b0ff-ff0019e28b90', 'Qwen3-VL-4B本地部署', '基于本地GPU部署的Qwen3-VL-4B多模态视觉模型，适用于视频监控场景的违规行为检测', 'qwen3-vl-4b', 'multimodal', '你是一个专业的视频监控AI助手，负责分析监控画面中的行为和场景，识别潜在的安全隐患和违规行为。', NULL, 0.3, 0.8, 200, 0.75, '{本地部署,GPU加速,多模态,视频分析,安全监控}', 'active', 39, 12, '{"batch_size": 4, "gpu_accelerated": true, "local_deployment": true, "max_concurrent_requests": 10}', '2025-11-21 00:55:32.452267+00', '2025-11-24 06:00:11.564089+00', '', 'vllm-local', NULL, 't', '["safety_helmet", "smoking", "using_phone", "climbing", "intrusion", "fire", "crowd", "vehicle"]', 'composite');

-- ----------------------------
-- Table structure for ai_provider_configs
-- ----------------------------
DROP TABLE IF EXISTS "public"."ai_provider_configs";
CREATE TABLE "public"."ai_provider_configs" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "provider_name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "display_name" varchar(200) COLLATE "pg_catalog"."default" NOT NULL,
  "icon" varchar(50) COLLATE "pg_catalog"."default" DEFAULT '🤖'::character varying,
  "description" text COLLATE "pg_catalog"."default",
  "api_base_url" varchar(500) COLLATE "pg_catalog"."default" NOT NULL,
  "api_key" varchar(500) COLLATE "pg_catalog"."default",
  "api_version" varchar(50) COLLATE "pg_catalog"."default" DEFAULT 'v1'::character varying,
  "available_models" jsonb DEFAULT '[]'::jsonb,
  "default_model" varchar(200) COLLATE "pg_catalog"."default",
  "max_tokens_limit" jsonb DEFAULT '{}'::jsonb,
  "request_headers" jsonb DEFAULT '{}'::jsonb,
  "request_timeout" int4 DEFAULT 60,
  "is_active" bool,
  "sort_order" int4 DEFAULT 0,
  "extra_config" jsonb DEFAULT '{}'::jsonb,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON TABLE "public"."ai_provider_configs" IS 'AI提供商配置表：管理各大AI服务商的API配置和连接信息';

-- ----------------------------
-- Records of ai_provider_configs
-- ----------------------------
INSERT INTO "public"."ai_provider_configs" VALUES ('b7102feb-646c-4425-91c6-a62fe2f5bc6a', 'moonshot', 'Moonshot', '🌙', 'Moonshot AI大模型，专注于长上下文理解', 'https://api.moonshot.cn/v1/chat/completions', 'sk-xxxxxxxxxxxxxxxxxxxx', 'v1', '["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]', 'moonshot-v1-8k', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 60, 't', 2, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO "public"."ai_provider_configs" VALUES ('68071e9f-9274-4a26-82db-89104a6dcb3a', 'gpt', 'OpenAI GPT', '🤖', 'OpenAI GPT系列模型，支持文本和视觉理解', 'https://api.openai.com/v1/chat/completions', '', 'v1', '["gpt-4-vision-preview", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]', 'gpt-4-vision-preview', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 60, 'f', 3, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO "public"."ai_provider_configs" VALUES ('a196fa76-189e-4e17-8a73-9a27e45ab917', 'claude', 'Claude', '🎭', 'Anthropic Claude大模型，擅长理解和推理', 'https://api.anthropic.com/v1/messages', '', 'v1', '["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]', 'claude-3-sonnet', '{}', '{"x-api-key": "{api_key}", "Content-Type": "application/json", "anthropic-version": "2023-06-01"}', 60, 'f', 4, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO "public"."ai_provider_configs" VALUES ('6e1823ec-e19d-4e86-ae44-c09d08aaba4f', 'gemini', 'Google Gemini', '💎', 'Google Gemini多模态大模型', 'https://generativelanguage.googleapis.com/v1/models', '', 'v1', '["gemini-1.5-pro", "gemini-1.0-pro-vision", "gemini-1.0-pro"]', 'gemini-1.5-pro', '{}', '{"Content-Type": "application/json"}', 60, 'f', 5, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO "public"."ai_provider_configs" VALUES ('b2a59c44-997f-4d42-9b87-ad31439fa4df', 'baidu', '百度文心', '🐻', '百度文心一言大模型', 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat', '', 'v1', '["ernie-4.0-turbo", "ernie-3.5-turbo", "ernie-bot-4"]', 'ernie-4.0-turbo', '{}', '{"Content-Type": "application/json"}', 60, 'f', 6, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO "public"."ai_provider_configs" VALUES ('5de3f7bc-0053-4f65-9cd2-487f1db3f3c6', 'qwen', '通义千问(测试)', '🟡', '阿里云通义千问大模型，支持文本和视觉理解', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', 'sk-xxxxxxxxxxxxxxxxxxxx', 'v1', '["qwen-vl-plus", "qwen-vl-max", "qwen-turbo", "qwen-plus", "qwen-max"]', 'qwen-vl-plus', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 90, 't', 1, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 07:10:43.639778+00');
INSERT INTO "public"."ai_provider_configs" VALUES ('45029a8c-4b14-4bc2-92fe-948b03a577e4', 'lanyi', 'lanyi', '🤖', NULL, 'https://llm.example.com/api/compatible/v1/chat/completions', 'sk-xxxxxxxxxxxxxxxxxxxx', 'v1', '["lanyi-qwen2.5-vl-72b-instruct", "lanyi-step3", "qwen-vl-plus", "lanyi-instruct"]', 'qwen-vl-plus', '{}', '{"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3", "Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 60, 't', 0, '{}', '2025-09-22 01:32:55.437958+00', '2025-10-19 02:44:30.013255+00');
INSERT INTO "public"."ai_provider_configs" VALUES ('a5bc2499-8cfb-46cc-a473-5ec877d82072', 'vllm-local', 'vLLM本地部署', '🚀', '本地GPU部署的Qwen2.5-VL-7B多模态视觉模型，支持图像理解和分析', 'http://vllm:8000/v1/chat/completions', 'sk-xxxxxxxxxxxxxxxxxxxx', 'v1', '["qwen3-vl-4b"]', 'qwen3-vl-4b', '{"qwen3-vl-4b": 2048}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 120, 't', -1, '{"gpu_accelerated": true, "local_deployment": true, "max_images_per_request": 3}', '2025-11-21 00:46:58.333714+00', '2025-11-21 00:46:58.333714+00');

-- ----------------------------
-- Table structure for ai_test_results
-- ----------------------------
DROP TABLE IF EXISTS "public"."ai_test_results";
CREATE TABLE "public"."ai_test_results" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "config_id" uuid NOT NULL,
  "input_image_path" varchar(1000) COLLATE "pg_catalog"."default",
  "input_text" text COLLATE "pg_catalog"."default",
  "ai_response" text COLLATE "pg_catalog"."default",
  "confidence_score" float4,
  "processing_time" float4 NOT NULL,
  "is_success" bool,
  "error_message" text COLLATE "pg_catalog"."default",
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON TABLE "public"."ai_test_results" IS 'AI测试结果表：存储模型性能测试和评估的结果数据';

-- ----------------------------
-- Records of ai_test_results
-- ----------------------------
INSERT INTO "public"."ai_test_results" VALUES ('fc712ad3-3927-40c3-9b71-cf8f3c19f8f3', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', NULL, '请分析图片中的安全隐患', '', NULL, 20.26793, 'f', 'API请求失败 (400): 抱歉，您的问题中可能涉及敏感或风险信息', '2025-10-19 02:40:01.908692+00');

-- ----------------------------
-- Table structure for detection_type_templates
-- ----------------------------
DROP TABLE IF EXISTS "public"."detection_type_templates";
CREATE TABLE "public"."detection_type_templates" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "type_code" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "display_name" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "category" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "prompt_template" text COLLATE "pg_catalog"."default" NOT NULL,
  "json_field_name" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "severity" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'medium'::character varying,
  "sort_order" int4 NOT NULL DEFAULT 0,
  "enabled" bool NOT NULL DEFAULT true,
  "description" text COLLATE "pg_catalog"."default",
  "example_scenarios" text COLLATE "pg_catalog"."default",
  "usage_count" int4 DEFAULT 0,
  "detection_count" int4 DEFAULT 0,
  "avg_confidence" float4 DEFAULT 0.0,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON COLUMN "public"."detection_type_templates"."type_code" IS '类型编码(唯一)，如: safety_helmet, smoking';
COMMENT ON COLUMN "public"."detection_type_templates"."display_name" IS '显示名称，如: 安全帽检测, 吸烟行为检测';
COMMENT ON COLUMN "public"."detection_type_templates"."category" IS '类别: safety(安全), behavior(行为), environment(环境)';
COMMENT ON COLUMN "public"."detection_type_templates"."prompt_template" IS '提示词模板内容，用于动态组装复合提示词';
COMMENT ON COLUMN "public"."detection_type_templates"."json_field_name" IS 'AI响应JSON中的字段名，用于解析响应';
COMMENT ON COLUMN "public"."detection_type_templates"."severity" IS '违规严重程度: low(低), medium(中), high(高)';
COMMENT ON COLUMN "public"."detection_type_templates"."sort_order" IS '在复合提示词中的排序顺序，数字越小越靠前';
COMMENT ON TABLE "public"."detection_type_templates" IS '检测类型模板表：预定义的AI检测类型和提示词模板，用于复合检测';

-- ----------------------------
-- Records of detection_type_templates
-- ----------------------------
INSERT INTO "public"."detection_type_templates" VALUES ('6ba6c92c-1177-4861-a2c8-433a32bdd253', 'safety_helmet', '未佩戴安全帽', 'safety', '请仔细观察画面中的所有人员，判断是否有人员未佩戴安全帽。安全帽通常为黄色、白色、蓝色、红色等醒目颜色，佩戴在头部。如果发现有工作人员未佩戴安全帽或佩戴不规范（如未扣紧、歪戴等），请在结论中说明人数和位置。', 'safety_helmet', 'high', 1, 't', '检测施工现场、生产车间等区域人员是否正确佩戴安全帽', '建筑工地、工厂车间、电力设施、矿山作业等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('a6008302-659e-4739-a71a-c2f86512c2fe', 'reflective_vest', '未穿反光衣', 'safety', '请观察画面中的工作人员是否穿着反光衣（也称反光背心）。反光衣通常为荧光黄色、橙色或绿色，带有反光条纹。检查所有应该穿着反光衣的人员（如道路施工、夜间作业、交通指挥等场景）是否正确穿着。', 'reflective_vest', 'high', 2, 't', '检测道路施工、夜间作业等场景人员是否穿着反光衣', '道路施工、机场停机坪、夜间施工、交通指挥等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('3829d22f-08a8-4c9c-9b61-76d55d0b9f1e', 'smoking', '吸烟行为', 'behavior', '请检测画面中是否有人员正在吸烟。重点观察人员的手部动作（手持烟卷）、嘴部（叼着香烟）以及是否有烟雾。禁烟区域包括：加油站、化工厂、仓库、生产车间等易燃易爆场所。', 'smoking', 'high', 3, 't', '检测禁烟区域的吸烟行为，预防火灾和安全事故', '加油站、化工厂、仓库、公共场所禁烟区等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('1d1e6938-0b44-47d2-a213-ba9509a2cd14', 'work_uniform', '未穿工装', 'safety', '请检查画面中的工作人员是否穿着规定的工作服装。工作服通常有统一的颜色和款式，可能带有公司标识。重点关注生产区域、作业区域的人员着装是否符合规范。', 'work_uniform', 'medium', 4, 't', '检测生产区域人员是否按规定穿着工作服', '生产车间、实验室、食品加工厂、洁净室等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('155cb72a-3d44-4667-827b-d53d7dc33550', 'safety_harness', '高处作业未系安全带', 'safety', '请观察画面中是否有人员在高处作业（如脚手架、梯子、高空平台等）。如果存在高处作业人员，请检查其是否系挂安全带。安全带通常为带有金属扣的背带式装置，需要系在身上并挂在固定点上。', 'safety_harness', 'high', 5, 't', '检测高处作业人员是否系挂安全带，防止坠落事故', '高空作业、脚手架施工、塔吊作业、幕墙清洁等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('bc974902-f551-4a8f-ae43-1febc09e9939', 'climbing', '攀爬危险高处', 'behavior', '请检测画面中是否有人员正在攀爬高处，如爬墙、翻越护栏、攀爬设备等危险行为。重点观察人员是否在非正常通道或未设安全防护的区域进行攀爬。', 'climbing', 'high', 6, 't', '检测非法攀爬行为，防止坠落和意外事故', '施工现场、仓库货架、围墙翻越、设备攀爬等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('d89ded6a-53e0-4303-a96b-9f9382e48452', 'phone_usage', '工作时玩手机', 'behavior', '请观察画面中的人员是否在工作时间玩手机。重点关注人员是否低头看手机、手持手机操作、或者将手机放在耳边通话。特别关注驾驶、操作设备、流水线作业等需要专注的场景。', 'phone_usage', 'medium', 7, 't', '检测工作时间玩手机行为，防止注意力分散导致事故', '驾驶操作、设备操作、流水线作业、值班岗位等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('95a479d9-e04f-4b83-9346-46dc833999ed', 'sleeping_on_duty', '睡岗或趴桌', 'behavior', '请检测画面中的值班人员是否存在睡岗行为。观察人员是否趴在桌面上、头部低垂、身体姿态异常放松等睡眠特征。重点关注安保岗位、监控室、值班室等需要保持警觉的岗位。', 'sleeping_on_duty', 'high', 8, 't', '检测值班岗位人员睡岗行为，确保岗位值守', '安保岗位、监控室、门卫室、生产值班室等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('7ad174f2-4207-494a-bcd5-8b63d7c90f8f', 'absence_from_post', '离岗脱岗', 'behavior', '请检测画面中的工作岗位是否有人员在岗。观察监控画面中是否长时间无人出现，或者应该有人值守的岗位（如安保岗亭、监控室、收费站等）处于无人状态。', 'absence_from_post', 'high', 9, 't', '检测重要岗位的人员离岗情况，确保岗位值守', '安保岗位、收费站、监控室、门卫室等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('9a92f7aa-d2d8-4f9e-aac3-2cfc007973f9', 'intrusion', '非法入侵', 'security', '请检测画面中是否有人员非法进入禁止区域。重点观察围栏、警戒线、禁入标识等边界区域，判断是否有人员未经授权进入。关注人员的行为是否鬼祟、是否携带异常物品等。', 'intrusion', 'high', 10, 't', '检测非法入侵行为，保护重要区域安全', '仓库禁区、变电站、危险品存储区、军事设施等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('7c1e98fd-9ff8-4046-8079-ffc8ad8e058b', 'fire_smoke', '火灾烟雾', 'environment', '请仔细观察画面中是否存在火焰、烟雾或异常的光亮。火焰通常呈现橙红色或黄色，烟雾表现为灰色或黑色的雾状物。重点关注是否有明火、冒烟、或者异常的高温光晕。', 'fire_smoke', 'high', 11, 't', '检测火灾烟雾，实现早期火灾预警', '仓库、生产车间、森林、建筑物等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');
INSERT INTO "public"."detection_type_templates" VALUES ('ba860a61-be6a-43b2-a43e-24bb41468bc6', 'water_accumulation', '地面积水', 'environment', '请观察画面中的地面是否存在积水。积水通常表现为地面有反光、水面波纹、或者明显的水渍。重点关注通道、作业区域、电气设备附近等不应有积水的地方。', 'water_accumulation', 'medium', 12, 't', '检测地面积水情况，防止滑倒和电气事故', '生产车间、通道走廊、配电室、地下室等场景', 0, 0, 0, '2025-10-28 13:27:52.924203+00', '2025-10-28 13:27:52.924203+00');

-- ----------------------------
-- Table structure for schema_migrations
-- ----------------------------
DROP TABLE IF EXISTS "public"."schema_migrations";
CREATE TABLE "public"."schema_migrations" (
  "version" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "applied_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "description" text COLLATE "pg_catalog"."default"
)
;
COMMENT ON TABLE "public"."schema_migrations" IS '数据库版本迁移记录表：跟踪所有数据库架构版本';

-- ----------------------------
-- Records of schema_migrations
-- ----------------------------
INSERT INTO "public"."schema_migrations" VALUES ('v2.3.0', '2025-10-10 04:32:53.017921+00', '首次数据库初始化 - 完整架构');
INSERT INTO "public"."schema_migrations" VALUES ('v2.4.0_composite_detection', '2025-10-18 08:47:19.415223+00', '多违规类型复合检测支持 - 添加detection_type_templates表和相关字段');
INSERT INTO "public"."schema_migrations" VALUES ('v3.0.0_composite_detection', '2025-10-28 13:27:52.950198+00', '复合检测功能：创建detection_type_templates表，预置12种检测类型');

-- ----------------------------
-- Table structure for stream_analysis_tasks
-- ----------------------------
DROP TABLE IF EXISTS "public"."stream_analysis_tasks";
CREATE TABLE "public"."stream_analysis_tasks" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "stream_id" uuid NOT NULL,
  "algorithm_config_id" uuid NOT NULL,
  "task_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "status" varchar(20) COLLATE "pg_catalog"."default" NOT NULL DEFAULT 'enabled'::character varying,
  "is_active" bool NOT NULL DEFAULT true,
  "auto_recover" bool NOT NULL DEFAULT true,
  "time_config" jsonb NOT NULL DEFAULT '{}'::jsonb,
  "roi_config" jsonb DEFAULT '{}'::jsonb,
  "priority" int4 NOT NULL DEFAULT 1,
  "confidence_threshold" float8 NOT NULL DEFAULT 0.7,
  "analysis_interval" int4 NOT NULL DEFAULT 10,
  "last_run_at" timestamptz(6),
  "next_run_at" timestamptz(6),
  "run_count" int4 NOT NULL DEFAULT 0,
  "error_count" int4 NOT NULL DEFAULT 0,
  "last_error_message" text COLLATE "pg_catalog"."default",
  "total_frames_processed" int4 NOT NULL DEFAULT 0,
  "total_alerts_generated" int4 NOT NULL DEFAULT 0,
  "avg_processing_time" float8 DEFAULT 0,
  "created_at" timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "created_by" uuid,
  "updated_by" uuid
)
;
COMMENT ON COLUMN "public"."stream_analysis_tasks"."time_config" IS '时间配置JSON：支持多时间段、跨天时间、星期选择';
COMMENT ON COLUMN "public"."stream_analysis_tasks"."roi_config" IS 'ROI区域配置JSON：支持矩形和多边形感兴趣区域';
COMMENT ON TABLE "public"."stream_analysis_tasks" IS '视频流实时分析任务表 - 支持任务级别管理、时间调度、ROI配置';

-- ----------------------------
-- Records of stream_analysis_tasks
-- ----------------------------
INSERT INTO "public"."stream_analysis_tasks" VALUES ('558e33f6-2e64-4a68-960d-964c86c09037', '5438e20a-b756-4af6-9ac0-df738ce42f3f', '68d88f43-3e6a-4ce6-9647-11a354d94eed', '示例项目-示例点位_违规行为分析_分析任务', 'disabled', 'f', 't', '{"enabled": false, "timezone": "Asia/Shanghai", "time_ranges": [{"days": [1, 2, 3, 4, 5, 6, 0], "end_time": "18:00", "start_time": "07:00"}]}', '{"enabled": false, "regions": [], "image_info": null}', 1, 0.7, 10, NULL, NULL, 0, 0, NULL, 0, 0, 0, '2025-11-09 10:33:58.247104+00', '2025-11-09 08:16:14.004381+00', NULL, NULL);
INSERT INTO "public"."stream_analysis_tasks" VALUES ('406e5592-9269-4649-903f-39c55641cd46', '2d705575-ea5e-4c4a-87fa-9ed406f26eb5', '5b487c13-656a-45e7-b5aa-6d3c04fafa3d', '测试_烟雾检测_分析任务', 'enabled', 't', 't', '{"enabled": false, "timezone": "Asia/Shanghai", "time_ranges": [{"days": [1, 2, 3, 4, 5, 6, 0], "end_time": "18:00", "start_time": "07:00"}]}', '{"enabled": false, "regions": [], "image_info": null}', 1, 0.7, 10, NULL, NULL, 0, 0, NULL, 0, 0, 0, '2025-11-21 14:38:23.186901+00', '2025-11-24 03:31:07.10699+00', NULL, NULL);
INSERT INTO "public"."stream_analysis_tasks" VALUES ('bb7db7f7-8f0a-4878-9079-1ba6a63a8070', 'd40dad17-6109-4e2d-a201-376347ca20da', '5cec72be-8143-499f-addb-f98c1554e2fb', '示例摄像头01_违规行为分析_分析任务', 'enabled', 't', 't', '{"enabled": true, "timezone": "Asia/Shanghai", "time_ranges": [{"days": [1, 2, 3, 4, 5, 6], "end_time": "12:00", "start_time": "09:00"}, {"days": [1, 2, 3, 4, 5], "end_time": "17:10", "start_time": "14:00"}]}', '{"enabled": false, "regions": [], "image_info": null}', 1, 0.7, 10, NULL, NULL, 0, 0, NULL, 0, 0, 0, '2025-11-10 09:09:15.679853+00', '2025-11-24 03:28:40.111504+00', NULL, NULL);
INSERT INTO "public"."stream_analysis_tasks" VALUES ('b4f94920-7bff-47eb-8ae2-50932806d5f6', '61aca923-3971-41ae-88bd-427ef9a5b22d', '3d68750d-4cab-4d28-b184-270cc1ec223c', '示例摄像头02_违规行为分析_分析任务', 'enabled', 't', 't', '{"enabled": false, "timezone": "Asia/Shanghai", "time_ranges": [{"days": [1, 2, 3, 4, 5, 6, 0], "end_time": "18:00", "start_time": "07:00"}]}', '{"enabled": false, "regions": [], "image_info": null}', 1, 0.7, 10, NULL, NULL, 0, 0, NULL, 0, 0, 0, '2025-11-12 14:39:27.750083+00', '2025-11-24 03:29:45.827473+00', NULL, NULL);

-- ----------------------------
-- Table structure for stream_analysis_templates
-- ----------------------------
DROP TABLE IF EXISTS "public"."stream_analysis_templates";
CREATE TABLE "public"."stream_analysis_templates" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "stream_id" uuid NOT NULL,
  "template_id" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "template_name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "priority" int4 DEFAULT 1,
  "enabled" bool,
  "confidence_threshold" float4 DEFAULT 0.7,
  "analysis_status" "public"."stream_analysis_status_enum" DEFAULT 'NOT_STARTED'::stream_analysis_status_enum,
  "alerts_count" int4 DEFAULT 0,
  "detection_count" int4 DEFAULT 0,
  "confidence_avg" float4,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "last_detection_at" timestamptz(6),
  "error_message" text COLLATE "pg_catalog"."default"
)
;
COMMENT ON TABLE "public"."stream_analysis_templates" IS '流分析模板表：视频流AI分析配置模板';

-- ----------------------------
-- Records of stream_analysis_templates
-- ----------------------------

-- ----------------------------
-- Table structure for system_configs
-- ----------------------------
DROP TABLE IF EXISTS "public"."system_configs";
CREATE TABLE "public"."system_configs" (
  "param_code" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "param_desc" varchar(250) COLLATE "pg_catalog"."default" NOT NULL,
  "param_val" varchar(1000) COLLATE "pg_catalog"."default" NOT NULL,
  "ext_val" varchar(1000) COLLATE "pg_catalog"."default" DEFAULT NULL::character varying,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON COLUMN "public"."system_configs"."param_code" IS '配置参数编码(主键)';
COMMENT ON COLUMN "public"."system_configs"."param_desc" IS '配置参数描述';
COMMENT ON COLUMN "public"."system_configs"."param_val" IS '配置参数值';
COMMENT ON COLUMN "public"."system_configs"."ext_val" IS '扩展配置值';
COMMENT ON COLUMN "public"."system_configs"."created_at" IS '创建时间';
COMMENT ON COLUMN "public"."system_configs"."updated_at" IS '更新时间';
COMMENT ON TABLE "public"."system_configs" IS '系统配置参数表';

-- ----------------------------
-- Records of system_configs
-- ----------------------------
INSERT INTO "public"."system_configs" VALUES ('video_max_size', '视频文件最大大小(MB)', '500', NULL, '2025-10-10 04:32:53.017921+00', '2025-10-10 04:32:53.017921+00');
INSERT INTO "public"."system_configs" VALUES ('ai_request_timeout', 'AI请求超时时间(秒)', '30', NULL, '2025-10-10 04:32:53.017921+00', '2025-10-10 04:32:53.017921+00');
INSERT INTO "public"."system_configs" VALUES ('stream_analysis_interval', '流分析间隔时间(秒)', '10', NULL, '2025-10-10 04:32:53.017921+00', '2025-10-10 04:32:53.017921+00');
INSERT INTO "public"."system_configs" VALUES ('max_concurrent_analysis', '最大并发分析任务数', '5', NULL, '2025-10-10 04:32:53.017921+00', '2025-10-10 04:32:53.017921+00');
INSERT INTO "public"."system_configs" VALUES ('alert_retention_days', '告警记录保留天数', '30', NULL, '2025-10-10 04:32:53.017921+00', '2025-10-10 04:32:53.017921+00');
INSERT INTO "public"."system_configs" VALUES ('qywx_webhook', '企业微信群聊机器人地址', 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=25a2c1ac-aa9d-4e6a-93e6-6e8f7a70fd7f', NULL, '2025-10-09 16:38:22.815581+00', '2025-10-09 16:38:22.815581+00');

-- ----------------------------
-- Table structure for users
-- ----------------------------
DROP TABLE IF EXISTS "public"."users";
CREATE TABLE "public"."users" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "username" varchar(50) COLLATE "pg_catalog"."default" NOT NULL,
  "email" varchar(255) COLLATE "pg_catalog"."default",
  "password_hash" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "full_name" varchar(255) COLLATE "pg_catalog"."default",
  "phone" varchar(20) COLLATE "pg_catalog"."default",
  "department" varchar(100) COLLATE "pg_catalog"."default",
  "role" "public"."user_role_enum" DEFAULT 'user'::user_role_enum,
  "is_active" bool,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "last_login_at" timestamptz(6)
)
;
COMMENT ON TABLE "public"."users" IS '系统用户表：管理所有用户账户信息和权限';

-- ----------------------------
-- Records of users
-- ----------------------------
INSERT INTO "public"."users" VALUES ('629718f1-1bcc-4a06-99f1-7980ac5631e6', 'admin', 'admin@example.com', '$2b$12$7EjaM.O3UOFIirH9OPqOB.xbDEmGgbhrVHe2WQBd8xmgwcwEsoFAO', '系统管理员', NULL, NULL, 'admin', 't', '2025-10-10 04:32:53.502583+00', '2025-11-24 05:58:59.886279+00', '2025-11-24 13:59:00.110033+00');

-- ----------------------------
-- Table structure for video_analysis_results
-- ----------------------------
DROP TABLE IF EXISTS "public"."video_analysis_results";
CREATE TABLE "public"."video_analysis_results" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "video_file_id" uuid NOT NULL,
  "template_id" uuid NOT NULL,
  "status" "public"."analysis_status_enum" DEFAULT 'not_started'::analysis_status_enum,
  "analysis_result" text COLLATE "pg_catalog"."default",
  "confidence_score" float4,
  "processing_time" int4,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "completed_at" timestamptz(6)
)
;
COMMENT ON TABLE "public"."video_analysis_results" IS '视频分析结果表：存储AI分析的详细结果和性能指标';

-- ----------------------------
-- Records of video_analysis_results
-- ----------------------------

-- ----------------------------
-- Table structure for video_analysis_templates
-- ----------------------------
DROP TABLE IF EXISTS "public"."video_analysis_templates";
CREATE TABLE "public"."video_analysis_templates" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "category" varchar(100) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "prompt_content" text COLLATE "pg_catalog"."default" NOT NULL,
  "is_enabled" bool,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "video_id" uuid,
  "template_id" uuid,
  "template_name" varchar(255) COLLATE "pg_catalog"."default",
  "priority" int4 DEFAULT 0,
  "enabled" bool DEFAULT true,
  "analysis_status" varchar(50) COLLATE "pg_catalog"."default" DEFAULT 'not_started'::character varying,
  "progress" int4 DEFAULT 0,
  "alerts_count" int4 DEFAULT 0,
  "confidence_avg" float4 DEFAULT 0.0,
  "analysis_duration" int4,
  "error_message" text COLLATE "pg_catalog"."default",
  "started_at" timestamptz(6),
  "completed_at" timestamptz(6),
  "detection_type_code" varchar(50) COLLATE "pg_catalog"."default"
)
;
COMMENT ON COLUMN "public"."video_analysis_templates"."detection_type_code" IS '关联的检测类型编码，用于复合检测（可为NULL保持向后兼容）';
COMMENT ON TABLE "public"."video_analysis_templates" IS 'AI分析模板表：存储视频分析的提示词模板和配置';

-- ----------------------------
-- Records of video_analysis_templates
-- ----------------------------
INSERT INTO "public"."video_analysis_templates" VALUES ('311c79d5-3ccb-4b5c-bc3d-7445e93b4057', '违规行为分析', '违规行为分析', '视频违规行为分析', '你是一个专业的视频监控AI分析助手,擅长同时检测多种安全违规行为。

你的职责:
1. 仔细观察提供的图片,识别画面中的所有安全隐患和违规行为
2. 对每种检测类型进行独立判断,不要因为一种违规的存在而忽略其他类型
3. 给出客观、准确的检测结论,避免误报和漏报
4. 提供详细的违规位置、人数统计和严重程度评估

检测原则:
- 准确性优先: 只有高置信度的检测才报告为违规
- 全面性: 不要遗漏任何需要检测的类型
- 详细性: 提供足够的细节帮助理解违规情况
- 结构化: 严格按照要求的JSON格式返回结果

仔细分析图片中存在的违规行为', 't', '2025-10-29 00:23:16.611449+00', '2025-10-29 00:23:16.611449+00', '25c62bdc-c588-4654-865a-432960bde5c0', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 't', 'ready', 0, 0, 0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "public"."video_analysis_templates" VALUES ('e74370a5-33cc-4c26-aee1-1b661c083948', '违规行为分析', 'general', '违规行为分析', '请分析这张图片的内容。', 't', '2025-11-09 08:25:48.645029+00', '2025-11-09 08:25:48.645029+00', 'd78791c3-364e-439b-a926-08c7e0216fca', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 't', 'ready', 0, 0, 0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "public"."video_analysis_templates" VALUES ('59eda909-b59e-40eb-a53d-309bdfd60187', '违规行为分析', 'general', '违规行为分析', '请分析这张图片的内容。', 't', '2025-11-09 08:29:37.925814+00', '2025-11-09 08:29:37.925814+00', '61a17335-6a97-487d-bf10-35edf3d5ec3c', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 't', 'ready', 0, 0, 0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "public"."video_analysis_templates" VALUES ('70f2dbfb-2b41-429b-8291-994a42336863', '违规行为分析', 'general', '违规行为分析', '请分析这张图片的内容。', 't', '2025-11-09 15:29:44.99298+00', '2025-11-09 15:29:44.99298+00', '499c9df6-ad27-4898-a716-beab76bb0633', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 't', 'ready', 0, 0, 0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "public"."video_analysis_templates" VALUES ('b0243a7e-bbe3-44c7-a0c2-0c2dc20a4cca', 'Qwen3-VL-4B本地部署', '本地部署', '基于本地GPU部署的Qwen3-VL-4B多模态视觉模型，适用于视频监控场景的违规行为检测', '你是一个专业的视频监控AI助手，负责分析监控画面中的行为和场景，识别潜在的安全隐患和违规行为。', 't', '2025-11-21 01:32:01.451838+00', '2025-11-21 01:32:01.451838+00', 'b23618d7-629b-4560-886e-eeba663323d2', '69cdb856-fc7b-4146-b0ff-ff0019e28b90', 'Qwen3-VL-4B本地部署', 1, 't', 'ready', 0, 0, 0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "public"."video_analysis_templates" VALUES ('440e7fcf-0b95-45ec-8042-896fa69b0bc1', 'Qwen3-VL-4B本地部署', '本地部署', '基于本地GPU部署的Qwen3-VL-4B多模态视觉模型，适用于视频监控场景的违规行为检测', '你是一个专业的视频监控AI助手，负责分析监控画面中的行为和场景，识别潜在的安全隐患和违规行为。', 't', '2025-11-23 12:13:35.46961+00', '2025-11-23 12:13:35.46961+00', 'c574ba44-ec83-48a2-b958-958d239f79fb', '69cdb856-fc7b-4146-b0ff-ff0019e28b90', 'Qwen3-VL-4B本地部署', 1, 't', 'ready', 0, 0, 0, NULL, NULL, NULL, NULL, NULL);
INSERT INTO "public"."video_analysis_templates" VALUES ('f4589ed7-0baf-4f45-a0f1-5b83a935c17b', 'Qwen3-VL-4B本地部署', '本地部署', '基于本地GPU部署的Qwen3-VL-4B多模态视觉模型，适用于视频监控场景的违规行为检测', '你是一个专业的视频监控AI助手，负责分析监控画面中的行为和场景，识别潜在的安全隐患和违规行为。', 't', '2025-11-23 14:37:08.050612+00', '2025-11-23 14:37:08.050612+00', 'a8956969-6461-46f5-aa7b-d39a67a5d274', '69cdb856-fc7b-4146-b0ff-ff0019e28b90', 'Qwen3-VL-4B本地部署', 1, 't', 'ready', 0, 0, 0, NULL, NULL, NULL, NULL, NULL);

-- ----------------------------
-- Table structure for video_files
-- ----------------------------
DROP TABLE IF EXISTS "public"."video_files";
CREATE TABLE "public"."video_files" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "original_filename" varchar(500) COLLATE "pg_catalog"."default" NOT NULL,
  "file_path" varchar(1000) COLLATE "pg_catalog"."default" NOT NULL,
  "thumbnail_path" varchar(1000) COLLATE "pg_catalog"."default",
  "file_size" int8,
  "duration" float4,
  "fps" float4,
  "width" int4,
  "height" int4,
  "format" varchar(50) COLLATE "pg_catalog"."default",
  "status" "public"."video_status_enum" DEFAULT 'PENDING'::video_status_enum,
  "tags" text[] COLLATE "pg_catalog"."default" DEFAULT '{}'::text[],
  "description" text COLLATE "pg_catalog"."default",
  "analysis_progress" int4 DEFAULT 0,
  "total_alerts" int4 DEFAULT 0,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "analyzed_at" timestamptz(6),
  "last_alert_at" timestamptz(6),
  "deleted_at" timestamptz(6)
)
;
COMMENT ON TABLE "public"."video_files" IS '视频文件表：管理所有上传的视频文件信息和分析状态';

-- ----------------------------
-- Records of video_files
-- ----------------------------
INSERT INTO "public"."video_files" VALUES ('25c62bdc-c588-4654-865a-432960bde5c0', '施工区域', '未带安全帽.mp4', 'videos/uploads/20251014_060348_e84c8b62.mp4', NULL, 56955679, NULL, NULL, NULL, NULL, 'MP4', 'DELETED', '{安全帽}', '安全帽佩戴', 100, 0, '2025-10-13 22:03:48.428478+00', '2025-11-09 15:03:46.873041+00', NULL, NULL, NULL);
INSERT INTO "public"."video_files" VALUES ('d78791c3-364e-439b-a926-08c7e0216fca', '时代广场', '烟雾.mp4', 'videos/uploads/20251013_000642_204c040d.mp4', NULL, 90552427, NULL, NULL, NULL, NULL, 'MP4', 'DELETED', '{烟雾,火灾}', '烟雾测试', 100, 0, '2025-10-12 16:06:43.271514+00', '2025-11-09 15:03:49.498681+00', NULL, NULL, NULL);
INSERT INTO "public"."video_files" VALUES ('61a17335-6a97-487d-bf10-35edf3d5ec3c', '办公区', '吸烟.mp4', 'videos/uploads/20251011_013755_e7929d39.mp4', NULL, 79820963, NULL, NULL, NULL, NULL, 'MP4', 'DELETED', '{吸烟,办公区}', '吸烟检查', 100, 3, '2025-10-10 17:37:56.414399+00', '2025-11-09 15:03:51.662236+00', NULL, NULL, NULL);
INSERT INTO "public"."video_files" VALUES ('499c9df6-ad27-4898-a716-beab76bb0633', 'X项目-园区摄像头', '未带安全帽.mp4', 'videos/uploads/20251109_232911_a1e023a0.mp4', NULL, 56955679, NULL, NULL, NULL, NULL, 'MP4', 'DELETED', '{安全行为检测}', '安全帽、反光衣安全检测', 100, 0, '2025-11-09 15:29:12.874754+00', '2025-11-19 09:27:00.726186+00', NULL, NULL, NULL);
INSERT INTO "public"."video_files" VALUES ('a8956969-6461-46f5-aa7b-d39a67a5d274', '安全帽检测', '未带安全帽.mp4', 'videos/uploads/20251119_172734_b3e9a195.mp4', NULL, 56955679, NULL, NULL, NULL, NULL, 'MP4', 'COMPLETED', '{安全帽}', '安全帽检测', 100, 0, '2025-11-19 09:27:34.431479+00', '2025-11-24 05:42:49.429698+00', NULL, NULL, NULL);
INSERT INTO "public"."video_files" VALUES ('b23618d7-629b-4560-886e-eeba663323d2', '吸烟', '吸烟.mp4', 'videos/uploads/20251119_172906_e28af5a0.mp4', NULL, 79820963, NULL, NULL, NULL, NULL, 'MP4', 'ERROR', '{吸烟}', '吸烟检测', 0, 0, '2025-11-19 09:29:06.911114+00', '2025-11-24 02:16:34.973527+00', NULL, NULL, NULL);
INSERT INTO "public"."video_files" VALUES ('c574ba44-ec83-48a2-b958-958d239f79fb', '打架', '打架.mp4', 'videos/uploads/20251119_172755_a7089f75.mp4', NULL, 38000797, NULL, NULL, NULL, NULL, 'MP4', 'COMPLETED', '{打架}', '打架检测', 100, 0, '2025-11-19 09:27:55.379333+00', '2025-11-24 06:00:12.715458+00', NULL, NULL, NULL);

-- ----------------------------
-- Table structure for video_stream_algorithm_config_history
-- ----------------------------
DROP TABLE IF EXISTS "public"."video_stream_algorithm_config_history";
CREATE TABLE "public"."video_stream_algorithm_config_history" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "config_id" uuid NOT NULL,
  "stream_id" uuid NOT NULL,
  "template_id" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "template_name" varchar(255) COLLATE "pg_catalog"."default",
  "priority" int4,
  "confidence_threshold" float4,
  "is_active" bool,
  "operation" varchar(20) COLLATE "pg_catalog"."default" NOT NULL,
  "operation_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "operated_by" varchar(255) COLLATE "pg_catalog"."default",
  "old_values" jsonb,
  "new_values" jsonb
)
;
COMMENT ON TABLE "public"."video_stream_algorithm_config_history" IS '视频流算法配置历史表 - 审计所有配置变更记录';

-- ----------------------------
-- Records of video_stream_algorithm_config_history
-- ----------------------------
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('7707b776-5b92-4b14-9e2d-8c035be70809', '26fb203a-f158-4bb9-8d55-522052f5f750', '6d4c1a28-e0cc-40af-b11b-b52219419779', 'default_safety_monitor', '安全监控', 1, 0.7, 't', 'INSERT', '2025-10-11 01:11:18.443963+00', NULL, NULL, '{"id": "26fb203a-f158-4bb9-8d55-522052f5f750", "priority": 1, "is_active": true, "stream_id": "6d4c1a28-e0cc-40af-b11b-b52219419779", "created_at": "2025-10-11T01:11:18.443963+00:00", "created_by": null, "updated_at": "2025-10-11T01:11:18.443963+00:00", "template_id": "default_safety_monitor", "template_name": "安全监控", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('a4a0f11c-594c-4613-beb1-e2051baee80c', '26fb203a-f158-4bb9-8d55-522052f5f750', '6d4c1a28-e0cc-40af-b11b-b52219419779', 'default_safety_monitor', '安全监控', 1, 0.7, 't', 'DELETE', '2025-10-12 02:18:06.077242+00', NULL, '{"id": "26fb203a-f158-4bb9-8d55-522052f5f750", "priority": 1, "is_active": true, "stream_id": "6d4c1a28-e0cc-40af-b11b-b52219419779", "created_at": "2025-10-11T01:11:18.443963+00:00", "created_by": null, "updated_at": "2025-10-11T01:11:18.443963+00:00", "template_id": "default_safety_monitor", "template_name": "安全监控", "confidence_threshold": 0.7}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('aec3811c-83a3-427e-ab92-dc42ff78cfaa', '64d0f459-ece2-41af-9a8e-086ed35a6ae0', '5438e20a-b756-4af6-9ac0-df738ce42f3f', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, 0.7, 't', 'INSERT', '2025-10-12 08:25:53.554164+00', NULL, NULL, '{"id": "64d0f459-ece2-41af-9a8e-086ed35a6ae0", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-12T08:25:53.554164+00:00", "created_by": null, "updated_at": "2025-10-12T08:25:53.554164+00:00", "template_id": "37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb", "template_name": "未佩戴安全帽", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('86592ab3-b460-4862-adc5-c38fe5d22afc', '64d0f459-ece2-41af-9a8e-086ed35a6ae0', '5438e20a-b756-4af6-9ac0-df738ce42f3f', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, 0.7, 't', 'DELETE', '2025-10-12 09:04:15.917066+00', NULL, '{"id": "64d0f459-ece2-41af-9a8e-086ed35a6ae0", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-12T08:25:53.554164+00:00", "created_by": null, "updated_at": "2025-10-12T08:25:53.554164+00:00", "template_id": "37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb", "template_name": "未佩戴安全帽", "confidence_threshold": 0.7}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('1b0937ab-64ea-41a4-9f4b-0c20d17822ad', '4d2a6bcc-3495-4c3f-a0ed-c912e5bb243e', '5438e20a-b756-4af6-9ac0-df738ce42f3f', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, 0.7, 't', 'INSERT', '2025-10-12 09:22:33.774981+00', NULL, NULL, '{"id": "4d2a6bcc-3495-4c3f-a0ed-c912e5bb243e", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-12T09:22:33.774981+00:00", "created_by": null, "updated_at": "2025-10-12T09:22:33.774981+00:00", "template_id": "37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb", "template_name": "未佩戴安全帽", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('db8c3089-491b-4ca5-91db-923fefbcc51b', '4d2a6bcc-3495-4c3f-a0ed-c912e5bb243e', '5438e20a-b756-4af6-9ac0-df738ce42f3f', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, 0.7, 't', 'DELETE', '2025-10-13 22:41:54.416913+00', NULL, '{"id": "4d2a6bcc-3495-4c3f-a0ed-c912e5bb243e", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-12T09:22:33.774981+00:00", "created_by": null, "updated_at": "2025-10-12T09:22:33.774981+00:00", "template_id": "37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb", "template_name": "未佩戴安全帽", "confidence_threshold": 0.7}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('b653dd8e-a699-4318-a2d2-d0d38f916857', '9494140a-9f0e-4671-8b56-f2c8cce483b0', 'c300d5c0-a817-49ae-82e7-9c918e4e2482', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, 0.7, 't', 'INSERT', '2025-10-14 02:20:13.110838+00', NULL, NULL, '{"id": "9494140a-9f0e-4671-8b56-f2c8cce483b0", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T02:20:13.110838+00:00", "created_by": null, "updated_at": "2025-10-14T02:20:13.110838+00:00", "template_id": "37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb", "template_name": "未佩戴安全帽", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('5c188521-b4f0-440d-9cbc-c6eb10c90f63', '9494140a-9f0e-4671-8b56-f2c8cce483b0', 'c300d5c0-a817-49ae-82e7-9c918e4e2482', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, 0.7, 't', 'DELETE', '2025-10-14 09:15:33.802692+00', NULL, '{"id": "9494140a-9f0e-4671-8b56-f2c8cce483b0", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T02:20:13.110838+00:00", "created_by": null, "updated_at": "2025-10-14T02:20:13.110838+00:00", "template_id": "37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb", "template_name": "未佩戴安全帽", "confidence_threshold": 0.7}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('d3ebbb90-58b0-4a5e-8f84-4f00cddb8f2d', '92438993-9e61-415f-a08e-bbcc18d6ee43', 'c300d5c0-a817-49ae-82e7-9c918e4e2482', '87982d90-e209-4f6d-a202-9bfc1258825b', '佩戴安全帽', 1, 0.7, 't', 'INSERT', '2025-10-14 13:20:27.156191+00', NULL, NULL, '{"id": "92438993-9e61-415f-a08e-bbcc18d6ee43", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T13:20:27.156191+00:00", "created_by": null, "updated_at": "2025-10-14T13:20:27.156191+00:00", "template_id": "87982d90-e209-4f6d-a202-9bfc1258825b", "template_name": "佩戴安全帽", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('bd9f1563-ac8b-48d3-a25e-0bb25702a0d7', '832f36e7-06b2-4a74-80b7-c6ed547630ac', 'c300d5c0-a817-49ae-82e7-9c918e4e2482', '43c24e84-63b9-41bc-a9d7-572ac96097bd', '烟雾火灾检测算法(蓝翼版)', 1, 0.7, 't', 'INSERT', '2025-10-14 13:24:41.774222+00', NULL, NULL, '{"id": "832f36e7-06b2-4a74-80b7-c6ed547630ac", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T13:24:41.774222+00:00", "created_by": null, "updated_at": "2025-10-14T13:24:41.774222+00:00", "template_id": "43c24e84-63b9-41bc-a9d7-572ac96097bd", "template_name": "烟雾火灾检测算法(蓝翼版)", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('6ec4d361-5020-463b-8a70-cfda4caa7963', '5ca2eedd-930e-4944-befb-5bd836ff4f48', '5438e20a-b756-4af6-9ac0-df738ce42f3f', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 0.7, 't', 'INSERT', '2025-10-18 23:56:57.823556+00', NULL, NULL, '{"id": "5ca2eedd-930e-4944-befb-5bd836ff4f48", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-18T23:56:57.823556+00:00", "created_by": null, "updated_at": "2025-10-18T23:56:57.823556+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('c1520fa4-26ac-4f1c-a84c-7dca5f4a611f', '5ca2eedd-930e-4944-befb-5bd836ff4f48', '5438e20a-b756-4af6-9ac0-df738ce42f3f', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 0.7, 't', 'DELETE', '2025-10-20 05:55:43.817256+00', NULL, '{"id": "5ca2eedd-930e-4944-befb-5bd836ff4f48", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-18T23:56:57.823556+00:00", "created_by": null, "updated_at": "2025-10-18T23:56:57.823556+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('a8cc8d3a-af0e-492b-a283-1d670cb4652a', '06369509-335e-467a-84fd-d133f88be249', '5438e20a-b756-4af6-9ac0-df738ce42f3f', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 0.7, 't', 'INSERT', '2025-10-20 06:32:21.105645+00', NULL, NULL, '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T06:32:21.105645+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('1a2b2e01-5f66-4411-8aec-33732f59d34f', '5b487c13-656a-45e7-b5aa-6d3c04fafa3d', '2d705575-ea5e-4c4a-87fa-9ed406f26eb5', '7e3a256c-4bfb-4f20-9b91-581ae9d1202c', '烟雾检测', 1, 0.7, 't', 'INSERT', '2025-11-21 06:38:23.184683+00', NULL, NULL, '{"id": "5b487c13-656a-45e7-b5aa-6d3c04fafa3d", "priority": 1, "is_active": true, "stream_id": "2d705575-ea5e-4c4a-87fa-9ed406f26eb5", "created_at": "2025-11-21T14:38:23.186901+00:00", "created_by": null, "updated_at": "2025-11-21T14:38:23.186901+00:00", "template_id": "7e3a256c-4bfb-4f20-9b91-581ae9d1202c", "template_name": "烟雾检测", "confidence_threshold": 0.7, "detection_type_codes": []}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('b90d38b6-61f8-4110-b3fd-5a629e0648a2', '06369509-335e-467a-84fd-d133f88be249', '5438e20a-b756-4af6-9ac0-df738ce42f3f', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 0.7, 't', 'UPDATE', '2025-10-20 08:44:11.925157+00', NULL, '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T06:32:21.105645+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}', '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T08:44:11.925157+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('09ccef54-4d5a-43f5-8b76-c15d7212b382', '06369509-335e-467a-84fd-d133f88be249', '5438e20a-b756-4af6-9ac0-df738ce42f3f', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 0.7, 't', 'UPDATE', '2025-10-20 09:57:11.645861+00', NULL, '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T08:44:11.925157+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}', '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T09:57:11.645861+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('1e7baa62-1db1-4fcf-a572-0d0df4a8f37d', '06369509-335e-467a-84fd-d133f88be249', '5438e20a-b756-4af6-9ac0-df738ce42f3f', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 0.7, 't', 'UPDATE', '2025-10-20 10:01:26.424353+00', NULL, '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T09:57:11.645861+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}', '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T10:01:26.424353+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('2519b94e-01c3-48bf-ac99-a4f3a2210330', '832f36e7-06b2-4a74-80b7-c6ed547630ac', 'c300d5c0-a817-49ae-82e7-9c918e4e2482', '43c24e84-63b9-41bc-a9d7-572ac96097bd', '烟雾火灾检测算法(蓝翼版)', 1, 0.7, 't', 'UPDATE', '2025-10-20 13:47:20.409361+00', NULL, '{"id": "832f36e7-06b2-4a74-80b7-c6ed547630ac", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T13:24:41.774222+00:00", "created_by": null, "updated_at": "2025-10-14T13:24:41.774222+00:00", "template_id": "43c24e84-63b9-41bc-a9d7-572ac96097bd", "template_name": "烟雾火灾检测算法(蓝翼版)", "confidence_threshold": 0.7}', '{"id": "832f36e7-06b2-4a74-80b7-c6ed547630ac", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T13:24:41.774222+00:00", "created_by": null, "updated_at": "2025-10-20T13:47:20.409361+00:00", "template_id": "43c24e84-63b9-41bc-a9d7-572ac96097bd", "template_name": "烟雾火灾检测算法(蓝翼版)", "confidence_threshold": 0.7}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('5e32e040-2a9b-49cb-a8d6-7b5db4c8df6d', '832f36e7-06b2-4a74-80b7-c6ed547630ac', 'c300d5c0-a817-49ae-82e7-9c918e4e2482', '43c24e84-63b9-41bc-a9d7-572ac96097bd', '烟雾火灾检测算法(蓝翼版)', 1, 0.7, 't', 'DELETE', '2025-10-20 22:55:20.403376+00', NULL, '{"id": "832f36e7-06b2-4a74-80b7-c6ed547630ac", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T13:24:41.774222+00:00", "created_by": null, "updated_at": "2025-10-20T13:47:20.409361+00:00", "template_id": "43c24e84-63b9-41bc-a9d7-572ac96097bd", "template_name": "烟雾火灾检测算法(蓝翼版)", "confidence_threshold": 0.7}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('5e0bdd4e-e7bf-4f8f-adfb-58fb660090bd', '92438993-9e61-415f-a08e-bbcc18d6ee43', 'c300d5c0-a817-49ae-82e7-9c918e4e2482', '87982d90-e209-4f6d-a202-9bfc1258825b', '佩戴安全帽', 1, 0.7, 't', 'DELETE', '2025-10-20 22:55:22.94616+00', NULL, '{"id": "92438993-9e61-415f-a08e-bbcc18d6ee43", "priority": 1, "is_active": true, "stream_id": "c300d5c0-a817-49ae-82e7-9c918e4e2482", "created_at": "2025-10-14T13:20:27.156191+00:00", "created_by": null, "updated_at": "2025-10-14T13:20:27.156191+00:00", "template_id": "87982d90-e209-4f6d-a202-9bfc1258825b", "template_name": "佩戴安全帽", "confidence_threshold": 0.7}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('67af5515-381b-4976-a032-e1c30808988e', '06369509-335e-467a-84fd-d133f88be249', '5438e20a-b756-4af6-9ac0-df738ce42f3f', 'b0e86779-e015-4bf4-a3e9-af2b7608df87', '违规行为分析', 1, 0.7, 't', 'DELETE', '2025-11-09 02:25:53.022001+00', NULL, '{"id": "06369509-335e-467a-84fd-d133f88be249", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-10-20T06:32:21.105645+00:00", "created_by": null, "updated_at": "2025-10-20T10:01:26.424353+00:00", "template_id": "b0e86779-e015-4bf4-a3e9-af2b7608df87", "template_name": "违规行为分析", "confidence_threshold": 0.7, "detection_type_codes": []}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('9c136f4b-4b71-4572-8a49-11b958d891ac', '68d88f43-3e6a-4ce6-9647-11a354d94eed', '5438e20a-b756-4af6-9ac0-df738ce42f3f', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 0.7, 't', 'INSERT', '2025-11-09 02:33:58.244188+00', NULL, NULL, '{"id": "68d88f43-3e6a-4ce6-9647-11a354d94eed", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-11-09T10:33:58.247104+00:00", "created_by": null, "updated_at": "2025-11-09T10:33:58.247104+00:00", "template_id": "35b9e32d-db0b-422d-aced-e2477484a413", "template_name": "违规行为分析", "confidence_threshold": 0.7, "detection_type_codes": []}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('77b91d04-ea8d-4f41-87d5-7352e3423d9e', '5cec72be-8143-499f-addb-f98c1554e2fb', 'd40dad17-6109-4e2d-a201-376347ca20da', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 0.7, 't', 'INSERT', '2025-11-10 01:09:15.67506+00', NULL, NULL, '{"id": "5cec72be-8143-499f-addb-f98c1554e2fb", "priority": 1, "is_active": true, "stream_id": "d40dad17-6109-4e2d-a201-376347ca20da", "created_at": "2025-11-10T09:09:15.679853+00:00", "created_by": null, "updated_at": "2025-11-10T09:09:15.679853+00:00", "template_id": "35b9e32d-db0b-422d-aced-e2477484a413", "template_name": "违规行为分析", "confidence_threshold": 0.7, "detection_type_codes": []}');
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('ff7c3139-5176-4182-8aa3-152c75b0fc05', '68d88f43-3e6a-4ce6-9647-11a354d94eed', '5438e20a-b756-4af6-9ac0-df738ce42f3f', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 0.7, 't', 'DELETE', '2025-11-10 02:51:40.718016+00', NULL, '{"id": "68d88f43-3e6a-4ce6-9647-11a354d94eed", "priority": 1, "is_active": true, "stream_id": "5438e20a-b756-4af6-9ac0-df738ce42f3f", "created_at": "2025-11-09T10:33:58.247104+00:00", "created_by": null, "updated_at": "2025-11-09T10:33:58.247104+00:00", "template_id": "35b9e32d-db0b-422d-aced-e2477484a413", "template_name": "违规行为分析", "confidence_threshold": 0.7, "detection_type_codes": []}', NULL);
INSERT INTO "public"."video_stream_algorithm_config_history" VALUES ('fd3f788e-4664-4b9d-992a-a10f02bde599', '3d68750d-4cab-4d28-b184-270cc1ec223c', '61aca923-3971-41ae-88bd-427ef9a5b22d', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 0.7, 't', 'INSERT', '2025-11-12 06:39:27.74419+00', NULL, NULL, '{"id": "3d68750d-4cab-4d28-b184-270cc1ec223c", "priority": 1, "is_active": true, "stream_id": "61aca923-3971-41ae-88bd-427ef9a5b22d", "created_at": "2025-11-12T14:39:27.750083+00:00", "created_by": null, "updated_at": "2025-11-12T14:39:27.750083+00:00", "template_id": "35b9e32d-db0b-422d-aced-e2477484a413", "template_name": "违规行为分析", "confidence_threshold": 0.7, "detection_type_codes": []}');

-- ----------------------------
-- Table structure for video_stream_algorithm_configs
-- ----------------------------
DROP TABLE IF EXISTS "public"."video_stream_algorithm_configs";
CREATE TABLE "public"."video_stream_algorithm_configs" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "stream_id" uuid NOT NULL,
  "template_id" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "template_name" varchar(255) COLLATE "pg_catalog"."default",
  "priority" int4 DEFAULT 1,
  "confidence_threshold" float4 DEFAULT 0.7,
  "is_active" bool DEFAULT true,
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "created_by" varchar(255) COLLATE "pg_catalog"."default",
  "detection_type_codes" jsonb DEFAULT '[]'::jsonb
)
;
COMMENT ON COLUMN "public"."video_stream_algorithm_configs"."stream_id" IS '视频流ID，关联video_streams表';
COMMENT ON COLUMN "public"."video_stream_algorithm_configs"."template_id" IS 'AI算法模板ID';
COMMENT ON COLUMN "public"."video_stream_algorithm_configs"."template_name" IS 'AI算法模板名称（冗余字段，便于查询）';
COMMENT ON COLUMN "public"."video_stream_algorithm_configs"."priority" IS '算法执行优先级，数字越大优先级越高';
COMMENT ON COLUMN "public"."video_stream_algorithm_configs"."confidence_threshold" IS '置信度阈值，0.0-1.0之间';
COMMENT ON COLUMN "public"."video_stream_algorithm_configs"."is_active" IS '是否启用该算法配置';
COMMENT ON COLUMN "public"."video_stream_algorithm_configs"."detection_type_codes" IS '用户选择要启用的检测类型编码列表，JSONB数组格式，从算法的detection_capabilities中选择。
示例: ["smoking", "using_phone"]
用途: 定义用户在该视频流上实际要使用的检测类型，支持从算法能力中灵活选择';
COMMENT ON TABLE "public"."video_stream_algorithm_configs" IS '视频流算法配置表 - 存储每个视频流配置的AI分析算法';

-- ----------------------------
-- Records of video_stream_algorithm_configs
-- ----------------------------
INSERT INTO "public"."video_stream_algorithm_configs" VALUES ('5cec72be-8143-499f-addb-f98c1554e2fb', 'd40dad17-6109-4e2d-a201-376347ca20da', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 0.7, 't', '2025-11-10 09:09:15.679853+00', '2025-11-10 09:09:15.679853+00', NULL, '[]');
INSERT INTO "public"."video_stream_algorithm_configs" VALUES ('3d68750d-4cab-4d28-b184-270cc1ec223c', '61aca923-3971-41ae-88bd-427ef9a5b22d', '35b9e32d-db0b-422d-aced-e2477484a413', '违规行为分析', 1, 0.7, 't', '2025-11-12 14:39:27.750083+00', '2025-11-12 14:39:27.750083+00', NULL, '[]');
INSERT INTO "public"."video_stream_algorithm_configs" VALUES ('5b487c13-656a-45e7-b5aa-6d3c04fafa3d', '2d705575-ea5e-4c4a-87fa-9ed406f26eb5', '7e3a256c-4bfb-4f20-9b91-581ae9d1202c', '烟雾检测', 1, 0.7, 't', '2025-11-21 14:38:23.186901+00', '2025-11-21 14:38:23.186901+00', NULL, '[]');

-- ----------------------------
-- Table structure for video_streams
-- ----------------------------
DROP TABLE IF EXISTS "public"."video_streams";
CREATE TABLE "public"."video_streams" (
  "id" uuid NOT NULL DEFAULT gen_random_uuid(),
  "name" varchar(255) COLLATE "pg_catalog"."default" NOT NULL,
  "description" text COLLATE "pg_catalog"."default",
  "stream_url" varchar(1000) COLLATE "pg_catalog"."default" NOT NULL,
  "stream_type" "public"."stream_type_enum" NOT NULL DEFAULT 'RTSP'::stream_type_enum,
  "username" varchar(100) COLLATE "pg_catalog"."default",
  "password" varchar(100) COLLATE "pg_catalog"."default",
  "status" "public"."stream_status_enum" NOT NULL DEFAULT 'OFFLINE'::stream_status_enum,
  "last_online_at" timestamptz(6),
  "connection_error" text COLLATE "pg_catalog"."default",
  "fps" float4,
  "width" int4,
  "height" int4,
  "codec" varchar(50) COLLATE "pg_catalog"."default",
  "thumbnail_path" varchar(1000) COLLATE "pg_catalog"."default",
  "latest_frame_path" varchar(1000) COLLATE "pg_catalog"."default",
  "analysis_status" "public"."stream_analysis_status_enum" NOT NULL DEFAULT 'NOT_STARTED'::stream_analysis_status_enum,
  "analysis_interval" int4 DEFAULT 10,
  "enable_recording" bool,
  "total_analysis_count" int4 DEFAULT 0,
  "total_alerts" int4 DEFAULT 0,
  "last_analysis_at" timestamptz(6),
  "last_alert_at" timestamptz(6),
  "location" varchar(255) COLLATE "pg_catalog"."default",
  "group_name" varchar(100) COLLATE "pg_catalog"."default",
  "tags" text[] COLLATE "pg_catalog"."default" DEFAULT '{}'::text[],
  "created_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP,
  "updated_at" timestamptz(6) DEFAULT CURRENT_TIMESTAMP
)
;
COMMENT ON TABLE "public"."video_streams" IS '视频流表：管理RTSP等实时视频流的配置和状态';

-- ----------------------------
-- Records of video_streams
-- ----------------------------
INSERT INTO "public"."video_streams" VALUES ('2d705575-ea5e-4c4a-87fa-9ed406f26eb5', '测试', NULL, 'rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream', 'RTSP', NULL, NULL, 'ONLINE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'NOT_STARTED', 10, NULL, 0, 0, NULL, NULL, NULL, NULL, '{}', '2025-11-21 06:37:12.248648+00', '2025-11-21 06:37:18.929018+00');
INSERT INTO "public"."video_streams" VALUES ('61aca923-3971-41ae-88bd-427ef9a5b22d', '示例摄像头02', '示例摄像头点位', 'rtsp://admin:CHANGE_ME@192.168.1.100:554/Streaming/Channels/101', 'RTSP', NULL, NULL, 'OFFLINE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'NOT_STARTED', 10, NULL, 0, 0, NULL, NULL, '示例点位', '示例项目', '{视频监控}', '2025-11-11 00:08:04.006072+00', '2025-11-21 06:40:10.929485+00');
INSERT INTO "public"."video_streams" VALUES ('d40dad17-6109-4e2d-a201-376347ca20da', '示例摄像头01', '示例点位', 'rtsp://admin:CHANGE_ME@192.168.1.101:554/Streaming/Channels/101', 'RTSP', NULL, NULL, 'OFFLINE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'NOT_STARTED', 10, NULL, 0, 0, NULL, NULL, '示例点位', '示例项目', '{示例项目}', '2025-11-10 00:13:56.7446+00', '2025-11-21 06:41:41.063379+00');

-- ----------------------------
-- Function structure for audit_video_stream_algorithm_config
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."audit_video_stream_algorithm_config"();
CREATE FUNCTION "public"."audit_video_stream_algorithm_config"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
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
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for update_stream_analysis_tasks_updated_at
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."update_stream_analysis_tasks_updated_at"();
CREATE FUNCTION "public"."update_stream_analysis_tasks_updated_at"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Function structure for update_updated_at_column
-- ----------------------------
DROP FUNCTION IF EXISTS "public"."update_updated_at_column"();
CREATE FUNCTION "public"."update_updated_at_column"()
  RETURNS "pg_catalog"."trigger" AS $BODY$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100;

-- ----------------------------
-- Indexes structure for table ai_agent_history
-- ----------------------------
CREATE INDEX "idx_ai_agent_history_created_at" ON "public"."ai_agent_history" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_ai_agent_history_intent" ON "public"."ai_agent_history" USING gin (
  "intent" "pg_catalog"."jsonb_ops"
);
CREATE INDEX "idx_ai_agent_history_session_id" ON "public"."ai_agent_history" USING btree (
  "session_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_agent_history_user_id" ON "public"."ai_agent_history" USING btree (
  "user_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table ai_agent_history
-- ----------------------------
CREATE TRIGGER "update_ai_agent_history_updated_at" BEFORE UPDATE ON "public"."ai_agent_history"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table ai_agent_history
-- ----------------------------
ALTER TABLE "public"."ai_agent_history" ADD CONSTRAINT "ai_agent_history_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ai_agent_sessions
-- ----------------------------
CREATE INDEX "idx_ai_agent_sessions_created_at" ON "public"."ai_agent_sessions" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_ai_agent_sessions_last_message_at" ON "public"."ai_agent_sessions" USING btree (
  "last_message_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_ai_agent_sessions_user_id" ON "public"."ai_agent_sessions" USING btree (
  "user_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table ai_agent_sessions
-- ----------------------------
ALTER TABLE "public"."ai_agent_sessions" ADD CONSTRAINT "ai_agent_sessions_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ai_analysis_logs
-- ----------------------------
CREATE INDEX "idx_ai_analysis_logs_algorithm_id" ON "public"."ai_analysis_logs" USING btree (
  "algorithm_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_analysis_logs_call_date" ON "public"."ai_analysis_logs" USING btree (
  "call_date" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_analysis_logs_call_status" ON "public"."ai_analysis_logs" USING btree (
  "call_status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_analysis_logs_task_id" ON "public"."ai_analysis_logs" USING btree (
  "task_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_analysis_logs_video_id" ON "public"."ai_analysis_logs" USING btree (
  "video_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table ai_analysis_logs
-- ----------------------------
CREATE TRIGGER "update_ai_analysis_logs_updated_at" BEFORE UPDATE ON "public"."ai_analysis_logs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table ai_analysis_logs
-- ----------------------------
ALTER TABLE "public"."ai_analysis_logs" ADD CONSTRAINT "ai_analysis_logs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ai_model_configs
-- ----------------------------
CREATE INDEX "idx_ai_model_configs_composite_detection" ON "public"."ai_model_configs" USING btree (
  "composite_detection" "pg_catalog"."bool_ops" ASC NULLS LAST
) WHERE composite_detection = true;
CREATE INDEX "idx_ai_model_configs_created_at" ON "public"."ai_model_configs" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_ai_model_configs_detection_capabilities" ON "public"."ai_model_configs" USING gin (
  "detection_capabilities" "pg_catalog"."jsonb_ops"
);
COMMENT ON INDEX "public"."idx_ai_model_configs_detection_capabilities" IS 'GIN索引用于优化detection_capabilities字段的查询性能，支持包含(@>)和相等(=)操作';
CREATE INDEX "idx_ai_model_configs_model_type" ON "public"."ai_model_configs" USING btree (
  "model_type" "pg_catalog"."enum_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_model_configs_status" ON "public"."ai_model_configs" USING btree (
  "status" "pg_catalog"."enum_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_model_configs_tags" ON "public"."ai_model_configs" USING gin (
  "tags" COLLATE "pg_catalog"."default" "pg_catalog"."array_ops"
);
CREATE INDEX "idx_ai_model_configs_updated_at" ON "public"."ai_model_configs" USING btree (
  "updated_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);

-- ----------------------------
-- Triggers structure for table ai_model_configs
-- ----------------------------
CREATE TRIGGER "update_ai_model_configs_updated_at" BEFORE UPDATE ON "public"."ai_model_configs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table ai_model_configs
-- ----------------------------
ALTER TABLE "public"."ai_model_configs" ADD CONSTRAINT "ai_model_configs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ai_provider_configs
-- ----------------------------
CREATE UNIQUE INDEX "ai_provider_configs_provider_name_key" ON "public"."ai_provider_configs" USING btree (
  "provider_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_provider_configs_created_at" ON "public"."ai_provider_configs" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_ai_provider_configs_is_active" ON "public"."ai_provider_configs" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_provider_configs_provider_name" ON "public"."ai_provider_configs" USING btree (
  "provider_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_provider_configs_sort_order" ON "public"."ai_provider_configs" USING btree (
  "sort_order" "pg_catalog"."int4_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table ai_provider_configs
-- ----------------------------
CREATE TRIGGER "update_ai_provider_configs_updated_at" BEFORE UPDATE ON "public"."ai_provider_configs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table ai_provider_configs
-- ----------------------------
ALTER TABLE "public"."ai_provider_configs" ADD CONSTRAINT "ai_provider_configs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table ai_test_results
-- ----------------------------
CREATE INDEX "idx_ai_test_results_config_id" ON "public"."ai_test_results" USING btree (
  "config_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_ai_test_results_created_at" ON "public"."ai_test_results" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_ai_test_results_is_success" ON "public"."ai_test_results" USING btree (
  "is_success" "pg_catalog"."bool_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table ai_test_results
-- ----------------------------
ALTER TABLE "public"."ai_test_results" ADD CONSTRAINT "ai_test_results_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table detection_type_templates
-- ----------------------------
CREATE INDEX "idx_detection_type_templates_category" ON "public"."detection_type_templates" USING btree (
  "category" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_detection_type_templates_enabled" ON "public"."detection_type_templates" USING btree (
  "enabled" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_detection_type_templates_sort_order" ON "public"."detection_type_templates" USING btree (
  "sort_order" "pg_catalog"."int4_ops" ASC NULLS LAST
);
CREATE INDEX "idx_detection_type_templates_type_code" ON "public"."detection_type_templates" USING btree (
  "type_code" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table detection_type_templates
-- ----------------------------
CREATE TRIGGER "update_detection_type_templates_updated_at" BEFORE UPDATE ON "public"."detection_type_templates"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table detection_type_templates
-- ----------------------------
ALTER TABLE "public"."detection_type_templates" ADD CONSTRAINT "detection_type_templates_type_code_key" UNIQUE ("type_code");

-- ----------------------------
-- Checks structure for table detection_type_templates
-- ----------------------------
ALTER TABLE "public"."detection_type_templates" ADD CONSTRAINT "detection_type_templates_severity_check" CHECK (severity::text = ANY (ARRAY['low'::character varying::text, 'medium'::character varying::text, 'high'::character varying::text]));

-- ----------------------------
-- Primary Key structure for table detection_type_templates
-- ----------------------------
ALTER TABLE "public"."detection_type_templates" ADD CONSTRAINT "detection_type_templates_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Primary Key structure for table schema_migrations
-- ----------------------------
ALTER TABLE "public"."schema_migrations" ADD CONSTRAINT "schema_migrations_pkey" PRIMARY KEY ("version");

-- ----------------------------
-- Indexes structure for table stream_analysis_tasks
-- ----------------------------
CREATE INDEX "idx_stream_analysis_tasks_active" ON "public"."stream_analysis_tasks" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_stream_analysis_tasks_auto_recover" ON "public"."stream_analysis_tasks" USING btree (
  "auto_recover" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_stream_analysis_tasks_next_run" ON "public"."stream_analysis_tasks" USING btree (
  "next_run_at" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
) WHERE status::text = 'enabled'::text;
CREATE INDEX "idx_stream_analysis_tasks_status" ON "public"."stream_analysis_tasks" USING btree (
  "status" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_stream_analysis_tasks_stream_id" ON "public"."stream_analysis_tasks" USING btree (
  "stream_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table stream_analysis_tasks
-- ----------------------------
CREATE TRIGGER "trigger_update_stream_analysis_tasks_updated_at" BEFORE UPDATE ON "public"."stream_analysis_tasks"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_stream_analysis_tasks_updated_at"();

-- ----------------------------
-- Checks structure for table stream_analysis_tasks
-- ----------------------------
ALTER TABLE "public"."stream_analysis_tasks" ADD CONSTRAINT "chk_confidence_threshold" CHECK (confidence_threshold >= 0::double precision AND confidence_threshold <= 1::double precision);
ALTER TABLE "public"."stream_analysis_tasks" ADD CONSTRAINT "chk_priority" CHECK (priority >= 1 AND priority <= 10);
ALTER TABLE "public"."stream_analysis_tasks" ADD CONSTRAINT "chk_status" CHECK (status::text = ANY (ARRAY['enabled'::character varying::text, 'disabled'::character varying::text, 'running'::character varying::text, 'error'::character varying::text, 'scheduled'::character varying::text]));

-- ----------------------------
-- Primary Key structure for table stream_analysis_tasks
-- ----------------------------
ALTER TABLE "public"."stream_analysis_tasks" ADD CONSTRAINT "stream_analysis_tasks_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table stream_analysis_templates
-- ----------------------------
CREATE INDEX "idx_stream_templates_enabled" ON "public"."stream_analysis_templates" USING btree (
  "enabled" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_stream_templates_priority" ON "public"."stream_analysis_templates" USING btree (
  "priority" "pg_catalog"."int4_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_stream_templates_stream_id" ON "public"."stream_analysis_templates" USING btree (
  "stream_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE UNIQUE INDEX "stream_analysis_templates_stream_id_template_id_key" ON "public"."stream_analysis_templates" USING btree (
  "stream_id" "pg_catalog"."uuid_ops" ASC NULLS LAST,
  "template_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table stream_analysis_templates
-- ----------------------------
CREATE TRIGGER "update_stream_analysis_templates_updated_at" BEFORE UPDATE ON "public"."stream_analysis_templates"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table stream_analysis_templates
-- ----------------------------
ALTER TABLE "public"."stream_analysis_templates" ADD CONSTRAINT "stream_analysis_templates_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table system_configs
-- ----------------------------
CREATE INDEX "idx_system_configs_param_desc" ON "public"."system_configs" USING btree (
  "param_desc" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table system_configs
-- ----------------------------
CREATE TRIGGER "update_system_configs_updated_at" BEFORE UPDATE ON "public"."system_configs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table system_configs
-- ----------------------------
ALTER TABLE "public"."system_configs" ADD CONSTRAINT "system_configs_pkey" PRIMARY KEY ("param_code");

-- ----------------------------
-- Indexes structure for table users
-- ----------------------------
CREATE INDEX "idx_users_email" ON "public"."users" USING btree (
  "email" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_role" ON "public"."users" USING btree (
  "role" "pg_catalog"."enum_ops" ASC NULLS LAST
);
CREATE INDEX "idx_users_username" ON "public"."users" USING btree (
  "username" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table users
-- ----------------------------
CREATE TRIGGER "update_users_updated_at" BEFORE UPDATE ON "public"."users"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_username_key" UNIQUE ("username");
ALTER TABLE "public"."users" ADD CONSTRAINT "users_email_key" UNIQUE ("email");

-- ----------------------------
-- Primary Key structure for table users
-- ----------------------------
ALTER TABLE "public"."users" ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table video_analysis_results
-- ----------------------------
CREATE INDEX "idx_analysis_results_status" ON "public"."video_analysis_results" USING btree (
  "status" "pg_catalog"."enum_ops" ASC NULLS LAST
);
CREATE INDEX "idx_analysis_results_template_id" ON "public"."video_analysis_results" USING btree (
  "template_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_analysis_results_video_id" ON "public"."video_analysis_results" USING btree (
  "video_file_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table video_analysis_results
-- ----------------------------
ALTER TABLE "public"."video_analysis_results" ADD CONSTRAINT "video_analysis_results_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table video_analysis_templates
-- ----------------------------
CREATE INDEX "idx_video_analysis_templates_detection_type" ON "public"."video_analysis_templates" USING btree (
  "detection_type_code" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table video_analysis_templates
-- ----------------------------
CREATE TRIGGER "update_video_analysis_templates_updated_at" BEFORE UPDATE ON "public"."video_analysis_templates"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table video_analysis_templates
-- ----------------------------
ALTER TABLE "public"."video_analysis_templates" ADD CONSTRAINT "video_analysis_templates_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table video_files
-- ----------------------------
CREATE INDEX "idx_video_files_created_at" ON "public"."video_files" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_files_original_filename" ON "public"."video_files" USING btree (
  "original_filename" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_files_status" ON "public"."video_files" USING btree (
  "status" "pg_catalog"."enum_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_files_tags" ON "public"."video_files" USING gin (
  "tags" COLLATE "pg_catalog"."default" "pg_catalog"."array_ops"
);

-- ----------------------------
-- Triggers structure for table video_files
-- ----------------------------
CREATE TRIGGER "update_video_files_updated_at" BEFORE UPDATE ON "public"."video_files"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table video_files
-- ----------------------------
ALTER TABLE "public"."video_files" ADD CONSTRAINT "video_files_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table video_stream_algorithm_config_history
-- ----------------------------
CREATE INDEX "idx_video_stream_algorithm_config_history_config_id" ON "public"."video_stream_algorithm_config_history" USING btree (
  "config_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_stream_algorithm_config_history_operation_at" ON "public"."video_stream_algorithm_config_history" USING btree (
  "operation_at" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_stream_algorithm_config_history_stream_id" ON "public"."video_stream_algorithm_config_history" USING btree (
  "stream_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);

-- ----------------------------
-- Primary Key structure for table video_stream_algorithm_config_history
-- ----------------------------
ALTER TABLE "public"."video_stream_algorithm_config_history" ADD CONSTRAINT "video_stream_algorithm_config_history_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table video_stream_algorithm_configs
-- ----------------------------
CREATE INDEX "idx_video_stream_algorithm_configs_created_at" ON "public"."video_stream_algorithm_configs" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_stream_algorithm_configs_detection_type_codes" ON "public"."video_stream_algorithm_configs" USING gin (
  "detection_type_codes" "pg_catalog"."jsonb_ops"
);
COMMENT ON INDEX "public"."idx_video_stream_algorithm_configs_detection_type_codes" IS 'GIN索引用于优化detection_type_codes字段的查询性能，支持包含(@>)和相等(=)操作';
CREATE INDEX "idx_video_stream_algorithm_configs_is_active" ON "public"."video_stream_algorithm_configs" USING btree (
  "is_active" "pg_catalog"."bool_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_stream_algorithm_configs_stream_id" ON "public"."video_stream_algorithm_configs" USING btree (
  "stream_id" "pg_catalog"."uuid_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_stream_algorithm_configs_template_id" ON "public"."video_stream_algorithm_configs" USING btree (
  "template_id" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table video_stream_algorithm_configs
-- ----------------------------
CREATE TRIGGER "audit_video_stream_algorithm_config_trigger" AFTER INSERT OR UPDATE OR DELETE ON "public"."video_stream_algorithm_configs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."audit_video_stream_algorithm_config"();
CREATE TRIGGER "update_video_stream_algorithm_configs_updated_at" BEFORE UPDATE ON "public"."video_stream_algorithm_configs"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Uniques structure for table video_stream_algorithm_configs
-- ----------------------------
ALTER TABLE "public"."video_stream_algorithm_configs" ADD CONSTRAINT "uk_stream_algorithm_config" UNIQUE ("stream_id", "template_id");

-- ----------------------------
-- Primary Key structure for table video_stream_algorithm_configs
-- ----------------------------
ALTER TABLE "public"."video_stream_algorithm_configs" ADD CONSTRAINT "video_stream_algorithm_configs_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Indexes structure for table video_streams
-- ----------------------------
CREATE INDEX "idx_video_streams_created_at" ON "public"."video_streams" USING btree (
  "created_at" "pg_catalog"."timestamptz_ops" DESC NULLS FIRST
);
CREATE INDEX "idx_video_streams_group" ON "public"."video_streams" USING btree (
  "group_name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_streams_location" ON "public"."video_streams" USING btree (
  "location" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_streams_name" ON "public"."video_streams" USING btree (
  "name" COLLATE "pg_catalog"."default" "pg_catalog"."text_ops" ASC NULLS LAST
);
CREATE INDEX "idx_video_streams_status" ON "public"."video_streams" USING btree (
  "status" "pg_catalog"."enum_ops" ASC NULLS LAST
);

-- ----------------------------
-- Triggers structure for table video_streams
-- ----------------------------
CREATE TRIGGER "update_video_streams_updated_at" BEFORE UPDATE ON "public"."video_streams"
FOR EACH ROW
EXECUTE PROCEDURE "public"."update_updated_at_column"();

-- ----------------------------
-- Primary Key structure for table video_streams
-- ----------------------------
ALTER TABLE "public"."video_streams" ADD CONSTRAINT "video_streams_pkey" PRIMARY KEY ("id");

-- ----------------------------
-- Foreign Keys structure for table ai_agent_history
-- ----------------------------
ALTER TABLE "public"."ai_agent_history" ADD CONSTRAINT "fk_ai_agent_history_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table ai_agent_sessions
-- ----------------------------
ALTER TABLE "public"."ai_agent_sessions" ADD CONSTRAINT "fk_ai_agent_sessions_user_id" FOREIGN KEY ("user_id") REFERENCES "public"."users" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table video_analysis_templates
-- ----------------------------
ALTER TABLE "public"."video_analysis_templates" ADD CONSTRAINT "fk_video_analysis_templates_detection_type" FOREIGN KEY ("detection_type_code") REFERENCES "public"."detection_type_templates" ("type_code") ON DELETE SET NULL ON UPDATE NO ACTION;

-- ----------------------------
-- Foreign Keys structure for table video_stream_algorithm_configs
-- ----------------------------
ALTER TABLE "public"."video_stream_algorithm_configs" ADD CONSTRAINT "fk_stream_algorithm_configs_stream_id" FOREIGN KEY ("stream_id") REFERENCES "public"."video_streams" ("id") ON DELETE CASCADE ON UPDATE NO ACTION;
