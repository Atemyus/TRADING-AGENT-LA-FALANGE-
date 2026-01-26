'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect, useCallback, useRef } from 'react'
import Link from 'next/link'
import dynamic from 'next/dynamic'
import {
  Brain,
  Play,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
  Zap,
  Settings,
  ChevronDown,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Target,
  Shield,
  Wifi,
  WifiOff,
  Camera,
  Eye,
  Monitor,
  BarChart3,
  Layers,
} from 'lucide-react'
import { aiApi, type AIServiceStatus, type TradingViewAgentResult } from '@/lib/api'
import { usePriceStream } from '@/hooks/useWebSocket'
import { useChartCapture, type AIAnalysisResult } from '@/hooks/useChartCapture'
import { ALL_SYMBOLS, CATEGORY_LABELS, findSymbol, toTradingViewSymbol, type TradingSymbol } from '@/lib/symbols'

// Dynamic import for TradingView chart
const TradingViewWidget = dynamic(
  () => import('@/components/charts/TradingViewWidget'),
  { ssr: false, loading: () => <div className="h-[400px] bg-slate-900 rounded-xl animate-pulse" /> }
)

// Provider styling for AIML API models
const providerStyles: Record<string, { color: string; icon: string; bg: string }> = {
  // The 8 AIML models (matching backend provider names)
  'OpenAI': { color: 'text-green-400', icon: '💬', bg: 'bg-green-500/20' },
  'Google': { color: 'text-blue-400', icon: '💎', bg: 'bg-blue-500/20' },
  'DeepSeek': { color: 'text-cyan-400', icon: '🔍', bg: 'bg-cyan-500/20' },
  'xAI': { color: 'text-red-400', icon: '⚡', bg: 'bg-red-500/20' },
  'Alibaba': { color: 'text-orange-400', icon: '🌟', bg: 'bg-orange-500/20' },
  'Zhipu': { color: 'text-purple-400', icon: '🧪', bg: 'bg-purple-500/20' },
  'Meta': { color: 'text-sky-400', icon: '🦙', bg: 'bg-sky-500/20' },
  'Mistral': { color: 'text-amber-400', icon: '🌪️', bg: 'bg-amber-500/20' },
  // Also match lowercase provider keys from backend
  'aiml_openai': { color: 'text-green-400', icon: '💬', bg: 'bg-green-500/20' },
  'aiml_google': { color: 'text-blue-400', icon: '💎', bg: 'bg-blue-500/20' },
  'aiml_deepseek': { color: 'text-cyan-400', icon: '🔍', bg: 'bg-cyan-500/20' },
  'aiml_xai': { color: 'text-red-400', icon: '⚡', bg: 'bg-red-500/20' },
  'aiml_alibaba': { color: 'text-orange-400', icon: '🌟', bg: 'bg-orange-500/20' },
  'aiml_zhipu': { color: 'text-purple-400', icon: '🧪', bg: 'bg-purple-500/20' },
  'aiml_meta': { color: 'text-sky-400', icon: '🦙', bg: 'bg-sky-500/20' },
  'aiml_mistral': { color: 'text-amber-400', icon: '🌪️', bg: 'bg-amber-500/20' },
}

// The 8 AI models we use via AIML API (exact model IDs)
// ORDERED: Vision-capable models first (for Standard mode which uses only 5)
const AI_MODELS = [
  { provider: 'OpenAI', model: 'ChatGPT 5.2', icon: '💬', vision: true },
  { provider: 'Google', model: 'Gemini 3 Pro', icon: '💎', vision: true },
  { provider: 'xAI', model: 'Grok 4.1 Fast', icon: '⚡', vision: true },
  { provider: 'Alibaba', model: 'Qwen3 VL', icon: '🌟', vision: true },
  { provider: 'DeepSeek', model: 'DeepSeek V3.1', icon: '🔍', vision: false },
  { provider: 'Zhipu', model: 'GLM 4.5 Air', icon: '🧪', vision: false },
  { provider: 'Meta', model: 'Llama 4 Scout', icon: '🦙', vision: false },
  { provider: 'Mistral', model: 'Mistral 7B v0.3', icon: '🌪️', vision: false },
]

// Group symbols by category for the dropdown
const GROUPED_SYMBOLS = Object.entries(
  ALL_SYMBOLS.reduce((acc, symbol) => {
    if (!acc[symbol.category]) acc[symbol.category] = []
    acc[symbol.category].push(symbol)
    return acc
  }, {} as Record<TradingSymbol['category'], TradingSymbol[]>)
)

const MODES = [
  { value: 'quick', label: 'Quick', description: '1 TF, 3 AI', icon: Zap },
  { value: 'standard', label: 'Standard', description: '2 TF, 5 AI', icon: Target },
  { value: 'premium', label: 'Premium', description: '3 TF, 7 AI', icon: Shield },
  { value: 'ultra', label: 'Ultra', description: '5 TF, 8 AI', icon: Layers },
]

// TradingView Free plan limit: 2 indicators
const MAX_INDICATORS_FREE_PLAN = 2

export default function AIAnalysisPage() {
  const [symbol, setSymbol] = useState('EUR_USD')
  const [mode, setMode] = useState<'quick' | 'standard' | 'premium' | 'ultra'>('standard')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [hasInitialized, setHasInitialized] = useState(false)
  const [aiStatus, setAiStatus] = useState<AIServiceStatus | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(true)

  // Vision Analysis State
  const [isCapturing, setIsCapturing] = useState(false)
  const [visionResult, setVisionResult] = useState<AIAnalysisResult | null>(null)
  const [showChart, setShowChart] = useState(false)
  const chartRef = useRef<HTMLDivElement>(null)
  const { captureChart } = useChartCapture()

  // TradingView Agent State
  const [tvAgentResult, setTvAgentResult] = useState<TradingViewAgentResult | null>(null)
  const [maxIndicators] = useState(MAX_INDICATORS_FREE_PLAN)  // Fixed to Free plan limit
  const [expandedTvResult, setExpandedTvResult] = useState<string | null>(null)

  const selectedSymbol = findSymbol(symbol)

  // Use WebSocket for real-time price streaming
  const { prices: streamPrices, isConnected: isPriceConnected } = usePriceStream([symbol])

  // Fetch AI status on mount
  useEffect(() => {
    const fetchAiStatus = async () => {
      try {
        const status = await aiApi.getStatus()
        setAiStatus(status)
      } catch (err) {
        console.error('Failed to fetch AI status:', err)
      } finally {
        setLoadingStatus(false)
      }
    }
    fetchAiStatus()
  }, [])

  // Update current price from WebSocket stream
  useEffect(() => {
    if (streamPrices[symbol]) {
      const mid = parseFloat(streamPrices[symbol].mid)
      if (mid > 0) {
        setCurrentPrice(mid)
      }
    }
  }, [streamPrices, symbol])

  const runAnalysis = useCallback(async () => {
    setIsAnalyzing(true)
    setError(null)
    setTvAgentResult(null)

    try {
      // Get the TradingView symbol format (e.g., "FX:EURUSD" or "OANDA:XAUUSD")
      const symbolInfo = findSymbol(symbol)
      const tvSymbol = symbolInfo?.tvSymbol || null

      // TradingView Agent - browser automation with multi-timeframe analysis
      const response = await aiApi.tradingViewAgent(
        symbol,
        tvSymbol,
        mode,
        maxIndicators,
        true // headless
      )
      setTvAgentResult(response)
    } catch (err) {
      console.error('Analysis failed:', err)
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'

      // Provide specific error messages based on the error
      if (errorMessage.includes('No providers available')) {
        setError('No AI providers configured. Go to Settings > AI Providers and add your AIML API key.')
      } else if (errorMessage.includes('No broker configured')) {
        setError('Broker not configured. Go to Settings > Broker to connect your trading account.')
      } else if (errorMessage.includes('AIML') || errorMessage.includes('API key')) {
        setError('AIML API key invalid or missing. Go to Settings > AI Providers to configure.')
      } else if (errorMessage.includes('playwright') || errorMessage.includes('TradingView Agent not available')) {
        setError('TradingView Agent not available. Install playwright on the server.')
      } else {
        setError(`Analysis failed: ${errorMessage}`)
      }
    } finally {
      setIsAnalyzing(false)
    }
  }, [symbol, mode, maxIndicators])

  // Capture TradingView chart and analyze with Vision AI
  const captureAndAnalyze = useCallback(async () => {
    if (!chartRef.current) {
      setError('Chart not ready. Please wait for it to load.')
      return
    }

    setIsCapturing(true)
    setError(null)
    setVisionResult(null)

    try {
      const result = await captureChart(
        chartRef.current,
        selectedSymbol?.label || symbol,
        ['15m'] // Default timeframe for vision capture
      )

      if (result.success && result.analysis) {
        setVisionResult(result.analysis)
      } else {
        setError(result.error || 'Failed to analyze chart')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chart capture failed')
    } finally {
      setIsCapturing(false)
    }
  }, [captureChart, selectedSymbol?.label, symbol])

  // Auto-run analysis on page load (only if providers are configured)
  useEffect(() => {
    if (!hasInitialized && !loadingStatus && aiStatus && aiStatus.active_providers > 0) {
      setHasInitialized(true)
      // Small delay to ensure component is mounted and price is fetched
      const timer = setTimeout(() => {
        runAnalysis()
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [hasInitialized, loadingStatus, aiStatus, runAnalysis])

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
          <span className="text-sm text-dark-400">AI Models:</span>
          {loadingStatus ? (
            <Loader2 size={16} className="animate-spin text-dark-400" />
          ) : aiStatus ? (
            <span className={`font-mono font-bold ${aiStatus.active_providers > 0 ? 'text-neon-green' : 'text-neon-red'}`}>
              {aiStatus.active_providers}
            </span>
          ) : (
            <span className="font-mono font-bold text-dark-400">-</span>
          )}
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
            <label className="block text-sm font-medium mb-2">Symbol ({ALL_SYMBOLS.length} assets)</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="input"
            >
              {GROUPED_SYMBOLS.map(([category, symbols]) => (
                <optgroup key={category} label={CATEGORY_LABELS[category as TradingSymbol['category']]}>
                  {symbols.map(s => (
                    <option key={s.value} value={s.value}>{s.label}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>

          {/* TradingView Free Plan Info */}
          <div>
            <label className="block text-sm font-medium mb-2">TradingView Plan</label>
            <div className="input bg-dark-800/50 cursor-not-allowed">
              Free Plan - Max {MAX_INDICATORS_FREE_PLAN} indicators
            </div>
          </div>

          {/* Mode Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Multi-TF Mode</label>
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
                    title={m.description}
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
                  Running TradingView Agent...
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

        {/* Current Price Display - Real-time WebSocket */}
        <div className="flex items-center justify-between p-4 bg-dark-800/50 rounded-lg">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-sm text-dark-400">Selected Symbol</p>
              <p className="text-xl font-semibold">{selectedSymbol?.label}</p>
            </div>
            <div className="h-10 w-px bg-dark-700" />
            <div>
              <p className="text-sm text-dark-400">Current Price</p>
              <motion.p
                key={currentPrice}
                initial={{ scale: 1.05, color: '#00ff88' }}
                animate={{ scale: 1, color: '#ffffff' }}
                transition={{ duration: 0.3 }}
                className="text-2xl font-mono font-bold tabular-nums"
              >
                {currentPrice > 0 ? currentPrice.toFixed(symbol.includes('JPY') ? 3 : 5) : '—'}
              </motion.p>
            </div>
            {/* Bid/Ask spread */}
            {streamPrices[symbol] && (
              <>
                <div className="h-10 w-px bg-dark-700" />
                <div className="text-sm">
                  <div className="flex gap-4">
                    <div>
                      <span className="text-dark-400">Bid: </span>
                      <span className="font-mono text-neon-red">{parseFloat(streamPrices[symbol].bid).toFixed(symbol.includes('JPY') ? 3 : 5)}</span>
                    </div>
                    <div>
                      <span className="text-dark-400">Ask: </span>
                      <span className="font-mono text-neon-green">{parseFloat(streamPrices[symbol].ask).toFixed(symbol.includes('JPY') ? 3 : 5)}</span>
                    </div>
                  </div>
                  <div className="text-dark-500 text-xs mt-1">
                    Spread: {streamPrices[symbol].spread} pips
                  </div>
                </div>
              </>
            )}
          </div>
          <div className="flex items-center gap-2 text-sm">
            {isPriceConnected ? (
              <>
                <motion.div
                  animate={{ opacity: [1, 0.5, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  className="flex items-center gap-1 text-neon-green"
                >
                  <Wifi size={14} />
                  <span>Live</span>
                </motion.div>
              </>
            ) : (
              <>
                <WifiOff size={14} className="text-dark-400" />
                <span className="text-dark-400">Connecting...</span>
              </>
            )}
          </div>
        </div>
      </motion.div>

      {/* TradingView Chart with Vision Analysis */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card overflow-hidden"
      >
        <div className="p-4 border-b border-dark-700/50 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Eye size={20} className="text-primary-400" />
            <div>
              <h3 className="font-semibold">Chart Vision Analysis</h3>
              <p className="text-xs text-dark-400">AI sees the chart with all visible indicators</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowChart(!showChart)}
              className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 rounded-lg text-sm transition-colors"
            >
              {showChart ? 'Hide Chart' : 'Show Chart'}
            </button>
            {showChart && (
              <button
                onClick={captureAndAnalyze}
                disabled={isCapturing}
                className="px-4 py-1.5 bg-primary-500 hover:bg-primary-600 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50"
              >
                {isCapturing ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Camera size={14} />
                    Capture & Analyze
                  </>
                )}
              </button>
            )}
          </div>
        </div>

        <AnimatePresence>
          {showChart && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div ref={chartRef} className="relative">
                <TradingViewWidget
                  symbol={selectedSymbol?.label || 'EUR/USD'}
                  interval="15"
                  height={400}
                  theme="dark"
                  allowSymbolChange={false}
                  showToolbar={true}
                  showDrawingTools={true}
                />
                {isCapturing && (
                  <div className="absolute inset-0 bg-dark-900/80 flex items-center justify-center">
                    <div className="text-center">
                      <Loader2 size={40} className="animate-spin mx-auto mb-3 text-primary-400" />
                      <p className="text-sm">Capturing chart & sending to 8 AI models...</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Vision Analysis Result */}
              {visionResult && (
                <div className="p-4 border-t border-dark-700/50 bg-dark-800/30">
                  <h4 className="font-semibold mb-3 flex items-center gap-2">
                    <Eye size={16} className="text-primary-400" />
                    Vision Analysis Result
                  </h4>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="p-3 bg-dark-700/50 rounded-lg">
                      <p className="text-xs text-dark-400 mb-1">Direction</p>
                      <p className={`text-lg font-bold ${
                        visionResult.direction === 'LONG' ? 'text-neon-green' :
                        visionResult.direction === 'SHORT' ? 'text-neon-red' : 'text-neon-yellow'
                      }`}>
                        {visionResult.direction}
                      </p>
                    </div>
                    <div className="p-3 bg-dark-700/50 rounded-lg">
                      <p className="text-xs text-dark-400 mb-1">Confidence</p>
                      <p className="text-lg font-bold">{visionResult.confidence}%</p>
                    </div>
                    <div className="p-3 bg-dark-700/50 rounded-lg">
                      <p className="text-xs text-dark-400 mb-1">Stop Loss</p>
                      <p className="text-lg font-mono text-neon-red">{visionResult.stop_loss || '—'}</p>
                    </div>
                    <div className="p-3 bg-dark-700/50 rounded-lg">
                      <p className="text-xs text-dark-400 mb-1">Take Profit</p>
                      <p className="text-lg font-mono text-neon-green">
                        {visionResult.take_profit?.[0] || '—'}
                      </p>
                    </div>
                  </div>
                  {visionResult.patterns_detected && visionResult.patterns_detected.length > 0 && (
                    <div className="mb-3">
                      <p className="text-xs text-dark-400 mb-2">Patterns Detected</p>
                      <div className="flex flex-wrap gap-2">
                        {visionResult.patterns_detected.map((pattern, i) => (
                          <span key={i} className="px-2 py-1 bg-primary-500/20 text-primary-300 rounded text-xs">
                            {pattern}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {visionResult.reasoning && (
                    <div className="p-3 bg-dark-700/30 rounded-lg">
                      <p className="text-xs text-dark-400 mb-1">AI Reasoning</p>
                      <p className="text-sm text-dark-300">{visionResult.reasoning}</p>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>

      {/* No AI Providers Warning */}
      {!loadingStatus && aiStatus && aiStatus.active_providers === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-4 bg-neon-yellow/20 border border-neon-yellow/50 rounded-lg"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="text-neon-yellow flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-neon-yellow mb-1">AI Providers Not Configured</h3>
              <p className="text-dark-300 text-sm mb-3">
                No AI providers are currently active. Configure your AIML API key to enable AI analysis.
              </p>
              <Link
                href="/dashboard/settings"
                className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-600 rounded-lg text-sm font-medium transition-colors"
              >
                <Settings size={16} />
                Go to Settings
              </Link>
            </div>
          </div>
        </motion.div>
      )}

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-4 bg-neon-red/20 border border-neon-red/50 rounded-lg"
          >
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-neon-red flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <span>{error}</span>
                {error.includes('Settings') && (
                  <Link
                    href="/dashboard/settings"
                    className="ml-3 inline-flex items-center gap-1 text-primary-400 hover:text-primary-300 text-sm font-medium"
                  >
                    <Settings size={14} />
                    Configure
                  </Link>
                )}
              </div>
            </div>
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
              <p className="text-dark-400 mb-6">
                Running analysis with {aiStatus?.active_providers || 6} AI models via AIML API
              </p>
              <div className="flex justify-center gap-2">
                {(aiStatus?.providers
                  ? aiStatus.providers.map(p => ({ name: p.name, healthy: p.healthy, model: p.model }))
                  : AI_MODELS.map(m => ({ name: m.provider, healthy: true, model: m.model }))
                ).map((provider, i) => {
                  const providerName = provider.name
                  const style = providerStyles[providerName] || providerStyles[providerName.toLowerCase()] || { bg: 'bg-dark-700', icon: '🤖' }
                  return (
                    <motion.div
                      key={providerName}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: i * 0.15 }}
                      className={`w-10 h-10 rounded-lg ${style.bg} flex items-center justify-center`}
                      title={providerName}
                    >
                      <span>{style.icon}</span>
                    </motion.div>
                  )
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* TradingView Agent Results */}
      {tvAgentResult && !isAnalyzing && (
        <div className="space-y-6">
          {/* Main Signal Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="card p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-4">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
                  tvAgentResult.direction === 'LONG' ? 'bg-neon-green/20' :
                  tvAgentResult.direction === 'SHORT' ? 'bg-neon-red/20' : 'bg-neon-yellow/20'
                }`}>
                  {tvAgentResult.direction === 'LONG' ? (
                    <TrendingUp size={32} className="text-neon-green" />
                  ) : tvAgentResult.direction === 'SHORT' ? (
                    <TrendingDown size={32} className="text-neon-red" />
                  ) : (
                    <Minus size={32} className="text-neon-yellow" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <Monitor size={16} className="text-primary-400" />
                    <p className="text-sm text-dark-400">TradingView Agent Signal</p>
                  </div>
                  <h2 className={`text-4xl font-bold ${
                    tvAgentResult.direction === 'LONG' ? 'text-neon-green' :
                    tvAgentResult.direction === 'SHORT' ? 'text-neon-red' : 'text-neon-yellow'
                  }`}>
                    {tvAgentResult.direction}
                  </h2>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-dark-400">Confidence</p>
                <p className="text-4xl font-bold font-mono">{tvAgentResult.confidence.toFixed(1)}%</p>
              </div>
            </div>

            {/* Confidence & Alignment Bars */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <p className="text-xs text-dark-400 mb-1">Model Confidence</p>
                <div className="h-3 bg-dark-800 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${tvAgentResult.confidence}%` }}
                    className="h-full bg-gradient-to-r from-primary-500 to-primary-400 rounded-full"
                  />
                </div>
              </div>
              <div>
                <p className="text-xs text-dark-400 mb-1">Timeframe Alignment: {tvAgentResult.timeframe_alignment.toFixed(0)}%</p>
                <div className="h-3 bg-dark-800 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${tvAgentResult.timeframe_alignment}%` }}
                    className={`h-full rounded-full ${
                      tvAgentResult.is_aligned ? 'bg-gradient-to-r from-neon-green to-neon-blue' : 'bg-gradient-to-r from-neon-yellow to-neon-orange'
                    }`}
                  />
                </div>
              </div>
            </div>

            {/* Trade Parameters */}
            {tvAgentResult.is_strong_signal && (
              <div className="grid grid-cols-5 gap-4 p-4 bg-dark-800/50 rounded-xl">
                <div>
                  <p className="text-xs text-dark-400 mb-1">Entry</p>
                  <p className="font-mono font-bold">{tvAgentResult.entry_price?.toFixed(5) || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-dark-400 mb-1">Stop Loss</p>
                  <p className="font-mono font-bold text-neon-red">{tvAgentResult.stop_loss?.toFixed(5) || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-dark-400 mb-1">Take Profit</p>
                  <p className="font-mono font-bold text-neon-green">{tvAgentResult.take_profit?.toFixed(5) || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-dark-400 mb-1">Break Even</p>
                  <p className="font-mono font-bold">{tvAgentResult.break_even_trigger?.toFixed(5) || '—'}</p>
                </div>
                <div>
                  <p className="text-xs text-dark-400 mb-1">Trailing SL</p>
                  <p className="font-mono font-bold">{tvAgentResult.trailing_stop_pips ? `${tvAgentResult.trailing_stop_pips} pips` : '—'}</p>
                </div>
              </div>
            )}
          </motion.div>

          {/* Multi-Timeframe Analysis */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Timeframe Consensus */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="card p-6"
            >
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <BarChart3 size={20} className="text-primary-400" />
                Timeframe Analysis
              </h3>
              <div className="space-y-3">
                {Object.entries(tvAgentResult.timeframe_consensus).map(([tf, consensus]) => (
                  <div key={tf} className="flex items-center justify-between p-3 bg-dark-800/50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-primary-400">{tf === 'D' ? 'Daily' : `${tf}m`}</span>
                      <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                        consensus.direction === 'LONG' ? 'bg-neon-green/20 text-neon-green' :
                        consensus.direction === 'SHORT' ? 'bg-neon-red/20 text-neon-red' : 'bg-neon-yellow/20 text-neon-yellow'
                      }`}>
                        {consensus.direction}
                      </span>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm">{consensus.confidence.toFixed(0)}%</p>
                      <p className="text-xs text-dark-400">{consensus.models_agree}/{consensus.total_models} agree</p>
                    </div>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Models Used & Indicators */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="card p-6"
            >
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <Brain size={20} className="text-primary-400" />
                AI Models
              </h3>
              <div className="space-y-2 mb-4">
                {tvAgentResult.models_used.map((model, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 bg-dark-800/50 rounded-lg">
                    <span className="text-lg">{['💬', '💎', '⚡', '🌟', '🔍', '🧪', '🦙', '🌪️'][i] || '🤖'}</span>
                    <span className="text-sm">{model}</span>
                  </div>
                ))}
              </div>
              <h4 className="text-sm font-semibold mb-2 text-dark-400">Indicators Used</h4>
              <div className="flex flex-wrap gap-2">
                {tvAgentResult.indicators_used.map((ind, i) => (
                  <span key={i} className="px-2 py-1 bg-primary-500/20 text-primary-300 rounded text-xs">
                    {ind}
                  </span>
                ))}
              </div>
            </motion.div>

            {/* Key Observations */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="card p-6"
            >
              <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                <CheckCircle size={20} className="text-neon-green" />
                Key Observations
              </h3>
              <ul className="space-y-2">
                {tvAgentResult.key_observations.slice(0, 6).map((obs, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="flex items-start gap-2 text-sm"
                  >
                    <CheckCircle size={14} className="text-neon-green mt-1 flex-shrink-0" />
                    <span className="text-dark-300">{obs}</span>
                  </motion.li>
                ))}
              </ul>
            </motion.div>
          </div>

          {/* Individual Model Results - Grouped by Model */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="card overflow-hidden"
          >
            <div className="p-4 border-b border-dark-700/50">
              <h3 className="text-lg font-semibold">Individual AI Analyses</h3>
              <p className="text-xs text-dark-400">
                {tvAgentResult.models_used.length} models analyzed across {tvAgentResult.timeframes_analyzed.length} timeframes
                ({tvAgentResult.individual_results?.length || 0} total analyses)
              </p>
            </div>
            <div className="divide-y divide-dark-700/30">
              {/* Group results by model */}
              {tvAgentResult.models_used.map((modelName, modelIdx) => {
                const modelResults = tvAgentResult.individual_results?.filter(r => r.model_display_name === modelName) || []
                const icons = ['💬', '💎', '⚡', '🌟', '🔍', '🧪', '🦙', '🌪️']
                const icon = icons[modelIdx] || '🤖'
                const isExpanded = expandedTvResult === modelName

                // Calculate model consensus
                const longVotes = modelResults.filter(r => r.direction === 'LONG').length
                const shortVotes = modelResults.filter(r => r.direction === 'SHORT').length
                const avgConfidence = modelResults.reduce((sum, r) => sum + r.confidence, 0) / modelResults.length || 0
                const modelDirection = longVotes > shortVotes ? 'LONG' : shortVotes > longVotes ? 'SHORT' : 'HOLD'

                return (
                  <motion.div
                    key={modelName}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: modelIdx * 0.05 }}
                    className="p-4 hover:bg-dark-800/30 transition-colors cursor-pointer"
                    onClick={() => setExpandedTvResult(isExpanded ? null : modelName)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-primary-500/20 flex items-center justify-center">
                          <span className="text-2xl">{icon}</span>
                        </div>
                        <div>
                          <p className="font-semibold text-lg">{modelName}</p>
                          <div className="flex items-center gap-2 text-xs text-dark-400">
                            <span>{modelResults[0]?.analysis_style || 'Technical'} analysis</span>
                            <span>•</span>
                            <span>{modelResults.length} timeframe{modelResults.length > 1 ? 's' : ''}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        {/* Timeframe badges */}
                        <div className="hidden md:flex items-center gap-1">
                          {modelResults.map((r, i) => (
                            <div
                              key={i}
                              className={`px-2 py-0.5 rounded text-xs font-mono ${
                                r.direction === 'LONG' ? 'bg-neon-green/20 text-neon-green' :
                                r.direction === 'SHORT' ? 'bg-neon-red/20 text-neon-red' :
                                'bg-neon-yellow/20 text-neon-yellow'
                              }`}
                              title={`${r.timeframe}m: ${r.direction} (${r.confidence}%)`}
                            >
                              {r.timeframe === 'D' ? 'D' : `${r.timeframe}m`}
                            </div>
                          ))}
                        </div>
                        {/* Overall model direction */}
                        <div className={`px-3 py-1.5 rounded-lg text-sm font-bold ${
                          modelDirection === 'LONG' ? 'bg-neon-green/20 text-neon-green' :
                          modelDirection === 'SHORT' ? 'bg-neon-red/20 text-neon-red' :
                          'bg-neon-yellow/20 text-neon-yellow'
                        }`}>
                          {modelDirection}
                        </div>
                        <div className="w-16 text-right">
                          <p className="font-mono font-bold">{avgConfidence.toFixed(0)}%</p>
                          <p className="text-xs text-dark-400">avg</p>
                        </div>
                        <ChevronDown size={16} className={`text-dark-400 transition-transform ${
                          isExpanded ? 'rotate-180' : ''
                        }`} />
                      </div>
                    </div>
                    <AnimatePresence>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: 'auto', opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          className="mt-4 space-y-4"
                        >
                          {/* Per-timeframe details */}
                          {modelResults.map((r, i) => (
                            <div key={i} className="p-4 bg-dark-800/50 rounded-xl border border-dark-700/30">
                              <div className="flex items-center justify-between mb-3">
                                <div className="flex items-center gap-2">
                                  <span className="px-2 py-1 bg-primary-500/30 text-primary-300 rounded font-mono text-sm font-bold">
                                    {r.timeframe === 'D' ? 'Daily' : `${r.timeframe}m`}
                                  </span>
                                  <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                    r.direction === 'LONG' ? 'bg-neon-green/20 text-neon-green' :
                                    r.direction === 'SHORT' ? 'bg-neon-red/20 text-neon-red' :
                                    'bg-neon-yellow/20 text-neon-yellow'
                                  }`}>
                                    {r.direction} • {r.confidence}%
                                  </span>
                                </div>
                                {r.error && (
                                  <div className="flex items-center gap-1 text-neon-red text-xs">
                                    <XCircle size={12} />
                                    <span>Error</span>
                                  </div>
                                )}
                              </div>

                              {/* Key observations */}
                              {r.key_observations && r.key_observations.length > 0 && (
                                <div className="mb-3">
                                  <p className="text-xs text-dark-400 mb-2">Key Observations</p>
                                  <ul className="space-y-1">
                                    {r.key_observations.slice(0, 5).map((obs, j) => (
                                      <li key={j} className="flex items-start gap-2 text-xs text-dark-300">
                                        <CheckCircle size={12} className="text-neon-green mt-0.5 flex-shrink-0" />
                                        <span>{obs}</span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {/* Full reasoning */}
                              {r.reasoning && (
                                <div className="p-3 bg-dark-900/50 rounded-lg">
                                  <p className="text-xs text-dark-400 mb-2">Full Analysis</p>
                                  <p className="text-sm text-dark-300 leading-relaxed whitespace-pre-wrap">{r.reasoning}</p>
                                </div>
                              )}

                              {/* Trade levels if available */}
                              {(r.entry_price || r.stop_loss || r.take_profit.length > 0) && (
                                <div className="mt-3 flex flex-wrap gap-3 text-xs">
                                  {r.entry_price && (
                                    <div>
                                      <span className="text-dark-400">Entry: </span>
                                      <span className="font-mono text-white">{r.entry_price.toFixed(5)}</span>
                                    </div>
                                  )}
                                  {r.stop_loss && (
                                    <div>
                                      <span className="text-dark-400">SL: </span>
                                      <span className="font-mono text-neon-red">{r.stop_loss.toFixed(5)}</span>
                                    </div>
                                  )}
                                  {r.take_profit.length > 0 && (
                                    <div>
                                      <span className="text-dark-400">TP: </span>
                                      <span className="font-mono text-neon-green">{r.take_profit[0].toFixed(5)}</span>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>

          {/* Combined Reasoning - Improved */}
          {tvAgentResult.combined_reasoning && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              className="card overflow-hidden"
            >
              <div className="p-4 border-b border-dark-700/50 bg-gradient-to-r from-primary-500/10 to-transparent">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                  <Eye size={20} className="text-primary-400" />
                  Combined AI Reasoning
                </h3>
                <p className="text-xs text-dark-400 mt-1">Aggregated analysis from all AI models</p>
              </div>
              <div className="p-6 space-y-6">
                {tvAgentResult.combined_reasoning.split('\n\n').map((section, idx) => {
                  // Parse sections that start with **ModelName**
                  // Using [\s\S]* instead of .* with 's' flag for ES5 compatibility
                  const modelMatch = section.match(/^\*\*(.+?)\*\*\s*\((\d+m?)\):\s*([\s\S]+)$/)
                  if (modelMatch) {
                    const [, modelName, timeframe, reasoning] = modelMatch
                    const modelIdx = tvAgentResult.models_used.findIndex(m => m === modelName)
                    const icons = ['💬', '💎', '⚡', '🌟', '🔍', '🧪', '🦙', '🌪️']
                    const icon = icons[modelIdx] || '🤖'

                    return (
                      <div key={idx} className="p-4 bg-dark-800/50 rounded-xl border border-dark-700/50">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="w-10 h-10 rounded-lg bg-primary-500/20 flex items-center justify-center">
                            <span className="text-lg">{icon}</span>
                          </div>
                          <div>
                            <p className="font-semibold">{modelName}</p>
                            <p className="text-xs text-dark-400">{timeframe} timeframe analysis</p>
                          </div>
                        </div>
                        <p className="text-sm text-dark-300 leading-relaxed">{reasoning}</p>
                      </div>
                    )
                  }
                  // Plain text section
                  return section.trim() ? (
                    <p key={idx} className="text-sm text-dark-300 leading-relaxed">{section}</p>
                  ) : null
                })}
              </div>
            </motion.div>
          )}
        </div>
      )}
    </div>
  )
}
