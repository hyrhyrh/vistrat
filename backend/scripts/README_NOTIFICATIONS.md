# 企业微信通知工具使用指南

## 概述

本项目提供了完整的企业微信群聊机器人通知功能,支持定时汇总通知、即时告警通知和自定义报表发送。

## 功能特性

1. **定时汇总通知**: 每天11:00和17:00自动发送告警汇总
2. **即时告警通知**: 严重和错误级别的告警立即推送
3. **自定义报表发送**: 支持发送Markdown格式的自定义报表
4. **多渠道支持**: 可扩展支持钉钉、邮件等通知渠道

## API端点

### 1. 发送测试通知
```bash
POST /api/alert-notifications/test
```

### 2. 发送自定义报表
```bash
POST /api/alert-notifications/send-daily-report
Content-Type: application/json

{
  "report_content": "报表内容(Markdown格式)",
  "title": "报表标题"
}
```

### 3. 获取统计信息
```bash
GET /api/alert-notifications/statistics
```

### 4. 健康检查
```bash
GET /api/alert-notifications/health
```

## 命令行工具

### 1. 通用通知发送工具

**文件**: `send_wechat_notification.py`

**功能**: 发送自定义通知到企业微信群

**使用方法**:

```bash
# 发送测试通知
python scripts/send_wechat_notification.py --test

# 发送自定义通知
python scripts/send_wechat_notification.py --title "系统告警" --content "检测到异常行为"

# 从文件读取内容并发送
python scripts/send_wechat_notification.py --title "每日报表" --file report.md
```

**参数说明**:
- `--test`: 发送测试通知
- `--title`: 通知标题
- `--content`: 通知内容(Markdown格式)
- `--file`: 从文件读取内容

### 2. 每日告警统计报表发送工具

**文件**: `send_daily_alert_report.py`

**功能**: 发送预定义的每日告警统计报表

**使用方法**:

```bash
python scripts/send_daily_alert_report.py
```

## 配置说明

### 企业微信Webhook配置

1. 在企业微信中创建群聊机器人,获取Webhook URL
2. 在系统配置表 `system_configs` 中添加配置:

```sql
INSERT INTO system_configs (param_code, param_val, param_name, param_desc)
VALUES (
  'qywx_webhook',
  'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY',
  '企业微信Webhook地址',
  '用于发送告警通知的企业微信群聊机器人Webhook地址'
);
```

### 定时通知配置

在 `services/alert_notification_service.py` 中修改:

```python
self.scheduled_times = [
    dt_time(11, 0),  # 上午11:00
    dt_time(17, 0)   # 下午17:00
]
```

## Markdown格式支持

企业微信支持的Markdown语法:

- **标题**: `# 一级标题` `## 二级标题` `### 三级标题`
- **加粗**: `**加粗文本**`
- **斜体**: `*斜体文本*`
- **引用**: `> 引用文本`
- **代码**: `` `代码` ``
- **链接**: `[链接文字](http://example.com)`
- **列表**: `- 列表项`

## 示例

### 发送告警统计报表

```python
import httpx
import asyncio

async def send_alert_report():
    api_url = "http://localhost:16532/api/alert-notifications/send-daily-report"

    payload = {
        "title": "📊 今日安全帽告警统计报表",
        "report_content": """## 📊 今天的告警数据统计

### 告警总览
- **告警总数**: 14条
- **告警级别**: 全部为 critical(严重)级别

### 告警类型分布
- **未佩戴安全帽**: 8条告警
- **佩戴安全帽**(检测违规): 6条告警

### 建议
1. 加强早班和上午时段的安全巡查
2. 对高发区域进行重点监管
"""
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, json=payload)
        print(response.json())

asyncio.run(send_alert_report())
```

### 使用命令行工具发送

```bash
# 创建报表文件
cat > daily_report.md <<EOF
## 📊 系统运行报表

### 系统状态
- 所有服务运行正常
- CPU使用率: 45%
- 内存使用率: 62%

### 今日统计
- 处理视频流: 15个
- 检测告警: 28条
- 分析帧数: 15,234帧
EOF

# 发送报表
python scripts/send_wechat_notification.py --title "📊 系统运行报表" --file daily_report.md
```

## 故障排查

### 问题1: 通知发送失败

**可能原因**:
1. Webhook URL配置错误
2. 网络连接问题
3. 企业微信机器人被禁用

**解决方法**:
```bash
# 检查配置
curl http://localhost:16532/api/alert-notifications/health

# 检查统计信息
curl http://localhost:16532/api/alert-notifications/statistics

# 发送测试通知
python scripts/send_wechat_notification.py --test
```

### 问题2: 后端服务未启动

**解决方法**:
```bash
# 检查服务状态
ps aux | grep "python main.py"

# 启动后端服务
cd backend
python main.py
```

### 问题3: 通知格式错误

**原因**: Markdown语法不正确

**解决方法**:
- 检查Markdown语法是否符合企业微信支持的格式
- 使用在线Markdown编辑器预览效果
- 参考 `services/notification_adapters.py` 中的格式示例

## 扩展开发

### 添加新的通知渠道

1. 在 `services/notification_adapters.py` 中创建新的适配器类:

```python
class DingTalkAdapter(NotificationAdapter):
    """钉钉群聊机器人适配器"""

    async def send(self, message: NotificationMessage) -> bool:
        # 实现发送逻辑
        pass
```

2. 在 `services/alert_notification_service.py` 中注册适配器:

```python
async def _initialize_adapters(self):
    # 添加钉钉适配器
    if self.dingtalk_webhook_url:
        dingtalk_adapter = DingTalkAdapter(self.dingtalk_webhook_url)
        self.adapters.append(dingtalk_adapter)
```

### 自定义定时任务

修改 `services/alert_notification_service.py` 中的 `_scheduler_loop` 方法:

```python
async def _scheduler_loop(self):
    while self._running:
        now = datetime.now()

        # 自定义定时逻辑
        if now.hour == 8 and now.minute == 0:
            await self._send_morning_report()

        await asyncio.sleep(60)
```

## 相关文档

- [企业微信机器人API文档](https://developer.work.weixin.qq.com/document/path/91770)
- [告警通知服务源码](../services/alert_notification_service.py)
- [通知适配器源码](../services/notification_adapters.py)
- [API端点源码](../api/alert_notifications.py)

## 技术支持

如有问题,请查看:
1. 后端日志: `/tmp/backend.log`
2. 系统健康检查: `GET /api/alert-notifications/health`
3. 统计信息: `GET /api/alert-notifications/statistics`
