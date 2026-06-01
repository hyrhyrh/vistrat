# AI 视频监控系统 - 端到端测试文档（E2E Test Plan）

> **项目**：AI Watchdog v3.0 — 多模态视觉模型智能监控预警系统
> **测试范围**：从用户登录 / 注册开始的所有核心业务流程、页面交互、字段校验、临界值、权限控制
> **测试对象**：`http://localhost:5173/`（前端 Vite dev server）+ `http://localhost:16532/`（后端 FastAPI）
> **执行工具**：Playwright（`npx playwright test` / `npx playwright open --headed`）
> **默认管理员账号**：`admin` / `admin123`（应用启动时自动初始化）

---

## 0. 测试总览

| 模块 | 页面路由 | 需要登录 | Admin 专属 | 用例数 |
|------|----------|----------|------------|--------|
| 登录/认证 | `/login` | 否 | 否 | 11 |
| 实时预览 | `/live-preview` | 是 | 否 | 4 |
| 离线视频管理 | `/video-management` | 是 | 否 | 12 |
| 实时流管理 | `/stream-management` | 是 | 否 | 10 |
| 告警中心 | `/alerts` | 是 | 否 | 8 |
| 分析结果查询 | `/analysis-results` | 是 | 否 | 6 |
| AI 编排算法 | `/prompts` | 是 | 否 | 5 |
| AI 模型编排 | `/ai-model` | 是 | 否 | 10 |
| AI 供应商配置 | `/ai-provider-config` | 是 | 否 | 6 |
| 检测类型模板 | `/detection-templates` | 是 | 否 | 5 |
| 性能监控 | `/performance` | 是 | 否 | 3 |
| 用户管理 | `/user-management` | 是 | **是** | 12 |
| 权限与路由保护 | 全局 | — | — | 5 |
| **合计** | | | | **97** |

测试优先级：
- **P0（冒烟）**：登录、主导航、关键 CRUD 的 happy path
- **P1（功能）**：字段校验、临界值、错误提示、分页
- **P2（增强）**：上传大文件、并发、权限越权、WebSocket
- **P3（UI）**：样式回归、响应式、可访问性

---

## 1. 认证与注册模块（`/login`）

### 1.1 前置条件
- 后端 `/api/auth/login`、`/api/auth/verify` 正常
- DB 已存在默认管理员 `admin / admin123`

### 1.2 测试用例

| 编号 | 优先级 | 用例名 | 步骤 | 预期结果 |
|------|--------|--------|------|----------|
| AUTH-001 | P0 | 页面正常渲染 | 访问 `/login` | 表单出现，包含 用户名 / 密码 / "记住我" / "登录" 按钮 |
| AUTH-002 | P0 | 默认 admin 登录成功 | 输入 `admin / admin123`，点击登录 | 跳转到受保护页（如 `/live-preview`），顶部出现用户菜单；`localStorage.token` 或 `sessionStorage.token` 存在 |
| AUTH-003 | P0 | 密码错误 | `admin / wrongpass` | 错误提示 "用户名或密码错误"，URL 仍在 `/login`，不生成 token |
| AUTH-004 | P1 | 用户名不存在 | `nouser123 / x` | 错误提示；不生成 token |
| AUTH-005 | P1 | 用户名必填校验 | 密码填值，用户名留空，点击登录 | 前端表单阻止提交并显示 "请输入用户名" |
| AUTH-006 | P1 | 密码必填校验 | 用户名填值，密码留空 | 前端表单阻止提交并显示 "请输入密码" |
| AUTH-007 | P1 | "记住我"勾选 → localStorage 存储 | 勾选后登录 | `localStorage.token` 存在，且 `localStorage.rememberedUsername === 'admin'` |
| AUTH-008 | P1 | 未勾选"记住我" → sessionStorage | 取消勾选后登录 | `sessionStorage.token` 存在，`localStorage.token` 不存在 |
| AUTH-009 | P1 | 自动填充记住的用户名 | 登录一次勾选记住 → 退出 → 再次访问 `/login` | 用户名输入框被预填为 `admin` |
| AUTH-010 | P1 | 登出清除 token | 登录后点击"登出" | 重定向 `/login`，localStorage / sessionStorage 的 token 被清除 |
| AUTH-011 | P2 | token 过期 | 篡改 localStorage 的 token 值 → 刷新页面 | `/api/auth/verify` 失败，自动重定向 `/login` |

### 1.3 字段临界值（后端 Pydantic 约束）
| 字段 | 最小 | 最大 | 备注 |
|------|------|------|------|
| username | 3 字符 | 50 字符 | 注册端点约束；登录端点不强校验长度，以 DB 是否存在为准 |
| password | 6 字符 | 无 | `min_length=6` |
| email | 标准格式 | 无 | 可为空 |
| role | enum | — | `admin / user / viewer` |

> **注册流程**：后端 `POST /api/auth/register` 已开放，但前端 UI 为占位符。E2E 测试注册用例可通过直接调用 API 完成（见 `API-AUTH-01~05`）。

---

## 2. 全局路由保护

| 编号 | 用例 | 步骤 | 预期 |
|------|------|------|------|
| ROUTE-001 | 未登录访问受保护页重定向 | 清空存储，直接访问 `/video-management` | 重定向到 `/login` |
| ROUTE-002 | 登录后刷新不丢状态 | 登录 → F5 | 仍保持登录，停留在原页面 |
| ROUTE-003 | 非 admin 访问 /user-management | 用 viewer 账号登录访问 | 跳转首页或 403 提示 |
| ROUTE-004 | 登录后访问 `/login` | 已登录访问 | 自动跳转到默认主页 |
| ROUTE-005 | 未知路径 | 访问 `/xxx-not-exist` | 404 或重定向首页 |

---

## 3. 离线视频管理（`/video-management`）

### 3.1 关键字段与临界值

| 字段 | 约束 | 测试点 |
|------|------|--------|
| 文件大小 | ≤ 500 MB | 499 MB 正常 / 500 MB 精确 / 501 MB 拒绝 |
| 文件格式 | `.mp4/.avi/.mov/.wmv/.flv` | `.mkv/.txt` 应被拒绝 |
| 视频名称 | 1–255 字符 | 0 / 1 / 255 / 256 字符 |
| 搜索 limit | 1–100 | 0 / 1 / 100 / 101 |
| 搜索 offset | ≥ 0 | -1 / 0 |

### 3.2 测试用例

| 编号 | 优先级 | 用例 | 预期 |
|------|--------|------|------|
| VIDEO-001 | P0 | 页面打开，列表自动加载 | 显示统计卡片和视频表格 |
| VIDEO-002 | P0 | 点击"上传视频"弹出对话框 | 对话框含 文件选择 / 名称 / 描述 / 标签 / 确认按钮 |
| VIDEO-003 | P0 | 上传 .mp4 成功 | 列表出现新记录，status=PENDING，提示"上传成功" |
| VIDEO-004 | P1 | 上传非法格式 .txt | 弹出错误 "不支持的文件格式" |
| VIDEO-005 | P1 | 上传文件超过 500 MB | 拒绝上传，提示大小限制 |
| VIDEO-006 | P1 | 名称为空点击确定 | 前端提示 "请输入视频名称" |
| VIDEO-007 | P1 | 搜索：按名称 | 输入关键字 → 点击搜索 → 列表过滤匹配项 |
| VIDEO-008 | P1 | 搜索：按状态筛选 | 选择 COMPLETED → 列表只显示已完成 |
| VIDEO-009 | P1 | 搜索：重置 | 点击重置 → 条件清空，列表恢复 |
| VIDEO-010 | P1 | 分页翻页 | 点击下一页 → 调用 `offset += limit` 新请求 |
| VIDEO-011 | P1 | 编辑视频名称 | 点击编辑 → 改名 → 保存 → 列表即时更新 |
| VIDEO-012 | P0 | 删除视频 | 点击删除 → Popconfirm 确认 → 记录从列表移除 |

---

## 4. 实时流管理（`/stream-management`）

### 4.1 字段

| 字段 | 约束 |
|------|------|
| name | 必填，1–255 |
| stream_url | 必填，格式 `rtsp://` / `http(s)://.../live.flv` / `http(s)://.../*.m3u8` |
| stream_type | enum `rtsp / webrtc / hls` |
| group_name | 可选 |

### 4.2 用例

| 编号 | 优先级 | 用例 | 预期 |
|------|--------|------|------|
| STREAM-001 | P0 | 页面加载 | 显示流列表、统计卡片 |
| STREAM-002 | P0 | 新建 RTSP 流 | 填入 `rtsp://demo.test/s1` → 创建成功，列表新增 |
| STREAM-003 | P1 | 必填校验：URL 为空 | 前端阻止提交并提示 |
| STREAM-004 | P1 | 非法 URL 格式 | 前端或后端报错 |
| STREAM-005 | P1 | 编辑流信息 | 修改名称 → 保存 → 即时刷新 |
| STREAM-006 | P0 | 删除流 | Popconfirm → 调用 DELETE → 列表移除 |
| STREAM-007 | P1 | 启用/停用 switch | 切换 → PATCH `/api/streams/{id}` → UI 变更 |
| STREAM-008 | P2 | 实时预览按钮 | 弹出播放器模态 |
| STREAM-009 | P2 | 查看告警抽屉 | 抽屉展示该流历史告警 |
| STREAM-010 | P1 | 新建流：stream_type 枚举 | 下拉仅包含 rtsp/webrtc/hls |

---

## 5. 告警中心（`/alerts`）

### 5.1 字段临界值
| 字段 | 约束 |
|------|------|
| page | ≥1 |
| size | 1–100，默认 8 |
| start_time / end_time | ISO 8601 |
| confidence | 0–1 |

### 5.2 用例

| 编号 | 优先级 | 用例 | 预期 |
|------|--------|------|------|
| ALERT-001 | P0 | 页面加载默认最近 7 天 | 列表显示近 7 天告警 |
| ALERT-002 | P1 | 按算法名筛选 | 下拉选 → 点击搜索 → 只显示对应算法告警 |
| ALERT-003 | P1 | 按相机名筛选 | 输入 → 搜索 |
| ALERT-004 | P1 | 自定义时间范围 | 选择起止 → 搜索 → 结果符合 |
| ALERT-005 | P1 | 清空筛选条件：重置 | 点击重置 → 时间回到近 7 天 |
| ALERT-006 | P1 | 分页 | 点击第二页 → 请求 page=2 |
| ALERT-007 | P2 | 点击告警图片预览大图 | 弹出预览模态 |
| ALERT-008 | P2 | size 临界值 0 / 101 | 应拒绝或走默认 |

---

## 6. 分析结果查询（`/analysis-results`）

| 编号 | 优先级 | 用例 |
|------|--------|------|
| RESULT-001 | P0 | 页面加载历史任务列表 |
| RESULT-002 | P1 | 按 video_id 筛选 |
| RESULT-003 | P1 | 按状态筛选（ANALYZING/COMPLETED/ERROR） |
| RESULT-004 | P1 | 点击任务 → 展开查看帧分析结果 |
| RESULT-005 | P1 | 下载/导出结果（若支持） |
| RESULT-006 | P2 | 空数据态显示 |

---

## 7. AI 编排算法（`/prompts`）与 AI 模型编排（`/ai-model`）

### 7.1 AI 编排算法列表

| 编号 | 用例 |
|------|------|
| PROMPT-001 | 列表加载 |
| PROMPT-002 | 按名称搜索过滤 |
| PROMPT-003 | 点击"新建算法"跳转 `/ai-model` |
| PROMPT-004 | 点击编辑跳转 `/ai-model?edit=id` |
| PROMPT-005 | 点击删除（Popconfirm → DELETE） |

### 7.2 AI 模型编排（新建/编辑）

**关键字段与临界值：**

| 字段 | 范围 | 测试点 |
|------|------|--------|
| name | 1–255 | 0 / 1 / 255 / 256 |
| provider | enum | qwen / moonshot / gpt / claude / gemini / baidu / lanyi |
| temperature | 0–2 | -0.1 / 0 / 2 / 2.1 |
| top_p | 0–1 | -0.1 / 0 / 1 / 1.1 |
| max_tokens | ≥1 | 0 / 1 / 99999 |
| confidence_threshold | 0–1 | 0 / 0.7 / 1 / 1.01 |

| 编号 | 优先级 | 用例 | 预期 |
|------|--------|------|------|
| MODEL-001 | P0 | 页面表单完整渲染 | 所有字段存在 |
| MODEL-002 | P0 | 填写完整表单并保存 | 跳转列表，新算法出现 |
| MODEL-003 | P1 | name 为空 | 前端校验失败 |
| MODEL-004 | P1 | temperature=2.1 | InputNumber 拒绝或后端 422 |
| MODEL-005 | P1 | top_p=-0.1 | 拒绝 |
| MODEL-006 | P1 | max_tokens=0 | 拒绝 |
| MODEL-007 | P1 | confidence_threshold=1.01 | 拒绝 |
| MODEL-008 | P2 | 上传测试图片点击测试 | 显示 ai_response / confidence / processing_time |
| MODEL-009 | P2 | 重置表单 | 所有字段清空 |
| MODEL-010 | P1 | 返回列表 | 路由变 `/prompts` |

---

## 8. AI 供应商配置（`/ai-provider-config`）

| 编号 | 用例 |
|------|------|
| PROVIDER-001 | 列表加载 |
| PROVIDER-002 | 新建供应商（name + api_key + base_url） |
| PROVIDER-003 | 测试连接按钮 |
| PROVIDER-004 | 编辑 |
| PROVIDER-005 | 启用/停用切换 |
| PROVIDER-006 | 删除 |

---

## 9. 检测类型模板（`/detection-templates`）

| 编号 | 用例 |
|------|------|
| DTYPE-001 | 列表加载 |
| DTYPE-002 | 新建模板 |
| DTYPE-003 | 批量导入 |
| DTYPE-004 | 编辑/删除 |
| DTYPE-005 | type_code 唯一性 |

---

## 10. 性能监控（`/performance`）

| 编号 | 用例 |
|------|------|
| PERF-001 | 页面加载图表 |
| PERF-002 | 指标实时刷新 |
| PERF-003 | 图表鼠标悬停显示明细 |

---

## 11. 用户管理（`/user-management`，Admin 专属）

### 11.1 字段临界值
| 字段 | 约束 |
|------|------|
| username | 3–50 字符 |
| password | ≥6 字符 |
| email | 标准格式 |
| role | `admin / user / viewer` |

### 11.2 用例

| 编号 | 优先级 | 用例 | 预期 |
|------|--------|------|------|
| USER-001 | P0 | Admin 登录后进入 | 显示用户列表、统计卡片 |
| USER-002 | P0 | 新建用户 `testuser / user123456 / user` | 列表出现新用户 |
| USER-003 | P1 | username 长度 2 字符 | 前端/后端提示 ≥3 |
| USER-004 | P1 | username 长度 51 字符 | 拒绝 |
| USER-005 | P1 | password 长度 5 字符 | 后端返回 422 |
| USER-006 | P1 | 重复 username | 提示 "用户名已存在" |
| USER-007 | P1 | 非法 email | 提示格式错误 |
| USER-008 | P1 | 修改密码（新密码 ≥6） | 成功 |
| USER-009 | P1 | 切换 is_active | UI 更新 |
| USER-010 | P0 | 删除测试用户 | Popconfirm → 列表移除 |
| USER-011 | P1 | 禁止删除自己 | 按钮禁用或接口返回 400 |
| USER-012 | P1 | 禁止删除 admin 用户 | 接口返回 400 "无法删除系统管理员" |

---

## 12. 核心业务端到端流程（E2E Happy Path）

### 12.1 视频上传→分析→查看结果
1. 登录 admin → 进入 `/video-management`
2. 上传 demo.mp4（≤ 500MB）
3. 上传完成后点击该行"配置算法"→选择已有算法→启动分析
4. 轮询 `analysis_progress` 直到 100%
5. 跳转 `/analysis-results?video_id=X`
6. 查看帧分析详情与告警

### 12.2 实时流→检测→告警
1. 进入 `/stream-management`
2. 创建 `rtsp://demo.test/s1`
3. 绑定算法 → 启用
4. 切换 `/alerts` → 验证该流产生的告警

### 12.3 算法编排→测试→上线
1. `/prompts` → 新建算法
2. 填写表单 → 测试配置（上传测试图）→ 查看响应
3. 保存（status=draft）
4. 手工激活为 active

### 12.4 用户生命周期
1. admin 新建 user 账号
2. 用该账号登录 → 校验路由权限（不能访问 `/user-management`）
3. admin 修改该用户角色为 viewer → 重新登录生效
4. admin 禁用用户 → 用户无法登录
5. admin 删除用户

---

## 13. Playwright 执行方式

```bash
# 一次性安装
npx playwright install chromium

# 交互式打开页面（用户指定方式）
npx playwright open --viewport-size 1280,800 http://localhost:5173/

# 自动化运行所有用例
npx playwright test tests/e2e --reporter=list

# 只运行冒烟集
npx playwright test tests/e2e --grep @smoke
```

测试脚本位置：`tests/e2e/*.spec.ts`。

---

## 14. 通过/失败判定

- **P0 全部通过**才允许合并到 main
- **P1 通过率 ≥ 90%** 作为版本发布门槛
- 所有失败用例必须登记缺陷单，标注复现步骤、截图、控制台日志
- 每次跑完生成 `test-results/` 目录与 HTML 报告
