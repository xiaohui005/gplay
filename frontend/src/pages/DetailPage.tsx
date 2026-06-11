import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getQuote, getAnalysis, collectStock, addWatchlist, removeWatchlist, getWatchlist, getTAnalysis, getKline, getNews } from '../api/client'
import type { StockQuote, AnalysisResult, TAnalysisResult, KlineBar, NewsItem } from '../types/api'
import KlineChart from '../components/KlineChart'

export default function DetailPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const nav = useNavigate()
  const [quote, setQuote] = useState<StockQuote | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [collecting, setCollecting] = useState(false)
  const [error, setError] = useState('')
  const [following, setFollowing] = useState(false)
  const [tAnalysis, setTAnalysis] = useState<TAnalysisResult | null>(null)

  const [klineData, setKlineData] = useState<KlineBar[]>([])
  const [klineDays, setKlineDays] = useState(60)
  const [newsItems, setNewsItems] = useState<NewsItem[]>([])

  useEffect(() => {
    if (!symbol) return
    getWatchlist().then(res => {
      setFollowing(res.items.some(i => i.symbol === symbol))
    }).catch(() => {})
  }, [symbol])

  const fetchData = useCallback((sym: string) => {
    getQuote(sym).then(setQuote).catch(() => setQuote(null))
    getAnalysis(sym)
      .then(setAnalysis)
      .catch((e) => setError(e instanceof Error ? e.message : '请求失败'))
    getTAnalysis(sym).then(setTAnalysis).catch(() => {})
    getKline(sym, 60).then(res => setKlineData(res.items)).catch(() => {})
    getNews(sym).then(res => setNewsItems(res.items)).catch(() => {})
  }, [])

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    setError('')
    fetchData(symbol)
    setLoading(false)
  }, [symbol, fetchData])

  const handleCollect = async () => {
    if (!symbol || collecting) return
    setCollecting(true)
    setError('')
    try {
      const result = await collectStock(symbol)
      fetchData(symbol)
      alert(`采集完成: ${result.name} ${result.price} (${result.changePercent >= 0 ? '+' : ''}${result.changePercent.toFixed(2)}%)` +
        (result.klineBars ? ` | K线 ${result.klineBars} 条` : '') +
        (result.newsCount ? ` | 资讯 ${result.newsCount} 条` : ''))
    } catch (e) {
      setError(e instanceof Error ? e.message : '采集失败')
    } finally {
      setCollecting(false)
    }
  }

  const handleKlineDays = useCallback((days: number) => {
    if (!symbol) return
    setKlineDays(days)
    getKline(symbol, days).then(res => setKlineData(res.items)).catch(() => {})
  }, [symbol])

  const toggleFollow = async () => {
    if (!symbol) return
    try {
      if (following) {
        await removeWatchlist(symbol)
        setFollowing(false)
      } else {
        await addWatchlist(symbol)
        setFollowing(true)
      }
    } catch { /* ignore */ }
  }

  if (loading) return <div className="page"><p className="hint">加载中...</p></div>
  if (!analysis) return (
    <div className="page detail-page">
      <button className="back-btn" onClick={() => nav('/')}>← 返回搜索</button>
      {error && <p className="hint error">{error}</p>}
      <p className="hint">该股票尚未采集</p>
      <button className="collect-btn" onClick={handleCollect} disabled={collecting}>
        {collecting ? '采集中...' : '采集这只股票'}
      </button>
    </div>
  )

  const s = analysis.score
  const mg = analysis.masterGuidance
  return (
    <div className="page detail-page">
      <div className="toolbar">
        <button className="back-btn" onClick={() => nav('/')}>← 返回搜索</button>
        <button className="collect-btn" onClick={handleCollect} disabled={collecting}>
          {collecting ? '采集中...' : '刷新数据'}
        </button>
        <button className="collect-btn" onClick={() => nav(`/analysis/${symbol}`)}>技术研判</button>
        <button className={`follow-btn ${following ? 'following' : ''}`} onClick={toggleFollow}>
          {following ? '★ 已关注' : '☆ 关注'}
        </button>
      </div>

      {/* 头部行情 */}
      <div className="card header-card">
        <h2>{symbol} <span className="dim">{analysis.market ?? ''}</span></h2>
        <div className="quote-row">
          <span className={`price ${getColorClass(quote?.changePercent)}`}>
            {quote?.latestPrice?.toFixed(2) ?? s.total ?? '--'}
          </span>
          <span className={`change ${getColorClass(quote?.changePercent)}`}>
            {quote?.changePercent != null
              ? `${quote.changePercent >= 0 ? '+' : ''}${quote.changePercent.toFixed(2)}%`
              : '--'}
          </span>
          <span className="dim">趋势: {analysis.trendStatus}</span>
          <span className="dim">数据: {analysis.dataTime ?? '无'}</span>
        </div>
      </div>

      {/* K 线图 */}
      <KlineChart data={klineData} days={klineDays} onDaysChange={handleKlineDays} />

      {/* 风险等级 + 建议 */}
      <div className={`card suggestion-card level-${analysis.riskLevel?.toLowerCase()}`}>
        <div className="suggestion-header">
          <span className="badge">{analysis.suggestion}</span>
          <span className="risk-label">风险: {analysis.riskLevel}</span>
          <span className="score">综合评分: {s.total}</span>
        </div>
        {analysis.suggestionReasons.length > 0 && (
          <p className="reason">{analysis.suggestionReasons[0]}</p>
        )}
      </div>

      {/* 评分区 */}
      <div className="card">
        <h3>评分详情</h3>
        <div className="scores-grid">
          {renderScore('趋势', s.trend)}
          {renderScore('量价', s.volumePrice)}
          {renderScore('资金', s.capital)}
          {renderScore('板块', s.sector)}
          {renderScore('基本面', s.fundamental)}
          {renderScore('事件', s.event)}
          <div className="score-item">
            <span className="score-label">风险扣分</span>
            <span className="score-val red">-{s.riskPenalty}</span>
            <span className="score-weight" />
          </div>
        </div>
      </div>

      {/* 大师指导 */}
      <div className="card">
        <h3>股票大师指导</h3>
        <p className="summary">{mg.summary}</p>
        {mg.masters.map((m) => (
          <details key={m.code} className="master-item">
            <summary>
              <span className={`master-status ${m.status?.toLowerCase()}`}>{m.status}</span>
              <strong>{m.name}</strong> — {m.explanation}
            </summary>
            <p className="master-detail">{m.detail}</p>
            {m.evidence.length > 0 && (
              <ul className="evidence">
                {m.evidence.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            )}
          </details>
        ))}
      </div>

      {/* 上涨条件 */}
      {mg.upsideConditions.length > 0 && (
        <div className="card">
          <h3>上涨条件 ({mg.upsideConditions.length})</h3>
          {mg.upsideConditions.map((c) => (
            <div key={c.conditionId} className="condition-item">
              <strong>{c.title}</strong>
              <p>{c.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* 回调条件 */}
      {mg.pullbackConditions.length > 0 && (
        <div className="card">
          <h3>回调条件 ({mg.pullbackConditions.length})</h3>
          {mg.pullbackConditions.map((c) => (
            <div key={c.conditionId} className="condition-item">
              <strong>{c.title}</strong>
              <p>{c.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* 买卖计划 */}
      {mg.buyPlan.length > 0 && (
        <div className="card">
          <h3>买入计划</h3>
          {mg.buyPlan.map((p, i) => (
            <div key={i} className="plan-item">
              <strong>{p.title}</strong> {p.price && <span className="dim">({p.price})</span>}
              <p>{p.comment}</p>
            </div>
          ))}
        </div>
      )}
      {mg.sellPlan.length > 0 && (
        <div className="card">
          <h3>卖出计划 / 止损</h3>
          {mg.sellPlan.map((p, i) => (
            <div key={i} className="plan-item">
              <strong>{p.title}</strong> {p.price && <span className="dim">({p.price})</span>}
              <p>{p.comment}</p>
            </div>
          ))}
        </div>
      )}

      {/* 复盘点 */}
      {mg.reviewPoints.length > 0 && (
        <div className="card">
          <h3>复盘提醒</h3>
          <ul>
            {mg.reviewPoints.map((pt, i) => <li key={i}>{pt}</li>)}
          </ul>
        </div>
      )}

      {/* 做T分析 */}
      {tAnalysis && (
        <div className="card">
          <h3>做T分析 <span className={`badge t-badge t-${tAnalysis.suitability.toLowerCase()}`}>{getTSuitLabel(tAnalysis.suitability)}</span></h3>
          <p className="summary">{tAnalysis.assessment.summary}</p>

          {/* 操作信号 */}
          <div className="t-signal-box">
            <div className="t-signal t-signal-buy">
              <span className="t-signal-label">买入价</span>
              <span className="t-signal-price">{tAnalysis.signals.buyPrice}</span>
              <span className="t-signal-note">MA10支撑 / ATR下轨</span>
            </div>
            <div className="t-signal t-signal-sell">
              <span className="t-signal-label">卖出价</span>
              <span className="t-signal-price">{tAnalysis.signals.sellPrice}</span>
              <span className="t-signal-note">MA5压力 / ATR上轨</span>
            </div>
            <div className="t-signal t-signal-loss">
              <span className="t-signal-label">止损价</span>
              <span className="t-signal-price">{tAnalysis.signals.stopLoss}</span>
              <span className="t-signal-note">跌破离场</span>
            </div>
          </div>

          <div className="t-signal-meta">
            <span>预期收益 <b className="green">+{tAnalysis.signals.expectedProfitPct}%</b></span>
            <span>风险 <b className="red">{tAnalysis.signals.riskPct}%</b></span>
            <span>盈亏比 <b>{tAnalysis.signals.rewardRiskRatio}</b></span>
          </div>

          <div className="t-signal-detail">
            <div className="t-signal-col">
              <span className="t-signal-col-title t-positive">买入条件</span>
              <ul>{tAnalysis.signals.buyConditions.map((c, i) => <li key={i}>{c}</li>)}</ul>
            </div>
            <div className="t-signal-col">
              <span className="t-signal-col-title t-negative">卖出条件</span>
              <ul>{tAnalysis.signals.sellConditions.map((c, i) => <li key={i}>{c}</li>)}</ul>
            </div>
          </div>

          <div className="t-grid">
            <div className="t-metric">
              <span className="t-label">近10日振幅</span>
              <span className="t-val">{tAnalysis.metrics.avgAmplitude10 != null ? `${tAnalysis.metrics.avgAmplitude10.toFixed(1)}%` : '--'}</span>
            </div>
            <div className="t-metric">
              <span className="t-label">ATR</span>
              <span className="t-val">{tAnalysis.metrics.atrPercent != null ? `${tAnalysis.metrics.atrPercent.toFixed(1)}%` : '--'}</span>
            </div>
            <div className="t-metric">
              <span className="t-label">换手率</span>
              <span className="t-val">{tAnalysis.metrics.turnoverRate != null ? `${tAnalysis.metrics.turnoverRate.toFixed(1)}%` : '--'}</span>
            </div>
            <div className="t-metric">
              <span className="t-label">量比</span>
              <span className="t-val">{tAnalysis.metrics.volumeRatio != null ? tAnalysis.metrics.volumeRatio.toFixed(1) : '--'}</span>
            </div>
          </div>
          {tAnalysis.assessment.strengths.length > 0 && (
            <div className="t-section">
              <span className="t-positive">优势</span>
              <ul>{tAnalysis.assessment.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
            </div>
          )}
          {tAnalysis.assessment.weaknesses.length > 0 && (
            <div className="t-section">
              <span className="t-negative">劣势</span>
              <ul>{tAnalysis.assessment.weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul>
            </div>
          )}
          <div className="t-section">
            <span className="t-tip">建议</span>
            <ul>{tAnalysis.assessment.suggestions.map((s, i) => <li key={i}>{s}</li>)}</ul>
          </div>
          <div className="t-levels">
            <span>MA5: {tAnalysis.levels.ma5 ?? '--'}</span>
            <span>MA10: {tAnalysis.levels.ma10 ?? '--'}</span>
            <span>MA20: {tAnalysis.levels.ma20 ?? '--'}</span>
          </div>
        </div>
      )}

      {/* 相关资讯 */}
      <div className="card">
        <h3>相关资讯 {newsItems.length > 0 && <span className="dim">({newsItems.length})</span>}</h3>
        {newsItems.length === 0 ? (
          <p className="hint">暂无相关资讯</p>
        ) : (
          <div className="news-list">
            {newsItems.map((n) => (
              <a key={n.id} className="news-item" href={n.url} target="_blank" rel="noopener noreferrer">
                <div className="news-title">
                  <span className={`news-tag tag-${n.sentiment}`}>{SENTIMENT_LABELS[n.sentiment]}</span>
                  {n.title}
                </div>
                <div className="news-meta">
                  <span className="news-source">{n.source}</span>
                  <span className="news-time">{formatTime(n.publishTime)}</span>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>

      {/* 免责声明 + 版本 */}
      <div className="card dim-card">
        <p className="disclaimer">{analysis.disclaimer}</p>
        <p className="meta">策略: {analysis.strategyVersion} | 延迟: {analysis.delayMinutes} 分钟</p>
      </div>
    </div>
  )
}

function renderScore(label: string, val: number | null) {
  return (
    <div className="score-item">
      <span className="score-label">{label}</span>
      <span className={`score-val ${val != null ? getScoreColor(val) : 'dim'}`}>
        {val != null ? val : '--'}
      </span>
      <span className="score-weight">{val != null ? '' : '无数据'}</span>
    </div>
  )
}

function getColorClass(pct: number | null | undefined): string {
  if (pct == null) return ''
  if (pct > 0) return 'red'
  if (pct < 0) return 'green'
  return ''
}

function getScoreColor(s: number): string {
  if (s >= 70) return 'green'
  if (s >= 50) return ''
  return 'red'
}

function getTSuitLabel(s: string): string {
  switch (s) {
    case 'HIGHLY_SUITABLE': return '非常适合'
    case 'SUITABLE': return '适合'
    case 'GENERAL': return '一般'
    default: return '不适合'
  }
}

const SENTIMENT_LABELS: Record<string, string> = {
  positive: '利好',
  negative: '利空',
  neutral: '中等',
}

function formatTime(t: string | null): string {
  if (!t) return ''
  try {
    const d = new Date(t)
    const now = new Date()
    const diffMs = now.getTime() - d.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return '刚刚'
    if (diffMin < 60) return `${diffMin}分钟前`
    const diffHour = Math.floor(diffMin / 60)
    if (diffHour < 24) return `${diffHour}小时前`
    const diffDay = Math.floor(diffHour / 24)
    if (diffDay < 7) return `${diffDay}天前`
    return d.toLocaleDateString('zh-CN')
  } catch {
    return t
  }
}
