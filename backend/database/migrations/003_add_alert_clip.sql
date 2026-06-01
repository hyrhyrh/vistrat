-- =====================================================================
-- Migration: 003_add_alert_clip.sql
--
-- Purpose: 为 alerts（按月分区的主表）添加视频片段字段
--          - clip_url:    片段 URL（MinIO / 回放链接），成功生成后填入
--          - clip_status: 片段生成状态（pending / ready / failed / skipped）
--
-- 说明:
--   * alerts 主表是 RANGE 分区表（按 created_at 按月分区），
--     PostgreSQL >= 11 对分区父表 ALTER TABLE ADD COLUMN 会自动
--     级联到所有现有及将来创建的分区，无需分别处理子分区。
--   * 分区表不支持"仅父表"的 CHECK，直接在父表加约束即可继承到所有子分区。
--   * 索引 filter 仅为 pending/failed 扫描优化，使用 CREATE INDEX IF NOT EXISTS。
--     分区表索引会变成 partitioned index，自动传播到各分区。
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 1. 新增字段
-- ---------------------------------------------------------------------
ALTER TABLE alerts
  ADD COLUMN IF NOT EXISTS clip_url    VARCHAR(512),
  ADD COLUMN IF NOT EXISTS clip_status VARCHAR(16) NOT NULL DEFAULT 'pending';

-- ---------------------------------------------------------------------
-- 2. 状态枚举约束
-- ---------------------------------------------------------------------
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_clip_status_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_clip_status_check
  CHECK (clip_status IN ('pending', 'ready', 'failed', 'skipped'));

-- ---------------------------------------------------------------------
-- 3. 查询 pending/failed 片段任务的索引
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_alerts_clip_status
  ON alerts(clip_status)
  WHERE clip_status IN ('pending', 'failed');

-- ---------------------------------------------------------------------
-- 4. 登记迁移
-- ---------------------------------------------------------------------
INSERT INTO schema_migrations(version, applied_at)
VALUES ('003_add_alert_clip', NOW())
ON CONFLICT (version) DO NOTHING;

COMMIT;
