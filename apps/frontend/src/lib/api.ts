/**
 * API Client for La Falange Trading Platform
 * Connects to real backend endpoints for live data
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// ============ Types ============

export interface AIVote {
  provider: string
  model: string
  direction: 'BUY' | 'SELL' | 'HOLD' | 'LONG' | 'SHORT'
  confidence: number
  reasoning?: string
  is_valid: boolean
  error?: string
}

export interface ConsensusResult {
  direction: 'BUY' | 'SELL' | 'HOLD' | 'LONG' | 'SHORT'
  confidence: number
  should_trade: boolean
  total_votes: number
  valid_votes: number
  votes_buy: number
  votes_sell: number
  votes_hold: number
  agreement_level: string
  agreement_percentage: number
  suggested_entry: string | number | null
  suggested_stop_loss: string | number | null
  suggested_take_profit: string | number | null
  risk_reward_ratio: number | null
  key_factors: string[]
  risks: string[]
  reasoning_summary: string
  votes: AIVote[]
  total_cost_usd: number
  total_tokens: number
  processing_time_ms: number
  providers_used: string[]
  failed_providers: string[]
}

export interface AccountSummary {
  account_id: string
  balance: string
  equity: string
  margin_used: string
  margin_available: string
  unrealized_pnl: string
  realized_pnl_today: string
  currency: string
  leverage: number
  margin_level: string | null
  open_positions: number
  pending_orders: number
}

export interface Position {
  position_id: string
  symbol: string
  side: string
  size: string
  entry_price: string
  current_price: string
  unrealized_pnl: string
  unrealized_pnl_percent: string
  margin_used: string
  leverage: number
  stop_loss: string | null
  take_profit: string | null
  opened_at: string
}

export interface PositionsResponse {
  positions: Position[]
  total_unrealized_pnl: string
  total_margin_used: string
}

export interface PriceData {
  symbol: string
  bid: string
  ask: string
  mid: string
  spread: string
  timestamp: string
}

export interface PerformanceMetrics {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: string
  profit_factor: string
  total_pnl: string
  average_win: string
  average_loss: string
  largest_win: string
  largest_loss: string
  max_drawdown: string
  max_drawdown_percent: string
  expectancy: string
  average_hold_time: string
}

export interface AIServiceStatus {
  total_providers: number
  active_providers: number
  disabled_providers: number
  consensus_method: string
  min_confidence: number
  min_agreement: number
  providers: Array<{
    name: string
    healthy: boolean
    model: string
  }>
}

export interface BotStatus {
  is_running: boolean
  mode: string
  current_symbol: string | null
  last_analysis: string | null
  trades_today: number
  pnl_today: string
  uptime_seconds: number
}

// TradingView Agent Types
export interface TimeframeConsensus {
  direction: string
  confidence: number
  models_agree: number
  total_models: number
}

export interface TradingViewModelResult {
  model: string
  model_display_name: string
  timeframe: string
  analysis_style: string
  direction: string
  confidence: number
  indicators_used: string[]
  drawings_made: Array<Record<string, unknown>>
  reasoning: string
  key_observations: string[]
  entry_price: number | null
  stop_loss: number | null
  take_profit: number[]
  break_even_trigger: number | null
  trailing_stop_pips: number | null
  error: string | null
}

export interface TradingViewAgentResult {
  direction: string
  confidence: number
  is_strong_signal: boolean
  models_agree: number
  total_models: number
  mode: string
  timeframes_analyzed: string[]
  models_used: string[]
  timeframe_alignment: number
  is_aligned: boolean
  timeframe_consensus: Record<string, TimeframeConsensus>
  entry_price: number | null
  stop_loss: number | null
  take_profit: number | null
  break_even_trigger: number | null
  trailing_stop_pips: number | null
  analysis_styles_used: string[]
  indicators_used: string[]
  key_observations: string[]
  combined_reasoning: string
  vote_breakdown: Record<string, number>
  individual_results: TradingViewModelResult[]
}

export interface TradingViewAgentStatus {
  available: boolean
  modes: Record<string, { timeframes: string[], models: number }>
  tradingview_plans: Record<string, { max_indicators: number, price: string }>
  ai_models: Array<{ key: string, name: string, style: string }>
}

// ============ API Client ============

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`

  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    })
  } catch (networkError) {
    // Network error (server down, CORS, etc.)
    throw new Error('Cannot connect to server. Please check if the backend is running.')
  }

  if (!response.ok) {
    // Handle HTTP errors
    let errorMessage = `Server error: ${response.status}`

    if (response.status === 503) {
      errorMessage = 'Server is temporarily unavailable. Please try again later.'
    } else if (response.status === 502) {
      errorMessage = 'Server is starting up. Please wait a moment and try again.'
    } else if (response.status === 500) {
      errorMessage = 'Internal server error. Please check the backend logs.'
    } else {
      try {
        const error = await response.json()
        errorMessage = error.detail || error.message || errorMessage
      } catch {
        // Response is not JSON, use default message
      }
    }

    throw new Error(errorMessage)
  }

  return response.json()
}

// ============ AI Analysis API ============

export const aiApi = {
  /**
   * Run AI market analysis with multi-model consensus
   * This calls the 6 AIML models and returns aggregated results
   */
  analyze: async (
    symbol: string,
    currentPrice: number,
    timeframe: string = '5m',
    mode: 'quick' | 'standard' | 'premium' = 'standard'
  ): Promise<ConsensusResult> => {
    return fetchApi('/api/v1/ai/analyze', {
      method: 'POST',
      body: JSON.stringify({
        symbol: symbol.replace('/', '_'),
        timeframe,
        current_price: currentPrice,
        mode,
        indicators: {},
      }),
    })
  },

  /**
   * Get AI service status and active providers
   */
  getStatus: async (): Promise<AIServiceStatus> => {
    return fetchApi('/api/v1/ai/status')
  },

  /**
   * Get available AI providers
   */
  getProviders: async () => {
    return fetchApi('/api/v1/ai/providers')
  },

  /**
   * Health check for AI providers
   */
  healthCheck: async () => {
    return fetchApi('/api/v1/ai/health')
  },

  /**
   * Run TradingView Agent analysis with real browser automation
   * AI models interact with TradingView.com directly
   */
  tradingViewAgent: async (
    symbol: string,
    mode: 'quick' | 'standard' | 'premium' | 'ultra' = 'standard',
    maxIndicators: number = 3,
    headless: boolean = true
  ): Promise<TradingViewAgentResult> => {
    return fetchApi('/api/v1/ai/tradingview-agent', {
      method: 'POST',
      body: JSON.stringify({
        symbol: symbol.replace('/', '').replace('_', ''),  // EUR_USD -> EURUSD
        mode,
        max_indicators: maxIndicators,
        headless,
      }),
    })
  },

  /**
   * Get TradingView Agent status and available configurations
   */
  getTradingViewAgentStatus: async (): Promise<TradingViewAgentStatus> => {
    return fetchApi('/api/v1/ai/tradingview-agent/status')
  },
}

// ============ Analytics API ============

export const analyticsApi = {
  /**
   * Get account summary with balance, equity, margin
   */
  getAccount: async (): Promise<AccountSummary> => {
    return fetchApi('/api/v1/analytics/account')
  },

  /**
   * Get performance metrics (win rate, P&L, etc.)
   */
  getPerformance: async (): Promise<PerformanceMetrics> => {
    return fetchApi('/api/v1/analytics/performance')
  },

  /**
   * Get technical indicators for a symbol
   */
  getIndicators: async (symbol: string, timeframe: string = 'M15') => {
    return fetchApi(`/api/v1/analytics/indicators/${symbol.replace('/', '_')}?timeframe=${timeframe}`)
  },

  /**
   * Get full technical analysis
   */
  getAnalysis: async (symbol: string, timeframe: string = 'M15') => {
    return fetchApi(`/api/v1/analytics/analysis/${symbol.replace('/', '_')}?timeframe=${timeframe}`)
  },
}

// ============ Trading API ============

export const tradingApi = {
  /**
   * Get current price for a symbol
   */
  getPrice: async (symbol: string): Promise<PriceData> => {
    return fetchApi(`/api/v1/trading/price/${symbol.replace('/', '_')}`)
  },

  /**
   * Get prices for multiple symbols
   */
  getPrices: async (symbols: string[]): Promise<{ prices: PriceData[] }> => {
    const symbolsStr = symbols.map(s => s.replace('/', '_')).join(',')
    return fetchApi(`/api/v1/trading/prices?symbols=${symbolsStr}`)
  },

  /**
   * Get all open positions
   */
  getPositions: async (): Promise<PositionsResponse> => {
    return fetchApi('/api/v1/positions')
  },

  /**
   * Place a new order
   */
  placeOrder: async (order: {
    symbol: string
    side: 'buy' | 'sell'
    order_type?: 'market' | 'limit' | 'stop'
    size: number
    price?: number
    stop_loss?: number
    take_profit?: number
    leverage?: number
  }) => {
    return fetchApi('/api/v1/trading/orders', {
      method: 'POST',
      body: JSON.stringify({
        ...order,
        symbol: order.symbol.replace('/', '_'),
      }),
    })
  },

  /**
   * Close a position
   */
  closePosition: async (symbol: string) => {
    return fetchApi(`/api/v1/positions/${symbol.replace('/', '_')}`, {
      method: 'DELETE',
    })
  },

  /**
   * Modify position SL/TP
   */
  modifyPosition: async (symbol: string, stopLoss?: number, takeProfit?: number) => {
    return fetchApi(`/api/v1/positions/${symbol.replace('/', '_')}`, {
      method: 'PATCH',
      body: JSON.stringify({
        stop_loss: stopLoss,
        take_profit: takeProfit,
      }),
    })
  },

  /**
   * Get pending orders
   */
  getOrders: async () => {
    return fetchApi('/api/v1/trading/orders')
  },

  /**
   * Cancel an order
   */
  cancelOrder: async (orderId: string) => {
    return fetchApi(`/api/v1/trading/orders/${orderId}`, {
      method: 'DELETE',
    })
  },
}

// ============ Bot Control API ============

export const botApi = {
  /**
   * Get bot status
   */
  getStatus: async (): Promise<BotStatus> => {
    return fetchApi('/api/v1/bot/status')
  },

  /**
   * Start the trading bot
   */
  start: async (config?: Record<string, unknown>) => {
    return fetchApi('/api/v1/bot/start', {
      method: 'POST',
      body: JSON.stringify(config || {}),
    })
  },

  /**
   * Stop the trading bot
   */
  stop: async () => {
    return fetchApi('/api/v1/bot/stop', {
      method: 'POST',
    })
  },

  /**
   * Pause the trading bot
   */
  pause: async () => {
    return fetchApi('/api/v1/bot/pause', {
      method: 'POST',
    })
  },

  /**
   * Resume the trading bot
   */
  resume: async () => {
    return fetchApi('/api/v1/bot/resume', {
      method: 'POST',
    })
  },

  /**
   * Update bot configuration
   */
  updateConfig: async (config: Record<string, unknown>) => {
    return fetchApi('/api/v1/bot/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  },

  /**
   * Get bot configuration
   */
  getConfig: async () => {
    return fetchApi('/api/v1/bot/config')
  },
}

// ============ Settings API ============

export interface BrokerSettingsData {
  broker_type: string
  oanda_api_key?: string
  oanda_account_id?: string
  oanda_environment?: string
  metaapi_token?: string
  metaapi_account_id?: string
  metaapi_platform?: string
  ig_api_key?: string
  ig_username?: string
  ig_password?: string
  ig_account_id?: string
  ig_environment?: string
  alpaca_api_key?: string
  alpaca_secret_key?: string
  alpaca_paper?: boolean
}

export interface AISettingsData {
  aiml_api_key?: string
  openai_api_key?: string
  anthropic_api_key?: string
  google_api_key?: string
  groq_api_key?: string
  mistral_api_key?: string
}

export interface RiskSettingsData {
  max_positions: number
  max_daily_trades: number
  max_daily_loss_percent: number
  risk_per_trade: number
  default_leverage: number
  trading_enabled: boolean
}

export interface NotificationSettingsData {
  telegram_enabled: boolean
  telegram_bot_token?: string
  telegram_chat_id?: string
  discord_enabled: boolean
  discord_webhook?: string
}

export interface AllSettingsData {
  broker: BrokerSettingsData
  ai: AISettingsData
  risk: RiskSettingsData
  notifications: NotificationSettingsData
}

export const settingsApi = {
  /**
   * Get all settings
   */
  getAll: async (): Promise<AllSettingsData> => {
    return fetchApi('/api/v1/settings')
  },

  /**
   * Update all settings
   */
  updateAll: async (settings: AllSettingsData): Promise<{ status: string; message: string }> => {
    return fetchApi('/api/v1/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    })
  },

  /**
   * Update broker settings
   */
  updateBroker: async (broker: BrokerSettingsData): Promise<{ status: string; message: string }> => {
    return fetchApi('/api/v1/settings/broker', {
      method: 'PUT',
      body: JSON.stringify(broker),
    })
  },

  /**
   * Update AI settings
   */
  updateAI: async (ai: AISettingsData): Promise<{ status: string; message: string }> => {
    return fetchApi('/api/v1/settings/ai', {
      method: 'PUT',
      body: JSON.stringify(ai),
    })
  },

  /**
   * Update risk settings
   */
  updateRisk: async (risk: RiskSettingsData): Promise<{ status: string; message: string }> => {
    return fetchApi('/api/v1/settings/risk', {
      method: 'PUT',
      body: JSON.stringify(risk),
    })
  },

  /**
   * Update notification settings
   */
  updateNotifications: async (notifications: NotificationSettingsData): Promise<{ status: string; message: string }> => {
    return fetchApi('/api/v1/settings/notifications', {
      method: 'PUT',
      body: JSON.stringify(notifications),
    })
  },

  /**
   * Test broker connection
   */
  testBroker: async (): Promise<{ status: string; message: string; account_name?: string }> => {
    return fetchApi('/api/v1/settings/test-broker', {
      method: 'POST',
    })
  },
}

// ============ Health Check ============

export const healthCheck = async (): Promise<{ status: string; version: string }> => {
  return fetchApi('/health')
}

// ============ Default Export ============

export default {
  ai: aiApi,
  analytics: analyticsApi,
  trading: tradingApi,
  bot: botApi,
  settings: settingsApi,
  healthCheck,
}
