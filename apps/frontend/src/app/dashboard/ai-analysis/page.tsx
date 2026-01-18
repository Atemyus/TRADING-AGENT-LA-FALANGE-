'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'
import {
  Brain,
  Play,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  DollarSign,
  Zap,
  RefreshCw,
  Settings,
  ChevronDown,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Target,
  Shield,
} from 'lucide-react'
import { aiApi, type ConsensusResult, type AIVote } from '@/lib/api'

// Provider styling
const providerStyles: Record<string, { color: string; icon: string; bg: string }> = {
  openai: { color: 'text-green-400', icon: '🤖', bg: 'bg-green-500/20' },
  anthropic: { color: 'text-orange-400', icon: '🧠', bg: 'bg-orange-500/20' },
  google: { color: 'text-blue-400', icon: '💎', bg: 'bg-blue-500/20' },
  groq: { color: 'text-red-400', icon: '⚡', bg: 'bg-red-500/20' },
  mistral: { color: 'text-orange-500', icon: '🌪️', bg: 'bg-orange-500/20' },
  ollama: { color: 'text-gray-400', icon: '🦙', bg: 'bg-gray-500/20' },
}

// Demo result for visualization
const demoResult: ConsensusResult = {
  direction: 'BUY',
  confidence: 78.5,
  should_trade: true,
  total_votes: 8,
  valid_votes: 7,
  votes_buy: 5,
  votes_sell: 1,
  votes_hold: 1,
  agreement_level: 'strong',
  agreement_percentage: 71.4,
  suggested_entry: '1.0892',
  suggested_stop_loss: '1.0850',
  suggested_take_profit: '1.0950',
  risk_reward_ratio: 1.38,
  key_factors: [
    'RSI showing bullish divergence at 42, recovering from oversold',
    'Price holding above 200 EMA support at 1.0865',
    'London session showing strong buying momentum',
    'MACD histogram turning positive after bearish cross',
  ],
  risks: [
    'USD strength on hawkish Fed expectations',
    'Key resistance at 1.0920 may cap upside',
    'Low liquidity expected during Asian session',
  ],
  reasoning_summary: 'Strong bullish consensus with 5/7 models recommending BUY. Technical setup shows RSI divergence combined with EMA support. Risk/reward ratio of 1.38 meets minimum threshold.',
  votes: [
    { provider: 'openai', model: 'gpt-4o', direction: 'BUY', confidence: 82, reasoning: 'Bullish divergence on RSI combined with price holding above 200 EMA suggests continuation of uptrend. Entry at current levels with tight stop below recent swing low.', is_valid: true },
    { provider: 'openai', model: 'gpt-4o-mini', direction: 'BUY', confidence: 75, reasoning: 'Trend continuation likely based on momentum indicators. Recommend scaling in at current price.', is_valid: true },
    { provider: 'anthropic', model: 'claude-sonnet', direction: 'BUY', confidence: 85, reasoning: 'Strong technical setup with multiple confluences: EMA support, RSI divergence, and session momentum. High probability long entry.', is_valid: true },
    { provider: 'anthropic', model: 'claude-haiku', direction: 'HOLD', confidence: 60, reasoning: 'Mixed signals present. While trend is bullish, approaching resistance zone suggests waiting for breakout confirmation.', is_valid: true },
    { provider: 'google', model: 'gemini-flash', direction: 'BUY', confidence: 78, reasoning: 'Momentum building with MACD crossover imminent. Favor long positions with defined risk.', is_valid: true },
    { provider: 'groq', model: 'llama3-70b', direction: 'BUY', confidence: 80, reasoning: 'Technical analysis indicates bullish bias. Multiple timeframe alignment supports long entry.', is_valid: true },
    { provider: 'mistral', model: 'mistral-large', direction: 'SELL', confidence: 65, reasoning: 'Resistance ahead at 1.0920. Prefer to fade the rally with tight stops above resistance.', is_valid: true },
    { provider: 'ollama', model: 'llama3.1:8b', direction: 'BUY', confidence: 0, reasoning: 'Error: Connection refused', is_valid: false, error: 'Connection refused' },
  ],
  total_cost_usd: 0.0234,
  total_tokens: 12500,
  processing_time_ms: 3250,
  providers_used: ['openai', 'anthropic', 'google', 'groq', 'mistral'],
  failed_providers: ['ollama'],
}

const SYMBOLS = [
  { value: 'EUR_USD', label: 'EUR/USD', price: '1.0892' },
  { value: 'GBP_USD', label: 'GBP/USD', price: '1.2651' },
  { value: 'USD_JPY', label: 'USD/JPY', price: '149.86' },
  { value: 'XAU_USD', label: 'XAU/USD (Gold)', price: '2045.50' },
  { value: 'US30', label: 'US30 (Dow)', price: '38252' },
  { value: 'NAS100', label: 'NAS100', price: '17522' },
]

const TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']

const MODES = [
  { value: 'quick', label: 'Quick', description: 'Fastest models only', icon: Zap },
  { value: 'standard', label: 'Standard', description: 'Balanced selection', icon: Target },
  { value: 'premium', label: 'Premium', description: 'Best quality models', icon: Shield },
]

export default function AIAnalysisPage() {
  const [symbol, setSymbol] = useState('EUR_USD')
  const [timeframe, setTimeframe] = useState('5m')
  const [mode, setMode] = useState<'quick' | 'standard' | 'premium'>('standard')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<ConsensusResult | null>(demoResult)
  const [error, setError] = useState<string | null>(null)
  const [expandedVote, setExpandedVote] = useState<string | null>(null)

  const selectedSymbol = SYMBOLS.find(s => s.value === symbol)

  const runAnalysis = async () => {
    setIsAnalyzing(true)
    setError(null)

    try {
      // In production, this would call the real API
      // const response = await aiApi.analyze({
      //   symbol,
      //   timeframe,
      //   current_price: parseFloat(selectedSymbol?.price || '0'),
      //   mode,
      // })

      // Simulate API call for demo
      await new Promise(resolve => setTimeout(resolve, 3000))
      setResult(demoResult)
    } catch (err) {
      setError('Failed to run analysis. Please check your API configuration.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold mb-2">AI Analysis</h1>
          <p className="text-dark-400">Multi-model consensus trading signals</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-dark-400">Providers Active:</span>
          <span className="font-mono font-bold text-neon-green">7/8</span>
        </div>
      </motion.div>

      {/* Analysis Controls */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card p-6"
      >
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          {/* Symbol Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="input"
            >
              {SYMBOLS.map(s => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* Timeframe */}
          <div>
            <label className="block text-sm font-medium mb-2">Timeframe</label>
            <div className="flex gap-1">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    timeframe === tf
                      ? 'bg-primary-500 text-white'
                      : 'bg-dark-800 text-dark-400 hover:text-dark-200'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Mode Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Analysis Mode</label>
            <div className="flex gap-2">
              {MODES.map(m => {
                const Icon = m.icon
                return (
                  <button
                    key={m.value}
                    onClick={() => setMode(m.value as typeof mode)}
                    className={`flex-1 p-2 rounded-lg text-center transition-colors ${
                      mode === m.value
                        ? 'bg-primary-500/20 border border-primary-500/50'
                        : 'bg-dark-800 border border-transparent hover:border-dark-600'
                    }`}
                  >
                    <Icon size={16} className="mx-auto mb-1" />
                    <span className="text-xs">{m.label}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Run Button */}
          <div className="flex items-end">
            <button
              onClick={runAnalysis}
              disabled={isAnalyzing}
              className="w-full btn-primary flex items-center justify-center gap-2 py-3"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 size={20} className="animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Play size={20} />
                  Run Analysis
                </>
              )}
            </button>
          </div>
        </div>

        {/* Current Price Display */}
        <div className="flex items-center justify-between p-4 bg-dark-800/50 rounded-lg">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-sm text-dark-400">Selected Symbol</p>
              <p className="text-xl font-semibold">{selectedSymbol?.label}</p>
            </div>
            <div className="h-10 w-px bg-dark-700" />
            <div>
              <p className="text-sm text-dark-400">Current Price</p>
              <p className="text-xl font-mono font-bold">{selectedSymbol?.price}</p>
            </div>
          </div>
          <div className="text-sm text-dark-400">
            <Clock size={14} className="inline mr-1" />
            Last updated: Just now
          </div>
        </div>
      </motion.div>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 bg-neon-red/20 border border-neon-red/50 rounded-lg flex items-center gap-3"
          >
            <AlertTriangle className="text-neon-red" />
            <span>{error}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading State */}
      <AnimatePresence>
        {isAnalyzing && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="card p-12"
          >
            <div className="text-center">
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                className="w-16 h-16 mx-auto mb-6 rounded-full border-4 border-primary-500 border-t-transparent"
              />
              <h3 className="text-xl font-semibold mb-2">Analyzing Market...</h3>
              <p className="text-dark-400 mb-6">Running analysis across multiple AI models</p>
              <div className="flex justify-center gap-2">
                {['openai', 'anthropic', 'google', 'groq', 'mistral'].map((provider, i) => (
                  <motion.div
                    key={provider}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: i * 0.2 }}
                    className={`w-10 h-10 rounded-lg ${providerStyles[provider]?.bg} flex items-center justify-center`}
                  >
                    <span>{providerStyles[provider]?.icon}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Results */}
      {result && !isAnalyzing && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Main Result */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="xl:col-span-2 space-y-6"
          >
            {/* Signal Card */}
            <div className="card p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                  <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
                    result.direction === 'BUY' ? 'bg-neon-green/20' :
                    result.direction === 'SELL' ? 'bg-neon-red/20' : 'bg-neon-yellow/20'
                  }`}>
                    {result.direction === 'BUY' ? (
                      <TrendingUp size={32} className="text-neon-green" />
                    ) : result.direction === 'SELL' ? (
                      <TrendingDown size={32} className="text-neon-red" />
                    ) : (
                      <Minus size={32} className="text-neon-yellow" />
                    )}
                  </div>
                  <div>
                    <p className="text-sm text-dark-400">AI Consensus Signal</p>
                    <h2 className={`text-4xl font-bold ${
                      result.direction === 'BUY' ? 'text-neon-green' :
                      result.direction === 'SELL' ? 'text-neon-red' : 'text-neon-yellow'
                    }`}>
                      {result.direction}
                    </h2>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm text-dark-400">Confidence</p>
                  <p className="text-4xl font-bold font-mono">{result.confidence.toFixed(1)}%</p>
                </div>
              </div>

              {/* Confidence Bar */}
              <div className="mb-6">
                <div className="h-4 bg-dark-800 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${result.confidence}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    className={`h-full rounded-full ${
                      result.confidence >= 70 ? 'bg-gradient-to-r from-neon-green to-neon-blue' :
                      result.confidence >= 50 ? 'bg-gradient-to-r from-neon-yellow to-neon-green' :
                      'bg-gradient-to-r from-neon-red to-neon-yellow'
                    }`}
                  />
                </div>
              </div>

              {/* Trade Recommendation */}
              {result.should_trade && (
                <div className="grid grid-cols-4 gap-4 p-4 bg-dark-800/50 rounded-xl">
                  <div>
                    <p className="text-xs text-dark-400 mb-1">Entry</p>
                    <p className="font-mono font-bold text-lg">{result.suggested_entry}</p>
                  </div>
                  <div>
                    <p className="text-xs text-dark-400 mb-1">Stop Loss</p>
                    <p className="font-mono font-bold text-lg text-neon-red">{result.suggested_stop_loss}</p>
                  </div>
                  <div>
                    <p className="text-xs text-dark-400 mb-1">Take Profit</p>
                    <p className="font-mono font-bold text-lg text-neon-green">{result.suggested_take_profit}</p>
                  </div>
                  <div>
                    <p className="text-xs text-dark-400 mb-1">Risk/Reward</p>
                    <p className="font-mono font-bold text-lg">{result.risk_reward_ratio?.toFixed(2)}</p>
                  </div>
                </div>
              )}
            </div>

            {/* Vote Distribution */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">Vote Distribution</h3>
              <div className="flex gap-1 h-12 mb-4">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(result.votes_buy / result.valid_votes) * 100}%` }}
                  transition={{ duration: 0.5 }}
                  className="bg-neon-green/30 rounded-l-lg flex items-center justify-center"
                >
                  <span className="text-neon-green font-semibold">{result.votes_buy} BUY</span>
                </motion.div>
                {result.votes_hold > 0 && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(result.votes_hold / result.valid_votes) * 100}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                    className="bg-neon-yellow/30 flex items-center justify-center"
                  >
                    <span className="text-neon-yellow font-semibold">{result.votes_hold} HOLD</span>
                  </motion.div>
                )}
                {result.votes_sell > 0 && (
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(result.votes_sell / result.valid_votes) * 100}%` }}
                    transition={{ duration: 0.5, delay: 0.2 }}
                    className="bg-neon-red/30 rounded-r-lg flex items-center justify-center"
                  >
                    <span className="text-neon-red font-semibold">{result.votes_sell} SELL</span>
                  </motion.div>
                )}
              </div>
              <div className="flex items-center justify-between text-sm text-dark-400">
                <span>{result.valid_votes} of {result.total_votes} models voted</span>
                <span>Agreement: {result.agreement_percentage.toFixed(1)}% ({result.agreement_level})</span>
              </div>
            </div>

            {/* Individual Votes */}
            <div className="card overflow-hidden">
              <div className="p-4 border-b border-dark-700/50">
                <h3 className="text-lg font-semibold">Individual Model Votes</h3>
              </div>
              <div className="divide-y divide-dark-700/30">
                {result.votes.map((vote, index) => (
                  <motion.div
                    key={`${vote.provider}-${vote.model}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="p-4 hover:bg-dark-800/30 transition-colors cursor-pointer"
                    onClick={() => setExpandedVote(expandedVote === `${vote.provider}-${vote.model}` ? null : `${vote.provider}-${vote.model}`)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg ${providerStyles[vote.provider]?.bg} flex items-center justify-center`}>
                          <span className="text-lg">{providerStyles[vote.provider]?.icon}</span>
                        </div>
                        <div>
                          <p className="font-semibold">{vote.model}</p>
                          <p className="text-xs text-dark-400">{vote.provider}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        {vote.is_valid ? (
                          <>
                            <div className={`px-3 py-1 rounded-lg text-sm font-semibold ${
                              vote.direction === 'BUY' ? 'bg-neon-green/20 text-neon-green' :
                              vote.direction === 'SELL' ? 'bg-neon-red/20 text-neon-red' :
                              'bg-neon-yellow/20 text-neon-yellow'
                            }`}>
                              {vote.direction}
                            </div>
                            <div className="w-20 text-right">
                              <p className="font-mono font-bold">{vote.confidence}%</p>
                            </div>
                          </>
                        ) : (
                          <div className="flex items-center gap-2 text-neon-red">
                            <XCircle size={16} />
                            <span className="text-sm">Failed</span>
                          </div>
                        )}
                        <ChevronDown size={16} className={`text-dark-400 transition-transform ${
                          expandedVote === `${vote.provider}-${vote.model}` ? 'rotate-180' : ''
                        }`} />
                      </div>
                    </div>
                    <AnimatePresence>
                      {expandedVote === `${vote.provider}-${vote.model}` && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="mt-4 p-4 bg-dark-800/50 rounded-lg"
                        >
                          <p className="text-sm text-dark-300">{vote.reasoning}</p>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>

          {/* Sidebar */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="space-y-6"
          >
            {/* Key Factors */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <CheckCircle size={20} className="text-neon-green" />
                Key Factors
              </h3>
              <ul className="space-y-3">
                {result.key_factors.map((factor, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-start gap-2 text-sm"
                  >
                    <CheckCircle size={14} className="text-neon-green mt-1 flex-shrink-0" />
                    <span className="text-dark-300">{factor}</span>
                  </motion.li>
                ))}
              </ul>
            </div>

            {/* Risks */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <AlertTriangle size={20} className="text-neon-yellow" />
                Risks
              </h3>
              <ul className="space-y-3">
                {result.risks.map((risk, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-start gap-2 text-sm"
                  >
                    <AlertTriangle size={14} className="text-neon-yellow mt-1 flex-shrink-0" />
                    <span className="text-dark-400">{risk}</span>
                  </motion.li>
                ))}
              </ul>
            </div>

            {/* Analysis Stats */}
            <div className="card p-6">
              <h3 className="text-lg font-semibold mb-4">Analysis Stats</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-400 flex items-center gap-2">
                    <Clock size={14} />
                    Processing Time
                  </span>
                  <span className="font-mono">{(result.processing_time_ms / 1000).toFixed(2)}s</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-400 flex items-center gap-2">
                    <Zap size={14} />
                    Tokens Used
                  </span>
                  <span className="font-mono">{result.total_tokens.toLocaleString()}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-dark-400 flex items-center gap-2">
                    <DollarSign size={14} />
                    Cost
                  </span>
                  <span className="font-mono">${result.total_cost_usd.toFixed(4)}</span>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  )
}
