import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getAnalysisHistory } from '../api/client'
import type { TechnicalAnalysisResult } from '../types/api'

export default function AnalysisHistoryPage() {
  const nav = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [symbol, setSymbol] = useState(searchParams.get('symbol') || '')
  const [results, setResults] = useState<TechnicalAnalysisResult[]>([])
  const [stats, setStats] = useState<{ totalRecords: number; verifiedCount: number; correctCount: number; accuracy: number | null } | null>(null)
  const [loading, setLoading] = useState(true)
  const [tableKeyword, setTableKeyword] = useState('')

  useEffect(() => {
    setLoading(true)
    const sym = searchParams.get('symbol') || undefined
    getAnalysisHistory(sym)
      .then(res => {
        setResults(res.items)
        setStats(res.stats)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [searchParams])

  const handleSearch = () => {
    const params = new URLSearchParams()
    if (symbol) params.set('symbol', symbol)
    setSearchParams(params)
  }

  const dirMap: Record<string, string> = { UP: '↑ 看涨', DOWN: '↓ 看跌', SIDEWAYS: '→ 盘整' }
  const filteredResults = results.filter(r => matchesTableKeyword(r, tableKeyword, dirMap))

  return (
    <div className="page ta-page">
      <div className="toolbar">
        <button className="back-btn" onClick={() => nav('/')}>← 返回搜索</button>
      </div>
      <h2>技术研判历史</h2>

      <div className="ta-search-bar">
        <input type="text" placeholder="输入股票代码筛选" value={symbol} onChange={e => setSymbol(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleSearch()} />
        <button onClick={handleSearch}>筛选</button>
      </div>

      <div className="ta-search-bar">
        <input
          type="text"
          placeholder="搜索表格内容：代码/名称/方向/结果/时间/价格"
          value={tableKeyword}
          onChange={e => setTableKeyword(e.target.value)}
        />
        {tableKeyword && <button onClick={() => setTableKeyword('')}>清空</button>}
      </div>

      {stats && (
        <div className="ta-stats-bar">
          <span>总分析: {stats.totalRecords}</span>
          <span>已验证: {stats.verifiedCount}</span>
          <span>正确: {stats.correctCount}</span>
          <span>准确率: <b>{stats.accuracy != null ? `${stats.accuracy}%` : '--'}</b></span>
        </div>
      )}

      {loading ? (
        <p className="hint">加载中...</p>
      ) : results.length === 0 ? (
        <p className="hint">暂无分析记录</p>
      ) : filteredResults.length === 0 ? (
        <p className="hint">没有匹配的历史记录</p>
      ) : (
        <table className="ta-history-table">
          <thead>
            <tr>
              <th>时间</th>
              <th>股票</th>
              <th>方向</th>
              <th>信心</th>
              <th>当时价格</th>
              <th>结果</th>
            </tr>
          </thead>
          <tbody>
            {filteredResults.map(r => (
              <tr key={r.id} onClick={() => nav(`/analysis/${r.symbol}`)} className="ta-history-row">
                <td>
                  {getAnalysisTimeLabel(r)}
                  {r.createdAt ? <br /> : null}
                  {r.createdAt ? <span className="dim">保存 {new Date(r.createdAt).toLocaleTimeString('zh-CN')}</span> : null}
                </td>
                <td>{r.symbol}<br /><span className="dim">{r.name}</span></td>
                <td><span className={`ta-dir-${r.direction.toLowerCase()}`}>{dirMap[r.direction] || r.direction}</span></td>
                <td>{r.confidence}%</td>
                <td>{r.priceAtAnalysis}</td>
                <td>{renderResult(r)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function renderResult(result: TechnicalAnalysisResult) {
  return <span className={getResultClass(result)}>{getResultLabel(result)}</span>
}

function getResultLabel(result: TechnicalAnalysisResult): string {
  if (result.isCorrect === true) return '✓ 命中'
  if (result.isCorrect === false) return '✗ 未命中'
  return '待验证'
}

function getResultClass(result: TechnicalAnalysisResult): string {
  if (result.isCorrect === true) return 'ta-correct'
  if (result.isCorrect === false) return 'ta-wrong'
  return 'dim'
}

function matchesTableKeyword(result: TechnicalAnalysisResult, keyword: string, dirMap: Record<string, string>) {
  const kw = keyword.trim().toLowerCase()
  if (!kw) return true
  const savedAt = result.createdAt ? new Date(result.createdAt).toLocaleTimeString('zh-CN') : ''
  const fields = [
    result.symbol,
    result.name,
    getAnalysisTimeLabel(result),
    savedAt,
    dirMap[result.direction] || result.direction,
    String(result.confidence),
    String(result.priceAtAnalysis),
    getResultLabel(result),
  ]
  return fields.some(v => String(v).toLowerCase().includes(kw))
}

function getAnalysisTimeLabel(result: TechnicalAnalysisResult) {
  if (result.analysisTimeLabel) return result.analysisTimeLabel
  if (!result.createdAt) return ''

  const savedAt = new Date(result.createdAt)
  const date = savedAt.toLocaleDateString('zh-CN')
  return savedAt.getHours() < 12 ? `${date} 早盘研判 10:00` : `${date} 收盘前研判 14:30`
}
