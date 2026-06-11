---
name: fullstack-feature
description: Use when adding a new feature that spans backend (model/handler) and frontend (component/API client), such as watchlist, collect, or similar CRUD-based features.
---

# Fullstack Feature Workflow

## 使用时机

Use when implementing a feature that touches both backend and frontend, typically following a Model → Handler → Router → API Client → Component → CSS pattern.

Do NOT use for:
- Pure backend changes (schemas, collectors, scheduled tasks) → use dev-server-workflow
- Pure frontend changes (layout, CSS, routing) → use dev-server-workflow

## 标准流程

### Step 0: Read existing patterns first

Before writing any code, read existing examples of each layer:
- Model: `server/src/models/stock_basic.py` or `user_watchlist.py`
- Handler: `server/src/handlers/watchlist.py` (3-endpoint CRUD pattern)
- API client: `frontend/src/api/client.ts` (get/post/del helpers)
- Types: `frontend/src/types/api.ts` (matching the handler response shape)

### Step 1: 后端 — 模型 (model)

```python
# server/src/models/your_model.py
import datetime
from sqlalchemy import Column, DateTime, Integer, String, Float
from src.db.database import Base

class YourModel(Base):
    __tablename__ = "your_table"
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.datetime.utcnow)
```

Then register in `server/src/models/__init__.py`:
```python
from src.models.your_model import YourModel
__all__ = [..., "YourModel"]
```

Migration is automatic: `run_migrations()` on startup calls `Base.metadata.create_all()`.

### Step 2: 后端 — 处理器 (handler)

```python
# server/src/handlers/your_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.db.database import get_db
from src.models import YourModel, StockBasic, StockQuoteSnapshot

router = APIRouter(prefix="/api/your-feature", tags=["your-feature"])

@router.get("")
def list_items(db: Session = Depends(get_db)):
    rows = db.query(YourModel).order_by(YourModel.added_at.desc()).all()
    items = []
    for r in rows:
        basic = db.query(StockBasic).filter(StockBasic.symbol == r.symbol).first()
        q = db.query(StockQuoteSnapshot).filter(
            StockQuoteSnapshot.symbol == r.symbol
        ).order_by(StockQuoteSnapshot.id.desc()).first()
        items.append({
            "symbol": r.symbol,
            "name": basic.name if basic else r.symbol,
            "latestPrice": q.latest_price if q else None,
            "changePercent": q.change_percent if q else None,
        })
    return {"items": items}

@router.post("/{symbol}")
def add_item(symbol: str, db: Session = Depends(get_db)):
    exist = db.query(YourModel).filter(YourModel.symbol == symbol).first()
    if exist:
        return {"status": "ok", "symbol": symbol, "message": "已存在"}
    basic = db.query(StockBasic).filter(StockBasic.symbol == symbol).first()
    if not basic:
        raise HTTPException(status_code=404, detail=f"股票 {symbol} 不存在")
    db.add(YourModel(symbol=symbol))
    db.commit()
    return {"status": "ok", "symbol": symbol}

@router.delete("/{symbol}")
def remove_item(symbol: str, db: Session = Depends(get_db)):
    row = db.query(YourModel).filter(YourModel.symbol == symbol).first()
    if not row:
        raise HTTPException(status_code=404)
    db.delete(row)
    db.commit()
    return {"status": "ok"}
```

Then wire in `server/src/main.py`:
```python
from src.handlers.your_feature import router as your_router
app.include_router(your_router)
```

### Step 3: 前端 — API 客户端 (client.ts)

```typescript
// frontend/src/api/client.ts
import type { YourItem } from '../types/api'

export function getYourFeature(): Promise<{ items: YourItem[] }> {
  return get('/your-feature')
}

export function addYourFeature(symbol: string): Promise<{ status: string }> {
  return post(`/your-feature/${symbol}`)
}

export function removeYourFeature(symbol: string): Promise<{ status: string }> {
  return del(`/your-feature/${symbol}`)
}
```

The `get`, `post`, `del` helpers already exist — don't recreate them:
- `get<T>(path)` → GET + JSON parse
- `post<T>(path)` → POST (no body) + JSON parse
- `del<T>(path)` → DELETE + JSON parse

### Step 4: 前端 — 类型定义 (types/api.ts)

```typescript
export interface YourItem {
  symbol: string
  name: string
  latestPrice: number | null
  changePercent: number | null
}
```

Response shape must match the handler's return value exactly.

### Step 5: 前端 — 组件 (pages/)

- Place feature-specific state (loading, error, data) in the component
- Use `useCallback` for handlers that depend on state
- IMPORTANT: define functions in dependency order — if `handleX` calls `doY`, define `doY` **before** `handleX`
- CSS goes in `frontend/src/index.css` (single file, no CSS modules)

### Step 6: 验证

```powershell
# 1. TypeScript 检查
cd frontend
npx tsc --noEmit

# 2. 前端构建
npx vite build

# 3. 重启后端（后端改动后必须重启）
taskkill /F /FI "WINDOWTITLE eq 股票智能研判"
cd server
python -m src.main

# 4. 测试 API
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8008/api/your-endpoint', timeout=5); print(r.read())"

# 5. 全量后端测试（可选）
python -m pytest
```

## 验收标准

- [ ] `npx tsc --noEmit` 通过（无类型错误）
- [ ] `npx vite build` 成功
- [ ] 后端重启后新端点正常响应
- [ ] 前端页面能正确渲染数据
- [ ] CRUD 操作（至少查询和创建）端到端可用

## 常见错误

### 页面空白 / React 崩溃

**原因**：JS 暂时性死区 — `const handleX` 中引用了在它后面定义的 `const doY`。

**解决**：确保函数按依赖顺序定义。如果 `handleX` 调用 `doY`，`doY` 必须在 `handleX` 之前定义。

### 后端模型没建表

**原因**：模型未在 `models/__init__.py` 中 import，`Base.metadata` 找不到。

**解决**：确认 `__init__.py` 中有 `from src.models.your_model import YourModel`。

### API 返回 404

**原因**：路由未注册 — `main.py` 中缺少 `app.include_router(your_router)`。

**解决**：确认 main.py 中 import 并 include_router。

### frontend API 报 404

**原因**：前端请求路径与后端路由不匹配（常见：多/少 `/api` 前缀）。

**解决**：`client.ts` 中的 BASE 已经是 `/api`，路径不要再加 `/api`。
