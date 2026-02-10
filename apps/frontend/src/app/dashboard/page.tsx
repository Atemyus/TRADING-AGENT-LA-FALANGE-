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
import { aiApi, analyticsApi, tradingApi, botApi, brokerAccountsApi } from '@/lib/api'
import type { AccountSummary, ConsensusResult, PerformanceMetrics } from '@/lib/api'
import type { Position } from '@/components/trading/PositionsTable'
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

// Aggregated broker stats type
interface AggregatedBrokerStats {
  totalBalance: number
  totalEquity: number
  totalUnrealizedPnl: number
  totalMarginUsed: number
  totalOpenPositions: number
  brokerCount: number
  currency: string
}

export default function DashboardPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('EUR/USD')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [consensusResult, setConsensusResult] = useState<ConsensusResult | null>(null)
  const [account, setAccount] = useState<AccountSummary | null>(null)
  const [performance, setPerformance] = useState<PerformanceMetrics | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<import('@/components/trading/OrderHistory').Order[]>([])
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [aggregatedStats, setAggregatedStats] = useState<AggregatedBrokerStats | null>(null)

  // WebSocket symbol format
  const wsSymbol = selectedSymbol.replace('/', '_')

  // Use WebSocket for real-time price streaming
  const { prices: streamPrices, isConnected: isPriceConnected } = usePriceStream([wsSymbol])

  // Fetch all dashboard data
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

    // Fetch aggregated account data from all running brokers
    try {
      const aggregatedData = await brokerAccountsApi.getAggregatedAccount()
      if (aggregatedData.broker_count > 0) {
        setAggregatedStats({
          totalBalance: aggregatedData.total_balance,
          totalEquity: aggregatedData.total_equity,
          totalUnrealizedPnl: aggregatedData.total_unrealized_pnl,
          totalMarginUsed: aggregatedData.total_margin_used,
          totalOpenPositions: aggregatedData.total_open_positions,
          brokerCount: aggregatedData.broker_count,
          currency: aggregatedData.currency,
        })
      }
    } catch {
      // Multi-broker aggregation not available
    }

    // Fetch positions from all brokers (multi-broker support)
    try {
      const allPositions: Position[] = []

      // Try to get positions from all multi-broker instances
      try {
        const multiBrokerData = await brokerAccountsApi.getAllPositions()
        if (multiBrokerData.positions && multiBrokerData.positions.length > 0) {
          const mapped = multiBrokerData.positions.map((p) => ({
            id: p.position_id,
            symbol: p.symbol,
            side: p.side.toLowerCase() as 'long' | 'short',
            size: String(p.size),
            entryPrice: String(p.entry_price),
            currentPrice: String(p.current_price),
            pnl: parseFloat(p.unrealized_pnl),
            pnlPercent: parseFloat(p.unrealized_pnl_percent || '0'),
            stopLoss: p.stop_loss ? String(p.stop_loss) : undefined,
            takeProfit: p.take_profit ? String(p.take_profit) : undefined,
            leverage: p.leverage || 1,
            marginUsed: String(p.margin_used),
            openedAt: p.opened_at || '',
            brokerId: p.broker_id,
            brokerName: p.broker_name,
          }))
          allPositions.push(...mapped)
        }
      } catch {
        // Multi-broker not available, fall back to legacy single broker
      }

      // Also try legacy tradingApi for main broker (if not already included)
      if (allPositions.length === 0) {
        try {
          const posData = await tradingApi.getPositions()
          const mapped: Position[] = posData.positions.map((p: import('@/lib/api').Position) => ({
            id: p.position_id,
            symbol: p.symbol,
            side: p.side as 'long' | 'short',
            size: p.size,
            entryPrice: p.entry_price,
            currentPrice: p.current_price,
            pnl: parseFloat(p.unrealized_pnl),
            pnlPercent: parseFloat(p.unrealized_pnl_percent || '0'),
            stopLoss: p.stop_loss || undefined,
            takeProfit: p.take_profit || undefined,
            leverage: p.leverage || 1,
            marginUsed: p.margin_used,
            openedAt: p.opened_at,
          }))
          allPositions.push(...mapped)
        } catch {
          // Legacy broker not available
        }
      }

      setPositions(allPositions)
    } catch (err) {
      console.error('Failed to fetch positions:', err)
    }

    // Fetch trade history from bot as order history
    try {
      const tradeData = await botApi.getTrades(50)
      const mapped: import('@/components/trading/OrderHistory').Order[] = tradeData.trades.map((t) => {
        // Map status: "filled" from broker deals, "open" = pending, closed = filled
        let status: 'filled' | 'pending' | 'cancelled' | 'rejected' = 'filled'
        if (t.status === 'open') {
          status = 'pending'
        } else if (t.status === 'cancelled' || t.status === 'rejected') {
          status = t.status as 'cancelled' | 'rejected'
        } else if (t.status === 'filled' || t.profit_loss !== null) {
          status = 'filled'
        }

        return {
          id: t.id,
          symbol: t.symbol,
          side: (t.direction === 'LONG' || t.direction === 'DEAL_TYPE_BUY' ? 'buy' : 'sell') as 'buy' | 'sell',
          type: 'market' as const,
          size: String(t.units),
          price: String(t.entry_price),
          status,
          pnl: t.profit_loss ?? undefined,
          closedAt: t.exit_timestamp ?? undefined,
          createdAt: t.timestamp,
        }
      })
      setOrders(mapped)
    } catch (err) {
      console.error('Failed to fetch trade history:', err)
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

  // Initial data load + auto-refresh every 15 seconds
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      await fetchAccountData()
      setIsLoading(false)
    }
    loadData()

    // Auto-refresh dashboard data
    const interval = setInterval(() => {
      fetchAccountData()
    }, 15000) // 15 seconds

    return () => clearInterval(interval)
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
          className="bg-primary-500/10 border border-primary-500/30 rounded-2xl p-4 flex items-center gap-3"
        >
          <div className="w-10 h-10 rounded-xl bg-primary-500/20 flex items-center justify-center">
            <AlertCircle className="text-primary-400" size={20} />
          </div>
          <span className="text-sm flex-1">{error}</span>
          <button
            onClick={fetchAccountData}
            className="p-2.5 hover:bg-dark-800 rounded-xl transition-colors border border-transparent hover:border-primary-500/20"
          >
            <RefreshCw size={16} className="text-primary-400" />
          </button>
        </motion.div>
      )}

      {/* Price Ticker Row */}
      <motion.div variants={itemVariants}>
        <PriceTicker selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
      </motion.div>

      {/* Stats Row - Real Data (uses aggregated multi-broker data when available) */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <StatCard
          label={aggregatedStats && aggregatedStats.brokerCount > 1 ? `Total Balance (${aggregatedStats.brokerCount} brokers)` : "Account Balance"}
          value={
            aggregatedStats
              ? formatCurrency(aggregatedStats.totalBalance)
              : account
                ? formatCurrency(account.balance)
                : isLoading ? 'Loading...' : '$0.00'
          }
          change={account ? `${formatCurrency(account.realized_pnl_today)} today` : ''}
          isPositive={account ? parseFloat(account.realized_pnl_today) >= 0 : true}
          icon={DollarSign}
        />
        <StatCard
          label="Unrealized P&L"
          value={
            aggregatedStats
              ? formatCurrency(aggregatedStats.totalUnrealizedPnl)
              : account
                ? formatCurrency(account.unrealized_pnl)
                : isLoading ? 'Loading...' : '$0.00'
          }
          change={
            aggregatedStats
              ? `${aggregatedStats.totalOpenPositions} positions`
              : account
                ? `${account.open_positions} positions`
                : ''
          }
          isPositive={
            aggregatedStats
              ? aggregatedStats.totalUnrealizedPnl >= 0
              : account
                ? parseFloat(account.unrealized_pnl) >= 0
                : true
          }
          icon={
            (aggregatedStats && aggregatedStats.totalUnrealizedPnl >= 0) ||
            (account && parseFloat(account.unrealized_pnl) >= 0)
              ? TrendingUp
              : TrendingDown
          }
        />
        <StatCard
          label="Open Positions"
          value={
            aggregatedStats
              ? String(aggregatedStats.totalOpenPositions)
              : account
                ? String(account.open_positions)
                : isLoading ? '...' : '0'
          }
          subtext={
            aggregatedStats
              ? `${formatCurrency(aggregatedStats.totalMarginUsed)} margin`
              : account
                ? `${formatCurrency(account.margin_used)} margin`
                : ''
          }
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
            positions={positions}
            onClose={(id) => {
              // Find position symbol by id
              const pos = positions.find(p => p.id === id)
              if (pos) {
                tradingApi.closePosition(pos.symbol).then(() => {
                  fetchAccountData()
                }).catch(console.error)
              }
            }}
            onModify={(id) => console.log('Modify position:', id)}
          />
        </motion.div>

        {/* Order History */}
        <motion.div variants={itemVariants}>
          <OrderHistory orders={orders} />
        </motion.div>
      </div>

      {/* Quick Stats Footer - Real Data */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <div className="card-gold p-5 flex items-center gap-4">
          <div className="p-3 bg-imperial-500/20 rounded-xl">
            <Zap size={22} className="text-imperial-400" />
          </div>
          <div>
            <p className="text-xs text-dark-500 uppercase tracking-wider">Symbol</p>
            <p className="font-mono font-bold text-lg text-gradient-gold">{selectedSymbol}</p>
          </div>
        </div>
        <div className="card-gold p-5 flex items-center gap-4">
          <div className="p-3 bg-primary-500/20 rounded-xl">
            <BarChart3 size={22} className="text-primary-400" />
          </div>
          <div>
            <p className="text-xs text-dark-500 uppercase tracking-wider">Total Trades</p>
            <p className="font-mono font-bold text-lg text-gradient-gold">{performance?.total_trades ?? 0}</p>
          </div>
        </div>
        <div className="card-gold p-5 flex items-center gap-4">
          <div className="p-3 bg-profit/20 rounded-xl">
            <TrendingUp size={22} className="text-profit" />
          </div>
          <div>
            <p className="text-xs text-dark-500 uppercase tracking-wider">Best Trade</p>
            <p className="font-mono font-bold text-lg text-profit">
              {performance ? formatCurrency(performance.largest_win) : '$0.00'}
            </p>
          </div>
        </div>
        <div className="card-gold p-5 flex items-center gap-4">
          <div className="p-3 bg-loss/20 rounded-xl">
            <TrendingDown size={22} className="text-loss" />
          </div>
          <div>
            <p className="text-xs text-dark-500 uppercase tracking-wider">Worst Trade</p>
            <p className="font-mono font-bold text-lg text-loss">
              {performance ? formatCurrency(performance.largest_loss) : '$0.00'}
            </p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
