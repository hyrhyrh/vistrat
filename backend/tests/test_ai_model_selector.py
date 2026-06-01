"""
AI模型选择器单元测试
覆盖模型选择算法、能力评分、复杂度分析、边界条件等场景
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from models.ai_model_types import (
    ModelType, TaskComplexity, ModelCapabilities, PromptCategory,
    PromptPriority, PromptTemplate, ModelPerformance,
)
from services.ai_model_selector import (
    AIModelSelector, ModelCapabilityProvider, TaskAnalyzer,
)


# ============================================================================
# ModelCapabilityProvider 测试
# ============================================================================

class TestModelCapabilityProvider:
    """模型能力提供者测试"""

    def setup_method(self):
        self.provider = ModelCapabilityProvider()

    def test_get_capability_已知模型返回能力对象(self):
        """已注册的模型应返回 ModelCapabilities"""
        cap = self.provider.get_capability(ModelType.QWEN_VL)
        assert cap is not None
        assert cap.model_type == ModelType.QWEN_VL
        assert 0 <= cap.vision_quality <= 1

    def test_get_capability_未知模型返回None(self):
        """未注册的模型应返回 None"""
        cap = self.provider.get_capability(ModelType.GEMINI_PRO)
        assert cap is None

    def test_get_all_capabilities_包含四个模型(self):
        """应返回全部 4 个已注册模型"""
        all_caps = self.provider.get_all_capabilities()
        assert len(all_caps) == 4
        assert ModelType.QWEN_VL in all_caps
        assert ModelType.GPT4_VISION in all_caps

    def test_get_all_capabilities_返回副本不影响原始(self):
        """返回的字典是副本，修改不影响原始数据"""
        copy = self.provider.get_all_capabilities()
        copy.clear()
        assert len(self.provider.get_all_capabilities()) == 4


# ============================================================================
# TaskAnalyzer 测试
# ============================================================================

class TestTaskAnalyzer:
    """任务分析器测试"""

    def setup_method(self):
        self.analyzer = TaskAnalyzer()

    def _make_template(self, content: str,
                       priority: PromptPriority = PromptPriority.MEDIUM,
                       category: PromptCategory = PromptCategory.SAFETY_DETECTION) -> PromptTemplate:
        return PromptTemplate(
            id="t1", name="test", category=category,
            content=content, priority=priority,
        )

    def test_analyze_task_complexity_CRITICAL优先级(self):
        """CRITICAL 优先级直接返回 CRITICAL 复杂度"""
        tpl = self._make_template("简单内容", priority=PromptPriority.CRITICAL)
        assert self.analyzer.analyze_task_complexity(tpl) == TaskComplexity.CRITICAL

    def test_analyze_task_complexity_复杂关键词(self):
        """包含多个复杂关键词应返回 COMPLEX"""
        tpl = self._make_template("需要推理和分析，综合判断场景")
        assert self.analyzer.analyze_task_complexity(tpl) == TaskComplexity.COMPLEX

    def test_analyze_task_complexity_简单关键词(self):
        """仅包含简单关键词应返回 SIMPLE"""
        tpl = self._make_template("识别图片中的物体并计数")
        assert self.analyzer.analyze_task_complexity(tpl) == TaskComplexity.SIMPLE

    def test_analyze_task_complexity_混合关键词返回MEDIUM(self):
        """简单和复杂关键词混合时返回 MEDIUM"""
        tpl = self._make_template("识别物体并进行分析")
        assert self.analyzer.analyze_task_complexity(tpl) == TaskComplexity.MEDIUM

    def test_analyze_task_complexity_无关键词返回MEDIUM(self):
        """无匹配关键词应返回 MEDIUM"""
        tpl = self._make_template("这是一段没有任何标记词的文本")
        assert self.analyzer.analyze_task_complexity(tpl) == TaskComplexity.MEDIUM

    @pytest.mark.parametrize("category,expected_key", [
        (PromptCategory.SAFETY_DETECTION, "vision_quality"),
        (PromptCategory.BEHAVIOR_ANALYSIS, "reasoning_ability"),
        (PromptCategory.OBJECT_DETECTION, "vision_quality"),
        (PromptCategory.SCENE_UNDERSTANDING, "text_understanding"),
    ])
    def test_get_category_requirements_各类别有合理权重(self, category, expected_key):
        """每个类别都应返回包含关键能力要求的字典"""
        reqs = self.analyzer.get_category_requirements(category)
        assert expected_key in reqs
        assert 0 < reqs[expected_key] <= 1.0

    def test_get_category_requirements_未知类别返回默认(self):
        """未注册类别应返回默认权重"""
        # 使用 mock 枚举值模拟未知类别
        unknown = MagicMock()
        reqs = self.analyzer.get_category_requirements(unknown)
        assert "vision_quality" in reqs


# ============================================================================
# AIModelSelector 测试
# ============================================================================

class TestAIModelSelector:
    """AI模型选择器核心测试"""

    def setup_method(self):
        # 使用 mock 性能跟踪器避免文件 I/O
        with patch("services.ai_model_selector.ModelPerformanceTracker"):
            self.selector = AIModelSelector()
            # 确保 performance_tracker 返回 None（无历史数据）
            self.selector.performance_tracker.get_model_performance.return_value = None

    # ------------------------------------------------------------------
    # 基于任务类型的选择
    # ------------------------------------------------------------------

    @pytest.mark.parametrize("task_type,expected_model", [
        ("视觉分析", ModelType.QWEN_VL.value),
        ("安全检测", ModelType.GPT4_VISION.value),
        ("行为分析", ModelType.CLAUDE_VISION.value),
        ("物体识别", ModelType.QWEN_VL.value),
        ("文本理解", ModelType.MOONSHOT.value),
    ])
    def test_select_model_按任务类型选择(self, task_type, expected_model):
        """按任务类型应选择预定义的模型"""
        result = self.selector.select_model(task_type=task_type)
        assert result == expected_model

    def test_select_model_未知任务类型返回默认模型(self):
        """未知任务类型应回退到默认模型（qwen-vl）"""
        result = self.selector.select_model(task_type="未知任务")
        assert result == ModelType.QWEN_VL.value

    # ------------------------------------------------------------------
    # 基于模板的选择
    # ------------------------------------------------------------------

    def test_select_model_基于模板选择返回最优模型(self):
        """提供模板时应通过评分算法选择最优模型"""
        template = PromptTemplate(
            id="tpl1",
            name="安全检测",
            category=PromptCategory.SAFETY_DETECTION,
            content="检测画面中的危险行为，需要推理和分析",
            priority=PromptPriority.HIGH,
        )
        result = self.selector.select_model(prompt_template=template)
        # 应返回一个有效的模型值
        valid_models = [m.value for m in ModelType]
        assert result in valid_models

    def test_select_model_CRITICAL优先级选择高能力模型(self):
        """CRITICAL 优先级应倾向选择推理能力强的模型"""
        template = PromptTemplate(
            id="tpl2",
            name="关键安全",
            category=PromptCategory.SAFETY_DETECTION,
            content="紧急分析推理判断",
            priority=PromptPriority.CRITICAL,
        )
        result = self.selector.select_model(prompt_template=template)
        # GPT4_VISION 或 CLAUDE_VISION 推理能力最强
        assert result in [ModelType.GPT4_VISION.value, ModelType.CLAUDE_VISION.value]

    # ------------------------------------------------------------------
    # 评分函数测试
    # ------------------------------------------------------------------

    def test_calculate_capability_score_满分场景(self):
        """能力值完全满足要求时分数应接近能力均值"""
        cap = ModelCapabilities(
            model_type=ModelType.QWEN_VL,
            vision_quality=1.0,
            reasoning_ability=1.0,
            speed=1.0,
            text_understanding=1.0,
        )
        requirements = {"vision_quality": 1.0, "reasoning_ability": 1.0}
        score = self.selector._calculate_capability_score(cap, requirements)
        assert score == pytest.approx(1.0, abs=0.01)

    def test_calculate_capability_score_空要求返回零(self):
        """空要求字典应返回 0.0"""
        cap = ModelCapabilities(model_type=ModelType.QWEN_VL)
        score = self.selector._calculate_capability_score(cap, {})
        assert score == 0.0

    def test_calculate_capability_score_未知属性被忽略(self):
        """要求中包含不存在的属性应被忽略"""
        cap = ModelCapabilities(model_type=ModelType.QWEN_VL, vision_quality=0.9)
        requirements = {"vision_quality": 1.0, "nonexistent_field": 0.5}
        score = self.selector._calculate_capability_score(cap, requirements)
        # 只有 vision_quality 被计算
        assert score == pytest.approx(0.9, abs=0.01)

    def test_calculate_performance_score_无历史数据返回默认(self):
        """无历史性能数据时应返回 0.5"""
        self.selector.performance_tracker.get_model_performance.return_value = None
        score = self.selector._calculate_performance_score(
            ModelType.QWEN_VL, PromptCategory.SAFETY_DETECTION
        )
        assert score == 0.5

    def test_calculate_performance_score_有历史数据(self):
        """有历史性能数据时应基于成功率和分类性能计算"""
        perf = MagicMock()
        perf.success_rate = 0.8
        perf.category_performance = {PromptCategory.SAFETY_DETECTION: 0.9}
        self.selector.performance_tracker.get_model_performance.return_value = perf

        score = self.selector._calculate_performance_score(
            ModelType.QWEN_VL, PromptCategory.SAFETY_DETECTION
        )
        expected = 0.8 * 0.6 + 0.9 * 0.4
        assert score == pytest.approx(expected, abs=0.01)

    @pytest.mark.parametrize("complexity", list(TaskComplexity))
    def test_calculate_complexity_score_所有复杂度级别(self, complexity):
        """所有复杂度级别都应返回 0-1 之间的分数"""
        cap = ModelCapabilities(model_type=ModelType.QWEN_VL)
        score = self.selector._calculate_complexity_score(cap, complexity)
        assert 0.0 <= score <= 1.0

    @pytest.mark.parametrize("priority,expected", [
        (PromptPriority.LOW, 0.3),
        (PromptPriority.MEDIUM, 0.5),
        (PromptPriority.HIGH, 0.8),
        (PromptPriority.CRITICAL, 1.0),
    ])
    def test_get_priority_weight_映射正确(self, priority, expected):
        """优先级权重映射应正确"""
        assert self.selector._get_priority_weight(priority) == expected

    def test_get_fallback_model_返回qwen_vl(self):
        """后备模型应为 qwen-vl"""
        assert self.selector._get_fallback_model() == ModelType.QWEN_VL.value

    # ------------------------------------------------------------------
    # 边界条件
    # ------------------------------------------------------------------

    def test_select_model_无可用模型回退到默认(self):
        """当所有模型能力为 None 时应回退到默认模型"""
        self.selector.capability_provider.get_capability = MagicMock(return_value=None)
        template = PromptTemplate(
            id="t", name="test", category=PromptCategory.SAFETY_DETECTION,
            content="test", priority=PromptPriority.MEDIUM,
        )
        result = self.selector.select_model(prompt_template=template)
        assert result == ModelType.QWEN_VL.value

    def test_select_model_单一模型时选择该模型(self):
        """只有一个可用模型时应选择它"""
        self.selector.available_models = [ModelType.MOONSHOT]
        template = PromptTemplate(
            id="t", name="test", category=PromptCategory.OBJECT_DETECTION,
            content="识别物体", priority=PromptPriority.LOW,
        )
        result = self.selector.select_model(prompt_template=template)
        assert result == ModelType.MOONSHOT.value

    def test_select_model_异常时回退到默认(self):
        """选择过程异常应回退到默认模型"""
        self.selector._select_by_template = MagicMock(side_effect=Exception("boom"))
        template = PromptTemplate(
            id="t", name="test", category=PromptCategory.SAFETY_DETECTION,
            content="test", priority=PromptPriority.MEDIUM,
        )
        result = self.selector.select_model(prompt_template=template)
        assert result == ModelType.QWEN_VL.value


# ============================================================================
# 性能记录测试
# ============================================================================

class TestRecordModelPerformance:
    """模型性能记录测试"""

    def setup_method(self):
        with patch("services.ai_model_selector.ModelPerformanceTracker"):
            self.selector = AIModelSelector()

    def test_record_model_performance_有效模型(self):
        """有效模型应调用 performance_tracker 记录"""
        self.selector.record_model_performance(
            model=ModelType.QWEN_VL.value,
            success=True,
            response_time=1.5,
            confidence=0.95,
            category=PromptCategory.SAFETY_DETECTION,
        )
        self.selector.performance_tracker.record_model_usage.assert_called_once()

    def test_record_model_performance_未知模型不抛异常(self):
        """未知模型名称不应抛出异常"""
        # 不应抛出异常
        self.selector.record_model_performance(
            model="unknown-model",
            success=True,
            response_time=1.0,
            confidence=0.5,
            category=PromptCategory.SAFETY_DETECTION,
        )

    def test_get_model_statistics_返回字典(self):
        """统计信息应返回字典"""
        self.selector.performance_tracker.get_performance_summary.return_value = {
            "total_models": 0, "models": {}
        }
        result = self.selector.get_model_statistics()
        assert isinstance(result, dict)
        assert "total_models" in result
