#!/usr/bin/env python3
"""
测试clean_ai_response函数
"""

# 模拟AI返回的原始内容
raw_response = """
__TOOL_CALL_START__{"_type": "tool_call_start", "tool_name": "elasticsearch_search", "tool_display_name": "Elasticsearch search DSL query", "parameters": {"index": "video_alerts", "query": {"aggs": {"by_algorithm": {"terms": {"field": "algorithm_name.keyword", "size": 10}}, "by_severity": {"terms": {"field": "severity", "size": 10}}, "hourly_distribution": {"date_histogram": {"calendar_interval": "hour", "field": "datetime"}}, "total_count": {"value_count": {"field": "_id"}}}, "query": {"range": {"datetime": {"gte": "now/d", "lte": "now"}}}, "size": 0}}}__TOOL_CALL_START__

__TOOL_CALL_RESULT__{"_type": "tool_call_result", "tool_name": "elasticsearch_search", "result": {"error": "BadRequestError(400, 'search_phase_execution_exception', 'Fielddata access on the _id field is disallowed, you can re-enable it by updating the dynamic cluster setting: indices.id_field_data.enabled', Fielddata access on the _id field is disallowed, you can re-enable it by updating the dynamic cluster setting: indices.id_field_data.enabled)"}, "success": false}__TOOL_CALL_RESULT__
我需要修正查询语句，让我重新执行查询：

### 📊 今日告警数据分析报告

**统计时间**: 2025年10月20日（今天）

---

## 📈 核心数据概览

**今日告警总数**: **343条**

- 所有告警均为 **严重级别(critical)** ⚠️
- 告警集中在工作时段（09:00-15:00）
"""

# 导入清理函数
import re

def clean_ai_response(text: str) -> str:
    """清理AI响应"""
    if not text:
        return text

    # 1. 移除工具调用开始标记及其内容（包含完整的JSON）
    text = re.sub(r'__TOOL_CALL_START__\{.*?\}__TOOL_CALL_START__', '', text, flags=re.DOTALL)

    # 2. 移除工具调用结果标记及其内容（包含完整的JSON）
    text = re.sub(r'__TOOL_CALL_RESULT__\{.*?\}__TOOL_CALL_RESULT__', '', text, flags=re.DOTALL)

    # 3. 移除可能残留的单个标记
    text = re.sub(r'__TOOL_CALL_START__', '', text)
    text = re.sub(r'__TOOL_CALL_RESULT__', '', text)
    text = re.sub(r'__TOOL_CALL_END__', '', text)

    # 4. 移除"我需要修正查询语句"等工具调用相关的说明文本
    text = re.sub(r'我需要修正查询语句.*?\n', '\n', text)
    text = re.sub(r'让我重新执行查询.*?\n', '\n', text)

    # 5. 清理多余的空行
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 6. 去掉首尾空白
    text = text.strip()

    return text

# 测试
print("=" * 60)
print("原始内容长度:", len(raw_response))
print("原始内容:")
print(raw_response)
print("\n" + "=" * 60)

cleaned = clean_ai_response(raw_response)

print("清理后内容长度:", len(cleaned))
print("清理后内容:")
print(cleaned)
print("\n" + "=" * 60)
