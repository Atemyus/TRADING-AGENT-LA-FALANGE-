'use client'

import { motion } from 'framer-motion'
import { useState, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  DollarSign,
  Zap,
  BarChart3,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'

import { PerformanceChart } from '@/components/charts/PerformanceChart'
import { AIConsensusPanel } from '@/components/ai/AIConsensusPanel'
import { PriceTicker } from '@/components/trading/PriceTicker'
import { PositionsTable } from '@/components/trading/PositionsTable'
import { OrderHistory } from '@/components/trading/OrderHistory'
import { StatCard } from '@/components/common/StatCard'
import { aiApi, analyticsApi, tradingApi } from '@/lib/api'
import type { AccountSummary, ConsensusResult, PerformanceMetrics } from '@/lib/api'
import { usePriceStream } from '@/hooks/useWebSocket'

// Dynamic import for TradingView chart to avoid SSR issues
const TradingViewWidget = dynamic(
  () => import('@/components/charts/TradingViewWidget'),
  { ssr: false, loading: () => <div className="h-[500px] bg-slate-900 rounded-xl animate-pulse" /> }
)

// Animation variants
const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

export default function DashboardPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('EUR/USD')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [consensusResult, setConsensusResult] = useState<ConsensusResult | null>(null)
  const [account, setAccount] = useState<AccountSummary | null>(null)
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null)
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // WebSocket symbol format
  const wsSymbol = selectedSymbol.replace('/', '_')

  // Use WebSocket for real-time price streaming
  const { prices: streamPrices, isConnected: isPriceConnected } = usePriceStream([wsSymbol])

  // Fetch account data
  const fetchAccountData = useCallback(async () => {
    try {
      const [accountData, performanceData] = await Promise.all([
        analyticsApi.getAccount(),
        analyticsApi.getPerformance(),
      ])
      setAccount(accountData)
      setPerformance(performanceData)
      setError(null)
    } catch (err) {
      console.error('Failed to fetch account data:', err)
      setError('Could not connect to backend. Configure broker in Settings.')
    }
  }, [])

  // Update current price from WebSocket stream
  useEffect(() => {
    if (streamPrices[wsSymbol]) {
      const mid = parseFloat(streamPrices[wsSymbol].mid)
      if (mid > 0) {
        setCurrentPrice(mid)
      }
    }
  }, [streamPrices, wsSymbol])

  // Initial data load
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await fetchAccountData()
      setIsLoading(false)
    }
    loadData()
  }, [fetchAccountData])

  // Run AI analysis - calls real backend
  const handleAnalyze = async () => {
    setIsAnalyzing(true)
    setError(null)

    try {
      // Use current price from WebSocket
      const price = currentPrice || 0

      if (!price || price === 0) {
        setError('Cannot analyze without price data. Waiting for live prices...')
        setIsAnalyzing(false)
        return
      }

      // Call the real AI analysis endpoint
      const result = await aiApi.analyze(
        selectedSymbol,
        price,
        '5m',
        'standard'
      )

      setConsensusResult(result)
    } catch (err) {
      console.error('AI Analysis failed:', err)
      setError(`Analysis failed: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Format currency
  const formatCurrency = (value: string | number | undefined) => {
    if (!value) return '$0.00'
    const num = typeof value === 'string' ? parseFloat(value) : value
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(num)
  }

  // Format percentage
  const formatPercent = (value: string | number | undefined) => {
    if (!value) return '0%'
    const num = typeof value === 'string' ? parseFloat(value) : value
    return `${num.toFixed(1)}%`
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Error Banner */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-neon-yellow/10 border border-neon-yellow/30 rounded-lg p-4 flex items-center gap-3"
        >
          <AlertCircle className="text-neon-yellow" size={20} />
          <span className="text-sm">{error}</span>
          <button
            onClick={fetchAccountData}
            className="ml-auto p-2 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <RefreshCw size={16} />
          </button>
        </motion.div>
      )}

      {/* Price Ticker Row */}
      <motion.div variants={itemVariants}>
        <PriceTicker selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
      </motion.div>

      {/* Stats Row - Real Data */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <StatCard
          label="Account Balance"
          value={account ? formatCurrency(account.balance) : isLoading ? 'Loading...' : '$0.00'}
          change={account ? `${formatCurrency(account.realized_pnl_today)} today` : ''}
          isPositive={account ? parseFloat(account.realized_pnl_today) >= 0 : true}
          icon={DollarSign}
        />
        <StatCard
          label="Unrealized P&L"
          value={account ? formatCurrency(account.unrealized_pnl) : isLoading ? 'Loading...' : '$0.00'}
          change={account ? `${account.open_positions} positions` : ''}
          isPositive={account ? parseFloat(account.unrealized_pnl) >= 0 : true}
          icon={account && parseFloat(account.unrealized_pnl) >= 0 ? TrendingUp : TrendingDown}
        />
        <StatCard
          label="Open Positions"
          value={account ? String(account.open_positions) : isLoading ? '...' : '0'}
          subtext={account ? `${formatCurrency(account.margin_used)} margin` : ''}
          icon={Activity}
        />
        <StatCard
          label="Win Rate"
          value={performance ? formatPercent(performance.win_rate) : isLoading ? '...' : '0%'}
          subtext={performance ? `${performance.total_trades} trades` : ''}
          icon={Target}
        />
      </motion.div>

      {/* TradingView Real-Time Chart - Full Width */}
      <motion.div variants={itemVariants}>
        <TradingViewWidget
          symbol={selectedSymbol}
          interval="60"
          height={500}
          theme="dark"
          allowSymbolChange={true}
          showToolbar={true}
          showDrawingTools={true}
        />
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Performance Chart - Takes 2 columns */}
        <motion.div variants={itemVariants} className="xl:col-span-2">
          <PerformanceChart height={350} />
        </motion.div>

        {/* AI Consensus Panel - Now with real data */}
        <motion.div variants={itemVariants}>
          <AIConsensusPanel
            result={consensusResult}
            isLoading={isAnalyzing}
            onAnalyze={handleAnalyze}
          />
        </motion.div>
      </div>

      {/* Positions & Orders Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Positions Table */}
        <motion.div variants={itemVariants}>
          <PositionsTable
            onClose={(id) => {
              tradingApi.closePosition(id).then(() => {
                fetchAccountData()
              }).catch(console.error)
            }}
            onModify={(id) => console.log('Modify position:', id)}
          />
        </motion.div>

        {/* Order History */}
        <motion.div variants={itemVariants}>
          <OrderHistory />
        </motion.div>
      </div>

      {/* Quick Stats Footer - Real Data */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-purple/20 rounded-lg">
            <Zap size={20} className="text-neon-purple" />
          </div>
          <div>
            <p className="text-xs text-dark-400">Symbol</p>
            <p className="font-mono font-bold">{selectedSymbol}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-blue/20 rounded-lg">
            <BarChart3 size={20} className="text-neon-blue" />
          </div>
          <div>
            <p className="text-xs text-dark-400">Total Trades</p>
            <p className="font-mono font-bold">{performance?.total_trades ?? 0}</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-green/20 rounded-lg">
            <TrendingUp size={20} className="text-neon-green" />
          </div>
          <div>
            <p className="text-xs text-dark-400">Best Trade</p>
            <p className="font-mono font-bold text-neon-green">
              {performance ? formatCurrency(performance.largest_win) : '$0.00'}
            </p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-red/20 rounded-lg">
            <TrendingDown size={20} className="text-neon-red" />
          </div>
          <div>
            <p className="text-xs text-dark-400">Worst Trade</p>
            <p className="font-mono font-bold text-neon-red">
              {performance ? formatCurrency(performance.largest_loss) : '$0.00'}
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
