# Bark 推送配置页实施计划

> **对于代理工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 来逐任务实施此计划。步骤使用复选框（`- [ ]`）语法进行跟踪。

**目标：** 新增 Bark 推送配置页，支持保存配置并发送测试推送。

**架构：** 后端新增通知配置模型、服务和设置接口；配置保存在 SQLite 中，测试推送由后端调用 Bark HTTP API。前端新增 `/settings` 页面，通过现有 `/api` 代理读取、保存并测试配置。

**技术栈：** FastAPI、SQLAlchemy、requests、React、TypeScript、Vite。

---

### 任务 1：后端通知配置模型

**文件：**
- 创建：`server/src/models/notification_config.py`
- 修改：`server/src/models/__init__.py`

- [ ] **步骤 1：创建配置模型**

创建 `NotificationConfig`，字段包含 `bark_enabled`、`bark_server_url`、`bark_device_key`、时间戳和 `to_dict()`。

- [ ] **步骤 2：注册模型导入**

在 `server/src/models/__init__.py` 导入 `NotificationConfig` 并加入 `__all__`，让 `run_migrations()` 能自动建表。

- [ ] **步骤 3：运行模型导入验证**

运行：`python -c "from src.models import NotificationConfig; print(NotificationConfig.__tablename__)"`
工作目录：`server`
预期：输出 `notification_config`。

### 任务 2：后端 Bark 服务和设置接口

**文件：**
- 创建：`server/src/services/bark_service.py`
- 创建：`server/src/handlers/settings.py`
- 修改：`server/src/main.py`

- [ ] **步骤 1：创建 BarkService**

实现 `send_test()`，使用 `requests.get()` 调用 `{server}/{device_key}/GPlay Bark 推送测试/如果你收到这条消息，说明 GPlay Bark 推送配置已生效。`。

- [ ] **步骤 2：创建 settings router**

实现：
- `GET /api/settings/notification`
- `PUT /api/settings/notification`
- `POST /api/settings/notification/test`

- [ ] **步骤 3：注册 router**

在 `server/src/main.py` 导入并 `include_router(settings_router)`，根接口 `endpoints` 增加 `settings`。

- [ ] **步骤 4：运行后端接口导入验证**

运行：`python -c "from src.handlers.settings import router; print(router.prefix)"`
工作目录：`server`
预期：输出 `/api/settings`。

### 任务 3：前端 API 类型和客户端方法

**文件：**
- 修改：`frontend/src/types/api.ts`
- 修改：`frontend/src/api/client.ts`

- [ ] **步骤 1：新增类型**

在 `api.ts` 增加 `NotificationSettings` 和 `SaveNotificationSettingsPayload`。

- [ ] **步骤 2：扩展 fetch helper**

在 `client.ts` 增加支持 JSON 请求体的 `put<T>()`。

- [ ] **步骤 3：新增设置 API 方法**

实现：
- `getNotificationSettings()`
- `saveNotificationSettings(payload)`
- `testNotificationSettings()`

### 任务 4：前端配置页和入口

**文件：**
- 创建：`frontend/src/pages/SettingsPage.tsx`
- 修改：`frontend/src/App.tsx`
- 修改：`frontend/src/pages/SearchPage.tsx`
- 修改：`frontend/src/index.css`

- [ ] **步骤 1：创建 SettingsPage**

页面加载时读取配置，提供 Bark 启用开关、服务地址、Device Key、保存按钮、测试按钮和状态提示。

- [ ] **步骤 2：注册路由**

在 `App.tsx` 增加 `/settings` 路由。

- [ ] **步骤 3：添加入口**

在 `SearchPage.tsx` 顶部增加“配置”按钮，点击跳转 `/settings`。

- [ ] **步骤 4：添加样式**

在 `index.css` 增加配置页表单、按钮和状态提示样式。

### 任务 5：验证和交付

**文件：**
- 不新增文件。

- [ ] **步骤 1：运行后端启动验证**

运行：`python -m src.main`
工作目录：`server`
预期：服务可访问 `http://localhost:8008/health`。

- [ ] **步骤 2：验证默认配置接口**

运行：`Invoke-RestMethod -Uri "http://localhost:8008/api/settings/notification"`
预期：返回空 Bark 配置。

- [ ] **步骤 3：运行前端构建**

运行：`npm run build`
工作目录：`frontend`
预期：TypeScript 和 Vite 构建通过。

- [ ] **步骤 4：汇总交付**

说明改动文件、验证命令和 Bark 测试推送使用方式。
