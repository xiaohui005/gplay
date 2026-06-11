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

export interface TMetrics {
  avgAmplitude5: number
  avgAmplitude10: number
  avgAmplitude20: number
  atr: number
  atrPercent: number
  avgVolume5: number | null
  avgVolume20: number | null
  volumeRatio: number | null
  turnoverRate: number | null
  volatilityTrend: string
}

export interface TLevels {
  ma5: number | null
  ma10: number | null
  ma20: number | null
  ma60: number | null
  currentPrice: number
}

export interface TAssessment {
  summary: string
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
}

export interface TAnalysisResult {
  symbol: string
  name: string
  suitability: string
  score: number
  metrics: TMetrics
  levels: TLevels
  signals: TSignals
  assessment: TAssessment
}

export interface TSignals {
  buyPrice: number
  sellPrice: number
  stopLoss: number
  expectedProfit: number
  expectedProfitPct: number
  riskAmount: number
  riskPct: number
  rewardRiskRatio: number
  buyConditions: string[]
  sellConditions: string[]
}

export interface TechnicalIndicators {
  trend: {
    maAlignment: string
    maCross: string
    ma5: number | null
    ma10: number | null
    ma20: number | null
    detail: string
  }
  momentum: {
    macd: {
      dif: number
      dea: number
      histogram: number
      direction: string
      status: string
      detail: string
    }
    rsi: {
      value: number
      status: string
      detail: string
    }
  }
  volatility: {
    position: string
    upper: number
    middle: number
    lower: number
    width: number
    detail: string
  }
  volume: {
    volumeRatio: number
    volumeTrend: string
    priceVolumeConfirm: boolean
    detail: string
  }
  supportResistance: {
    nearestSupport: number
    nearestResistance: number
    distanceToSupport: number
    distanceToResistance: number
    detail: string
  }
}

export interface TechnicalAnalysisResult {
  id: number | null
  symbol: string
  name: string
  createdAt: string
  priceAtAnalysis: number
  direction: string
  confidence: number
  recommendation: string
  signals: {
    buyPrice: number
    sellPrice: number
    stopLoss: number
  }
  indicators: TechnicalIndicators
  summary: string
  keyEvidence: string[]
  riskWarning: string[]
  isCorrect: boolean | null
  actualDirection: string | null
  analysisSession?: string | null
  analysisTimeLabel?: string | null
}

export interface AnalysisHistoryResponse {
  items: TechnicalAnalysisResult[]
  total: number
  page: number
  limit: number
  stats: {
    totalRecords: number
    verifiedCount: number
    correctCount: number
    accuracy: number | null
  }
}

export interface KlineBar {
  tradeDate: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
}

export interface NewsItem {
  id: number
  title: string
  source: string
  publishTime: string | null
  url: string
  contentSummary: string
  sentiment: 'positive' | 'negative' | 'neutral'
}
