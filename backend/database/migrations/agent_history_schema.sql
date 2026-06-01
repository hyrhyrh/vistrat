--
-- AI Agent历史记录表结构
-- 需要追加到 schema.sql 中
--

-- ==================== AI Agent历史记录表 ====================

-- 表: AI Agent对话历史
DROP TABLE IF EXISTS public.ai_agent_history CASCADE;
CREATE TABLE public.ai_agent_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL,                                  -- 用户ID(关联users表)
    session_id uuid NOT NULL,                               -- 对话会话ID
    question text NOT NULL,                                 -- 用户问题
    intent jsonb NOT NULL,                                  -- 意图分析结果(JSON)
    data_summary jsonb,                                     -- 数据摘要(total_count, took_ms等)
    insights text,                                          -- AI分析结果(Markdown)
    report_markdown text,                                   -- Markdown报告
    report_html text,                                       -- HTML报告
    extra_metadata jsonb,                                   -- 元数据(timestamp, query_time_ms等) - 避免与SQLAlchemy保留字冲突
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ai_agent_history_user_id
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

COMMENT ON TABLE public.ai_agent_history IS 'AI Agent对话历史表：保存所有AI分析对话记录';
COMMENT ON COLUMN public.ai_agent_history.user_id IS '用户ID，关联users表';
COMMENT ON COLUMN public.ai_agent_history.session_id IS '对话会话ID，相同session_id表示同一次对话';
COMMENT ON COLUMN public.ai_agent_history.question IS '用户提出的问题';
COMMENT ON COLUMN public.ai_agent_history.intent IS '意图分析结果JSON：包含time_window, entities, metrics等';
COMMENT ON COLUMN public.ai_agent_history.data_summary IS '数据摘要JSON：包含total_count, took_ms等统计信息';
COMMENT ON COLUMN public.ai_agent_history.insights IS 'AI分析结果Markdown格式文本';
COMMENT ON COLUMN public.ai_agent_history.report_markdown IS '完整Markdown格式报告';
COMMENT ON COLUMN public.ai_agent_history.report_html IS '完整HTML格式报告';
COMMENT ON COLUMN public.ai_agent_history.extra_metadata IS '元数据JSON：包含timestamp, query_time_ms, data_count等';

-- 表: AI Agent对话会话
DROP TABLE IF EXISTS public.ai_agent_sessions CASCADE;
CREATE TABLE public.ai_agent_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,
    user_id uuid NOT NULL,                                  -- 用户ID
    title text,                                             -- 会话标题(根据首个问题生成)
    message_count integer DEFAULT 0 NOT NULL,               -- 消息数量
    last_message_at timestamp(6) with time zone,            -- 最后消息时间
    created_at timestamp(6) with time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ai_agent_sessions_user_id
        FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

COMMENT ON TABLE public.ai_agent_sessions IS 'AI Agent对话会话表：管理用户的对话会话';
COMMENT ON COLUMN public.ai_agent_sessions.title IS '会话标题，通常由首个问题生成';
COMMENT ON COLUMN public.ai_agent_sessions.message_count IS '会话中的消息数量';
COMMENT ON COLUMN public.ai_agent_sessions.last_message_at IS '最后一条消息的时间';


-- ==================== 索引定义 ====================

-- AI Agent历史记录索引
DROP INDEX IF EXISTS public.idx_ai_agent_history_user_id CASCADE;
CREATE INDEX idx_ai_agent_history_user_id ON public.ai_agent_history USING btree (user_id);

DROP INDEX IF EXISTS public.idx_ai_agent_history_session_id CASCADE;
CREATE INDEX idx_ai_agent_history_session_id ON public.ai_agent_history USING btree (session_id);

DROP INDEX IF EXISTS public.idx_ai_agent_history_created_at CASCADE;
CREATE INDEX idx_ai_agent_history_created_at ON public.ai_agent_history USING btree (created_at DESC);

DROP INDEX IF EXISTS public.idx_ai_agent_history_intent CASCADE;
CREATE INDEX idx_ai_agent_history_intent ON public.ai_agent_history USING gin (intent);

-- AI Agent会话索引
DROP INDEX IF EXISTS public.idx_ai_agent_sessions_user_id CASCADE;
CREATE INDEX idx_ai_agent_sessions_user_id ON public.ai_agent_sessions USING btree (user_id);

DROP INDEX IF EXISTS public.idx_ai_agent_sessions_created_at CASCADE;
CREATE INDEX idx_ai_agent_sessions_created_at ON public.ai_agent_sessions USING btree (created_at DESC);

DROP INDEX IF EXISTS public.idx_ai_agent_sessions_last_message_at CASCADE;
CREATE INDEX idx_ai_agent_sessions_last_message_at ON public.ai_agent_sessions USING btree (last_message_at DESC);


-- ==================== 触发器定义 ====================

-- AI Agent历史记录updated_at自动更新触发器
CREATE TRIGGER update_ai_agent_history_updated_at
    BEFORE UPDATE ON public.ai_agent_history
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


-- ==================== 初始化完成 ====================
-- AI Agent历史记录表结构创建完成
