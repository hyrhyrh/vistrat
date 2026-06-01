# 项目瘦身清理方案

## 清理分析日期: 2025-12-15
## 🟢 已执行清理: 2025-12-15 11:58

---

## 📋 目录

1. [前端未使用的页面和组件](#前端清理)
2. [后端未使用的代码文件](#后端清理)
3. [测试文件清理](#测试文件清理)
4. [空目录和冗余文件清理](#其他清理)
5. [模型文件优化](#模型文件优化)

---

## 🎨 前端清理

### ❌ 未被路由引用的页面（可删除）

| 文件 | 大小 | 原因 |
|------|------|------|
| `pages/RealtimeStreamManagePage.tsx` | 16.6 KB | App.tsx 中没有引用此页面 |
| `pages/StreamManagementPage.tsx` | 18.2 KB | App.tsx 中没有引用此页面 |

### ❌ 未被引用的组件（可删除）

| 文件 | 大小 | 原因 |
|------|------|------|
| `components/video/HLSPlayer.tsx` | 13.9 KB | 只有自身定义，没有被其他文件引用 |
| `components/stream/EnhancedVideoPlayer.tsx` | 16.6 KB | 只有自身定义，没有被其他文件引用 |
| `components/stream/RealtimeWebSocketPlayer.tsx` | 9.8 KB | 只有自身定义，没有被其他文件引用 |

### ⚠️ 需确认是否使用的页面

| 文件 | 大小 | 说明 |
|------|------|------|
| `pages/SafetyMonitoringDashboard.tsx` | 19.3 KB | App.tsx 中引用但菜单中已注释掉（被 WithAI 版本替代） |
| `pages/SafetyMonitoringDashboard.css` | 25.4 KB | 上述页面的样式，两个Dashboard都在用 |

---

## 🔧 后端清理

### ❌ 未使用的模型文件（可删除）

| 文件 | 大小 | 原因 |
|------|------|------|
| `models/video_stream_minimal.py` | 5.3 KB | 没有被任何文件引用 |
| `models/video_stream_simple.py` | 9.4 KB | 没有被任何文件引用 |
| `models/time_range.py` | 2.1 KB | 需进一步确认是否被使用 |

### ❌ 未使用的API文件（需确认）

| 文件 | 大小 | 原因 |
|------|------|------|
| `api/agent_claude.py` | 2.8 KB | 前端没有调用此API |
| `api/video_compat.py` | 1.5 KB | 向后兼容API，需确认是否还有客户端在用 |

### ❌ 空目录（可删除）

| 目录 | 说明 |
|------|------|
| `backend/archive/` | 空目录 |

### ❌ 根目录测试文件（应移动到 tests/ 目录）

| 文件 | 大小 | 建议 |
|------|------|------|
| `test_composite_detection_logic.py` | 9.0 KB | 移动到 tests/ 目录 |
| `test_results_composite_detection.md` | 6.3 KB | 移动到 tests/ 或 docs/ 目录 |
| `test_rtsp_opencv.py` | 4.2 KB | 移动到 tests/ 目录 |
| `test_sqlalchemy_jsonb.py` | 2.5 KB | 移动到 tests/ 目录 |
| `test_stream_processor.py` | 4.6 KB | 移动到 tests/ 目录 |

---

## 🧪 测试文件清理

### scripts/ 目录中的测试脚本（建议移动到 tests/）

| 文件 | 大小 | 说明 |
|------|------|------|
| `scripts/test_ai_alert_notification.py` | 4.7 KB | 测试脚本 |
| `scripts/test_clean_function.py` | 2.9 KB | 测试脚本 |
| `scripts/test_frame_quality.py` | 4.9 KB | 测试脚本 |
| `scripts/test_frame_quality_debug.py` | 4.5 KB | 测试脚本 |
| `scripts/test_model_options.py` | 2.5 KB | 测试脚本 |
| `scripts/test_qwen_api.py` | 3.9 KB | 测试脚本 |

---

## 📁 其他清理

### 可能冗余的配置文件

| 文件 | 说明 |
|------|------|
| `backend/.env.example` | 与根目录 `.env.example` 可能重复 |

---

## 📊 预估节省空间

| 类别 | 文件数 | 预估大小 |
|------|--------|----------|
| 前端未使用页面 | 2 | ~35 KB |
| 前端未使用组件 | 3 | ~40 KB |
| 后端未使用模型 | 2 | ~15 KB |
| 测试文件整理 | 11 | ~55 KB |
| **总计** | **~18** | **~145 KB** |

---

## ✅ 执行步骤

### 第一阶段：确认删除（低风险）

1. 删除前端未使用的组件
   - `HLSPlayer.tsx`
   - `EnhancedVideoPlayer.tsx`
   - `RealtimeWebSocketPlayer.tsx`

2. 删除前端未使用的页面
   - `RealtimeStreamManagePage.tsx`
   - `StreamManagementPage.tsx`

3. 删除后端未使用的模型
   - `video_stream_minimal.py`
   - `video_stream_simple.py`

4. 删除空目录
   - `backend/archive/`

### 第二阶段：整理测试文件

1. 创建 `backend/tests/` 目录
2. 移动根目录测试文件到 `tests/`
3. 移动 `scripts/test_*.py` 到 `tests/`

### 第三阶段：确认后删除（需谨慎）

1. 确认 `SafetyMonitoringDashboard.tsx` 是否可删除
2. 确认 `agent_claude.py` 是否有调用
3. 确认 `video_compat.py` 是否还需要

---

## ⚠️ 注意事项

1. 执行清理前请确保代码已提交到 Git
2. 建议先在开发环境测试
3. 删除后运行前后端验证功能正常
