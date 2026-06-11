import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTechnicalAnalysis } from '../api/client'
import type { TechnicalAnalysisResult } from '../types/api'

export default function TechnicalAnalysisPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const nav = useNavigate()
  const [result, setResult] = useState<TechnicalAnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!symbol) return
    setLoading(true)
    setError('')
    getTechnicalAnalysis(symbol)
      .then(setResult)
      .catch(e => setError(e instanceof Error ? e.message : '分析失败'))
      .finally(() => setLoading(false))
  }, [symbol])

  if (loading) return <div className="page"><p className="hint">分析中...</p></div>
  if (error) return (
    <div className="page ta-page">
      <button className="back-btn" onClick={() => nav(-1)}>← 返回</button>
      <p className="hint error">{error}</p>
    </div>
  )
  if (!result) return null

  const dirMap: Record<string, { label: string; cls: string }> = {
    UP: { label: '看涨 ↑', cls: 'ta-up' },
    DOWN: { label: '看跌 ↓', cls: 'ta-down' },
    SIDEWAYS: { label: '盘整 →', cls: 'ta-sideways' },
  }
  const dir = dirMap[result.direction] || { label: '未知', cls: '' }

  return (
    <div className="page ta-page">
      <div className="toolbar">
        <button className="back-btn" onClick={() => nav(-1)}>← 返回</button>
        <button className="collect-btn" onClick={() => { setLoading(true); setError(''); getTechnicalAnalysis(symbol!).then(setResult).catch(e => setError(e.message)).finally(() => setLoading(false)) }}>
          重新分析
        </button>
      </div>

      <div className="ta-header">
        <h2>{result.symbol} <span className="dim">{result.name}</span></h2>
        <span className="dim">分析时间: {result.createdAt ? new Date(result.createdAt).toLocaleString('zh-CN') : ''}</span>
      </div>

      <div className={`ta-direction-card ${dir.cls}`}>
        <div className="ta-direction-badge">{dir.label}</div>
        <div className="ta-confidence-section">
          <span className="ta-confidence-label">信心度</span>
          <div className="ta-confidence-bar-wrap">
            <div className="ta-confidence-bar" style={{ width: `${result.confidence}%` }} />
          </div>
          <span className="ta-confidence-val">{result.confidence}%</span>
        </div>

        {/* 操作建议 */}
        {result.recommendation && (
          <div className="ta-signal-box">
            <div className={`ta-rec-badge ${result.direction === 'UP' ? 'ta-rec-buy' : result.direction === 'DOWN' ? 'ta-rec-sell' : 'ta-rec-wait'}`}>
              {result.recommendation}
            </div>
            <div className="ta-signal-prices">
              {result.signals?.buyPrice ? <span>买入 <b className="green">{result.signals.buyPrice}</b></span> : null}
              {result.signals?.sellPrice ? <span>卖出 <b className="red">{result.signals.sellPrice}</b></span> : null}
              {result.signals?.stopLoss ? <span>止损 <b className="red">{result.signals.stopLoss}</b></span> : null}
            </div>
          </div>
        )}

        <p className="ta-summary">{result.summary}</p>
      </div>

      <div className="ta-indicator-grid">
        <div className="ta-indicator-card">
          <h4>趋势</h4>
          <span className={`ta-badge ${result.indicators.trend.maAlignment === 'bullish' ? 'ta-bullish' : result.indicators.trend.maAlignment === 'bearish' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.trend.maAlignment === 'bullish' ? '多头' : result.indicators.trend.maAlignment === 'bearish' ? '空头' : '中性'}
          </span>
          <p className="ta-detail">{result.indicators.trend.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>MACD</h4>
          <span className={`ta-badge ${result.indicators.momentum.macd.status === 'bullish' ? 'ta-bullish' : result.indicators.momentum.macd.status === 'bearish' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.momentum.macd.status === 'bullish' ? '多头' : result.indicators.momentum.macd.status === 'bearish' ? '空头' : '中性'}
          </span>
          <p className="ta-detail">{result.indicators.momentum.macd.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>RSI</h4>
          <span className={`ta-badge ${result.indicators.momentum.rsi.status === 'oversold' ? 'ta-bullish' : result.indicators.momentum.rsi.status === 'overbought' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.momentum.rsi.value}
          </span>
          <p className="ta-detail">{result.indicators.momentum.rsi.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>布林带</h4>
          <span className={`ta-badge ${result.indicators.volatility.position === 'lower' ? 'ta-bullish' : result.indicators.volatility.position === 'upper' ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.volatility.position === 'upper' ? '上轨' : result.indicators.volatility.position === 'lower' ? '下轨' : '中轨'}
          </span>
          <p className="ta-detail">{result.indicators.volatility.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>量能</h4>
          <span className={`ta-badge ${result.indicators.volume.priceVolumeConfirm && result.indicators.volume.volumeRatio > 1 ? 'ta-bullish' : !result.indicators.volume.priceVolumeConfirm ? 'ta-bearish' : 'ta-neutral'}`}>
            {result.indicators.volume.priceVolumeConfirm ? '配合' : '背离'}
          </span>
          <p className="ta-detail">{result.indicators.volume.detail}</p>
        </div>
        <div className="ta-indicator-card">
          <h4>支撑/压力</h4>
          <p className="ta-detail">{result.indicators.supportResistance.detail}</p>
          <div className="ta-sr-levels">
            <span>支撑: {result.indicators.supportResistance.nearestSupport}</span>
            <span>压力: {result.indicators.supportResistance.nearestResistance}</span>
          </div>
        </div>
      </div>

      <div className="ta-evidence-risk">
        <div className="ta-evidence">
          <h4 className="ta-green">📌 看涨证据</h4>
          <ul>{(result.keyEvidence || []).map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
        <div className="ta-risk">
          <h4 className="ta-red">⚠️ 风险提示</h4>
          <ul>{(result.riskWarning || []).map((r, i) => <li key={i}>{r}</li>)}</ul>
        </div>
      </div>
    </div>
  )
}
