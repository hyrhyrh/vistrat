-- 视频流最小化表结构
-- 只保留核心必要字段：名称、流地址、类型、位置、分组、描述、标签、状态

-- 删除旧表和枚举
DROP TABLE IF EXISTS video_streams CASCADE;
DROP TABLE IF EXISTS stream_analysis_configs CASCADE;
DROP TABLE IF EXISTS stream_statistics CASCADE;
DROP TYPE IF EXISTS stream_status_enum CASCADE;
DROP TYPE IF EXISTS stream_type_enum CASCADE;
DROP TYPE IF EXISTS stream_analysis_status_enum CASCADE;

-- 流类型枚举
CREATE TYPE stream_type_enum AS ENUM (
    'RTSP', 'RTMP', 'HLS', 'WEBRTC', 'HTTP_FLV', 'LOCAL_CAMERA'
);

-- 流状态枚举（简化为在线/离线）
CREATE TYPE stream_status_enum AS ENUM (
    'ONLINE', 'OFFLINE'
);

-- 视频流基础信息表（极简设计）
CREATE TABLE video_streams (
    -- 主键
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- 必要字段
    name VARCHAR(255) NOT NULL,                    -- 摄像头名称
    stream_url VARCHAR(1000) NOT NULL,             -- 流地址
    stream_type stream_type_enum NOT NULL DEFAULT 'RTSP',  -- 流类型
    location VARCHAR(255),                         -- 位置
    group_name VARCHAR(100),                       -- 分组
    description TEXT,                              -- 描述
    tags TEXT[] DEFAULT '{}',                     -- 标签
    status stream_status_enum DEFAULT 'OFFLINE',  -- 状态（在线/离线）
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引优化查询
CREATE INDEX idx_video_streams_name ON video_streams(name);
CREATE INDEX idx_video_streams_group ON video_streams(group_name);
CREATE INDEX idx_video_streams_status ON video_streams(status);
CREATE INDEX idx_video_streams_location ON video_streams(location);

-- 更新时间触发器
CREATE TRIGGER update_video_streams_updated_at 
    BEFORE UPDATE ON video_streams 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入测试数据
INSERT INTO video_streams (name, stream_url, stream_type, description, location, group_name, tags) VALUES
('大厅摄像头', 'rtsp://192.168.1.100:554/stream1', 'RTSP', '监控大厅主入口', '1楼大厅', '室内监控', '{"entrance","security"}'),
('停车场摄像头', 'rtsp://192.168.1.101:554/stream1', 'RTSP', '监控停车场区域', '地下停车场', '户外监控', '{"parking","outdoor"}'),
('会议室摄像头', 'rtsp://192.168.1.102:554/stream1', 'RTSP', '监控会议室情况', '2楼会议室A', '室内监控', '{"meeting","office"}');

-- 表注释
COMMENT ON TABLE video_streams IS '视频流基础信息表 - 极简设计，只包含核心必要字段';