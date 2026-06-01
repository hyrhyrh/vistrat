# 百度AI语音识别配置指南

**版本**: v1.0
**更新时间**: 2025-10-11
**服务商**: 百度AI开放平台

---

## 📋 概述

本项目使用百度AI开放平台的语音识别服务,替代依赖Google服务的Web Speech API,确保在中国大陆网络环境下稳定可用。

**核心优势**:
- ✅ 完全国产化,无需访问Google服务
- ✅ 免费额度充足(每日50,000次调用)
- ✅ 中文识别准确率高(>95%)
- ✅ 响应速度快(<1秒)
- ✅ API密钥在后端保密,安全可靠

---

## 🔧 配置步骤

### Step 1: 注册百度AI开放平台账号

1. 访问: https://ai.baidu.com/
2. 点击"控制台" → "立即注册"
3. 使用手机号完成注册
4. 完成实名认证(上传身份证)

### Step 2: 创建语音识别应用

1. 登录控制台: https://console.bce.baidu.com/ai/
2. 选择"语音技术" → "语音识别"
3. 点击"创建应用"
4. 填写应用信息:
   - **应用名称**: vistrat语音识别
   - **应用归属**: 个人/企业
   - **接口选择**: 勾选"短语音识别标准版"
   - **应用描述**: AI监控系统语音输入功能
5. 点击"立即创建"

### Step 3: 获取API密钥

创建成功后,在应用列表中可以看到:
- **AppID**: 应用ID(数字)
- **API Key**: API密钥(字符串)
- **Secret Key**: 密钥(字符串)

**示例**:
```
AppID: 12345678
API Key: ABCDefgh123456XYZ
Secret Key: xyz789ABC456def
```

### Step 4: 配置环境变量

#### 方法1: 在Docker Compose中配置(推荐)

编辑 `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      # 百度AI语音识别配置
      BAIDU_APP_ID: "12345678"
      BAIDU_API_KEY: "ABCDefgh123456XYZ"
      BAIDU_SECRET_KEY: "xyz789ABC456def"
```

#### 方法2: 在.env文件中配置

创建 `backend/.env` 文件:

```bash
# 百度AI语音识别配置
BAIDU_APP_ID=12345678
BAIDU_API_KEY=ABCDefgh123456XYZ
BAIDU_SECRET_KEY=xyz789ABC456def
```

#### 方法3: 在系统环境变量中配置

```bash
export BAIDU_APP_ID="12345678"
export BAIDU_API_KEY="ABCDefgh123456XYZ"
export BAIDU_SECRET_KEY="xyz789ABC456def"
```

---

## 🚀 使用方法

### 1. 启动服务

```bash
# Docker方式
docker-compose up -d

# 或本地开发方式
cd backend
uv venv .venv
source .venv/bin/activate
uv sync
python main.py
```

### 2. 检查服务状态

访问健康检查端点:

```bash
curl http://localhost:16532/api/speech/health
```

**正常响应**:
```json
{
  "status": "healthy",
  "service": "baidu_speech_recognition",
  "configured": true,
  "message": "语音识别服务正常"
}
```

**未配置响应**:
```json
{
  "status": "not_configured",
  "service": "baidu_speech_recognition",
  "configured": false,
  "message": "未配置API密钥"
}
```

### 3. 前端使用

1. 打开AI分析助手对话框
2. 点击麦克风图标按钮
3. 首次使用会提示授权麦克风权限,点击"允许"
4. 看到"开始录音,请说话..."提示
5. 说话后再次点击按钮停止录音
6. 等待识别结果(约1-2秒)
7. 识别文本自动填充到输入框
8. 检查文本无误后点击发送

---

## 📊 免费额度说明

### 短语音识别标准版

| 项目 | 额度 |
|-----|------|
| 每日免费调用量 | 50,000次 |
| 音频时长限制 | ≤60秒 |
| 音频格式 | PCM/WAV/AMR/M4A |
| 采样率 | 8000/16000 Hz |
| 并发限制 | 100 QPS |

**说明**:
- 免费额度完全满足个人和小型企业使用
- 超出免费额度后按次计费:0.0015元/次
- 每日额度在北京时间00:00重置

### 计费示例

假设每天有1000次语音输入:
- 完全在免费额度内,无需付费
- 即使每天10,000次,也只用了20%额度

---

## 🛠️ 技术实现

### 架构流程

```
用户点击录音
    ↓
前端MediaRecorder录音(16kHz单声道)
    ↓
录音完成,上传音频Blob到后端
    ↓
后端接收音频,转换为WAV格式
    ↓
调用百度AI识别API
    ↓
返回识别文本到前端
    ↓
自动填充到输入框
```

### 关键代码

**前端录音** (`frontend/src/hooks/useAudioRecorder.ts`):
```typescript
const stream = await navigator.mediaDevices.getUserMedia({
  audio: {
    channelCount: 1,     // 单声道
    sampleRate: 16000,   // 16kHz
    echoCancellation: true,
    noiseSuppression: true,
  },
});

const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm',
});
```

**后端识别** (`backend/api/speech.py`):
```python
from aip import AipSpeech

client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

result = client.asr(
    wav_data,
    'wav',
    16000,
    {
        'dev_pid': 1537,  # 普通话
    }
)

text = ''.join(result.get('result', []))
```

---

## 🔍 故障排查

### 问题1: 未配置API密钥

**症状**: 点击麦克风按钮后提示"语音识别服务未配置"

**解决方案**:
1. 检查环境变量是否正确设置
2. 重启后端服务
3. 访问 `/api/speech/health` 检查配置状态

### 问题2: 识别失败"err_no: 3302"

**症状**: 识别时提示"鉴权失败"

**解决方案**:
1. 检查API Key和Secret Key是否正确
2. 确认应用已开通"短语音识别"服务
3. 检查应用是否已审核通过

### 问题3: 未检测到语音内容

**症状**: 识别结果为空

**解决方案**:
1. 确保麦克风权限已授权
2. 说话声音要清晰,靠近麦克风
3. 避免环境噪音干扰
4. 录音时长至少1-2秒

### 问题4: 音频格式不支持"err_no: 3312"

**症状**: 上传音频后提示格式错误

**解决方案**:
1. 检查浏览器是否支持MediaRecorder API
2. 使用Chrome/Edge浏览器(Firefox可能不支持webm)
3. 后端已自动转换为WAV格式,无需手动处理

---

## 📚 相关文档

- [百度AI开放平台官方文档](https://ai.baidu.com/ai-doc/SPEECH/Vk38lxily)
- [短语音识别API文档](https://ai.baidu.com/ai-doc/SPEECH/ek38fwvlp)
- [Python SDK文档](https://ai.baidu.com/ai-doc/REFERENCE/Ck3dwjhhu)
- [MediaRecorder MDN文档](https://developer.mozilla.org/zh-CN/docs/Web/API/MediaRecorder)

---

## 🎯 最佳实践

### 1. 录音提示

- 录音前提示用户"请靠近麦克风说话"
- 录音中显示醒目的录音状态指示
- 停止录音后提示"正在识别,请稍候..."

### 2. 错误处理

- 网络错误时提示"网络异常,请检查连接"
- 识别失败时提示"未识别到内容,请重试"
- 超时后自动停止识别

### 3. 用户体验

- 识别成功后自动填充输入框
- 允许用户编辑识别结果
- 提供撤销/重新识别功能

---

## 💡 进阶优化

### 1. 流式识别(未来扩展)

使用百度AI的实时语音识别API,支持流式传输:
- 边录音边识别
- 实时显示识别文本
- 延迟更低(<500ms)

### 2. 关键词识别

配置常用关键词,提高识别准确率:
```python
result = client.asr(wav_data, 'wav', 16000, {
    'dev_pid': 1537,
    'lm_id': 123456,  # 自定义语言模型
})
```

### 3. 语音唤醒

集成"小度小度"等唤醒词,免按钮操作

---

## ⚠️ 注意事项

1. **API密钥安全**:
   - 不要将API密钥提交到公开代码仓库
   - 使用环境变量或配置文件管理
   - 定期更换密钥

2. **并发限制**:
   - 免费版QPS限制100
   - 超出限制会返回错误
   - 考虑添加限流保护

3. **隐私保护**:
   - 录音数据仅用于识别,不存储
   - 遵守用户隐私政策
   - 提示用户授权麦克风权限

---

**配置完成后,语音识别功能即可正常使用!** 🎉

如有问题,请参考[故障排查](#🔍-故障排查)章节或联系技术支持。
