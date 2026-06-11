---
name: dev-server-workflow
description: 本地开发服务器启动、重启、验证的标准流程。覆盖前后端分离启动、文件变更后重启时机判断、构建验证、端口冲突处理。
---

# Dev Server Workflow

## 使用时机

Use when:

- 首次启动项目前后端服务
- 修改后端代码（API、数据库、模型、服务）后需要重启
- 修改前端代码后确认是否只需要 HMR 而非重启
- 前后端联调时端口冲突或代理不生效
- 交付前需要构建验证
- 种子数据变动后需要重新播种

## 标准流程

### 1. 判断重启范围

| 变更类型 | 需要重启后端 | 需要重启前端 | 需要重新播种 |
|---|---|---|---|
| 后端 API 路由/处理器 | ✅ | ❌（Vite proxy 自动转发） | ❌ |
| 数据库模型/SQL | ✅ | ❌ | 视情况 |
| 后端服务/依赖注入 | ✅ | ❌ | ❌ |
| 前端页面组件 | ❌（HMR 自动生效） | ❌（HMR 自动生效） | ❌ |
| 前端路由 | ❌（HMR 自动生效） | ❌ | ❌ |
| `vite.config.ts` | ❌ | ✅ | ❌ |
| 前端依赖 | ❌ | ✅（需重跑 `npm install`） | ❌ |
| 种子数据 | ✅ | ❌ | ✅ |
| 后端测试 | ❌（独立运行） | ❌ | ❌ |

### 2. 启动服务

```powershell
# 终端 1：后端
cd D:\gongju\gplay\server
python -m src.main

# 终端 2：前端（开发模式，支持 HMR）
cd D:\gongju\gplay\frontend
npx vite --host
```

### 3. 重启后端

```powershell
# 方式 A：按窗口标题杀死
taskkill /F /FI "WINDOWTITLE eq 股票智能研判"
# 方式 B：按端口杀死
netstat -ano | findstr ":8008"
# 取最后一列 PID，逐个 kill
taskkill /F /PID <PID>

# 重新启动
cd D:\gongju\gplay\server
python -m src.main
```

### 4. 验证服务

```powershell
# 验证后端存活
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8008/', timeout=5); print(r.status, r.read()[:200].decode())"

# 验证搜索接口
python -c "import urllib.request, json; r=urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/search?keyword=600000', timeout=5); print(json.loads(r.read())['items'][0]['name'])"

# 验证研判接口
python -c "import urllib.request, json; r=urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/600000/analysis', timeout=5); d=json.loads(r.read()); print(d['suggestion'], d['score']['total'])"

# 验证一键采集
python -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8008/api/stocks/601899/collect', method='POST'); r=urllib.request.urlopen(req, timeout=15); import json; d=json.loads(r.read()); print(d['status'], d['name'], d['price'])"

# 验证前端代理
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:5173/', timeout=5); print(r.status)"
```

### 5. 构建验证（交付前）

```powershell
cd D:\gongju\gplay\frontend

# Step 1: TypeScript 类型检查
npx tsc --noEmit

# Step 2: Vite 生产构建
npx vite build

# 构建产物在 frontend/dist/
```

### 6. 后端测试

```powershell
cd D:\gongju\gplay\server

# 全量测试
python -m pytest

# 指定测试文件（可组合多个）
python -m pytest tests/test_analysis.py -v
python -m pytest tests/test_collection.py -v
python -m pytest tests/test_handlers.py -v
python -m pytest tests/test_stock.py -v
python -m pytest tests/test_scheduler.py -v
```

### 7. 种子数据

```powershell
# 覆写数据库并插入 16 只样本股票
cd D:\gongju\gplay\server
python -m src.seed

# 重新播种后必须重启后端
# 然后验证种子数据
python -c "import urllib.request, json; r=urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/search?keyword=600000', timeout=5); print(len(json.loads(r.read())['items']), '只股票')"
```

## 验收标准

- [ ] 后端启动后在 `http://127.0.0.1:8008/` 返回 JSON（含 `status: "ok"`）
- [ ] 搜索接口返回正确股票列表
- [ ] 研判接口返回评分、建议、大师详情、条件、买卖计划
- [ ] 一键采集接口返回 `status: "ok"` + 股价信息
- [ ] 前端 dev server 在 `http://127.0.0.1:5173/` 可访问，API 请求正确代理到后端
- [ ] `npx tsc --noEmit` 通过（无类型错误）
- [ ] `npx vite build` 成功（产生 `frontend/dist/`）
- [ ] `python -m pytest` 全部通过

## 常见错误

### 端口被占用

```powershell
netstat -ano | findstr ":8008"
netstat -ano | findstr ":5173"
# 取对应 PID 执行 taskkill
taskkill /F /PID <PID>
```

### Vite 代理 404（/api 请求返回前端 HTML）

原因：Vite dev server 先于后端启动，或后端重启后端口变了。

解决：确保后端先启动，或重启 Vite 进程。

### Python 模块找不到

```powershell
cd D:\gongju\gplay\server
# 确认当前目录下有 src/ 目录
python -c "import src; print(src.__file__)"
```

### 采集接口报 404

原因：后端未包含最新的 stock_router 注册。

解决：检查 `src/main.py` 中是否包含 `app.include_router(stock_router)`。

### 种子数据后搜索不到

原因：播种后未重启后端（SQLite 文件被覆写，但旧连接仍持有旧数据）。

解决：先重启后端，再搜索。
