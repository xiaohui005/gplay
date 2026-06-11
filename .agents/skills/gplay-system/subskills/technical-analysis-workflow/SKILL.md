---
name: technical-analysis-workflow
description: Use when changing GPlay 技术研判功能、信心度解释、信号通知、买卖止损价格、技术指标计算、研判历史或相关 API/页面展示。
---

# Technical Analysis Workflow

## 使用时机

Use when:

- 修改技术研判页、研判历史页或相关样式。
- 修改做T分析页、做T信号价或做T评分逻辑。
- 调整 `UP`/`DOWN`/`SIDEWAYS` 方向、信心度、推荐语、信号通知。
- 修改买入价、卖出价、止损价或 ATR/支撑压力相关逻辑。
- 调整技术指标计算、证据列表、风险提示或历史准确率。
- 排查技术研判页面白屏、加载卡住、价格远离现价、信号解释不清楚。

## 关键文件

| 层 | 文件 | 用途 |
|---|---|---|
| 指标引擎 | `server/src/analysis/technical_engine.py` | 计算趋势、MACD、RSI、布林带、量能、支撑压力、方向和信心度 |
| 做T处理器 | `server/src/handlers/t_analysis.py` | 计算做T评分、当前价、买入价、卖出价、止损价 |
| API 处理器 | `server/src/handlers/technical_analysis.py` | 拉取 K 线、生成记录、返回详情/历史/验证结果 |
| 调度器 | `server/src/services/task_scheduler.py` | `09:30`/`14:30` 自动保存关注股技术研判 |
| 数据模型 | `server/src/models/technical_record.py` | 存储研判记录、信心度、方向、指标 JSON、验证结果 |
| 类型 | `frontend/src/types/api.ts` | `TechnicalAnalysisResult` 和指标结构 |
| 页面 | `frontend/src/pages/TechnicalAnalysisPage.tsx` | 技术研判详情、信号通知、证据/风险展示 |
| 历史 | `frontend/src/pages/AnalysisHistoryPage.tsx` | 历史记录、准确率、验证状态 |
| 样式 | `frontend/src/styles/technical-analysis.css` | 技术研判页面样式 |

## 标准流程

### 1. 先确认数据含义

- `direction` 是综合方向：`UP` 看涨、`DOWN` 看跌、`SIDEWAYS` 盘整。
- `confidence` 不是涨跌概率，是技术指标对当前方向的一致程度。
- 低信心度方向要解释成“轻微偏向”，不能展示成强买/强卖。
- `recommendation` 是操作倾向，必须和信号价排序一致。
- 技术研判按每天两波记录：`09:30` 早盘研判、`14:30` 收盘前研判。
- 打开页面只做预览，点击保存或定时任务才写入历史，历史中同时保留研判时段和实际保存时间。
- 自动保存只针对关注列表股票，`09:30` 和 `14:30` 各执行一次。
- 每只股票每天最多 2 条历史：早盘 1 条、收盘前 1 条；同日同股票同时段再次保存必须更新原记录，不能新增重复记录。

### 2. 保持价格来源正确

- `fetch_kline()` 返回顺序可能与指标算法假设不一致，进入技术研判/做T计算前必须按 `date` 升序排序。
- 排序后才允许用 `closes[-1]` / `klines[-1]["close"]` 当最新价。
- 不要在未排序 K 线上遍历或取最后一个 close，否则会取到旧 K 线。
- 技术指标可以用完整 K 线序列，当前操作价必须基于最新价。
- 做T价位必须贴近当前价，买入价不能因为旧 MA/旧支撑位偏离现价太远。

### 3. 保持信号价顺序

| 方向 | 约束 |
|---|---|
| `UP` | `stopLoss < buyPrice < sellPrice` |
| `DOWN` | `buyPrice < sellPrice < stopLoss` |
| `SIDEWAYS` | 价格只作为观望区间参考，不应显示成强操作 |

### 4. 前端展示原则

- 页面必须解释“信心度/信号强度不是概率”。
- `confidence < 30` 展示为弱信号，避免误导用户直接操作。
- `30 <= confidence < 60` 展示为中等信号，提示结合 K 线和成交量确认。
- `confidence >= 60` 才展示为强信号，但仍要提示止损。
- 新增指标时优先追加到信号通知或证据/风险列表，不要先改 API schema。

### 5. 验证

```powershell
# 后端导入检查
python -c "import sys; sys.path.insert(0, 'server'); from src.handlers.technical_analysis import router; print('OK')"

# 技术研判接口检查
python -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/000630/technical-analysis',timeout=30).read()); print(d['priceAtAnalysis'], d['direction'], d['confidence'], d['signals'])"

# 做T价位检查
python -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://127.0.0.1:8008/api/stocks/000338/t-analysis',timeout=30).read()); print(d['levels']['currentPrice'], d['signals']['buyPrice'], d['signals']['sellPrice'], d['signals']['stopLoss'])"

# 同日同时段重复保存检查
python -c "from src.db.database import SessionLocal; from src.handlers.technical_analysis import save_technical_analysis_for_symbol; from src.models import TechnicalRecord; db=SessionLocal(); before=db.query(TechnicalRecord).filter(TechnicalRecord.symbol=='000338').count(); save_technical_analysis_for_symbol(db,'000338'); after=db.query(TechnicalRecord).filter(TechnicalRecord.symbol=='000338').count(); print(before, after); db.close()"

# 前端构建
cd D:\gongju\gplay\frontend
npm run build
```

## 验收标准

- [ ] 技术研判接口返回 `direction`、`confidence`、`signals`、`keyEvidence`、`riskWarning`。
- [ ] 当前价接近最新 K 线价，不出现明显旧价。
- [ ] 信号价满足方向排序约束。
- [ ] 做T买入价、卖出价、止损价贴近当前价，不出现 27 元股票给 17 元买点这类旧价。
- [ ] 页面清楚解释信心度不是概率。
- [ ] 弱信号不会被展示成强操作建议。
- [ ] 预览不自动入历史，保存按钮能写入历史。
- [ ] 关注列表股票会在 `09:30` 和 `14:30` 自动写入历史。
- [ ] 同日同股票同时段重复保存后，历史条数不增加。
- [ ] 历史时间展示研判时段（早盘 09:30 / 收盘前 14:30）和实际保存时间。
- [ ] `npm run build` 成功。

## 常见错误

| 问题 | 原因 | 处理 |
|---|---|---|
| 页面白屏 | 后端未返回 `keyEvidence`/`riskWarning`，前端直接 map | 前端使用空数组兜底，后端从指标 JSON 补齐 |
| 价格远离现价 | K 线顺序未排序，旧 close/旧 MA 被当成当前参考 | 计算前按 `date` 升序排序，再用 `closes[-1]` |
| 做T买点离谱 | 当前价和 MA/ATR 的时间序列不一致 | 做T内部排序 K 线、用实时价覆盖最新 close，并限制买点贴近现价 |
| 止损方向错误 | 未区分看涨/看跌排序 | 按 `UP`/`DOWN` 分别强制排序 |
| 信心度误解 | 用户把强度当概率 | 文案写明“不是涨跌概率” |
| 弱看跌像强卖出 | 只显示方向不显示强弱 | 增加弱/中/强信号通知 |
