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
- 需要用后端 `8008` 直接访问前端生产包，避免常开 Vite `5173`
- 种子数据变动后需要重新播种
- 前后端进程意外退出需要排查和恢复

## 标准流程

### 1. 判断重启范围

| 变更类型 | 需要重启后端 | 需要重启前端 | 需要重新播种 |
|---|---|---|---|
| 后端 API 路由/处理器 | ✅ | ❌（Vite proxy 自动转发） | ❌ |
| 数据库模型/SQL | ✅ | ❌ | 视情况 |
| 后端服务/依赖注入 | ✅ | ❌ | ❌ |
| 前端页面组件（开发模式） | ❌（HMR 自动生效） | ❌（HMR 自动生效） | ❌ |
| 前端路由（开发模式） | ❌（HMR 自动生效） | ❌ | ❌ |
| 前端页面/路由（8008 生产托管） | ✅（重启后端读取新 dist） | ❌ | ❌ |
| `vite.config.ts` | ❌ | ✅ | ❌ |
| 前端依赖 | ❌ | ✅（需重跑 `npm install`） | ❌ |
| 种子数据 | ✅ | ❌ | ✅ |
| 后端测试 | ❌（独立运行） | ❌ | ❌ |

### 2. 启动服务

#### 2a. 交互式终端（推荐）

```powershell
# 终端 1：后端
cd D:\gongju\gplay\server
python -m uvicorn src.main:app --port 8008

# 终端 2：前端（开发模式，支持 HMR）
cd D:\gongju\gplay\frontend
npx vite --host
```

#### 2b. 用 Start-Process 启动（后台进程，适合 OpenCode 自动操作）

```powershell
# 后端（带 --reload 无需每次重启）
Start-Process -WindowStyle Hidden -FilePath python -ArgumentList "-m uvicorn src.main:app --reload --port 8008" -WorkingDirectory D:\gongju\gplay\server

# 前端（注意：必须用 node_modules/.bin/vite，npx 下 Start-Process 会秒退）
Start-Process -WindowStyle Hidden -FilePath "node_modules/.bin/vite" -ArgumentList "--host","--port","5173" -WorkingDirectory D:\gongju\gplay\frontend
```

#### 2c. 验证进程存活

```powershell
netstat -ano | Select-String ":8008.*LISTEN"
netstat -ano | Select-String ":5173.*LISTEN"
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8008/
curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:5173/
```

#### 2d. 用 8008 直接托管前端生产包（推荐给日常使用）

```powershell
# 先构建前端产物
cd D:\gongju\gplay\frontend
npm run build

# 再启动或重启后端
cd D:\gongju\gplay\server
python -m uvicorn src.main:app --port 8008
```

访问方式：

| 地址 | 用途 |
|---|---|
| `http://127.0.0.1:8008/` | 前端生产页面 |
| `http://127.0.0.1:8008/analysis/history?symbol=000338` | React Router 深链接 |
| `http://127.0.0.1:8008/api` | 后端服务信息 |
| `http://127.0.0.1:8008/api/stocks/search?keyword=000338` | 后端 API |

### 3. 重启后端

```powershell
# 方式 A：按端口杀掉
netstat -ano | Select-String ":8008" | ForEach-Object { $parts = $_ -replace '\s+', ' ' -split ' '; $pid = $parts[-1]; if ($pid -match '^\d+$') { Stop-Process -Id $pid -Force; "Killed $pid" } }

# 重新启动
Start-Process -WindowStyle Hidden -FilePath python -ArgumentList "-m uvicorn src.main:app --reload --port 8008" -WorkingDirectory D:\gongju\gplay\server

# 验证
Start-Sleep 3; curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:8008/
```

### 4. 验证服务

```powershell
# 验证后端存活
python -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:8008/health', timeout=5).read()); print(d['status'])"

# 验证 8008 返回前端生产 HTML
python -c "import urllib.request; data=urllib.request.urlopen('http://127.0.0.1:8008/', timeout=5).read().decode('utf-8'); print('root' in data and 'assets/' in data)"

# 验证 React Router 深链接回退到前端 HTML
python -c "import urllib.request; data=urllib.request.urlopen('http://127.0.0.1:8008/analysis/history?symbol=000338', timeout=5).read().decode('utf-8'); print('root' in data and 'assets/' in data)"

# 验证搜索接口
python -c "import urllib.request, json; r=urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/search?keyword=600000', timeout=5); print(json.loads(r.read())['items'][0]['name'])"

# 验证研判接口
python -c "import urllib.request, json; r=urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/600000/analysis', timeout=5); d=json.loads(r.read()); print(d['suggestion'], d['score']['total'])"

# 验证做T分析接口
python -c "import urllib.request, json; r=urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/603993/t-analysis', timeout=15); d=json.loads(r.read()); print(d['suitability'], d['score'], 'signals:', 'buyPrice' in d)"

# 验证一键采集
python -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8008/api/stocks/601899/collect', method='POST'); r=urllib.request.urlopen(req, timeout=15); import json; d=json.loads(r.read()); print(d['status'], d['name'], d['price'])"

# 验证前端代理
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:5173/', timeout=5); print(r.status)"

# 验证前端详情页渲染（Playwright — 捕获 JS 错误）
node -e @"
const {chromium} = require('playwright');
(async () => {
  const b = await chromium.launch({headless:true});
  const p = await b.newPage();
  let errs = [];
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('http://127.0.0.1:5173/stock/603993', {timeout:15000});
  await p.waitForTimeout(8000);
  const text = await p.textContent('body');
  console.log('Has 做T分析:', text.includes('做T分析'));
  console.log('Has 买入价:', text.includes('买入价'));
  console.log('JS errors:', errs.length ? errs.join(' | ') : 'NONE');
  await b.close();
})().catch(e => console.error(e.message));
"@

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

- [ ] 后端启动后在 `http://127.0.0.1:8008/health` 返回 JSON（含 `status: "ok"`）
- [ ] 执行 `npm run build` 后，`http://127.0.0.1:8008/` 返回前端生产页面
- [ ] `http://127.0.0.1:8008/analysis/history?symbol=000338` 能返回前端 HTML（深链接可用）
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

### 8008 打开后提示前端 dist 不存在

原因：后端已启动，但 `frontend/dist/index.html` 尚未生成。

解决：在 `frontend/` 运行 `npm run build`，然后重启后端。

### 8008 深链接 404

原因：后端没有把非 `/api/*` 路径回退到 `frontend/dist/index.html`，或后端尚未重启到最新代码。

解决：确认 `server/src/main.py` 中有 SPA fallback，并重启后端。

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

### 前端 dev server 启动后秒死

原因：用 `Start-Process` 启动 `npx vite` 时，`npx` 的临时进程退出导致子进程被回收。

解决：直接用 `node_modules/.bin/vite` 路径绕过 npx：
```powershell
Start-Process -WindowStyle Hidden -FilePath "node_modules/.bin/vite" -ArgumentList "--host","--port","5173" -WorkingDirectory D:\gongju\gplay\frontend
```

### KlineChart "Object is disposed"

原因：React StrictMode 双挂载时 useEffect cleanup 只调了 `remove()` 没置 null。

解决：cleanup 中 `remove()` 后把所有 ref 置 null：
```typescript
return () => {
  if (chartRef.current) {
    chartRef.current.remove()
    chartRef.current = null
    candleSeriesRef.current = null
    volumeSeriesRef.current = null
  }
}
```

### 做T分析接口返回 UNSUITABLE score=0

原因：East Money K线 API 区域不可达，3 次重试后返回空数据。

解决：已切换到 Sina K线 API（`money.finance.sina.com.cn`），响应 <1s。

### 使用 Start-Process 后进程存活但端口已被 TIME_WAIT 占用

原因：PowerShell 的 Start-Process 无法等待进程启动完成；当上一进程刚 kill 时端口仍在 TIME_WAIT。

解决：kill 后等 3-5 秒再启动，或换一个临时端口测试。
