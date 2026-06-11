import type { StockItem, StockQuote, AnalysisResult, WatchlistItem } from '../types/api'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`请求失败 ${res.status}: ${text}`)
  }
  return res.json()
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`请求失败 ${res.status}: ${text}`)
  }
  return res.json()
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: 'DELETE' })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`请求失败 ${res.status}: ${text}`)
  }
  return res.json()
}

export function searchStocks(keyword: string, limit = 20): Promise<{ items: StockItem[] }> {
  return get(`/stocks/search?keyword=${encodeURIComponent(keyword)}&limit=${limit}`)
}

export function getQuote(symbol: string): Promise<StockQuote> {
  return get(`/stocks/${symbol}/quote`)
}

export function getAnalysis(symbol: string, strategyVersion?: string): Promise<AnalysisResult> {
  const qs = strategyVersion ? `?strategy_version=${encodeURIComponent(strategyVersion)}` : ''
  return get(`/stocks/${symbol}/analysis${qs}`)
}

export function collectStock(symbol: string): Promise<{ status: string; symbol: string; name: string; price: number; changePercent: number; klineBars: number }> {
  return post(`/stocks/${symbol}/collect`)
}

export function getWatchlist(): Promise<{ items: WatchlistItem[] }> {
  return get('/watchlist')
}

export function addWatchlist(symbol: string): Promise<{ status: string; message: string }> {
  return post(`/watchlist/${symbol}`)
}

export function removeWatchlist(symbol: string): Promise<{ status: string; message: string }> {
  return del(`/watchlist/${symbol}`)
}
