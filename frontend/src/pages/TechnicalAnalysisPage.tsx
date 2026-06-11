import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTechnicalAnalysis, saveTechnicalAnalysis } from '../api/client'
import type { TechnicalAnalysisResult } from '../types/api'

export default function TechnicalAnalysisPage() {
  const { symbol } = useParams<{ symbol: string }>()
  const nav = useNavigate()
  const [result, setResult] = useState<TechnicalAnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

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

  const handleSave = () => {
    if (!symbol || saving) return
    setSaving(true)
    setSaveMessage('')
    saveTechnicalAnalysis(symbol)
      .then(saved => {
        setResult(saved)
        setSaveMessage('已保存到研判历史')
      })
      .catch(e => setSaveMessage(e instanceof Error ? e.message : '保存失败'))
      .finally(() => setSaving(false))
  }

  const dirMap: Record<string, { label: string; cls: string }> = {
    UP: { label: '看涨 ↑', cls: 'ta-up' },
    DOWN: { label: '看跌 ↓', cls: 'ta-down' },
    SIDEWAYS: { label: '盘整 →', cls: 'ta-sideways' },
  }
  const dir = dirMap[result.direction] || { label: '未知', cls: '' }
  const signalNotice = getSignalNotice(result)
  const analysisTimeLabel = getAnalysisTimeLabel(result)

  return (
    <div className="page ta-page">
      <div className="toolbar">
        <button className="back-btn" onClick={() => nav(-1)}>← 返回</button>
        <button className="collect-btn" onClick={() => { setLoading(true); setError(''); getTechnicalAnalysis(symbol!).then(setResult).catch(e => setError(e.message)).finally(() => setLoading(false)) }}>
          重新分析
        </button>
        <button className="collect-btn" onClick={handleSave} disabled={saving}>
          {saving ? '保存中...' : '保存研判'}
        </button>
        <button className="collect-btn" onClick={() => nav(`/analysis/history?symbol=${result.symbol}`)}>
          研判历史
        </button>
      </div>

      <div className="ta-header">
        <h2>{result.symbol} <span className="dim">{result.name}</span></h2>
        <span className="dim">研判时段: {analysisTimeLabel}</span>
        {result.createdAt ? <span className="dim">保存时间: {new Date(result.createdAt).toLocaleString('zh-CN')}</span> : null}
        {saveMessage ? <span className="ta-save-message">{saveMessage}</span> : null}
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

      <div className={`ta-notice-card ${signalNotice.cls}`}>
        <div className="ta-notice-title">
          <span>{signalNotice.title}</span>
          <b>{signalNotice.level}</b>
        </div>
        <p>{signalNotice.message}</p>
        <small>信号强度不是涨跌概率，只表示当前技术指标对研判方向的一致程度。</small>
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

function getSignalNotice(result: TechnicalAnalysisResult) {
  const directionText: Record<string, string> = { UP: '看涨', DOWN: '看跌', SIDEWAYS: '盘整' }
  const direction = directionText[result.direction] || '未知'

  if (result.direction === 'SIDEWAYS') {
    return {
      cls: 'ta-notice-neutral',
      level: '观望信号',
      title: '信号通知',
      message: '多空方向暂不明确，当前更适合等待趋势或量能进一步确认。',
    }
  }

  if (result.confidence < 30) {
    return {
      cls: 'ta-notice-weak',
      level: `弱${direction}`,
      title: '信号通知',
      message: `系统轻微偏向${direction}，但指标一致性较弱，不建议只凭这个信号操作。`,
    }
  }

  if (result.confidence < 60) {
    return {
      cls: 'ta-notice-medium',
      level: `中等${direction}`,
      title: '信号通知',
      message: `部分指标支持${direction}，可结合K线位置、成交量和止损价再判断。`,
    }
  }

  return {
    cls: result.direction === 'UP' ? 'ta-notice-strong-up' : 'ta-notice-strong-down',
    level: `强${direction}`,
    title: '信号通知',
    message: `多项指标对${direction}方向较一致，仍需按页面给出的买卖价和止损价控制风险。`,
  }
}

function getAnalysisTimeLabel(result: TechnicalAnalysisResult) {
  if (result.analysisTimeLabel) return result.analysisTimeLabel
  if (!result.createdAt) return '预览中，点击保存后进入历史'

  const savedAt = new Date(result.createdAt)
  const date = savedAt.toLocaleDateString('zh-CN')
  return savedAt.getHours() < 12 ? `${date} 早盘研判 09:30` : `${date} 收盘前研判 14:30`
}
