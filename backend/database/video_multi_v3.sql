-- AI Watchdog v3.0 Schema
-- Fresh install, replaces v2.2 schema entirely
-- 4 core tables: video_streams, users, analysis_tasks, alerts
-- All timestamps UTC, all IDs UUID

-- ----------------------------
-- Enum types
-- ----------------------------

CREATE TYPE stream_type_enum AS ENUM (
    'RTSP', 'RTMP', 'HLS', 'WEBRTC', 'HTTP_FLV', 'LOCAL_CAMERA'
);

CREATE TYPE stream_status_enum AS ENUM (
    'ONLINE', 'OFFLINE'
);

CREATE TYPE task_status AS ENUM (
    'pending', 'running', 'paused', 'stopped', 'completed', 'failed'
);

CREATE TYPE alert_status AS ENUM (
    'pending', 'confirmed', 'dismissed', 'resolved'
);

-- ----------------------------
-- Table: video_streams
-- ----------------------------

CREATE TABLE video_streams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    stream_url VARCHAR(1000) NOT NULL,
    stream_type stream_type_enum NOT NULL DEFAULT 'RTSP',
    location VARCHAR(255),
    group_name VARCHAR(100),
    description TEXT,
    tags TEXT[],
    status stream_status_enum NOT NULL DEFAULT 'OFFLINE',
    project_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------
-- Table: users
-- ----------------------------

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    project_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ----------------------------
-- Table: analysis_tasks
-- ----------------------------

CREATE TABLE analysis_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL REFERENCES video_streams(id) ON DELETE CASCADE,
    status task_status NOT NULL DEFAULT 'pending',
    config JSONB,
    result JSONB,
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    error_message TEXT,
    project_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tasks_stream ON analysis_tasks (stream_id);
CREATE INDEX idx_tasks_status ON analysis_tasks (status) WHERE status IN ('running', 'pending');

-- ----------------------------
-- Table: alerts (partitioned by month)
-- ----------------------------

CREATE TABLE alerts (
    id UUID NOT NULL DEFAULT gen_random_uuid(),
    stream_id UUID NOT NULL,
    task_id UUID,
    level VARCHAR(20) NOT NULL DEFAULT 'warning',
    status alert_status NOT NULL DEFAULT 'pending',
    result JSONB,
    snapshot_path VARCHAR(500),
    message TEXT,
    project_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, created_at),
    FOREIGN KEY (stream_id) REFERENCES video_streams(id) ON DELETE CASCADE
) PARTITION BY RANGE (created_at);

-- Default partition (catches rows outside defined ranges)
CREATE TABLE alerts_default PARTITION OF alerts DEFAULT;

-- Month partitions
CREATE TABLE alerts_202604 PARTITION OF alerts
    FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE alerts_202605 PARTITION OF alerts
    FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- ----------------------------
-- Indexes on alerts
-- ----------------------------

CREATE INDEX idx_alerts_stream_time ON alerts (stream_id, created_at DESC);
CREATE INDEX idx_alerts_result ON alerts USING GIN (result jsonb_path_ops);
CREATE INDEX idx_alerts_status ON alerts (status) WHERE status = 'pending';
