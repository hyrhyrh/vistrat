# AI智能视频监控预警系统

## 🎯 项目简介

这是一个基于多模态视觉模型的智能视频监控预警系统，采用前后端分离架构设计。系统能够实时分析监控视频画面，自动检测异常行为并生成预警信息。通过结合先进的AI技术、实时视频处理和友好的Web界面，为安防监控提供完整的智能化解决方案。

## ✨ 核心功能

### 🎥 多源视频接入
- **本地视频文件**：支持上传分析本地视频文件（MP4、AVI、MOV等格式）
- **RTSP视频流**：实时接入网络摄像头和视频流服务
- **灵活配置**：可调节分析间隔、缓冲时长等参数

### 🤖 智能AI分析
- **多模态视觉理解**：基于通义千问等先进视觉模型
- **异常行为检测**：智能识别人员聚集、违规操作、安全隐患等
- **上下文感知**：结合历史信息提供更准确的判断

### 🚨 实时告警系统
- **WebSocket推送**：毫秒级实时告警通知
- **详细记录**：自动保存异常视频片段和截图
- **告警历史**：完整的告警记录和统计分析

### 🎛️ 可视化管理
- **React前端界面**：现代化、响应式设计
- **实时监控画面**：WebSocket视频流实时展示
- **AI提示词管理**：可视化配置和管理AI分析提示词
- **告警中心**：集中查看和管理所有告警信息

## 🏗️ 技术架构

### 后端技术栈
- **FastAPI** - 高性能API框架
- **OpenCV** - 视频处理和计算机视觉
- **WebSocket** - 实时通信
- **多模态AI模型** - 通义千问视觉理解 + 文本分析

### 前端技术栈
- **React 18** - 现代化前端框架
- **TypeScript** - 类型安全
- **Ant Design** - 企业级UI组件库
- **Vite** - 快速构建工具

## 🚀 快速开始

### 前置要求
- Python 3.9+
- Node.js 18+
- 通义千问API密钥
- Moonshot API密钥（或其他文本模型）

### 一键启动
```bash
# 克隆项目
git clone <repository-url>
cd vistrat

# 一键启动开发环境
./start_dev.sh
```

### 分步启动

#### 1. 配置API密钥
编辑 `backend/config.py`：
```python
class APIConfig:
    QWEN_API_KEY = "your-qwen-api-key"
    MOONSHOT_API_KEY = "your-moonshot-api-key"
```

#### 2. 启动后端
```bash
cd backend
pip install -r requirements.txt
python video_server.py
```

#### 3. 启动前端
```bash
cd frontend
npm install
npm run dev
```

#### 4. 访问系统
- 前端界面：http://localhost:3000
- 后端API：http://localhost:16532

## 📱 使用指南

### 本地视频监控
1. 进入"本地视频监控"页面
2. 上传视频文件或指定文件路径
3. 点击"开始分析"启动智能监控
4. 查看实时视频画面和分析状态

### RTSP视频流监控
1. 进入"RTSP视频流"页面
2. 输入RTSP流地址（如：rtsp://username:password@ip:port/stream）
3. 配置分析参数（可选）
4. 启动实时监控

### 实时告警中心
1. 进入"实时告警"页面
2. 查看实时推送的告警信息
3. 点击告警查看详细信息（包含异常视频和截图）
4. 查看告警统计和历史记录

### AI提示词管理
1. 进入"AI提示词管理"页面
2. 管理三类提示词模板：
   - **视频描述**：指导AI生成视频内容描述
   - **异常检测**：定义异常行为判断标准
   - **历史总结**：历史信息整合规则
3. 创建、编辑、删除提示词模板
4. 设置当前使用的模板

## 🔧 配置说明

### 视频处理配置
```python
class VideoConfig:
    ANALYSIS_INTERVAL = 10    # 分析间隔(秒)
    BUFFER_DURATION = 11      # 滑窗分析时长(秒)
    VIDEO_INTERVAL = 1800     # 视频分段时长(秒)
    JPEG_QUALITY = 70         # 视频流压缩质量
```

### API配置
```python
class APIConfig:
    QWEN_API_KEY = ""         # 通义千问API密钥
    QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    MOONSHOT_API_KEY = ""     # Moonshot API密钥
    REQUEST_TIMEOUT = 60.0    # 请求超时时间
```

### RAG知识库配置（可选）
```python
class RAGConfig:
    ENABLE_RAG = False        # 是否启用RAG
    VECTOR_API_URL = ""       # 向量数据库API地址
```

## 🐳 Docker部署

```bash
# 构建并启动
docker-compose up --build

# 后台运行
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 📁 目录结构
```
vistrat/
├── backend/                 # 后端服务
│   ├── video_server.py     # 主服务器
│   ├── api_routes.py       # API路由
│   ├── multi_modal_analyzer.py # AI分析器
│   ├── utility.py          # 工具函数
│   ├── config.py           # 配置文件
│   ├── prompt.py           # 提示词
│   ├── requirements.txt    # Python依赖
│   └── ...
├── frontend/                # 前端应用
│   ├── src/
│   │   ├── pages/          # 页面组件
│   │   ├── services/       # API服务
│   │   ├── hooks/          # React Hooks
│   │   ├── types/          # 类型定义
│   │   └── ...
│   ├── package.json        # 前端依赖
│   └── ...
├── start_dev.sh            # 开发环境一键启动
├── docker-compose.yml      # Docker编排
└── CLAUDE.md              # 开发指南
```

## 🔍 异常检测类型

系统支持检测以下异常情况：

### 安全类异常
- 人员聚集冲突
- 异常物品出现
- 违反安全规程操作
- 自然灾害预警
- 潜在安全危害

### 常规异常
- 宠物逃跑
- 物品被盗或移动
- 人员跌倒、摔倒
- 小孩爬到高处
- 违反交通规则

## 🛠️ 开发指南

### 添加新的异常检测规则
1. 修改 `backend/prompt.py` 中的 `prompt_detect`
2. 或通过前端"AI提示词管理"界面创建新模板

### 自定义视频处理逻辑
- 修改 `backend/multi_modal_analyzer.py` 中的分析流程
- 调整 `backend/config.py` 中的处理参数

### 扩展前端功能
- 在 `frontend/src/pages/` 下添加新页面
- 在 `frontend/src/services/` 下添加API服务
- 更新路由配置

## ⚡ 性能优化

- 视频流采用JPEG压缩减少带宽占用
- 异步处理确保实时性
- 帧缓冲区避免内存溢出
- WebSocket连接自动重连机制

## 🔒 安全说明

本系统专注于防御性安全监控：
- 异常行为检测和预警
- 安全事件记录和分析
- 不收集或存储敏感个人信息
- 所有检测结果仅用于安全防护目的

## 📞 技术支持

如有问题或建议，请提交Issue或联系开发团队。

---

🤖 **基于Claude Code生成的智能监控系统**