# AI视频分析预警日报功能使用指南

## 概述

本系统已实现专业的AI视频分析预警日报功能,通过Claude AI智能分析Elasticsearch中的告警数据,自动生成图文并茂的日度数据报告,并推送到企业微信群。

## 核心特性

### 1. 智能数据分析
- ✅ 自动从Elasticsearch `video_alerts` 索引提取今日告警数据
- ✅ 多维度统计分析:告警类型、时段、区域、严重程度、置信度
- ✅ AI智能生成风险总结和行动建议

### 2. 专业报告格式
- ✅ 基础信息表格(时间范围、监控点数量、检测范围)
- ✅ 核心指标概览(总告警数、风险等级分布、平均置信度)
- ✅ 详细数据分析(类型/时段/区域分布统计表)
- ✅ 置信度分析(4个区间统计)
- ✅ 风险总结(短期/中期/长期措施)

### 3. 自动化推送
- ✅ 每日定时发送(北京时间 11:30 和 17:30)
- ✅ 企业微信群推送(支持Markdown格式)
- ✅ 分布式锁机制(多worker环境防重)

## 技术架构

### 数据流程

```
Elasticsearch (video_alerts索引)
        ↓
Claude AI分析助手 (ES工具调用)
        ↓
日报生成引擎 (专用提示词模板)
        ↓
企业微信群推送 (Markdown格式)
```

### 核心文件

1. **提示词模板**: `backend/prompts/daily_alert_report_prompt.txt`
   - 定义报告格式和数据查询指导
   - 包含时区处理说明和查询示例

2. **日报生成服务**: `backend/services/alert_notification_service.py:332`
   - `_send_scheduled_summary()` 方法
   - 加载提示词,调用Claude AI,清理响应,推送消息

3. **测试API**: `backend/api/alert_notifications.py:104`
   - `POST /api/alert-notifications/test-daily-report`
   - 手动触发日报生成,方便测试

## 使用方法

### 方式1: 定时自动发送

系统已配置为每日自动发送日报,无需手动操作:

- **发送时间**: 北京时间 11:30 和 17:30
- **发送渠道**: 企业微信群(需在系统配置中设置webhook)
- **分布式锁**: 多worker环境下只会发送一次

### 方式2: 手动测试

#### 使用API测试

```bash
# 方法1: 使用curl
curl -X POST http://localhost:16532/api/alert-notifications/test-daily-report

# 方法2: 使用httpie (推荐)
http POST http://localhost:16532/api/alert-notifications/test-daily-report

# 方法3: 使用Python requests
import requests
response = requests.post("http://localhost:16532/api/alert-notifications/test-daily-report")
print(response.json())
```

#### 预期响应

```json
{
  "success": true,
  "message": "AI视频分析预警日报已生成并发送到企业微信",
  "tip": "请检查企业微信群消息"
}
```

### 方式3: 前端集成

可以在前端添加"生成日报"按钮,调用测试API:

```typescript
const generateDailyReport = async () => {
  try {
    const response = await fetch('/api/alert-notifications/test-daily-report', {
      method: 'POST',
    });
    const data = await response.json();

    if (data.success) {
      message.success('日报已生成并发送到企业微信');
    } else {
      message.error('日报生成失败');
    }
  } catch (error) {
    message.error(`请求失败: ${error.message}`);
  }
};
```

## 报告格式示例

### 一、报告基础信息

| 项目 | 内容 |
|------|------|
| 报告名称 | AI视频分析预警日度数据报告 |
| 查询时间范围 | 2025-12-15 00:00:00 - 2025-12-15 11:29:23（北京时间） |
| 数据来源 | 园区/厂区 AI 视频监控系统 |
| 覆盖监控点 | 共计 12 个摄像头 |
| 检测范围 | 未佩戴安全帽、未穿戴反光衣、抽烟、打架等违规行为 |

### 二、核心告警指标概览

- **当日总告警次数**: 156 次
- **风险等级分布**:
  - 🔴 高风险告警（critical/high）: 45 次（占比 28.8%）
  - 🟡 中风险告警（medium）: 78 次（占比 50.0%）
  - 🟢 低风险告警（low）: 33 次（占比 21.2%）

### 三、详细数据分析

#### 3.1 告警类型分布分析

| 告警类型 | 告警次数 | 占比 | 平均置信度 | 风险等级 |
|---------|---------|------|-----------|---------|
| 未佩戴安全帽 | 68 | 43.6% | 89.2% | 高 |
| 未穿戴反光衣 | 45 | 28.8% | 85.6% | 中 |
| 抽烟 | 32 | 20.5% | 91.3% | 中 |
| 其他违规 | 11 | 7.1% | 78.4% | 低 |

**关键结论**:
- 未佩戴安全帽为当日最高发告警(占比43.6%),主要集中在生产一区和卸货区
- 抽烟告警平均置信度最高(91.3%),检测准确度较高
- 其他违规告警置信度偏低(78.4%),建议人工复核

## 数据查询逻辑

### 时区处理 ⚠️ 重要

系统严格区分三个时间字段:

1. **created_at** (告警记录创建时间)
   - 用于: 统计"今日告警数量"
   - 原因: 始终是系统记录告警的时间(当前北京时间)

2. **datetime** (告警实际发生时间)
   - 用于: 分析"时段分布"(上午vs下午)
   - 原因: 对于离线视频,可能是几天前拍摄的时间

3. **timestamp** (UTC时间戳)
   - 用于: 技术计算和排序
   - 原因: 标准格式,与时区无关

### 查询示例

```json
{
  "query": {
    "range": {
      "created_at": {
        "gte": "2025-12-15T00:00:00+08:00",
        "lte": "2025-12-15T11:30:00+08:00",
        "time_zone": "+08:00"
      }
    }
  },
  "aggs": {
    "by_severity": {
      "terms": {
        "field": "severity",
        "size": 10
      }
    },
    "by_type": {
      "terms": {
        "field": "algorithm_name.keyword",
        "size": 10
      },
      "aggs": {
        "avg_confidence": {
          "avg": {
            "field": "confidence"
          }
        }
      }
    }
  }
}
```

## 配置说明

### 企业微信Webhook配置

日报推送需要配置企业微信群机器人Webhook:

1. 在企业微信群中添加机器人
2. 获取Webhook URL
3. 在系统配置表 `system_config` 中添加记录:
   ```sql
   INSERT INTO system_config (param_code, param_val, param_name, param_desc)
   VALUES (
     'qywx_webhook',
     'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY',
     '企业微信Webhook',
     '用于告警通知推送'
   );
   ```

### 定时任务配置

定时发送配置在 `alert_notification_service.py:114`:

```python
self.scheduled_times = [
    dt_time(11, 30),  # 北京时间 上午11:30
    dt_time(17, 30)   # 北京时间 下午17:30
]
```

如需修改时间,编辑此配置并重启后端服务。

## 故障排查

### 常见问题

1. **日报未自动发送**
   - 检查告警通知服务是否启动: `GET /api/alert-notifications/health`
   - 查看后端日志是否有错误
   - 确认企业微信Webhook配置正确

2. **报告内容为空**
   - 确认今日是否有告警数据
   - 检查Elasticsearch连接状态
   - 查看日志中的数据查询结果

3. **报告格式不正确**
   - 检查提示词文件是否存在: `backend/prompts/daily_alert_report_prompt.txt`
   - 查看Claude API是否正常响应
   - 检查日志中的AI响应内容

4. **推送失败**
   - 测试企业微信Webhook是否可用
   - 检查网络连接
   - 查看适配器发送日志

### 调试步骤

1. **测试告警通知服务状态**
   ```bash
   curl http://localhost:16532/api/alert-notifications/health
   ```

2. **查看服务统计信息**
   ```bash
   curl http://localhost:16532/api/alert-notifications/statistics
   ```

3. **手动触发日报生成**
   ```bash
   curl -X POST http://localhost:16532/api/alert-notifications/test-daily-report
   ```

4. **查看后端日志**
   ```bash
   # Docker部署
   docker-compose logs -f backend | grep "日报"

   # 本地开发
   tail -f backend.log | grep "日报"
   ```

## 扩展功能

### 未来优化方向

1. **图表生成** (需要MCP服务)
   - 集成图表生成库(如echarts、matplotlib)
   - 生成PNG图片并上传到MinIO
   - 在报告中嵌入图片链接

2. **自定义报告模板**
   - 前端配置界面,支持拖拽式设计
   - 保存多个模板,按需选择
   - 支持变量替换和条件渲染

3. **多渠道推送**
   - 钉钉群推送
   - 邮件发送(PDF附件)
   - 短信通知(高优先级摘要)

4. **历史报告查询**
   - 存储历史报告到数据库
   - 提供查询和对比接口
   - 生成周报、月报汇总

## 参考资料

- **提示词工程**: `backend/prompts/daily_alert_report_prompt.txt`
- **ES数据模型**: `backend/agent/docs/elasticsearch_schema.md`
- **告警通知服务**: `backend/services/alert_notification_service.py`
- **Claude ES客户端**: `backend/agent/llm/claude_es_client.py`

## 联系支持

如有问题或建议,请联系开发团队或提交Issue。
