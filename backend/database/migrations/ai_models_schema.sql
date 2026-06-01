-- AI大模型编排相关数据库表结构
-- 创建时间: 2025-09-05

-- 删除已存在的表和枚举类型（按依赖顺序）
DROP TABLE IF EXISTS ai_test_results CASCADE;
DROP TABLE IF EXISTS ai_model_configs CASCADE;
DROP TYPE IF EXISTS algorithm_status_enum CASCADE;
DROP TYPE IF EXISTS ai_model_type_enum CASCADE;
DROP TYPE IF EXISTS ai_provider_enum CASCADE;

-- 创建AI供应商枚举
CREATE TYPE ai_provider_enum AS ENUM (
    'qwen',      -- 通义千问
    'moonshot',  -- Moonshot
    'gpt',       -- OpenAI GPT
    'claude',    -- Anthropic Claude
    'gemini',    -- Google Gemini
    'baidu'      -- 百度文心一言
);

-- 创建AI模型类型枚举
CREATE TYPE ai_model_type_enum AS ENUM (
    'vision',     -- 视觉模型
    'text',       -- 文本模型
    'multimodal'  -- 多模态模型
);

-- 创建算法状态枚举
CREATE TYPE algorithm_status_enum AS ENUM (
    'draft',       -- 草稿
    'testing',     -- 测试中
    'active',      -- 已激活
    'deprecated'   -- 已弃用
);

-- AI模型配置表
CREATE TABLE ai_model_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- AI模型相关
    provider ai_provider_enum NOT NULL,
    model_name VARCHAR(200) NOT NULL,
    model_type ai_model_type_enum DEFAULT 'vision',
    
    -- 提示词配置
    system_prompt TEXT,
    user_prompt TEXT,
    
    -- 模型参数
    temperature REAL DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
    top_p REAL DEFAULT 0.9 CHECK (top_p >= 0 AND top_p <= 1),
    max_tokens INTEGER DEFAULT 1000 CHECK (max_tokens > 0),
    
    -- 业务配置
    confidence_threshold REAL DEFAULT 0.7 CHECK (confidence_threshold >= 0 AND confidence_threshold <= 1),
    tags TEXT[] DEFAULT '{}',
    
    -- 状态和统计
    status algorithm_status_enum DEFAULT 'draft',
    test_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    
    -- 扩展配置
    extra_config JSONB DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT valid_test_counts CHECK (success_count <= test_count),
    CONSTRAINT valid_success_count CHECK (success_count >= 0)
);

-- AI测试结果表
CREATE TABLE ai_test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID NOT NULL REFERENCES ai_model_configs(id) ON DELETE CASCADE,
    
    -- 测试输入
    input_image_path VARCHAR(1000),
    input_text TEXT,
    
    -- 测试结果
    ai_response TEXT,
    confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    processing_time REAL NOT NULL CHECK (processing_time >= 0),
    
    -- 结果状态
    is_success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_ai_model_configs_provider ON ai_model_configs(provider);
CREATE INDEX idx_ai_model_configs_status ON ai_model_configs(status);
CREATE INDEX idx_ai_model_configs_model_type ON ai_model_configs(model_type);
CREATE INDEX idx_ai_model_configs_created_at ON ai_model_configs(created_at DESC);
CREATE INDEX idx_ai_model_configs_updated_at ON ai_model_configs(updated_at DESC);
CREATE INDEX idx_ai_model_configs_tags ON ai_model_configs USING GIN(tags);

CREATE INDEX idx_ai_test_results_config_id ON ai_test_results(config_id);
CREATE INDEX idx_ai_test_results_created_at ON ai_test_results(created_at DESC);
CREATE INDEX idx_ai_test_results_is_success ON ai_test_results(is_success);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_ai_model_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
CREATE TRIGGER trigger_ai_model_configs_updated_at
    BEFORE UPDATE ON ai_model_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_model_configs_updated_at();

-- 添加表和字段注释
COMMENT ON TABLE ai_model_configs IS 'AI大模型编排配置表 - 存储AI算法模板配置信息';
COMMENT ON COLUMN ai_model_configs.id IS '配置唯一ID';
COMMENT ON COLUMN ai_model_configs.name IS '算法名称';
COMMENT ON COLUMN ai_model_configs.description IS '算法描述';
COMMENT ON COLUMN ai_model_configs.provider IS 'AI模型供应商';
COMMENT ON COLUMN ai_model_configs.model_name IS '具体模型名称';
COMMENT ON COLUMN ai_model_configs.model_type IS '模型类型';
COMMENT ON COLUMN ai_model_configs.system_prompt IS '系统提示词';
COMMENT ON COLUMN ai_model_configs.user_prompt IS '用户提示词';
COMMENT ON COLUMN ai_model_configs.temperature IS '温度参数(0-2)';
COMMENT ON COLUMN ai_model_configs.top_p IS 'Top-p参数(0-1)';
COMMENT ON COLUMN ai_model_configs.max_tokens IS '最大token数';
COMMENT ON COLUMN ai_model_configs.confidence_threshold IS '置信度阈值(0-1)';
COMMENT ON COLUMN ai_model_configs.tags IS '算法标签';
COMMENT ON COLUMN ai_model_configs.status IS '算法状态';
COMMENT ON COLUMN ai_model_configs.test_count IS '测试次数';
COMMENT ON COLUMN ai_model_configs.success_count IS '成功次数';
COMMENT ON COLUMN ai_model_configs.extra_config IS '扩展配置JSON';

COMMENT ON TABLE ai_test_results IS 'AI算法测试结果表 - 存储调试测试的结果记录';
COMMENT ON COLUMN ai_test_results.config_id IS '关联的配置ID';
COMMENT ON COLUMN ai_test_results.input_image_path IS '测试图片路径';
COMMENT ON COLUMN ai_test_results.input_text IS '输入文本';
COMMENT ON COLUMN ai_test_results.ai_response IS 'AI模型完整响应';
COMMENT ON COLUMN ai_test_results.confidence_score IS '置信度分数';
COMMENT ON COLUMN ai_test_results.processing_time IS '处理耗时(秒)';
COMMENT ON COLUMN ai_test_results.is_success IS '是否成功';
COMMENT ON COLUMN ai_test_results.error_message IS '错误信息';

-- 插入示例数据
INSERT INTO ai_model_configs (
    name, description, provider, model_name, model_type, 
    system_prompt, user_prompt, temperature, top_p, 
    confidence_threshold, tags, status
) VALUES 
(
    '视频异常检测算法',
    '基于通义千问视觉模型的视频异常检测算法，可识别各类异常行为',
    'qwen',
    'qwen-vl-plus',
    'vision',
    '你是一个专业的视频监控分析专家。请仔细分析提供的图像，识别其中可能存在的异常行为或安全隐患。',
    '请分析这张图片中是否存在以下异常情况：1. 人员聚集 2. 可疑行为 3. 安全隐患 4. 其他异常。请给出分析结果和置信度。',
    0.3,
    0.8,
    0.75,
    ARRAY['异常检测', '视频监控', '安全'],
    'active'
),
(
    '烟雾火灾检测算法',
    '专门用于检测烟雾和火灾的AI算法模型',
    'qwen',
    'qwen-vl-max',
    'vision',
    '你是一个专业的火灾检测专家。专注于识别图像中的烟雾、火焰和相关火灾隐患。',
    '请仔细检查这张图片是否包含：1. 烟雾 2. 火焰 3. 燃烧物 4. 火灾隐患。给出详细分析和置信度评分。',
    0.2,
    0.7,
    0.8,
    ARRAY['烟雾检测', '火灾预警', '安全监控'],
    'active'
),
(
    '入侵检测算法',
    'Moonshot模型实现的区域入侵检测算法',
    'moonshot',
    'moonshot-v1-8k',
    'multimodal',
    '你是一个安全监控专家，专门识别未授权进入和可疑人员活动。',
    '分析图片中是否有人员进入限制区域，是否存在可疑行为，评估安全风险等级。',
    0.5,
    0.9,
    0.7,
    ARRAY['入侵检测', '区域监控', '人员识别'],
    'testing'
);

-- 显示创建结果
SELECT 'AI模型配置表创建完成，已插入' || COUNT(*) || '条示例数据' AS result
FROM ai_model_configs;