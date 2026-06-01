-- 视频流管理数据库表结构
-- 用于存储实时视频流的配置、状态和分析信息

-- 创建流状态枚举类型
CREATE TYPE stream_status_enum AS ENUM (
    'OFFLINE', 'ONLINE', 'CONNECTING', 'ERROR', 'MAINTENANCE'
);

-- 创建流类型枚举
CREATE TYPE stream_type_enum AS ENUM (
    'RTSP', 'RTMP', 'HLS', 'WEBRTC', 'HTTP_FLV', 'LOCAL_CAMERA'
);

-- 创建分析状态枚举
CREATE TYPE stream_analysis_status_enum AS ENUM (
    'NOT_STARTED', 'RUNNING', 'PAUSED', 'STOPPED', 'ERROR'
);

-- 视频流主表
CREATE TABLE video_streams (
    -- 主键和基本信息
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- 流配置信息
    stream_url VARCHAR(1000) NOT NULL,
    stream_type stream_type_enum NOT NULL DEFAULT 'RTSP',
    
    -- 认证信息
    username VARCHAR(100),
    password VARCHAR(100),
    
    -- 流状态
    status stream_status_enum NOT NULL DEFAULT 'OFFLINE',
    last_online_at TIMESTAMP WITH TIME ZONE,
    connection_error TEXT,
    
    -- 视频技术参数
    fps REAL,
    width INTEGER,
    height INTEGER,
    codec VARCHAR(50),
    
    -- 缩略图和截图
    thumbnail_path VARCHAR(1000),
    latest_frame_path VARCHAR(1000),
    
    -- 分析配置
    analysis_status stream_analysis_status_enum NOT NULL DEFAULT 'NOT_STARTED',
    analysis_interval INTEGER DEFAULT 10 CHECK (analysis_interval >= 1 AND analysis_interval <= 300),
    enable_recording BOOLEAN DEFAULT false,
    
    -- 统计信息
    total_analysis_count INTEGER DEFAULT 0,
    total_alerts INTEGER DEFAULT 0,
    last_analysis_at TIMESTAMP WITH TIME ZONE,
    last_alert_at TIMESTAMP WITH TIME ZONE,
    
    -- 位置和分组
    location VARCHAR(255),
    group_name VARCHAR(100),
    tags TEXT[] DEFAULT '{}',
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 视频流分析模板关联表
CREATE TABLE stream_analysis_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL REFERENCES video_streams(id) ON DELETE CASCADE,
    template_id VARCHAR(100) NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    
    -- 分析配置
    priority INTEGER DEFAULT 1 CHECK (priority >= 1 AND priority <= 5),
    enabled BOOLEAN DEFAULT true,
    confidence_threshold REAL DEFAULT 0.7 CHECK (confidence_threshold >= 0.1 AND confidence_threshold <= 1.0),
    
    -- 分析状态
    analysis_status stream_analysis_status_enum DEFAULT 'NOT_STARTED',
    
    -- 结果统计
    alerts_count INTEGER DEFAULT 0,
    detection_count INTEGER DEFAULT 0,
    confidence_avg REAL,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_detection_at TIMESTAMP WITH TIME ZONE,
    
    -- 错误信息
    error_message TEXT,
    
    -- 唯一约束：每个流的每个模板只能关联一次
    UNIQUE(stream_id, template_id)
);

-- 创建索引优化查询性能
CREATE INDEX idx_video_streams_status ON video_streams(status);
CREATE INDEX idx_video_streams_group ON video_streams(group_name);
CREATE INDEX idx_video_streams_location ON video_streams(location);
CREATE INDEX idx_video_streams_created_at ON video_streams(created_at DESC);
CREATE INDEX idx_video_streams_name ON video_streams(name);

CREATE INDEX idx_stream_templates_stream_id ON stream_analysis_templates(stream_id);
CREATE INDEX idx_stream_templates_priority ON stream_analysis_templates(priority DESC);
CREATE INDEX idx_stream_templates_enabled ON stream_analysis_templates(enabled);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_video_streams_updated_at 
    BEFORE UPDATE ON video_streams 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stream_templates_updated_at 
    BEFORE UPDATE ON stream_analysis_templates 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入示例数据（可选，用于测试）
INSERT INTO video_streams (name, stream_url, stream_type, description, location, group_name, tags) VALUES
('大厅摄像头', 'rtsp://192.168.1.100:554/stream1', 'RTSP', '监控大厅主入口', '1楼大厅', '室内监控', '{"entrance","security","lobby"}'),
('停车场摄像头', 'rtsp://192.168.1.101:554/stream1', 'RTSP', '监控停车场区域', '地下停车场', '户外监控', '{"parking","vehicle","outdoor"}'),
('会议室摄像头', 'rtsp://192.168.1.102:554/stream1', 'RTSP', '监控会议室情况', '2楼会议室A', '室内监控', '{"meeting","indoor","office"}');

-- 添加表注释
COMMENT ON TABLE video_streams IS '视频流信息表 - 存储实时视频流的配置、状态和分析信息，支持RTSP/RTMP等多种协议';
COMMENT ON TABLE stream_analysis_templates IS '视频流分析模板关联表 - 管理视频流与AI提示词模板的多对多关系，支持动态配置分析算法';

-- 字段注释已在CREATE TABLE中定义