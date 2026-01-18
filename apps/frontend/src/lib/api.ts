/**
 * API Client for La Falange Trading Platform
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Types
export interface AIVote {
  provider: string
  model: string
  direction: 'BUY' | 'SELL' | 'HOLD' | 'LONG' | 'SHORT'
  confidence: number
  reasoning?: string
  is_valid?: boolean
  error?: string
}

export interface ConsensusResult {
  direction: 'BUY' | 'SELL' | 'HOLD' | 'LONG' | 'SHORT'
  confidence: number
  should_trade?: boolean
  total_votes?: number
  valid_votes?: number
  votes_buy?: number
  votes_sell?: number
  votes_hold?: number
  modelsAgree?: number
  totalModels?: number
  agreementRatio?: number
  agreement_level?: string
  agreement_percentage?: number
  isStrongSignal?: boolean
  suggested_entry?: string | number
  suggested_stop_loss?: string | number
  suggested_take_profit?: string | number
  avgStopLoss?: number
  avgTakeProfit?: number
  avgBreakEvenTrigger?: number
  risk_reward_ratio?: number
  trailingStopConsensus?: {
    enabled: boolean
    distancePips: number
  }
  votingBreakdown?: {
    LONG: number
    SHORT: number
    HOLD: number
  }
  modelVotes?: Record<string, {
    direction: string
    confidence: number
    latencyMs?: number
  }>
  key_factors?: string[]
  risks?: string[]
  reasoning_summary?: string
  votes?: AIVote[]
  individualResults?: AIVote[]
  total_cost_usd?: number
  total_tokens?: number
  processing_time_ms?: number
  providers_used?: string[]
  failed_providers?: string[]
}

export interface AnalysisRequest {
  symbol: string
  timeframes?: string[]
  chartImage?: string
}

export interface AnalysisResponse {
  direction: string
  confidence: number
  entryPrice?: number
  stopLoss?: number
  takeProfit?: number[]
  breakEvenTrigger?: number
  trailingStop?: {
    enabled: boolean
    activationPrice: number
    trailDistance: number
  }
  riskRewardRatio?: number
  reasoning: string
  patternsDetected: string[]
  modelsUsed: string[]
  consensusVotes: Record<string, string>
}

// API Client
async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `API error: ${response.status}`)
  }

  return response.json()
}

// AI Analysis API
export const aiApi = {
  // Analyze a single chart
  analyzeChart: async (request: AnalysisRequest): Promise<AnalysisResponse> => {
    return fetchApi('/api/v1/ai/analyze-chart', {
      method: 'POST',
      body: JSON.stringify({
        symbol: request.symbol,
        timeframes: request.timeframes || ['1H'],
        chart_image: request.chartImage,
        request_sl_tp_be_ts: true,
      }),
    })
  },

  // Analyze multiple timeframes
  analyzeMultiTimeframe: async (
    symbol: string,
    chartImages: Record<string, string>
  ): Promise<AnalysisResponse> => {
    return fetchApi('/api/v1/ai/analyze-multi-timeframe', {
      method: 'POST',
      body: JSON.stringify({
        symbol,
        chart_images: chartImages,
        request_sl_tp_be_ts: true,
      }),
    })
  },

  // Get consensus from AI models
  getConsensus: async (symbol: string, timeframe: string = '1H'): Promise<ConsensusResult> => {
    return fetchApi(`/api/v1/ai/consensus?symbol=${encodeURIComponent(symbol)}&timeframe=${timeframe}`)
  },

  // Quick analysis (text-based, no chart)
  quickAnalysis: async (symbol: string): Promise<ConsensusResult> => {
    return fetchApi(`/api/v1/ai/quick-analysis?symbol=${encodeURIComponent(symbol)}`)
  },
}

// Trading API
export const tradingApi = {
  // Get account info
  getAccount: async () => {
    return fetchApi('/api/v1/trading/account')
  },

  // Get open positions
  getPositions: async () => {
    return fetchApi('/api/v1/positions')
  },

  // Place order
  placeOrder: async (order: {
    symbol: string
    side: 'BUY' | 'SELL'
    units: number
    stopLoss?: number
    takeProfit?: number
  }) => {
    return fetchApi('/api/v1/trading/orders', {
      method: 'POST',
      body: JSON.stringify(order),
    })
  },

  // Close position
  closePosition: async (positionId: string) => {
    return fetchApi(`/api/v1/positions/${positionId}/close`, {
      method: 'POST',
    })
  },
}

// Bot Control API
export const botApi = {
  // Get bot status
  getStatus: async () => {
    return fetchApi('/api/v1/bot/status')
  },

  // Start bot
  start: async (config?: Record<string, unknown>) => {
    return fetchApi('/api/v1/bot/start', {
      method: 'POST',
      body: JSON.stringify(config || {}),
    })
  },

  // Stop bot
  stop: async () => {
    return fetchApi('/api/v1/bot/stop', {
      method: 'POST',
    })
  },

  // Update config
  updateConfig: async (config: Record<string, unknown>) => {
    return fetchApi('/api/v1/bot/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },
}

// Health check
export const healthCheck = async (): Promise<{ status: string; version: string }> => {
  return fetchApi('/health')
}

export default {
  ai: aiApi,
  trading: tradingApi,
  bot: botApi,
  healthCheck,
}
