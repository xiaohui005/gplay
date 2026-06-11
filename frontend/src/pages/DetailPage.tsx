import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getQuote, getAnalysis, collectStock } from '../api/client'
import type { StockQuote, AnalysisResult } from '../types/api'

export default function DetailPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const nav = useNavigate()
  const [quote, setQuote] = useState<StockQuote | null>(null)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [collecting, setCollecting] = useState(false)
  const [error, setError] = useState('')

  const fetchData = useCallback((sym: string) => {
    getQuote(sym).then(setQuote).catch(() => setQuote(null))
    getAnalysis(sym)
      .then(setAnalysis)
      .catch((e) => setError(e instanceof Error ? e.message : '请求失败'))
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
        (result.klineBars ? ` | K线 ${result.klineBars} 条` : ''))
    } catch (e) {
      setError(e instanceof Error ? e.message : '采集失败')
    } finally {
      setCollecting(false)
    }
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
