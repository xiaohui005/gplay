export interface StockItem {
  symbol: string
  name: string
  market: string
  tradeStatus?: string
  latestPrice: number | null
  changePercent: number | null
}

export interface StockQuote {
  symbol: string
  latestPrice: number | null
  changePercent: number | null
  volume: number | null
  amount: number | null
  turnoverRate: number | null
  volumeRatio: number | null
  high: number | null
  low: number | null
  openPrice: number | null
  preClose: number | null
  amplitude: number | null
  dataTime: string | null
  delayMinutes: number
}

export interface ScoreBlock {
  total: number
  trend: number
  volumePrice: number
  capital: number | null
  sector: number
  fundamental: number | null
  event: number | null
  riskPenalty: number
}

export interface MasterItem {
  code: string
  name: string
  status: string
  explanation: string
  detail: string
  evidence: string[]
}

export interface Condition {
  conditionId: string
  title: string
  description: string
  evidence: string[]
  status: string
  importance: string
}

export interface PlanItem {
  title: string
  price?: string
  comment?: string
  weight?: number
}

export interface MasterGuidance {
  summary: string
  masters: MasterItem[]
  upsideConditions: Condition[]
  pullbackConditions: Condition[]
  buyPlan: PlanItem[]
  sellPlan: PlanItem[]
  reviewPoints: string[]
}

export interface AnalysisResult {
  symbol: string
  market?: string
  dataTime: string | null
  delayMinutes: number
  trendStatus: string
  riskLevel: string
  suggestion: string
  suggestionReasons: string[]
  strategyVersion: string
  score: ScoreBlock
  masterGuidance: MasterGuidance
  disclaimer: string
}

export interface WatchlistItem {
  symbol: string
  name: string
  market: string
  latestPrice: number | null
  changePercent: number | null
  addedAt: string | null
}
