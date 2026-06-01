-- 简化的视频流表结构设计
-- 只保留核心必要字段，分离配置和数据

-- 流类型枚举
CREATE TYPE stream_type_enum AS ENUM (
    'RTSP', 'RTMP', 'HLS', 'WEBRTC', 'HTTP_FLV', 'LOCAL_CAMERA'
);

-- 流状态枚举  
CREATE TYPE stream_status_enum AS ENUM (
    'ACTIVE', 'INACTIVE', 'ERROR'
);

-- 视频流基础信息表（只保留核心字段）
CREATE TABLE video_streams (
    -- 主键
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 核心字段
    name VARCHAR(255) NOT NULL,              -- 摄像头名称
    stream_url VARCHAR(1000) NOT NULL,       -- 流地址
    stream_type stream_type_enum NOT NULL DEFAULT 'RTSP',  -- 流类型
    
    -- 基本信息
    description TEXT,                        -- 描述
    location VARCHAR(255),                   -- 位置
    group_name VARCHAR(100),                 -- 分组
    tags TEXT[] DEFAULT '{}',               -- 标签
    
    -- 状态
    status stream_status_enum DEFAULT 'INACTIVE',  -- 简化状态
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 索引
CREATE INDEX idx_video_streams_name ON video_streams(name);
CREATE INDEX idx_video_streams_group ON video_streams(group_name);
CREATE INDEX idx_video_streams_status ON video_streams(status);

-- 更新触发器
CREATE TRIGGER update_video_streams_updated_at 
    BEFORE UPDATE ON video_streams 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入测试数据
INSERT INTO video_streams (name, stream_url, stream_type, description, location, group_name, tags) VALUES
('大厅摄像头', 'rtsp://192.168.1.100:554/stream1', 'RTSP', '监控大厅主入口', '1楼大厅', '室内监控', '{"entrance","security"}'),
('停车场摄像头', 'rtsp://192.168.1.101:554/stream1', 'RTSP', '监控停车场区域', '地下停车场', '户外监控', '{"parking","outdoor"}');

-- 视频流分析配置表（分离出去）
CREATE TABLE stream_analysis_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL REFERENCES video_streams(id) ON DELETE CASCADE,
    
    -- 分析配置
    template_ids TEXT[] DEFAULT '{}',        -- 分析模板ID列表
    analysis_interval INTEGER DEFAULT 10,    -- 分析间隔（秒）
    confidence_threshold REAL DEFAULT 0.7,   -- 置信度阈值
    enable_recording BOOLEAN DEFAULT false,   -- 是否录制
    
    -- 认证信息（如果需要）
    username VARCHAR(100),
    password VARCHAR(100),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束：每个流只有一个配置
    UNIQUE(stream_id)
);

-- 视频流统计数据表（分离出去）
CREATE TABLE stream_statistics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL REFERENCES video_streams(id) ON DELETE CASCADE,
    
    -- 统计数据
    total_analysis_count INTEGER DEFAULT 0,
    total_alerts INTEGER DEFAULT 0,
    last_analysis_at TIMESTAMP WITH TIME ZONE,
    last_alert_at TIMESTAMP WITH TIME ZONE,
    last_online_at TIMESTAMP WITH TIME ZONE,
    
    -- 技术参数
    fps REAL,
    width INTEGER,
    height INTEGER,
    codec VARCHAR(50),
    
    -- 最新状态
    connection_error TEXT,
    thumbnail_path VARCHAR(1000),
    latest_frame_path VARCHAR(1000),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束：每个流只有一个统计记录
    UNIQUE(stream_id)
);

-- 创建索引
CREATE INDEX idx_stream_configs_stream_id ON stream_analysis_configs(stream_id);
CREATE INDEX idx_stream_stats_stream_id ON stream_statistics(stream_id);

-- 更新触发器
CREATE TRIGGER update_stream_configs_updated_at 
    BEFORE UPDATE ON stream_analysis_configs 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stream_stats_updated_at 
    BEFORE UPDATE ON stream_statistics 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 表注释
COMMENT ON TABLE video_streams IS '视频流基础信息表 - 只包含核心必要字段';
COMMENT ON TABLE stream_analysis_configs IS '视频流分析配置表 - 分离的配置信息';
COMMENT ON TABLE stream_statistics IS '视频流统计数据表 - 分离的运行时数据';