-- AI供应商配置表结构
-- 创建时间: 2025-09-05

-- 删除已存在的表
DROP TABLE IF EXISTS ai_provider_configs CASCADE;

-- AI供应商配置表
CREATE TABLE ai_provider_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_name VARCHAR(100) NOT NULL UNIQUE,
    display_name VARCHAR(200) NOT NULL,
    icon VARCHAR(50) DEFAULT '🤖',
    description TEXT,
    
    -- API配置
    api_base_url VARCHAR(500) NOT NULL,
    api_key VARCHAR(500),
    api_version VARCHAR(50) DEFAULT 'v1',
    
    -- 模型配置
    available_models JSONB DEFAULT '[]',
    default_model VARCHAR(200),
    
    -- 请求配置
    max_tokens_limit JSONB DEFAULT '{}',
    request_headers JSONB DEFAULT '{}',
    request_timeout INTEGER DEFAULT 60,
    
    -- 状态和扩展
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    extra_config JSONB DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX idx_ai_provider_configs_provider_name ON ai_provider_configs(provider_name);
CREATE INDEX idx_ai_provider_configs_is_active ON ai_provider_configs(is_active);
CREATE INDEX idx_ai_provider_configs_sort_order ON ai_provider_configs(sort_order);
CREATE INDEX idx_ai_provider_configs_created_at ON ai_provider_configs(created_at DESC);

-- 创建更新时间触发器函数
CREATE OR REPLACE FUNCTION update_ai_provider_configs_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 创建触发器
CREATE TRIGGER trigger_ai_provider_configs_updated_at
    BEFORE UPDATE ON ai_provider_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_ai_provider_configs_updated_at();

-- 添加表和字段注释
COMMENT ON TABLE ai_provider_configs IS 'AI供应商配置表 - 存储各AI厂商的API配置信息';
COMMENT ON COLUMN ai_provider_configs.id IS '配置唯一ID';
COMMENT ON COLUMN ai_provider_configs.provider_name IS '供应商名称，唯一标识';
COMMENT ON COLUMN ai_provider_configs.display_name IS '显示名称';
COMMENT ON COLUMN ai_provider_configs.icon IS '图标';
COMMENT ON COLUMN ai_provider_configs.description IS '供应商描述';
COMMENT ON COLUMN ai_provider_configs.api_base_url IS 'API基础地址';
COMMENT ON COLUMN ai_provider_configs.api_key IS 'API密钥';
COMMENT ON COLUMN ai_provider_configs.api_version IS 'API版本';
COMMENT ON COLUMN ai_provider_configs.available_models IS '可用模型列表JSON';
COMMENT ON COLUMN ai_provider_configs.default_model IS '默认模型';
COMMENT ON COLUMN ai_provider_configs.max_tokens_limit IS 'Token限制配置JSON';
COMMENT ON COLUMN ai_provider_configs.request_headers IS '请求头配置JSON';
COMMENT ON COLUMN ai_provider_configs.request_timeout IS '请求超时时间(秒)';
COMMENT ON COLUMN ai_provider_configs.is_active IS '是否启用';
COMMENT ON COLUMN ai_provider_configs.sort_order IS '排序顺序';
COMMENT ON COLUMN ai_provider_configs.extra_config IS '扩展配置JSON';

-- 插入初始数据
INSERT INTO ai_provider_configs (
    provider_name, display_name, icon, description,
    api_base_url, api_key, available_models, default_model,
    request_headers, sort_order, is_active
) VALUES 
-- 通义千问配置
(
    'qwen',
    '通义千问',
    '🟡',
    '阿里云通义千问大模型，支持文本和视觉理解',
    'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
    'sk-xxxxxxxxxxxxxxxxxxxx',
    '["qwen-vl-plus", "qwen-vl-max", "qwen-turbo", "qwen-plus", "qwen-max"]',
    'qwen-vl-plus',
    '{"Authorization": "Bearer {api_key}", "Content-Type": "application/json"}',
    1,
    true
),
-- Moonshot配置
(
    'moonshot',
    'Moonshot',
    '🌙', 
    'Moonshot AI大模型，专注于长上下文理解',
    'https://api.moonshot.cn/v1/chat/completions',
    'sk-xxxxxxxxxxxxxxxxxxxx',
    '["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]',
    'moonshot-v1-8k',
    '{"Authorization": "Bearer {api_key}", "Content-Type": "application/json"}',
    2,
    true
),
-- OpenAI GPT配置
(
    'gpt',
    'OpenAI GPT',
    '🤖',
    'OpenAI GPT系列模型，支持文本和视觉理解',
    'https://api.openai.com/v1/chat/completions', 
    '',
    '["gpt-4-vision-preview", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]',
    'gpt-4-vision-preview',
    '{"Authorization": "Bearer {api_key}", "Content-Type": "application/json"}',
    3,
    false
),
-- Claude配置  
(
    'claude',
    'Claude',
    '🎭',
    'Anthropic Claude大模型，擅长理解和推理',
    'https://api.anthropic.com/v1/messages',
    '',
    '["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]',
    'claude-3-sonnet',
    '{"x-api-key": "{api_key}", "anthropic-version": "2023-06-01", "Content-Type": "application/json"}',
    4,
    false
),
-- Google Gemini配置
(
    'gemini', 
    'Google Gemini',
    '💎',
    'Google Gemini多模态大模型',
    'https://generativelanguage.googleapis.com/v1/models',
    '',
    '["gemini-1.5-pro", "gemini-1.0-pro-vision", "gemini-1.0-pro"]',
    'gemini-1.5-pro',
    '{"Content-Type": "application/json"}',
    5,
    false
),
-- 百度文心配置
(
    'baidu',
    '百度文心',
    '🐻',
    '百度文心一言大模型',
    'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat',
    '',
    '["ernie-4.0-turbo", "ernie-3.5-turbo", "ernie-bot-4"]',
    'ernie-4.0-turbo',
    '{"Content-Type": "application/json"}',
    6,
    false
);

-- 显示创建结果
SELECT 'AI供应商配置表创建完成，已插入' || COUNT(*) || '条配置数据' AS result
FROM ai_provider_configs;