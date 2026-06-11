import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { searchStocks, collectStock, getWatchlist, addWatchlist, removeWatchlist } from '../api/client'
import type { StockItem, WatchlistItem } from '../types/api'

function isStockCode(s: string): boolean {
  return /^\d{6}$/.test(s)
}

export default function SearchPage() {
  const [keyword, setKeyword] = useState('')
  const [items, setItems] = useState<StockItem[]>([])
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()
  const timer = useRef<ReturnType<typeof setTimeout>>()
  const [collecting, setCollecting] = useState(false)
  const [collectMsg, setCollectMsg] = useState('')
  const [watchlist, setWatchlist] = useState<WatchlistItem[]>([])
  const [watching, setWatching] = useState<Set<string>>(new Set())

  const loadWatchlist = useCallback(async () => {
    try {
      const res = await getWatchlist()
      setWatchlist(res.items)
      setWatching(new Set(res.items.map(i => i.symbol)))
    } catch { /* ignore */ }
  }, [])

  useEffect(() => { loadWatchlist() }, [loadWatchlist])

  const doSearch = useCallback(async (kw: string) => {
    if (!kw.trim()) {
      setItems([])
      return
    }
    setLoading(true)
    try {
      const res = await searchStocks(kw)
      setItems(res.items)
    } catch {
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [])

  const handleCollect = useCallback(async () => {
    if (!isStockCode(keyword.trim())) return
    setCollecting(true)
    setCollectMsg('')
    try {
      const res = await collectStock(keyword.trim())
      if (res.status === 'ok') {
        setCollectMsg(`${res.name}（${res.symbol}）采集成功，当前价 ${res.price}（${res.changePercent >= 0 ? '+' : ''}${res.changePercent}%）`)
        await doSearch(keyword)
      }
    } catch {
      setCollectMsg('采集失败，可能网络异常或代码不存在')
    } finally {
      setCollecting(false)
    }
  }, [keyword, doSearch])

  const toggleFollow = useCallback(async (symbol: string) => {
    try {
      if (watching.has(symbol)) {
        await removeWatchlist(symbol)
        setWatching(prev => { const n = new Set(prev); n.delete(symbol); return n })
        setWatchlist(prev => prev.filter(i => i.symbol !== symbol))
      } else {
        await addWatchlist(symbol)
        setWatching(prev => { const n = new Set(prev); n.add(symbol); return n })
        await loadWatchlist()
      }
    } catch { /* ignore */ }
  }, [watching, loadWatchlist])

  useEffect(() => {
    clearTimeout(timer.current)
    if (keyword.trim().length < 2) {
      setItems([])
      return
    }
    timer.current = setTimeout(() => doSearch(keyword), 300)
    return () => clearTimeout(timer.current)
  }, [keyword, doSearch])

  return (
    <div className="page search-page">
      <h1>GPlay 股票智能研判</h1>

      {/* 我的关注 */}
      {watchlist.length > 0 && (
        <div className="watchlist-panel">
          <h3>我的关注 <span className="dim">({watchlist.length})</span></h3>
          <div className="watchlist-items">
            {watchlist.map(w => (
              <div key={w.symbol} className="watchlist-item" onClick={() => nav(`/stock/${w.symbol}`)}>
                <span className="wl-name">{w.name}</span>
                <span className="wl-code dim">{w.symbol}</span>
                <span className={`wl-price ${getColor(w.changePercent)}`}>
                  {w.latestPrice != null ? w.latestPrice.toFixed(2) : '--'}
                </span>
                <span className={`wl-change ${getColor(w.changePercent)}`}>
                  {w.changePercent != null ? `${w.changePercent >= 0 ? '+' : ''}${w.changePercent.toFixed(2)}%` : ''}
                </span>
                <button className="wl-unfollow" onClick={e => { e.stopPropagation(); toggleFollow(w.symbol) }}>✕</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <input
        className="search-input"
        placeholder="输入股票代码 / 名称 / 拼音（如 600000 / 浦发银行 / pfyh）"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        autoFocus
      />
      {loading && <p className="hint">查询中...</p>}
      {!loading && items.length === 0 && keyword.trim().length >= 2 && (
        <>
          <p className="hint">
            {isStockCode(keyword.trim()) ? '数据库中暂无该股票' : '未找到匹配的股票'}
          </p>
          {isStockCode(keyword.trim()) && !collecting && !collectMsg && (
            <button className="collect-btn" onClick={handleCollect}>采集 {keyword.trim()}</button>
          )}
          {collecting && <p className="hint">采集中...</p>}
          {collectMsg && (
            <div>
              <p className="hint" style={{ color: collectMsg.includes('失败') ? '#f44336' : '#2e7d32' }}>{collectMsg}</p>
              {collectMsg.includes('采集成功') && (
                <button className="collect-btn" style={{ marginTop: 8 }} onClick={() => nav(`/stock/${keyword.trim()}`)}>查看研判详情 →</button>
              )}
            </div>
          )}
        </>
      )}
      {items.length > 0 && (
        <table className="stock-table">
          <thead>
            <tr>
              <th>代码</th>
              <th>名称</th>
              <th>市场</th>
              <th>最新价</th>
              <th>涨跌幅</th>
              <th style={{ width: 50 }}></th>
            </tr>
          </thead>
          <tbody>
            {items.map((s) => (
              <tr key={s.symbol} onClick={() => nav(`/stock/${s.symbol}`)} className="clickable">
                <td>{s.symbol}</td>
                <td>{s.name}</td>
                <td>{s.market}</td>
                <td>{s.latestPrice?.toFixed(2) ?? '--'}</td>
                <td className={getColor(s.changePercent)}>
                  {s.changePercent != null ? `${s.changePercent >= 0 ? '+' : ''}${s.changePercent.toFixed(2)}%` : '--'}
                </td>
                <td>
                  <button
                    className={`follow-btn ${watching.has(s.symbol) ? 'following' : ''}`}
                    onClick={e => { e.stopPropagation(); toggleFollow(s.symbol) }}
                    title={watching.has(s.symbol) ? '取消关注' : '关注'}
                  >
                    {watching.has(s.symbol) ? '★' : '☆'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {keyword.trim().length < 2 && (
        <p className="hint muted">输入至少 2 个字符开始搜索</p>
      )}
    </div>
  )
}

function getColor(pct: number | null): string {
  if (pct == null) return ''
  if (pct > 0) return 'red'
  if (pct < 0) return 'green'
  return ''
}
