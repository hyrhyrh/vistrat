-- ==================================================================================
-- 复合检测功能数据库迁移脚本 v3.0
-- ==================================================================================
-- 功能: 支持"一帧一次复合分析"，同时检测多种违规类型
-- 日期: 2025-10-28
-- 作者: AI Watchdog Team
-- ==================================================================================

-- ==================== 第一部分: 创建detection_type_templates表 ====================

-- 检测类型模板表（预定义的检测类型和提示词模板）
DROP TABLE IF EXISTS public.detection_type_templates CASCADE;
CREATE TABLE public.detection_type_templates (
    id UUID DEFAULT gen_random_uuid() NOT NULL PRIMARY KEY,

    -- 类型标识
    type_code VARCHAR(50) UNIQUE NOT NULL,              -- 类型编码(唯一键): safety_helmet, smoking等
    display_name VARCHAR(100) NOT NULL,                 -- 显示名称: "安全帽检测", "吸烟行为检测"
    category VARCHAR(50) NOT NULL,                      -- 类别: safety, behavior, environment

    -- 提示词模板
    prompt_template TEXT NOT NULL,                      -- 提示词模板内容
    json_field_name VARCHAR(50) NOT NULL,               -- AI响应JSON中的字段名(如 "safety_helmet")

    -- 违规严重程度
    severity VARCHAR(20) DEFAULT 'medium' NOT NULL,     -- 违规严重程度: low, medium, high
    CHECK (severity IN ('low', 'medium', 'high')),

    -- 排序和状态
    sort_order INTEGER DEFAULT 0 NOT NULL,              -- 在复合提示词中的排序顺序
    enabled BOOLEAN DEFAULT TRUE NOT NULL,              -- 是否启用

    -- 描述和元数据
    description TEXT,                                   -- 检测类型的详细描述
    example_scenarios TEXT,                             -- 示例场景说明

    -- 统计信息（预留，用于性能追踪）
    usage_count INTEGER DEFAULT 0,                      -- 使用次数
    detection_count INTEGER DEFAULT 0,                  -- 检测到违规的次数
    avg_confidence REAL DEFAULT 0.0,                    -- 平均置信度

    -- 时间戳
    created_at TIMESTAMP(6) WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP(6) WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 注释
COMMENT ON TABLE public.detection_type_templates IS '检测类型模板表：预定义的AI检测类型和提示词模板，用于复合检测';
COMMENT ON COLUMN public.detection_type_templates.type_code IS '类型编码(唯一)，如: safety_helmet, smoking';
COMMENT ON COLUMN public.detection_type_templates.display_name IS '显示名称，如: 安全帽检测, 吸烟行为检测';
COMMENT ON COLUMN public.detection_type_templates.category IS '类别: safety(安全), behavior(行为), environment(环境)';
COMMENT ON COLUMN public.detection_type_templates.prompt_template IS '提示词模板内容，用于动态组装复合提示词';
COMMENT ON COLUMN public.detection_type_templates.json_field_name IS 'AI响应JSON中的字段名，用于解析响应';
COMMENT ON COLUMN public.detection_type_templates.severity IS '违规严重程度: low(低), medium(中), high(高)';
COMMENT ON COLUMN public.detection_type_templates.sort_order IS '在复合提示词中的排序顺序，数字越小越靠前';

-- 创建索引
CREATE INDEX idx_detection_type_templates_type_code ON public.detection_type_templates USING btree (type_code);
CREATE INDEX idx_detection_type_templates_category ON public.detection_type_templates USING btree (category);
CREATE INDEX idx_detection_type_templates_enabled ON public.detection_type_templates USING btree (enabled);
CREATE INDEX idx_detection_type_templates_sort_order ON public.detection_type_templates USING btree (sort_order);

-- 创建自动更新updated_at的触发器
CREATE TRIGGER update_detection_type_templates_updated_at
    BEFORE UPDATE ON public.detection_type_templates
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


-- ==================== 第二部分: 预置12种常见检测类型 ====================

INSERT INTO public.detection_type_templates
    (type_code, display_name, category, prompt_template, json_field_name, severity, sort_order, description, example_scenarios)
VALUES
    -- 1. 安全帽检测 (最常用)
    ('safety_helmet',
     '未佩戴安全帽',
     'safety',
     '请仔细观察画面中的所有人员，判断是否有人员未佩戴安全帽。安全帽通常为黄色、白色、蓝色、红色等醒目颜色，佩戴在头部。如果发现有工作人员未佩戴安全帽或佩戴不规范（如未扣紧、歪戴等），请在结论中说明人数和位置。',
     'safety_helmet',
     'high',
     1,
     '检测施工现场、生产车间等区域人员是否正确佩戴安全帽',
     '建筑工地、工厂车间、电力设施、矿山作业等场景'),

    -- 2. 反光衣检测
    ('reflective_vest',
     '未穿反光衣',
     'safety',
     '请观察画面中的工作人员是否穿着反光衣（也称反光背心）。反光衣通常为荧光黄色、橙色或绿色，带有反光条纹。检查所有应该穿着反光衣的人员（如道路施工、夜间作业、交通指挥等场景）是否正确穿着。',
     'reflective_vest',
     'high',
     2,
     '检测道路施工、夜间作业等场景人员是否穿着反光衣',
     '道路施工、机场停机坪、夜间施工、交通指挥等场景'),

    -- 3. 吸烟行为检测
    ('smoking',
     '吸烟行为',
     'behavior',
     '请检测画面中是否有人员正在吸烟。重点观察人员的手部动作（手持烟卷）、嘴部（叼着香烟）以及是否有烟雾。禁烟区域包括：加油站、化工厂、仓库、生产车间等易燃易爆场所。',
     'smoking',
     'high',
     3,
     '检测禁烟区域的吸烟行为，预防火灾和安全事故',
     '加油站、化工厂、仓库、公共场所禁烟区等场景'),

    -- 4. 未穿工装检测
    ('work_uniform',
     '未穿工装',
     'safety',
     '请检查画面中的工作人员是否穿着规定的工作服装。工作服通常有统一的颜色和款式，可能带有公司标识。重点关注生产区域、作业区域的人员着装是否符合规范。',
     'work_uniform',
     'medium',
     4,
     '检测生产区域人员是否按规定穿着工作服',
     '生产车间、实验室、食品加工厂、洁净室等场景'),

    -- 5. 高处作业未系安全带
    ('safety_harness',
     '高处作业未系安全带',
     'safety',
     '请观察画面中是否有人员在高处作业（如脚手架、梯子、高空平台等）。如果存在高处作业人员，请检查其是否系挂安全带。安全带通常为带有金属扣的背带式装置，需要系在身上并挂在固定点上。',
     'safety_harness',
     'high',
     5,
     '检测高处作业人员是否系挂安全带，防止坠落事故',
     '高空作业、脚手架施工、塔吊作业、幕墙清洁等场景'),

    -- 6. 攀爬高处
    ('climbing',
     '攀爬危险高处',
     'behavior',
     '请检测画面中是否有人员正在攀爬高处，如爬墙、翻越护栏、攀爬设备等危险行为。重点观察人员是否在非正常通道或未设安全防护的区域进行攀爬。',
     'climbing',
     'high',
     6,
     '检测非法攀爬行为，防止坠落和意外事故',
     '施工现场、仓库货架、围墙翻越、设备攀爬等场景'),

    -- 7. 玩手机检测
    ('phone_usage',
     '工作时玩手机',
     'behavior',
     '请观察画面中的人员是否在工作时间玩手机。重点关注人员是否低头看手机、手持手机操作、或者将手机放在耳边通话。特别关注驾驶、操作设备、流水线作业等需要专注的场景。',
     'phone_usage',
     'medium',
     7,
     '检测工作时间玩手机行为，防止注意力分散导致事故',
     '驾驶操作、设备操作、流水线作业、值班岗位等场景'),

    -- 8. 睡岗离岗检测
    ('sleeping_on_duty',
     '睡岗或趴桌',
     'behavior',
     '请检测画面中的值班人员是否存在睡岗行为。观察人员是否趴在桌面上、头部低垂、身体姿态异常放松等睡眠特征。重点关注安保岗位、监控室、值班室等需要保持警觉的岗位。',
     'sleeping_on_duty',
     'high',
     8,
     '检测值班岗位人员睡岗行为，确保岗位值守',
     '安保岗位、监控室、门卫室、生产值班室等场景'),

    -- 9. 离岗检测
    ('absence_from_post',
     '离岗脱岗',
     'behavior',
     '请检测画面中的工作岗位是否有人员在岗。观察监控画面中是否长时间无人出现，或者应该有人值守的岗位（如安保岗亭、监控室、收费站等）处于无人状态。',
     'absence_from_post',
     'high',
     9,
     '检测重要岗位的人员离岗情况，确保岗位值守',
     '安保岗位、收费站、监控室、门卫室等场景'),

    -- 10. 非法入侵检测
    ('intrusion',
     '非法入侵',
     'security',
     '请检测画面中是否有人员非法进入禁止区域。重点观察围栏、警戒线、禁入标识等边界区域，判断是否有人员未经授权进入。关注人员的行为是否鬼祟、是否携带异常物品等。',
     'intrusion',
     'high',
     10,
     '检测非法入侵行为，保护重要区域安全',
     '仓库禁区、变电站、危险品存储区、军事设施等场景'),

    -- 11. 火灾烟雾检测
    ('fire_smoke',
     '火灾烟雾',
     'environment',
     '请仔细观察画面中是否存在火焰、烟雾或异常的光亮。火焰通常呈现橙红色或黄色，烟雾表现为灰色或黑色的雾状物。重点关注是否有明火、冒烟、或者异常的高温光晕。',
     'fire_smoke',
     'high',
     11,
     '检测火灾烟雾，实现早期火灾预警',
     '仓库、生产车间、森林、建筑物等场景'),

    -- 12. 积水检测
    ('water_accumulation',
     '地面积水',
     'environment',
     '请观察画面中的地面是否存在积水。积水通常表现为地面有反光、水面波纹、或者明显的水渍。重点关注通道、作业区域、电气设备附近等不应有积水的地方。',
     'water_accumulation',
     'medium',
     12,
     '检测地面积水情况，防止滑倒和电气事故',
     '生产车间、通道走廊、配电室、地下室等场景')
ON CONFLICT (type_code) DO NOTHING;


-- ==================== 第三部分: 修改video_analysis_template表 ====================

-- 添加detection_type_code字段，关联到detection_type_templates表
DO $$
BEGIN
    -- 检查列是否已存在，不存在则添加
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'video_analysis_templates'
        AND column_name = 'detection_type_code'
    ) THEN
        ALTER TABLE public.video_analysis_templates
        ADD COLUMN detection_type_code VARCHAR(50);

        -- 添加注释
        COMMENT ON COLUMN public.video_analysis_templates.detection_type_code IS '关联的检测类型编码，用于复合检测（可为NULL保持向后兼容）';
    END IF;

    -- 检查外键约束是否已存在，不存在则添加
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_video_analysis_templates_detection_type'
    ) THEN
        ALTER TABLE public.video_analysis_templates
        ADD CONSTRAINT fk_video_analysis_templates_detection_type
        FOREIGN KEY (detection_type_code)
        REFERENCES public.detection_type_templates(type_code)
        ON DELETE SET NULL;  -- 删除检测类型时，将关联的算法模板的detection_type_code设为NULL
    END IF;
END $$;

-- 创建索引以提高查询性能
DROP INDEX IF EXISTS public.idx_video_analysis_templates_detection_type CASCADE;
CREATE INDEX idx_video_analysis_templates_detection_type
    ON public.video_analysis_templates USING btree (detection_type_code);


-- ==================== 第四部分: 更新schema_migrations版本记录 ====================

INSERT INTO public.schema_migrations (version, applied_at, description) VALUES
    ('v3.0.0_composite_detection', CURRENT_TIMESTAMP, '复合检测功能：创建detection_type_templates表，预置12种检测类型')
ON CONFLICT (version) DO NOTHING;


-- ==================== 完成提示 ====================

DO $$
BEGIN
    RAISE NOTICE '======================================================================';
    RAISE NOTICE '复合检测功能数据库迁移完成！';
    RAISE NOTICE '======================================================================';
    RAISE NOTICE '✅ 已创建 detection_type_templates 表';
    RAISE NOTICE '✅ 已预置 12 种常见检测类型';
    RAISE NOTICE '✅ 已修改 video_analysis_templates 表（新增 detection_type_code 字段）';
    RAISE NOTICE '✅ 已创建索引和外键约束';
    RAISE NOTICE '✅ 已记录版本迁移信息';
    RAISE NOTICE '';
    RAISE NOTICE '下一步：';
    RAISE NOTICE '1. 实现 PromptTemplateEngine 组件';
    RAISE NOTICE '2. 实现 CompositeDetectionService 服务';
    RAISE NOTICE '3. 实现 CompositeResponseParser 解析器';
    RAISE NOTICE '======================================================================';
END $$;
