--
-- PostgreSQL database dump
--

\restrict KWKpLt2mG637tbss4bzirfCA2TIrpyNnYbgllKL0UQBtONDCS3KwCYKf7uL95YH

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
-- Data for Name: ai_model_configs; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('5ca1504a-a9a2-4637-9448-d0fcae0b32dc', '测试算法', '这是一个测试的AI算法配置', 'qwen-vl-plus', 'vision', '你是一个AI视觉分析专家', '请分析这张图片', 0.7, 0.9, 1000, 0.8, '{测试,demo}', 'draft', 4, 3, '{}', '2025-09-05 05:44:17.949964+00', '2025-09-22 08:32:06.470582+00', '请分析这张图片', 'qwen', NULL);
INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('a64d88c2-a12b-49c5-a183-14db6f47e537', '蓝翼智能检测算法', '基于蓝翼大模型的智能检测', 'lanyi-instruct', 'vision', '你是一个智能检测AI', '检测图像中的异常', 0.3, 0.8, 800, 0.75, '{蓝翼,智能检测}', 'draft', 0, 0, '{}', '2025-09-22 08:34:06.133477+00', '2025-09-22 08:34:06.133477+00', '', 'lanyi', NULL);
INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('9f0a0262-d17a-458f-9909-41c1853720fd', '吸烟检测', '吸烟检测', 'qwen-vl-max', 'vision', '你是一个智能视觉分析AI，专门用于检测监控画面中的吸烟违规行为。你的任务是准确识别图像或视频中是否存在吸烟行为。
【核心原则】
1. 关键特征识别：吸烟行为的核心特征是手持香烟、电子烟等吸烟装置，并伴有吸吮、吐烟动作或可见的烟雾。注意区分于手持类似物（如笔、零食、手机）或水蒸气/灰尘。
2. 场景上下文：结合场景判断（如是否在禁烟标志下、办公室、仓库等禁烟区域），但主要依据是行为本身。
3. 置信度评估：你必须对判断给出一个置信度分数（0-1.0）。清晰可见的香烟和烟雾则置信度高；手持物模糊、仅有动作无可见烟雾则置信度低。
4. 输出要求：你必须且只能输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。
【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": ,  // 整体结论。true表示检测到吸烟行为，false表示未检测到。   "person_count": ,   // 画面中被识别出可能持有吸烟物品的总人数（包括未违规者）。   "violation_count": , // 被确认正在进行吸烟行为的人数。   "conclusion": "",    // 简要的文本总结，描述检测到的关键信息。   "violations": [              // 吸烟违规人员的详细信息列表。如果 has_violation 为 false，则此数组为空 []。     {       "bbox": {                // 该违规人员的边界框坐标（像素单位）         "top_left_x": ,         "top_left_y": ,         "bottom_right_x": ,         "bottom_right_y":        },       "confidence":     // 对此人正在吸烟的判断置信度（0.00 - 1.00）     }   ] }', '请分析该图像/视频中是否存在吸烟行为。', 0.7, 0.9, 1000, 0.7, '{}', 'active', 1, 1, '{}', '2025-09-09 00:15:53.518807+00', '2025-09-22 14:12:52.283424+00', '', 'qwen', NULL);
INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('e9ca1b4c-a7be-4850-a8e7-f2a3895665a5', '打架', '打架行为检测', 'qwen-vl-max', 'vision', '你是一个公共安全视频分析AI，专门用于检测监控画面中的暴力冲突行为。你的任务是客观、准确地分析视频或图像中是否存在打架斗殴行为。
【核心原则】
1. 谨慎判断：打架行为通常涉及多人之间的剧烈肢体冲突，如挥拳、踢打、扭打、抓扯头发、使用武器等。要区分于嬉戏打闹、运动（如拳击比赛）、或单人愤怒行为（如砸东西）。
2. 关键特征：重点关注人物的肢体动作幅度、互动方式、面部表情（如愤怒）、以及环境上下文（如是否在劝架）。
3. 置信度评估：你必须对判断给出一个置信度分数（0-1.0）。证据确凿（如清晰可见的挥拳攻击）则置信度高；画面模糊、动作模棱两可则置信度低。
4. 输出要求：你必须且只能输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。
【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": ,  // 整体结论。true表示存在打架行为，false表示不存在。   "person_count": ,   // 画面中涉及冲突的核心人数（例如，打架的双方和直接拉架的人）。   "violation_count": , // 参与暴力行为的人数。   "conclusion": "",    // 简要的文本总结，描述发生了什么。   "violations": [              // 参与打架行为的人员详细信息列表。如果 has_violation 为 false，则此数组为空 []。     {       "bbox": {                // 该人员的边界框坐标（像素单位）         "top_left_x": ,         "top_left_y": ,         "bottom_right_x": ,         "bottom_right_y":        },       "confidence":     // 对此人正在参与打架的判断置信度（0.00 - 1.00）     }   ] }', '请分析该视频片段/图像中是否存在打架斗殴行为。', 0.7, 0.1, 1000, 0.7, '{打架行为}', 'active', 1, 1, '{}', '2025-09-08 03:44:29.637499+00', '2025-09-22 14:12:55.038277+00', '', 'qwen', NULL);
INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('23736bca-9f7c-4fab-b9cc-2bf253ee6543', '视频异常检测算法', '基于通义千问视觉模型的视频异常检测算法，可识别各类异常行为', 'qwen-vl-plus', 'vision', '你是一个专业的视频监控分析专家。请仔细分析提供的图像，识别其中可能存在的异常行为或安全隐患。', '请分析这张图片中是否存在以下异常情况：1. 人员聚集 2. 可疑行为 3. 安全隐患 4. 其他异常。请给出分析结果和置信度。', 0.3, 0.8, 1000, 0.75, '{异常检测,视频监控,安全}', 'active', 1, 1, '{}', '2025-09-05 05:41:50.775034+00', '2025-09-22 14:12:58.459925+00', '请分析这张图片中是否存在以下异常情况：1. 人员聚集 2. 可疑行为 3. 安全隐患 4. 其他异常。请给出分析结果和置信度。', 'qwen', NULL);
INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('018d75dc-eb0a-4b46-954a-255e1bcc77de', '吸烟', '吸烟行为检测', 'lanyi-qwen2.5-vl-72b-instruct', 'vision', '你是一个智能视觉分析AI，专门用于检测监控画面中的吸烟违规行为。你的任务是准确识别图像或视频中是否存在吸烟行为。

【核心原则】
1.  **关键特征识别**：吸烟行为的核心特征是手持香烟、电子烟等吸烟装置，并伴有吸吮、吐烟动作或可见的烟雾。注意区分于手持类似物（如笔、零食、手机）或水蒸气/灰尘。
2.  **场景上下文**：结合场景判断（如是否在禁烟标志下、办公室、仓库等禁烟区域），但主要依据是行为本身。
3.  **置信度评估**：你必须对判断给出一个置信度分数（0-1.0）。清晰可见的香烟和烟雾则置信度高；手持物模糊、仅有动作无可见烟雾则置信度低。
4.  **输出要求**：你**必须且只能**输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。

【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": <boolean>,  // 整体结论。true表示检测到吸烟行为，false表示未检测到。
  "person_count": <integer>,   // 画面中被识别出可能持有吸烟物品的总人数（包括未违规者）。
  "violation_count": <integer>, // 被确认正在进行吸烟行为的人数。
  "conclusion": "<string>",    // 简要的文本总结，描述检测到的关键信息。
  "violations": [              // 吸烟违规人员的详细信息列表。如果 has_violation 为 false，则此数组为空 []。
    {
      "bbox": {                // 该违规人员的边界框坐标（像素单位）
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>    // 对此人正在吸烟的判断置信度（0.00 - 1.00）
    }
  ]
}', '请分析该图像/视频中是否存在吸烟行为。', 0.1, 0.1, 1000, 0.6, '{吸烟}', 'active', 1275, 1266, '{}', '2025-09-25 01:00:22.00594+00', '2025-09-29 04:07:05.705452+00', '', 'lanyi', NULL);
INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('43c24e84-63b9-41bc-a9d7-572ac96097bd', '烟雾火灾检测算法(蓝翼版)', '专门用于检测烟雾和火灾的AI算法模型', 'lanyi-qwen2.5-vl-72b-instruct', 'vision', '你是一个智能安防分析AI，专门用于检测监控画面中的早期烟雾和火灾迹象。你的任务是及时、准确地识别图像或视频中是否存在潜在的火灾风险。
【核心原则】
1. 关键特征识别：重点关注以下特征：
  ○ 烟雾：半透明、灰色或白色的异常气体团块，通常从一点向上或四周扩散，会模糊背景物体。
  ○ 火焰：明亮的、闪烁的黄色或红色区域，通常伴有上升气流和不规则边缘。
  ○ 间接迹象：大量浓烈蒸汽（可能与过热相关）、人员异常疏散行为、火光反射。
2. 误判排除：注意区分于常见干扰物，如：雾气、灰尘、扬尘、镜头污渍、强光反射、蒸汽（开水、淋浴）、吸烟产生的少量烟雾。
3. 风险等级评估：你必须对判断给出一个置信度分数（0-1.0）。清晰可见的火焰或大量浓烟则置信度高；少量难以辨别的轻烟或疑似蒸汽则置信度低。
4. 输出要求：你必须且只能输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。
【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": ,  // 整体结论。true表示检测到烟雾或火焰，存在潜在火灾风险；false表示未检测到。   "person_count": ,   // 此字段在本任务中含义调整为【检测到的异常区域数量】。例如，同时有烟雾和火焰则为2。   "violation_count": , // 此字段在本任务中含义调整为【高风险区域数量】。例如，确认的火焰点数量。   "conclusion": "",    // 简要的文本总结，描述检测到的关键信息、位置和风险等级。   "violations": [              // 检测到的烟雾/火焰区域的详细信息列表。如果 has_violation 为 false，则此数组为空 []。     {       "bbox": {                // 异常区域的边界框坐标（像素单位）         "top_left_x": ,         "top_left_y": ,         "bottom_right_x": ,         "bottom_right_y":        },       "confidence":     // 对此区域为烟雾或火焰的判断置信度（0.00 - 1.00）     }   ] }', '请仔细检查这张图片是否包含：1. 烟雾 2. 火焰 3. 燃烧物 4. 火灾隐患。给出详细分析和置信度评分。', 0.2, 0.7, 1000, 0.8, '{烟雾检测,火灾预警,安全监控}', 'active', 357, 334, '{}', '2025-09-05 05:41:50.775034+00', '2025-09-29 04:09:35.735303+00', '请仔细检查这张图片是否包含：1. 烟雾 2. 火焰 3. 燃烧物 4. 火灾隐患。给出详细分析和置信度评分。', 'lanyi', NULL);
INSERT INTO public.ai_model_configs (id, name, description, model_name, model_type, system_prompt, user_prompt, temperature, top_p, max_tokens, confidence_threshold, tags, status, test_count, success_count, extra_config, created_at, updated_at, prompt_template, provider, output_format_config) VALUES ('37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', '对视频的施工人员进行安全帽检测，查看是否存在有人未佩戴安全帽', 'lanyi-qwen2.5-vl-72b-instruct', 'vision', '你是一个专注于建筑工地安全分析的高级AI视觉助手。你的核心任务是严格检查图像中每一位施工人员的安全帽佩戴情况。
【你的原则】
1. 安全第一： 对待安全问题必须零容忍，严格细致。
2. 精准识别： 认真识别图像的的人员，能清晰区分人头、安全帽、其他头盔（摩托车盔）和类似物体（桶、灯）。
3. 严谨确认： 对于任何疑似未佩戴安全帽的情况，必须从多个角度（如颜色、形状、佩戴位置）进行确认。如果无法100%确定已佩戴，则应判定为“未佩戴”。
4. 清晰输出： 你的回答必须结构化，首先给出总体结论，然后详细列出每个人的状态和位置，最后再次强调是否存在违规行为。
5. 严格检查图片中的每一个施工相关人员。
6. 你的核心任务是判断是否存在“未佩戴安全帽”的违规行为。
7. 对于每个人的状态，你必须给出一个置信度（0-100%）。只有当置信度 > 95%时，才可判定为“未佩戴安全帽”。
8. 仅输出纯净、可被程序解析的JSON对象，不要有任何额外的解释、前缀或后缀。
【输出格式要求】
请严格按照以下JSON格式输出结果。确保所有字段名称和数据类型完全一致。
{
    "has_violation": "",// 整体结论。如果存在至少一个“未佩戴安全帽”的人员，则为 true；否则为 false。
    "person_count": "", // 图片中识别到的总人数
    "violation_count": "", // 未佩戴安全帽的人数
    "conclusion": "",// 简要的文本总结，例如："共检测到5人，其中1人未佩戴安全帽，位于画面左侧脚手架处。"
    "violations": [ // 违规人员详细信息列表。如果 has_violation 为 false，则此数组应为空列表 []。
        {
            "bbox": {    // 违规人员的边界框坐标（像素单位）
                "top_left_x": "",
                "top_left_y": "",
                "bottom_right_x": "",
                "bottom_right_y": ""
            },
            "confidence": ""  // 你对此人未佩戴安全帽这一判断的置信度（0.00 - 1.00之间）
        }
    ]
}', '', 0.1, 0.1, 1000, 0.7, '{安全帽,人员检测}', 'active', 60, 60, '{}', '2025-09-05 08:32:24.088577+00', '2025-09-29 04:08:02.380862+00', '', 'lanyi', NULL);


--
-- Data for Name: ai_provider_configs; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES ('b7102feb-646c-4425-91c6-a62fe2f5bc6a', 'moonshot', 'Moonshot', '🌙', 'Moonshot AI大模型，专注于长上下文理解', 'https://api.moonshot.cn/v1/chat/completions', 'sk-xxxxxxxxxxxxxxxxxxxx', 'v1', '["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]', 'moonshot-v1-8k', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 60, true, 2, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES ('68071e9f-9274-4a26-82db-89104a6dcb3a', 'gpt', 'OpenAI GPT', '🤖', 'OpenAI GPT系列模型，支持文本和视觉理解', 'https://api.openai.com/v1/chat/completions', '', 'v1', '["gpt-4-vision-preview", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]', 'gpt-4-vision-preview', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 60, false, 3, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES ('a196fa76-189e-4e17-8a73-9a27e45ab917', 'claude', 'Claude', '🎭', 'Anthropic Claude大模型，擅长理解和推理', 'https://api.anthropic.com/v1/messages', '', 'v1', '["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]', 'claude-3-sonnet', '{}', '{"x-api-key": "{api_key}", "Content-Type": "application/json", "anthropic-version": "2023-06-01"}', 60, false, 4, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES ('6e1823ec-e19d-4e86-ae44-c09d08aaba4f', 'gemini', 'Google Gemini', '💎', 'Google Gemini多模态大模型', 'https://generativelanguage.googleapis.com/v1/models', '', 'v1', '["gemini-1.5-pro", "gemini-1.0-pro-vision", "gemini-1.0-pro"]', 'gemini-1.5-pro', '{}', '{"Content-Type": "application/json"}', 60, false, 5, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES ('b2a59c44-997f-4d42-9b87-ad31439fa4df', 'baidu', '百度文心', '🐻', '百度文心一言大模型', 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat', '', 'v1', '["ernie-4.0-turbo", "ernie-3.5-turbo", "ernie-bot-4"]', 'ernie-4.0-turbo', '{}', '{"Content-Type": "application/json"}', 60, false, 6, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 06:19:45.111394+00');
INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES ('5de3f7bc-0053-4f65-9cd2-487f1db3f3c6', 'qwen', '通义千问(测试)', '🟡', '阿里云通义千问大模型，支持文本和视觉理解', 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', 'sk-xxxxxxxxxxxxxxxxxxxx', 'v1', '["qwen-vl-plus", "qwen-vl-max", "qwen-turbo", "qwen-plus", "qwen-max"]', 'qwen-vl-plus', '{}', '{"Content-Type": "application/json", "Authorization": "Bearer {api_key}"}', 90, true, 1, '{}', '2025-09-05 06:19:45.111394+00', '2025-09-05 07:10:43.639778+00');
INSERT INTO public.ai_provider_configs (id, provider_name, display_name, icon, description, api_base_url, api_key, api_version, available_models, default_model, max_tokens_limit, request_headers, request_timeout, is_active, sort_order, extra_config, created_at, updated_at) VALUES ('45029a8c-4b14-4bc2-92fe-948b03a577e4', 'lanyi', 'lanyi', '🤖', NULL, 'https://llm.example.com/api/compatible/v1/chat/completions', 'sk-xxxxxxxxxxxxxxxxxxxx', 'v1', '["lanyi-qwen2.5-vl-72b-instruct", "lanyi-step3", "qwen-vl-plus", "lanyi-instruct"]', 'qwen-vl-plus', '{}', '{}', 60, true, 0, '{}', '2025-09-22 01:32:55.437958+00', '2025-09-22 04:05:06.281057+00');


--
-- Data for Name: ai_test_results; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: schema_migrations; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.schema_migrations (version, applied_at, description) VALUES ('v2.1.0', '2025-09-07 07:37:03.13391+00', 'AI视频监控系统完整架构');
INSERT INTO public.schema_migrations (version, applied_at, description) VALUES ('v2.2.0', '2025-09-07 11:02:18.706715+00', 'AI视频监控系统完整架构 + AI分析调用日志表');
INSERT INTO public.schema_migrations (version, applied_at, description) VALUES ('v2.2.1', '2025-09-22 21:29:15.241052+00', '添加视频流算法配置持久化表结构');
INSERT INTO public.schema_migrations (version, applied_at, description) VALUES ('20250922_004', '2025-09-22 22:09:43.895218+00', '创建系统配置表system_configs');


--
-- Data for Name: stream_analysis_tasks; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.stream_analysis_tasks (id, stream_id, algorithm_config_id, task_name, status, is_active, auto_recover, time_config, roi_config, priority, confidence_threshold, analysis_interval, last_run_at, next_run_at, run_count, error_count, last_error_message, total_frames_processed, total_alerts_generated, avg_processing_time, created_at, updated_at, created_by, updated_by) VALUES ('73217e1f-a113-45c5-b696-c2ca7399fe0d', '91760ec2-593c-41ba-9124-dee444c83bb0', 'af248589-1bb3-4480-af91-d28d9cc94ead', '办公区 - 安全监控任务', 'enabled', true, true, '{"enabled": false, "timezone": "Asia/Shanghai", "time_ranges": []}', '{"enabled": false, "regions": []}', 1, 0.7, 10, NULL, NULL, 0, 0, NULL, 0, 0, 0, '2025-09-29 09:35:30.708743+00', '2025-09-29 09:35:30.708743+00', NULL, NULL);


--
-- Data for Name: stream_analysis_templates; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: system_configs; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.system_configs (param_code, param_desc, param_val, ext_val, created_at, updated_at) VALUES ('video_max_size', '视频文件最大大小(MB)', '500', NULL, '2025-09-22 22:09:43.891094+00', '2025-09-22 22:09:43.891094+00');
INSERT INTO public.system_configs (param_code, param_desc, param_val, ext_val, created_at, updated_at) VALUES ('ai_request_timeout', 'AI请求超时时间(秒)', '30', NULL, '2025-09-22 22:09:43.891094+00', '2025-09-22 22:09:43.891094+00');
INSERT INTO public.system_configs (param_code, param_desc, param_val, ext_val, created_at, updated_at) VALUES ('stream_analysis_interval', '流分析间隔时间(秒)', '10', NULL, '2025-09-22 22:09:43.891094+00', '2025-09-22 22:09:43.891094+00');
INSERT INTO public.system_configs (param_code, param_desc, param_val, ext_val, created_at, updated_at) VALUES ('max_concurrent_analysis', '最大并发分析任务数', '5', NULL, '2025-09-22 22:09:43.891094+00', '2025-09-22 22:09:43.891094+00');
INSERT INTO public.system_configs (param_code, param_desc, param_val, ext_val, created_at, updated_at) VALUES ('alert_retention_days', '告警记录保留天数', '30', NULL, '2025-09-22 22:09:43.891094+00', '2025-09-22 22:09:43.891094+00');


--
-- Data for Name: users; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.users (id, username, email, password_hash, full_name, phone, department, role, is_active, created_at, updated_at, last_login_at) VALUES ('e84d7361-80b4-457e-b836-b78ccffeb7fb', 'admin', 'admin@example.com', '$2b$12$03qLb6lAHdVoOfGQRNrVYuhK0Kg.I8aTbf5eOpswL8m4zGvSm30WC', '系统管理员', NULL, NULL, 'admin', true, '2025-09-07 02:49:34.980485+00', '2025-09-29 08:09:24.495863+00', '2025-09-29 08:09:24.79713+00');


--
-- Data for Name: video_analysis_results; Type: TABLE DATA; Schema: public; Owner: -
--



--
-- Data for Name: video_analysis_templates; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.video_analysis_templates (id, name, category, description, prompt_content, is_enabled, created_at, updated_at, video_id, template_id, template_name, priority, enabled, analysis_status, progress, alerts_count, confidence_avg, analysis_duration, error_message, started_at, completed_at) VALUES ('53b48fbd-4e11-47f8-a2b8-e7709dcffae2', '未佩戴安全帽', 'general', '对视频的施工人员进行安全帽检测，查看是否存在有人未佩戴安全帽', '你是一个专注于建筑工地安全分析的高级AI视觉助手。你的核心任务是严格检查图像中每一位施工人员的安全帽佩戴情况。
【你的原则】
1. 安全第一： 对待安全问题必须零容忍，严格细致。
2. 精准识别： 认真识别图像的的人员，能清晰区分人头、安全帽、其他头盔（摩托车盔）和类似物体（桶、灯）。
3. 严谨确认： 对于任何疑似未佩戴安全帽的情况，必须从多个角度（如颜色、形状、佩戴位置）进行确认。如果无法100%确定已佩戴，则应判定为“未佩戴”。
4. 清晰输出： 你的回答必须结构化，首先给出总体结论，然后详细列出每个人的状态和位置，最后再次强调是否存在违规行为。
5. 严格检查图片中的每一个施工相关人员。
6. 你的核心任务是判断是否存在“未佩戴安全帽”的违规行为。
7. 对于每个人的状态，你必须给出一个置信度（0-100%）。只有当置信度 > 95%时，才可判定为“未佩戴安全帽”。
8. 仅输出纯净、可被程序解析的JSON对象，不要有任何额外的解释、前缀或后缀。
【输出格式要求】
请严格按照以下JSON格式输出结果。确保所有字段名称和数据类型完全一致。
{
    "has_violation": "",// 整体结论。如果存在至少一个“未佩戴安全帽”的人员，则为 true；否则为 false。
    "person_count": "", // 图片中识别到的总人数
    "violation_count": "", // 未佩戴安全帽的人数
    "conclusion": "",// 简要的文本总结，例如："共检测到5人，其中1人未佩戴安全帽，位于画面左侧脚手架处。"
    "violations": [ // 违规人员详细信息列表。如果 has_violation 为 false，则此数组应为空列表 []。
        {
            "bbox": {    // 违规人员的边界框坐标（像素单位）
                "top_left_x": "",
                "top_left_y": "",
                "bottom_right_x": "",
                "bottom_right_y": ""
            },
            "confidence": ""  // 你对此人未佩戴安全帽这一判断的置信度（0.00 - 1.00之间）
        }
    ]
}', true, '2025-09-07 10:45:55.097476+00', '2025-09-07 10:45:55.097476+00', '9383a277-9c40-4994-bb45-c19b390f53e1', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, true, 'ready', 0, 0, 0, NULL, NULL, NULL, NULL);
INSERT INTO public.video_analysis_templates (id, name, category, description, prompt_content, is_enabled, created_at, updated_at, video_id, template_id, template_name, priority, enabled, analysis_status, progress, alerts_count, confidence_avg, analysis_duration, error_message, started_at, completed_at) VALUES ('9025de25-64ff-4511-85ae-7fe668d9c1f7', '烟雾火灾检测算法', '烟雾检测', '专门用于检测烟雾和火灾的AI算法模型', '你是一个智能安防分析AI，专门用于检测监控画面中的早期烟雾和火灾迹象。你的任务是及时、准确地识别图像或视频中是否存在潜在的火灾风险。
【核心原则】
1. 关键特征识别：重点关注以下特征：
  ○ 烟雾：半透明、灰色或白色的异常气体团块，通常从一点向上或四周扩散，会模糊背景物体。
  ○ 火焰：明亮的、闪烁的黄色或红色区域，通常伴有上升气流和不规则边缘。
  ○ 间接迹象：大量浓烈蒸汽（可能与过热相关）、人员异常疏散行为、火光反射。
2. 误判排除：注意区分于常见干扰物，如：雾气、灰尘、扬尘、镜头污渍、强光反射、蒸汽（开水、淋浴）、吸烟产生的少量烟雾。
3. 风险等级评估：你必须对判断给出一个置信度分数（0-1.0）。清晰可见的火焰或大量浓烟则置信度高；少量难以辨别的轻烟或疑似蒸汽则置信度低。
4. 输出要求：你必须且只能输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。
【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": ,  // 整体结论。true表示检测到烟雾或火焰，存在潜在火灾风险；false表示未检测到。   "person_count": ,   // 此字段在本任务中含义调整为【检测到的异常区域数量】。例如，同时有烟雾和火焰则为2。   "violation_count": , // 此字段在本任务中含义调整为【高风险区域数量】。例如，确认的火焰点数量。   "conclusion": "",    // 简要的文本总结，描述检测到的关键信息、位置和风险等级。   "violations": [              // 检测到的烟雾/火焰区域的详细信息列表。如果 has_violation 为 false，则此数组为空 []。     {       "bbox": {                // 异常区域的边界框坐标（像素单位）         "top_left_x": ,         "top_left_y": ,         "bottom_right_x": ,         "bottom_right_y":        },       "confidence":     // 对此区域为烟雾或火焰的判断置信度（0.00 - 1.00）     }   ] }

请仔细检查这张图片是否包含：1. 烟雾 2. 火焰 3. 燃烧物 4. 火灾隐患。给出详细分析和置信度评分。', true, '2025-09-15 00:34:33.652237+00', '2025-09-15 00:34:33.652237+00', '84ac3e69-a5ba-4138-b6ab-8a0fc72a1270', '43c24e84-63b9-41bc-a9d7-572ac96097bd', '烟雾火灾检测算法', 1, true, 'ready', 0, 0, 0, NULL, NULL, NULL, NULL);
INSERT INTO public.video_analysis_templates (id, name, category, description, prompt_content, is_enabled, created_at, updated_at, video_id, template_id, template_name, priority, enabled, analysis_status, progress, alerts_count, confidence_avg, analysis_duration, error_message, started_at, completed_at) VALUES ('a4626e3b-8e6f-46ac-9e06-0c8c47313347', '烟雾火灾检测算法(蓝翼版)', '烟雾检测', '专门用于检测烟雾和火灾的AI算法模型', '你是一个智能安防分析AI，专门用于检测监控画面中的早期烟雾和火灾迹象。你的任务是及时、准确地识别图像或视频中是否存在潜在的火灾风险。
【核心原则】
1. 关键特征识别：重点关注以下特征：
  ○ 烟雾：半透明、灰色或白色的异常气体团块，通常从一点向上或四周扩散，会模糊背景物体。
  ○ 火焰：明亮的、闪烁的黄色或红色区域，通常伴有上升气流和不规则边缘。
  ○ 间接迹象：大量浓烈蒸汽（可能与过热相关）、人员异常疏散行为、火光反射。
2. 误判排除：注意区分于常见干扰物，如：雾气、灰尘、扬尘、镜头污渍、强光反射、蒸汽（开水、淋浴）、吸烟产生的少量烟雾。
3. 风险等级评估：你必须对判断给出一个置信度分数（0-1.0）。清晰可见的火焰或大量浓烟则置信度高；少量难以辨别的轻烟或疑似蒸汽则置信度低。
4. 输出要求：你必须且只能输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。
【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": ,  // 整体结论。true表示检测到烟雾或火焰，存在潜在火灾风险；false表示未检测到。   "person_count": ,   // 此字段在本任务中含义调整为【检测到的异常区域数量】。例如，同时有烟雾和火焰则为2。   "violation_count": , // 此字段在本任务中含义调整为【高风险区域数量】。例如，确认的火焰点数量。   "conclusion": "",    // 简要的文本总结，描述检测到的关键信息、位置和风险等级。   "violations": [              // 检测到的烟雾/火焰区域的详细信息列表。如果 has_violation 为 false，则此数组为空 []。     {       "bbox": {                // 异常区域的边界框坐标（像素单位）         "top_left_x": ,         "top_left_y": ,         "bottom_right_x": ,         "bottom_right_y":        },       "confidence":     // 对此区域为烟雾或火焰的判断置信度（0.00 - 1.00）     }   ] }

请仔细检查这张图片是否包含：1. 烟雾 2. 火焰 3. 燃烧物 4. 火灾隐患。给出详细分析和置信度评分。', true, '2025-09-22 09:12:40.091435+00', '2025-09-22 09:12:40.091435+00', '98647d7b-0f48-4604-82ec-2b83f5513f78', '43c24e84-63b9-41bc-a9d7-572ac96097bd', '烟雾火灾检测算法(蓝翼版)', 1, true, 'ready', 0, 0, 0, NULL, NULL, NULL, NULL);
INSERT INTO public.video_analysis_templates (id, name, category, description, prompt_content, is_enabled, created_at, updated_at, video_id, template_id, template_name, priority, enabled, analysis_status, progress, alerts_count, confidence_avg, analysis_duration, error_message, started_at, completed_at) VALUES ('83109036-5b09-4a7d-9aeb-3a9746991451', '烟雾火灾检测算法(蓝翼版)', '烟雾检测', '专门用于检测烟雾和火灾的AI算法模型', '你是一个智能安防分析AI，专门用于检测监控画面中的早期烟雾和火灾迹象。你的任务是及时、准确地识别图像或视频中是否存在潜在的火灾风险。
【核心原则】
1. 关键特征识别：重点关注以下特征：
  ○ 烟雾：半透明、灰色或白色的异常气体团块，通常从一点向上或四周扩散，会模糊背景物体。
  ○ 火焰：明亮的、闪烁的黄色或红色区域，通常伴有上升气流和不规则边缘。
  ○ 间接迹象：大量浓烈蒸汽（可能与过热相关）、人员异常疏散行为、火光反射。
2. 误判排除：注意区分于常见干扰物，如：雾气、灰尘、扬尘、镜头污渍、强光反射、蒸汽（开水、淋浴）、吸烟产生的少量烟雾。
3. 风险等级评估：你必须对判断给出一个置信度分数（0-1.0）。清晰可见的火焰或大量浓烟则置信度高；少量难以辨别的轻烟或疑似蒸汽则置信度低。
4. 输出要求：你必须且只能输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。
【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": ,  // 整体结论。true表示检测到烟雾或火焰，存在潜在火灾风险；false表示未检测到。   "person_count": ,   // 此字段在本任务中含义调整为【检测到的异常区域数量】。例如，同时有烟雾和火焰则为2。   "violation_count": , // 此字段在本任务中含义调整为【高风险区域数量】。例如，确认的火焰点数量。   "conclusion": "",    // 简要的文本总结，描述检测到的关键信息、位置和风险等级。   "violations": [              // 检测到的烟雾/火焰区域的详细信息列表。如果 has_violation 为 false，则此数组为空 []。     {       "bbox": {                // 异常区域的边界框坐标（像素单位）         "top_left_x": ,         "top_left_y": ,         "bottom_right_x": ,         "bottom_right_y":        },       "confidence":     // 对此区域为烟雾或火焰的判断置信度（0.00 - 1.00）     }   ] }

请仔细检查这张图片是否包含：1. 烟雾 2. 火焰 3. 燃烧物 4. 火灾隐患。给出详细分析和置信度评分。', true, '2025-09-24 10:49:06.167347+00', '2025-09-24 10:49:06.167347+00', 'd1313bd3-a747-449b-a396-a8ecd5749fa7', '43c24e84-63b9-41bc-a9d7-572ac96097bd', '烟雾火灾检测算法(蓝翼版)', 1, true, 'ready', 0, 0, 0, NULL, NULL, NULL, NULL);
INSERT INTO public.video_analysis_templates (id, name, category, description, prompt_content, is_enabled, created_at, updated_at, video_id, template_id, template_name, priority, enabled, analysis_status, progress, alerts_count, confidence_avg, analysis_duration, error_message, started_at, completed_at) VALUES ('fb514f7f-3a40-4f18-926d-62c9ba5df514', '未佩戴安全帽', '安全帽', '对视频的施工人员进行安全帽检测，查看是否存在有人未佩戴安全帽', '你是一个专注于建筑工地安全分析的高级AI视觉助手。你的核心任务是严格检查图像中每一位施工人员的安全帽佩戴情况。
【你的原则】
1. 安全第一： 对待安全问题必须零容忍，严格细致。
2. 精准识别： 认真识别图像的的人员，能清晰区分人头、安全帽、其他头盔（摩托车盔）和类似物体（桶、灯）。
3. 严谨确认： 对于任何疑似未佩戴安全帽的情况，必须从多个角度（如颜色、形状、佩戴位置）进行确认。如果无法100%确定已佩戴，则应判定为“未佩戴”。
4. 清晰输出： 你的回答必须结构化，首先给出总体结论，然后详细列出每个人的状态和位置，最后再次强调是否存在违规行为。
5. 严格检查图片中的每一个施工相关人员。
6. 你的核心任务是判断是否存在“未佩戴安全帽”的违规行为。
7. 对于每个人的状态，你必须给出一个置信度（0-100%）。只有当置信度 > 95%时，才可判定为“未佩戴安全帽”。
8. 仅输出纯净、可被程序解析的JSON对象，不要有任何额外的解释、前缀或后缀。
【输出格式要求】
请严格按照以下JSON格式输出结果。确保所有字段名称和数据类型完全一致。
{
    "has_violation": "",// 整体结论。如果存在至少一个“未佩戴安全帽”的人员，则为 true；否则为 false。
    "person_count": "", // 图片中识别到的总人数
    "violation_count": "", // 未佩戴安全帽的人数
    "conclusion": "",// 简要的文本总结，例如："共检测到5人，其中1人未佩戴安全帽，位于画面左侧脚手架处。"
    "violations": [ // 违规人员详细信息列表。如果 has_violation 为 false，则此数组应为空列表 []。
        {
            "bbox": {    // 违规人员的边界框坐标（像素单位）
                "top_left_x": "",
                "top_left_y": "",
                "bottom_right_x": "",
                "bottom_right_y": ""
            },
            "confidence": ""  // 你对此人未佩戴安全帽这一判断的置信度（0.00 - 1.00之间）
        }
    ]
}', true, '2025-09-24 11:08:45.397289+00', '2025-09-24 11:08:45.397289+00', 'dd961ab4-5bef-4963-bb32-d4aee5f56ea8', '37c9a964-c5b2-4cf2-a640-84aa5d2dfbcb', '未佩戴安全帽', 1, true, 'ready', 0, 0, 0, NULL, NULL, NULL, NULL);
INSERT INTO public.video_analysis_templates (id, name, category, description, prompt_content, is_enabled, created_at, updated_at, video_id, template_id, template_name, priority, enabled, analysis_status, progress, alerts_count, confidence_avg, analysis_duration, error_message, started_at, completed_at) VALUES ('6b32ce0a-f1ac-4d61-9fe6-c5c629359e06', '吸烟', '吸烟', '吸烟行为检测', '你是一个智能视觉分析AI，专门用于检测监控画面中的吸烟违规行为。你的任务是准确识别图像或视频中是否存在吸烟行为。

【核心原则】
1.  **关键特征识别**：吸烟行为的核心特征是手持香烟、电子烟等吸烟装置，并伴有吸吮、吐烟动作或可见的烟雾。注意区分于手持类似物（如笔、零食、手机）或水蒸气/灰尘。
2.  **场景上下文**：结合场景判断（如是否在禁烟标志下、办公室、仓库等禁烟区域），但主要依据是行为本身。
3.  **置信度评估**：你必须对判断给出一个置信度分数（0-1.0）。清晰可见的香烟和烟雾则置信度高；手持物模糊、仅有动作无可见烟雾则置信度低。
4.  **输出要求**：你**必须且只能**输出一个纯净的JSON对象，无需任何额外的解释、Markdown代码块标记或前言后缀，以便程序直接解析。

【你的输出格式】
请严格按照以下JSON结构输出分析结果：
{
  "has_violation": <boolean>,  // 整体结论。true表示检测到吸烟行为，false表示未检测到。
  "person_count": <integer>,   // 画面中被识别出可能持有吸烟物品的总人数（包括未违规者）。
  "violation_count": <integer>, // 被确认正在进行吸烟行为的人数。
  "conclusion": "<string>",    // 简要的文本总结，描述检测到的关键信息。
  "violations": [              // 吸烟违规人员的详细信息列表。如果 has_violation 为 false，则此数组为空 []。
    {
      "bbox": {                // 该违规人员的边界框坐标（像素单位）
        "top_left_x": <integer>,
        "top_left_y": <integer>,
        "bottom_right_x": <integer>,
        "bottom_right_y": <integer>
      },
      "confidence": <float>    // 对此人正在吸烟的判断置信度（0.00 - 1.00）
    }
  ]
}

请分析该图像/视频中是否存在吸烟行为。', true, '2025-09-25 06:04:30.26371+00', '2025-09-25 06:04:30.26371+00', '25904e8a-8fba-49ad-b3a9-def7209bb4f6', '018d75dc-eb0a-4b46-954a-255e1bcc77de', '吸烟', 1, true, 'ready', 0, 0, 0, NULL, NULL, NULL, NULL);


--
-- Data for Name: video_files; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.video_files (id, name, original_filename, file_path, thumbnail_path, file_size, duration, fps, width, height, format, status, tags, description, analysis_progress, total_alerts, created_at, updated_at, analyzed_at, last_alert_at, deleted_at) VALUES ('98647d7b-0f48-4604-82ec-2b83f5513f78', '烟雾', '烟雾.mp4', 'videos/uploads/20250922_171202_f3bb1056.mp4', NULL, 90552427, NULL, NULL, NULL, NULL, 'MP4', 'DELETED', '{烟雾,火灾}', '烟雾火灾检测', 0, 0, '2025-09-22 09:12:03.053409+00', '2025-09-24 10:48:03.096554+00', NULL, NULL, NULL);
INSERT INTO public.video_files (id, name, original_filename, file_path, thumbnail_path, file_size, duration, fps, width, height, format, status, tags, description, analysis_progress, total_alerts, created_at, updated_at, analyzed_at, last_alert_at, deleted_at) VALUES ('84ac3e69-a5ba-4138-b6ab-8a0fc72a1270', '办公区监控', '吸烟.mp4', 'videos/uploads/20250915_082810_24359e0d.mp4', NULL, 79820963, NULL, NULL, NULL, NULL, 'MP4', 'DELETED', '{吸烟}', '吸烟检测', 100, 0, '2025-09-15 00:28:12.989983+00', '2025-09-24 10:48:11.274654+00', NULL, NULL, NULL);
INSERT INTO public.video_files (id, name, original_filename, file_path, thumbnail_path, file_size, duration, fps, width, height, format, status, tags, description, analysis_progress, total_alerts, created_at, updated_at, analyzed_at, last_alert_at, deleted_at) VALUES ('9383a277-9c40-4994-bb45-c19b390f53e1', '安全帽检测', '未带安全帽.mp4', 'videos/uploads/20250907_092147_a19eb543.mp4', NULL, 56955679, NULL, NULL, NULL, NULL, 'MP4', 'DELETED', '{安全帽}', '安全帽检测', 100, 0, '2025-09-07 09:21:48.352573+00', '2025-09-24 10:48:14.985683+00', NULL, NULL, NULL);
INSERT INTO public.video_files (id, name, original_filename, file_path, thumbnail_path, file_size, duration, fps, width, height, format, status, tags, description, analysis_progress, total_alerts, created_at, updated_at, analyzed_at, last_alert_at, deleted_at) VALUES ('25904e8a-8fba-49ad-b3a9-def7209bb4f6', '办公区监控', '吸烟.mp4', 'videos/uploads/20250925_140420_a36e28bb.mp4', NULL, 79820963, NULL, NULL, NULL, NULL, 'MP4', 'COMPLETED', '{吸烟,楼道}', '吸烟检测、办公区楼道', 100, 0, '2025-09-25 06:04:20.464338+00', '2025-09-29 04:07:12.899099+00', NULL, NULL, NULL);
INSERT INTO public.video_files (id, name, original_filename, file_path, thumbnail_path, file_size, duration, fps, width, height, format, status, tags, description, analysis_progress, total_alerts, created_at, updated_at, analyzed_at, last_alert_at, deleted_at) VALUES ('dd961ab4-5bef-4963-bb32-d4aee5f56ea8', '安全帽', '未带安全帽.mp4', 'videos/uploads/20250924_184936_6dbbe68d.mp4', NULL, 56955679, NULL, NULL, NULL, NULL, 'MP4', 'COMPLETED', '{安全帽}', '安全帽算法检测', 100, 0, '2025-09-24 10:49:36.321296+00', '2025-09-29 04:08:09.381291+00', NULL, NULL, NULL);
INSERT INTO public.video_files (id, name, original_filename, file_path, thumbnail_path, file_size, duration, fps, width, height, format, status, tags, description, analysis_progress, total_alerts, created_at, updated_at, analyzed_at, last_alert_at, deleted_at) VALUES ('d1313bd3-a747-449b-a396-a8ecd5749fa7', '烟雾', '烟雾.mp4', 'videos/uploads/20250924_184855_0d6a1fc2.mp4', NULL, 90552427, NULL, NULL, NULL, NULL, 'MP4', 'COMPLETED', '{烟雾,算法}', '烟雾检测算法', 100, 0, '2025-09-24 10:48:56.414833+00', '2025-09-29 04:09:48.299637+00', NULL, NULL, NULL);


--
-- Data for Name: video_stream_algorithm_config_history; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.video_stream_algorithm_config_history (id, config_id, stream_id, template_id, template_name, priority, confidence_threshold, is_active, operation, operation_at, operated_by, old_values, new_values) VALUES ('a1c87d63-9a5b-4929-b31d-1f93db07b9fc', 'af248589-1bb3-4480-af91-d28d9cc94ead', '91760ec2-593c-41ba-9124-dee444c83bb0', 'default_safety_monitor', '安全监控', 1, 0.7, true, 'INSERT', '2025-09-29 09:35:30.708743+00', NULL, NULL, '{"id": "af248589-1bb3-4480-af91-d28d9cc94ead", "priority": 1, "is_active": true, "stream_id": "91760ec2-593c-41ba-9124-dee444c83bb0", "created_at": "2025-09-29T09:35:30.708743+00:00", "created_by": null, "updated_at": "2025-09-29T09:35:30.708743+00:00", "template_id": "default_safety_monitor", "template_name": "安全监控", "confidence_threshold": 0.7}');


--
-- Data for Name: video_streams; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.video_streams (id, name, description, stream_url, stream_type, username, password, status, last_online_at, connection_error, fps, width, height, codec, thumbnail_path, latest_frame_path, analysis_status, analysis_interval, enable_recording, total_analysis_count, total_alerts, last_analysis_at, last_alert_at, location, group_name, tags, created_at, updated_at) VALUES ('799c6e3f-75d8-4f24-88cb-09c5ed53461b', '养护道路', NULL, 'rtsp://43.248.188.146:9977/rplay/中交一公*670b14728ad9902aecba32e22fa4f6bd.@42811.2.0', 'RTSP', NULL, NULL, 'ONLINE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'NOT_STARTED', 10, NULL, 0, 0, NULL, NULL, NULL, NULL, '{}', '2025-09-15 01:40:49.566672+00', '2025-09-17 03:01:08.171014+00');
INSERT INTO public.video_streams (id, name, description, stream_url, stream_type, username, password, status, last_online_at, connection_error, fps, width, height, codec, thumbnail_path, latest_frame_path, analysis_status, analysis_interval, enable_recording, total_analysis_count, total_alerts, last_analysis_at, last_alert_at, location, group_name, tags, created_at, updated_at) VALUES ('91760ec2-593c-41ba-9124-dee444c83bb0', '办公区', '办公区吸烟检测', 'rtsp://192.168.1.100:8554/test', 'RTSP', NULL, NULL, 'ONLINE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'NOT_STARTED', 10, NULL, 0, 0, NULL, NULL, '测试位置2', NULL, '{办公区楼道,吸烟}', '2025-09-16 09:06:08.395733+00', '2025-09-25 00:44:55.90171+00');
INSERT INTO public.video_streams (id, name, description, stream_url, stream_type, username, password, status, last_online_at, connection_error, fps, width, height, codec, thumbnail_path, latest_frame_path, analysis_status, analysis_interval, enable_recording, total_analysis_count, total_alerts, last_analysis_at, last_alert_at, location, group_name, tags, created_at, updated_at) VALUES ('8e44d986-0b9c-4872-a90f-7c612c07b2de', '测试流', '', 'rtsp://stream.strba.sk:1935/strba/VYHLAD_JAZERO.stream', 'RTSP', NULL, NULL, 'ONLINE', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 'NOT_STARTED', 10, NULL, 0, 0, NULL, NULL, NULL, NULL, '{测试,算法}', '2025-09-15 00:35:50.174315+00', '2025-09-25 03:30:56.721093+00');


--
-- Data for Name: video_stream_algorithm_configs; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.video_stream_algorithm_configs (id, stream_id, template_id, template_name, priority, confidence_threshold, is_active, created_at, updated_at, created_by) VALUES ('af248589-1bb3-4480-af91-d28d9cc94ead', '91760ec2-593c-41ba-9124-dee444c83bb0', 'default_safety_monitor', '安全监控', 1, 0.7, true, '2025-09-29 09:35:30.708743+00', '2025-09-29 09:35:30.708743+00', NULL);


--
-- PostgreSQL database dump complete
--

\unrestrict KWKpLt2mG637tbss4bzirfCA2TIrpyNnYbgllKL0UQBtONDCS3KwCYKf7uL95YH

