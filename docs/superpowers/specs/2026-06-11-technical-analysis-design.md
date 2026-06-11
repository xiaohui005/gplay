# 技术研判（Technical Analysis）功能设计

## 概述

新增独立的技术研判功能，从专业分析师角度综合多项技术指标，判断股票短期方向（涨/跌/盘整），并记录每次分析以便后续验证准确率。

## 数据模型

### TechnicalRecord

新建 `server/src/models/technical_record.py`：

| 字段 | 类型 | 说明 |
|---|---|---|
| id | int, PK, auto | 主键 |
| symbol | str, index | 股票代码 |
| name | str | 股票名称 |
| created_at | datetime, index | 分析时间 |
| price_at_analysis | float | 分析时的最新收盘价 |
| predicted_direction | str | UP / DOWN / SIDEWAYS |
| confidence_score | float | 信心度 0-100 |
| indicators_json | str | 所有指标快照（JSON） |
| summary | str | 分析师风格总评文字 |
| actual_direction | str, nullable | 实际方向（稍后填充） |
| is_correct | bool, nullable | 判断是否正确（稍后填充） |
| verified_at | datetime, nullable | 验证时间 |

### 初始化

在 `server/src/models/__init__.py` 注册并加入 `__all__`。

## 技术指标引擎

新建 `server/src/analysis/technical_engine.py`，输入 K 线数据，输出结构：

```python
{
    "direction": "UP",          # UP / DOWN / SIDEWAYS
    "confidence": 72,           # 0-100
    "summary": "...",           # 分析师总评
    "keyEvidence": [...],       # 关键证据列表
    "riskWarning": [...],       # 风险提示列表
    "indicators": {
        "trend": {
            "maAlignment": "bullish",    # bullish / bearish / neutral
            "maCross": "golden_cross",   # golden_cross / death_cross / none
            "adx": 25.3,                 # 趋势强度
            "detail": "MA5 > MA10 > MA20 多头排列"
        },
        "momentum": {
            "macdHistogram": 0.15,       # MACD 柱状图值
            "macdDirection": "rising",   # rising / falling
            "rsi": 62.5,
            "rsiStatus": "neutral",      # overbought / oversold / neutral
            "detail": "MACD 柱状图翻红，RSI 62 中性偏强"
        },
        "volatility": {
            "bollingerPosition": "upper",  # upper / middle / lower
            "bollingerWidth": 4.2,         # 带宽 %
            "detail": "价格运行在布林带上轨，短期偏强"
        },
        "volume": {
            "volumeRatio": 1.35,
            "volumeTrend": "increasing",
            "priceVolumeConfirm": True,    # 价量配合
            "detail": "成交量放大，价量配合良好"
        },
        "supportResistance": {
            "nearestSupport": 10.50,
            "nearestResistance": 11.20,
            "distanceToSupport": 2.1,      # % 距离
            "distanceToResistance": 4.5,
            "detail": "最近支撑 10.50，压力 11.20"
        }
    }
}
```

### 指标计算规则

1. **趋势**（权重 3）
   - MA 排列：MA5 > MA10 > MA20 → bullish；MA5 < MA10 < MA20 → bearish
   - 金叉/死叉：MA5 最近上穿 MA10 → golden_cross，下穿 → death_cross
   - ADX（需 14+ 根 K 线）：>25 趋势强，<20 趋势弱

2. **动量**（权重 2）
   - MACD：DIF > DEA 且柱状图上升 → bullish；DIF < DEA 且下降 → bearish
   - RSI(14)：>70 overbought（潜在下跌），<30 oversold（潜在反弹），30-70 中性

3. **波动**（权重 1）
   - 布林带位置：价格 > 上轨 → upper（偏强），< 下轨 → lower（偏弱），之间 → middle
   - 带宽：收窄预示突破

4. **量能**（权重 1.5）
   - 量比 > 1.3 → 放量；< 0.7 → 缩量
   - 价量配合：价格上涨且放量 → 健康看涨；价格上涨但缩量 → 看跌背离

5. **支撑/压力**（权重 1.5）
   - MA 均线作为动态支撑/压力
   - 当前价格距 MA5/MA10/MA20 距离判断强弱

### 综合打分

```
weighted_score = trend_vote * 3 + momentum_vote * 2 + volatility_vote * 1
                 + volume_vote * 1.5 + sr_vote * 1.5

direction = UP if weighted_score > 1 else DOWN if weighted_score < -1 else SIDEWAYS
confidence = min(abs(weighted_score) / max_possible_score * 100, 100)
```

## API 设计

### `GET /api/stocks/{symbol}/technical-analysis`

计算技术指标 → 保存记录 → 返回完整分析结果。

响应结构：
```json
{
    "id": 1,
    "symbol": "600519",
    "name": "贵州茅台",
    "createdAt": "2026-06-11T14:30:00",
    "priceAtAnalysis": 1520.50,
    "direction": "UP",
    "confidence": 72,
    "indicators": { ... },
    "summary": "贵州茅台短期趋势偏强...",
    "keyEvidence": ["MA5上穿MA10金叉", "MACD柱状图翻红", "成交量放大"],
    "riskWarning": ["RSI 68接近超买区", "布林带触及上轨"],
    "isCorrect": null
}
```

### `GET /api/technical-analysis/history?symbol=X&page=1&limit=20`

分页历史记录，按 `created_at` 降序。对 `is_correct` 为 null 的记录自动验证。

### `GET /api/technical-analysis/history/{id}`

单条详情，触发验证。

### 验证逻辑

服务端在返回历史记录时，对 `is_correct` 仍为 null 的记录自动验证：
1. 获取当前最新 K 线收盘价（截至验证时刻的最新价，不限当日）
2. 对比 `price_at_analysis`：实际变动 = `(latest_close - price_at_analysis) / price_at_analysis × 100`
3. 变动 > +0.5% → UP，< -0.5% → DOWN，其余 → SIDEWAYS
4. 若与实际方向匹配 → `is_correct = true`
5. 写入 `actual_direction`、`is_correct`、`verified_at`
6. 验证仅在记录创建至少 1 小时后触发，避免刚创建就被验证

## 前端页面

### 路由

| 路由 | 页面 |
|---|---|
| `/analysis/:symbol` | 技术研判结果页 |
| `/analysis/history` | 历史分析记录页 |

### 技术研判页 `/analysis/:symbol`

组件：`TechnicalAnalysisPage`

**布局：**
- 顶部工具栏：← 返回按钮（回到详情页或搜索页）
- 标题区：股票名称 + 符号 + 分析时间
- 方向判断卡：
  - 大号方向标识（↑ 看涨 / ↓ 看跌 / → 盘整）
  - 信心度进度条
  - 总评摘要
- 指标网格（2×3 或 3×2）：6 个指标卡片
  - 趋势、动量、波动、量能、支撑/压力、综合
  - 每张卡片：指标名 + 数值 + 色标状态（绿=看涨/红=看跌/灰=中性）
- 关键证据 + 风险提示
- 操作按钮：「重新分析」

**数据流：**
1. 页面加载 → `getTechnicalAnalysis(symbol)` → 后端计算并保存 → 渲染
2. 点击「重新分析」→ 再次调用同一个 API，产生新记录

### 分析历史页 `/analysis/history`

组件：`AnalysisHistoryPage`

**布局：**
- 搜索框：按股票代码筛选
- 统计栏：总次数 / 看涨次数 / 看跌次数 / 准确率
- 表格列：时间 / 股票 / 方向 / 信心 / 当时价格 / 是否符合预期
- 行点击 → 跳转到该次分析详情（`/analysis/history/{id}`）

**数据流：**
1. 页面加载 → `getAnalysisHistory()` → 表格渲染
2. 搜索输入 → 重新请求 + 筛选

### 详情页修改

`DetailPage.tsx`：
- 工具栏新增「技术研判」按钮，链接到 `/analysis/{symbol}`
- 放在「刷新数据」旁边

### 样式

新增 `technical-analysis.css`：
- `.ta-page` — 主容器
- `.ta-header` — 标题区
- `.ta-direction-badge` — 方向大标识（↑ 绿 / ↓ 红 / → 灰）
- `.ta-confidence-bar` — 信心度进度条（渐变绿→黄→红）
- `.ta-indicator-grid` — 指标卡片网格
- `.ta-indicator-card` — 单张指标卡
- `.ta-indicator-status-bullish/bearish/neutral` — 色标
- `.ta-evidence` / `.ta-risk` — 证据/风险区
- `.ta-history-table` — 历史记录表格
- `.ta-stats-bar` — 统计栏

## 文件变更清单

### 新增

| 文件 | 说明 |
|---|---|
| `server/src/models/technical_record.py` | 模型 |
| `server/src/analysis/technical_engine.py` | 指标计算引擎 |
| `server/src/handlers/technical_analysis.py` | API 处理 |
| `frontend/src/pages/TechnicalAnalysisPage.tsx` | 研判结果页 |
| `frontend/src/pages/AnalysisHistoryPage.tsx` | 历史记录页 |
| `frontend/src/styles/technical-analysis.css` | 样式 |

### 修改

| 文件 | 变更 |
|---|---|
| `server/src/models/__init__.py` | 注册 TechnicalRecord |
| `server/src/main.py` | 注册 technical_analysis_router |
| `frontend/src/types/api.ts` | 新增 TechnicalAnalysisResult 等类型 |
| `frontend/src/api/client.ts` | 新增 getTechnicalAnalysis / getAnalysisHistory |
| `frontend/src/pages/DetailPage.tsx` | 新增「技术研判」按钮 |
| `frontend/src/App.tsx` | 新增路由 `/analysis/:symbol` 和 `/analysis/history` |
| `frontend/src/index.css` | 引入 technical-analysis.css |

### 数据库

- 自动迁移：TechnicalRecord 表通过 `run_migrations()` 创建

## 风险与边界情况

1. K 线数据不足（< 20 根）→ 返回 SIDEWAYS + 低信心度 + 标注数据不足
2. 停牌股票 → 显示「当前停牌，无法分析」
3. 验证时股票已退市 → 标记为无法验证
4. 防重复提交：后端在创建前检查该 symbol 最近 10 秒内是否已有记录，若有则返回已有记录
