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
  Wifi,
  WifiOff,
  Camera,
  Eye,
} from 'lucide-react'
import { aiApi, type ConsensusResult, type AIVote, type AIServiceStatus } from '@/lib/api'
import { usePriceStream } from '@/hooks/useWebSocket'
import { useChartCapture, type AIAnalysisResult } from '@/hooks/useChartCapture'

// Dynamic import for TradingView chart
const TradingViewWidget = dynamic(
  () => import('@/components/charts/TradingViewWidget'),
  { ssr: false, loading: () => <div className="h-[400px] bg-slate-900 rounded-xl animate-pulse" /> }
)

// Provider styling for AIML API models
const providerStyles: Record<string, { color: string; icon: string; bg: string }> = {
  // The 6 AIML models (matching backend provider names)
  'OpenAI': { color: 'text-green-400', icon: '💬', bg: 'bg-green-500/20' },
  'Google': { color: 'text-blue-400', icon: '💎', bg: 'bg-blue-500/20' },
  'DeepSeek': { color: 'text-cyan-400', icon: '🔍', bg: 'bg-cyan-500/20' },
  'xAI': { color: 'text-red-400', icon: '⚡', bg: 'bg-red-500/20' },
  'Alibaba': { color: 'text-orange-400', icon: '🌟', bg: 'bg-orange-500/20' },
  'Zhipu': { color: 'text-purple-400', icon: '🧪', bg: 'bg-purple-500/20' },
  // Also match lowercase provider keys from backend
  'aiml_openai': { color: 'text-green-400', icon: '💬', bg: 'bg-green-500/20' },
  'aiml_google': { color: 'text-blue-400', icon: '💎', bg: 'bg-blue-500/20' },
  'aiml_deepseek': { color: 'text-cyan-400', icon: '🔍', bg: 'bg-cyan-500/20' },
  'aiml_xai': { color: 'text-red-400', icon: '⚡', bg: 'bg-red-500/20' },
  'aiml_alibaba': { color: 'text-orange-400', icon: '🌟', bg: 'bg-orange-500/20' },
  'aiml_zhipu': { color: 'text-purple-400', icon: '🧪', bg: 'bg-purple-500/20' },
}

// The 6 AI models we use via AIML API (exact model IDs)
const AI_MODELS = [
  { provider: 'OpenAI', model: 'ChatGPT 5.2', icon: '💬' },
  { provider: 'Google', model: 'Gemini 3 Pro Preview', icon: '💎' },
  { provider: 'DeepSeek', model: 'DeepSeek V3.2', icon: '🔍' },
  { provider: 'xAI', model: 'Grok 4.1 Fast', icon: '⚡' },
  { provider: 'Alibaba', model: 'Qwen Max', icon: '🌟' },
  { provider: 'Zhipu', model: 'GLM 4.5 Air', icon: '🧪' },
]

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
  { value: 'quick', label: 'Quick', description: '3 fast models, momentum focus', icon: Zap },
  { value: 'standard', label: 'Standard', description: '6 models, SMC analysis', icon: Target },
  { value: 'premium', label: 'Premium', description: '6 models, full institutional grade', icon: Shield },
]

export default function AIAnalysisPage() {
  const [symbol, setSymbol] = useState('EUR_USD')
  const [timeframe, setTimeframe] = useState('5m')
  const [mode, setMode] = useState<'quick' | 'standard' | 'premium'>('standard')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [result, setResult] = useState<ConsensusResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedVote, setExpandedVote] = useState<string | null>(null)
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

  const selectedSymbol = SYMBOLS.find(s => s.value === symbol)

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

    try {
      const priceToUse = currentPrice || parseFloat(selectedSymbol?.price || '1.0892')
      // Call the real AI analysis API
      const response = await aiApi.analyze(
        symbol,
        priceToUse,
        timeframe,
        mode
      )
      setResult(response)
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
      } else {
        setError(`Analysis failed: ${errorMessage}`)
      }
      setResult(null)
    } finally {
      setIsAnalyzing(false)
    }
  }, [symbol, currentPrice, selectedSymbol?.price, timeframe, mode])

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
        [timeframe]
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
  }, [captureChart, selectedSymbol?.label, symbol, timeframe])

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
                {currentPrice > 0 ? currentPrice.toFixed(symbol.includes('JPY') ? 3 : 5) : selectedSymbol?.price || '—'}
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
                  interval={timeframe === '1m' ? '1' : timeframe === '5m' ? '5' : timeframe === '15m' ? '15' : timeframe === '30m' ? '30' : timeframe === '1h' ? '60' : timeframe === '4h' ? '240' : 'D'}
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
                      <p className="text-sm">Capturing chart & sending to 6 AI models...</p>
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
                {(aiStatus?.providers || AI_MODELS.map(m => ({ name: m.provider, healthy: true, model: m.model }))).map((provider, i) => {
                  const providerName = 'name' in provider ? provider.name : provider.provider
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
