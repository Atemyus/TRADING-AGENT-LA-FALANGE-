'use client'

import { motion } from 'framer-motion'
import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import dynamic from 'next/dynamic'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
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
  Bot,
  Settings,
  Flame,
  Shield,
  Sparkles,
  ArrowRight,
  CircleDashed,
} from 'lucide-react'

import { PerformanceChart } from '@/components/charts/PerformanceChart'
import { AIConsensusPanel } from '@/components/ai/AIConsensusPanel'
import { PriceTicker } from '@/components/trading/PriceTicker'
import { PositionsTable } from '@/components/trading/PositionsTable'
import { OrderHistory } from '@/components/trading/OrderHistory'
import { StatCard } from '@/components/common/StatCard'
import { aiApi, tradingApi, botApi, brokerAccountsApi } from '@/lib/api'
import type { BrokerAccountData, ConsensusResult } from '@/lib/api'
import type { Position } from '@/components/trading/PositionsTable'
import { usePriceStream } from '@/hooks/useWebSocket'
import { useAuth } from '@/contexts/AuthContext'

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

interface WorkspaceSnapshot {
  status: 'running' | 'paused' | 'stopped' | 'disabled' | 'not_initialized'
  balance: number | null
  equity: number | null
  unrealizedPnl: number | null
  marginUsed: number | null
  openPositions: number
  dailyPnl: number | null
  currency: string
}

interface WorkspaceSymbolSelectionEventDetail {
  symbol: string
}

interface PerformancePoint {
  date: string
  pnl: number
  balance: number
}

export default function DashboardPage() {
  const searchParams = useSearchParams()
  const { user } = useAuth()
  const [selectedSymbol, setSelectedSymbol] = useState('EUR/USD')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [consensusResult, setConsensusResult] = useState<ConsensusResult | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [orders, setOrders] = useState<import('@/components/trading/OrderHistory').Order[]>([])
  const [currentPrice, setCurrentPrice] = useState<number>(0)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [aggregatedStats, setAggregatedStats] = useState<AggregatedBrokerStats | null>(null)
  const [brokers, setBrokers] = useState<BrokerAccountData[]>([])
  const [selectedBrokerId, setSelectedBrokerId] = useState<number | null>(null)
  const [workspaceSnapshots, setWorkspaceSnapshots] = useState<Record<number, WorkspaceSnapshot>>({})
  const workspaceSnapshotsRef = useRef<Record<number, WorkspaceSnapshot>>({})
  const [toggleLoadingByBroker, setToggleLoadingByBroker] = useState<Record<number, boolean>>({})

  useEffect(() => {
    workspaceSnapshotsRef.current = workspaceSnapshots
  }, [workspaceSnapshots])

  // WebSocket symbol format
  const wsSymbol = selectedSymbol.replace('/', '_')

  // Use WebSocket for real-time price streaming
  const { prices: streamPrices } = usePriceStream([wsSymbol])

  // Persist selected broker workspace across dashboard sections
  useEffect(() => {
    const brokerIdParam = Number(searchParams.get('brokerId') || '')
    if (!Number.isNaN(brokerIdParam) && brokerIdParam > 0) {
      setSelectedBrokerId(brokerIdParam)
      return
    }

    if (typeof window === 'undefined') return
    const stored = localStorage.getItem('selected_broker_id')
    if (!stored) return
    const parsed = Number(stored)
    if (!Number.isNaN(parsed) && parsed > 0) {
      setSelectedBrokerId(parsed)
    }
  }, [searchParams])

  useEffect(() => {
    if (typeof window === 'undefined') return
    if (selectedBrokerId && selectedBrokerId > 0) {
      localStorage.setItem('selected_broker_id', String(selectedBrokerId))
    } else {
      localStorage.removeItem('selected_broker_id')
    }
    window.dispatchEvent(new Event('selected-broker-changed'))
  }, [selectedBrokerId])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<WorkspaceSymbolSelectionEventDetail>
      const symbol = customEvent?.detail?.symbol
      if (symbol) {
        setSelectedSymbol(symbol)
      }
    }
    window.addEventListener('workspace-symbol-selected', handler)
    return () => {
      window.removeEventListener('workspace-symbol-selected', handler)
    }
  }, [])

  // Fetch all dashboard data
  const fetchAccountData = useCallback(async () => {
    // Load broker workspaces for slot cards
    let brokerList: BrokerAccountData[] = []
    let computedSnapshots: Record<number, WorkspaceSnapshot> = {}
    try {
      brokerList = await brokerAccountsApi.list()
      setBrokers(brokerList)
    } catch {
      setBrokers([])
      brokerList = []
    }

    try {
      const [allStatuses, allAccountInfo] = await Promise.all([
        brokerAccountsApi.getAllStatuses().catch(() => null),
        Promise.all(
          brokerList.map(async (broker) => {
            const info = await brokerAccountsApi.getAccountInfo(broker.id).catch(() => null)
            return { brokerId: broker.id, info }
          }),
        ),
      ])

      const infoMap = new Map<number, (typeof allAccountInfo)[number]['info']>()
      for (const entry of allAccountInfo) {
        infoMap.set(entry.brokerId, entry.info)
      }

      const statusMap = new Map<number, {
        normalizedStatus: WorkspaceSnapshot['status']
        openPositions: number
        dailyPnl: number | null
      }>()
      if (allStatuses?.brokers) {
        for (const status of allStatuses.brokers) {
          const normalizedStatus =
            status.status === 'running' || status.status === 'paused'
              ? status.status
              : status.status === 'not_initialized'
                ? 'not_initialized'
                : 'stopped'
          statusMap.set(status.broker_id, {
            normalizedStatus,
            openPositions: status.statistics?.open_positions || 0,
            dailyPnl: typeof status.statistics?.daily_pnl === 'number'
              ? status.statistics.daily_pnl
              : null,
          })
        }
      }

      const snapshots: Record<number, WorkspaceSnapshot> = {}
      const previousSnapshots = workspaceSnapshotsRef.current
      for (const broker of brokerList) {
        const accountInfo = infoMap.get(broker.id)
        const statusEntry = statusMap.get(broker.id)
        const previousSnapshot = previousSnapshots[broker.id]
        snapshots[broker.id] = {
          status: broker.is_enabled ? (statusEntry?.normalizedStatus || 'stopped') : 'disabled',
          balance: accountInfo?.balance ?? previousSnapshot?.balance ?? null,
          equity: accountInfo?.equity ?? previousSnapshot?.equity ?? null,
          unrealizedPnl: accountInfo?.unrealized_pnl ?? previousSnapshot?.unrealizedPnl ?? null,
          marginUsed: accountInfo?.margin_used ?? previousSnapshot?.marginUsed ?? null,
          openPositions: statusEntry?.openPositions ?? accountInfo?.open_positions ?? previousSnapshot?.openPositions ?? 0,
          dailyPnl:
            statusEntry?.dailyPnl ??
            accountInfo?.realized_pnl_today ??
            accountInfo?.unrealized_pnl ??
            previousSnapshot?.dailyPnl ??
            previousSnapshot?.unrealizedPnl ??
            null,
          currency: accountInfo?.currency || previousSnapshot?.currency || 'USD',
        }
      }
      computedSnapshots = snapshots
      setWorkspaceSnapshots(snapshots)
      workspaceSnapshotsRef.current = snapshots
    } catch {
      setWorkspaceSnapshots({})
      workspaceSnapshotsRef.current = {}
    }

    setError(null)

    if (selectedBrokerId) {
      // Scoped view: one selected broker workspace
      try {
        const brokerAccount = await brokerAccountsApi.getAccountInfo(selectedBrokerId)
        if (brokerAccount.balance !== null) {
          setAggregatedStats({
            totalBalance: brokerAccount.balance || 0,
            totalEquity: brokerAccount.equity || 0,
            totalUnrealizedPnl: brokerAccount.unrealized_pnl || 0,
            totalMarginUsed: brokerAccount.margin_used || 0,
            totalOpenPositions: 0,
            brokerCount: 1,
            currency: brokerAccount.currency || 'USD',
          })
        } else {
          setAggregatedStats(null)
        }
      } catch {
        const fallbackSnapshot = computedSnapshots[selectedBrokerId]
        if (fallbackSnapshot) {
          setAggregatedStats({
            totalBalance: fallbackSnapshot.balance ?? 0,
            totalEquity: fallbackSnapshot.equity ?? 0,
            totalUnrealizedPnl: fallbackSnapshot.unrealizedPnl ?? 0,
            totalMarginUsed: fallbackSnapshot.marginUsed ?? 0,
            totalOpenPositions: fallbackSnapshot.openPositions || 0,
            brokerCount: 1,
            currency: fallbackSnapshot.currency || 'USD',
          })
        } else {
          setAggregatedStats(null)
        }
      }
    } else {
      // Global view: aggregate all available workspaces
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
        } else {
          setAggregatedStats(null)
        }
      } catch {
        setAggregatedStats(null)
      }
    }

    // Fetch positions (selected workspace or global)
    try {
      const allPositions: Position[] = []
      let scopedOpenPositions = 0

      if (selectedBrokerId) {
        try {
          const scopedData = await brokerAccountsApi.getPositions(selectedBrokerId)
          if (scopedData.positions && scopedData.positions.length > 0) {
            const mapped = scopedData.positions.map((p) => ({
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
            scopedOpenPositions = mapped.length
          }
        } catch {
          // Scoped broker may not be running
        }
      } else {
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
      }

      setPositions(allPositions)
      if (selectedBrokerId) {
        setAggregatedStats((prev) => (
          prev
            ? { ...prev, totalOpenPositions: scopedOpenPositions }
            : prev
        ))
      }
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
          brokerId: t.broker_id,
          brokerName: t.broker_name,
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
  }, [selectedBrokerId])

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

  const handleToggleWorkspace = async (brokerId: number) => {
    setToggleLoadingByBroker((prev) => ({ ...prev, [brokerId]: true }))
    setError(null)
    try {
      await brokerAccountsApi.toggle(brokerId)
      await fetchAccountData()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle workspace')
    } finally {
      setToggleLoadingByBroker((prev) => {
        const next = { ...prev }
        delete next[brokerId]
        return next
      })
    }
  }

  // Format currency
  const formatCurrency = (value: string | number | undefined, currency = 'USD') => {
    if (!value) return '$0.00'
    const num = typeof value === 'string' ? parseFloat(value) : value
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
    }).format(num)
  }

  const formatCurrencyNullable = (value: number | null | undefined, currency = 'USD') => {
    if (value === null || value === undefined || Number.isNaN(value)) return '--'
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  // Format percentage
  const formatPercent = (value: string | number | undefined) => {
    if (!value) return '0%'
    const num = typeof value === 'string' ? parseFloat(value) : value
    return `${num.toFixed(1)}%`
  }

  useEffect(() => {
    if (!selectedBrokerId) return
    if (brokers.length > 0 && !brokers.some((b) => b.id === selectedBrokerId)) {
      setSelectedBrokerId(null)
    }
  }, [brokers, selectedBrokerId])

  const selectedBroker = brokers.find((b) => b.id === selectedBrokerId) || null
  const selectedSnapshot = selectedBrokerId ? workspaceSnapshots[selectedBrokerId] : null
  const selectedSlotDisabled = Boolean(
    selectedBrokerId &&
    (
      selectedBroker ? !selectedBroker.is_enabled : selectedSnapshot?.status === 'disabled'
    ),
  )

  useEffect(() => {
    if (typeof window === 'undefined') return

    if (!selectedBrokerId) {
      localStorage.removeItem('selected_broker_snapshot')
      window.dispatchEvent(new Event('selected-broker-snapshot-changed'))
      return
    }

    const snapshot = workspaceSnapshots[selectedBrokerId]
    if (!snapshot) {
      localStorage.removeItem('selected_broker_snapshot')
      window.dispatchEvent(new Event('selected-broker-snapshot-changed'))
      return
    }

    localStorage.setItem(
      'selected_broker_snapshot',
      JSON.stringify({
        brokerId: selectedBrokerId,
        isDisabled: selectedBroker ? !selectedBroker.is_enabled : snapshot.status === 'disabled',
        balance: snapshot.balance ?? null,
        todayPnl: snapshot.dailyPnl ?? snapshot.unrealizedPnl ?? null,
      }),
    )
    window.dispatchEvent(new Event('selected-broker-snapshot-changed'))
  }, [selectedBrokerId, workspaceSnapshots, selectedBroker])

  const licenseSlots = Math.max(1, user?.license_broker_slots || 1)
  const totalSlots = user?.is_superuser
    ? (user?.license_broker_slots ? licenseSlots : Math.max(1, brokers.length))
    : licenseSlots
  const workspaceGridCols = totalSlots <= 1
    ? 'grid-cols-1'
    : 'grid-cols-1 2xl:grid-cols-2'
  const brokersBySlot = new Map<number, BrokerAccountData>()
  for (const broker of brokers) {
    if (broker.slot_index && broker.slot_index >= 1 && broker.slot_index <= totalSlots) {
      brokersBySlot.set(broker.slot_index, broker)
    }
  }
  let fallbackSlot = 1
  for (const broker of brokers.filter((b) => !b.slot_index)) {
    while (fallbackSlot <= totalSlots && brokersBySlot.has(fallbackSlot)) {
      fallbackSlot += 1
    }
    if (fallbackSlot <= totalSlots) {
      brokersBySlot.set(fallbackSlot, broker)
      fallbackSlot += 1
    }
  }

  const formatSigned = (value: number | null | undefined, currency = 'USD') => {
    if (value === null || value === undefined) return '--'
    const signed = value > 0 ? `+${value}` : `${value}`
    const abs = Number.parseFloat(signed)
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      maximumFractionDigits: 2,
    }).format(abs)
  }

  const scopedCurrency = selectedSnapshot?.currency || aggregatedStats?.currency || 'USD'
  const baseScopedBalance = selectedSnapshot?.balance ?? aggregatedStats?.totalBalance ?? null
  const baseScopedUnrealizedPnl = selectedSnapshot?.unrealizedPnl ?? aggregatedStats?.totalUnrealizedPnl ?? null
  const baseScopedMarginUsed = selectedSnapshot?.marginUsed ?? aggregatedStats?.totalMarginUsed ?? null
  const baseScopedOpenPositions = selectedSnapshot?.openPositions ?? aggregatedStats?.totalOpenPositions ?? 0
  const baseScopedTodayPnl = selectedSnapshot?.dailyPnl ?? selectedSnapshot?.unrealizedPnl ?? aggregatedStats?.totalUnrealizedPnl ?? null

  const scopedBalance = selectedSlotDisabled ? null : baseScopedBalance
  const scopedUnrealizedPnl = selectedSlotDisabled ? null : baseScopedUnrealizedPnl
  const scopedMarginUsed = selectedSlotDisabled ? null : baseScopedMarginUsed
  const scopedOpenPositions = selectedSlotDisabled ? null : baseScopedOpenPositions
  const scopedTodayPnl = selectedSlotDisabled ? null : baseScopedTodayPnl

  const scopedOrders = useMemo(() => {
    if (selectedSlotDisabled) return []
    if (!selectedBrokerId) return orders
    return orders.filter((order) => order.brokerId === selectedBrokerId)
  }, [orders, selectedBrokerId, selectedSlotDisabled])

  const performanceData = useMemo<PerformancePoint[]>(() => {
    const groupedByDay = new Map<string, number>()

    for (const order of scopedOrders) {
      if (typeof order.pnl !== 'number' || Number.isNaN(order.pnl)) continue
      const reference = order.closedAt || order.createdAt
      const date = reference.slice(0, 10)
      groupedByDay.set(date, (groupedByDay.get(date) || 0) + order.pnl)
    }

    const sortedDays = Array.from(groupedByDay.entries())
      .map(([date, pnl]) => ({ date, pnl }))
      .sort((a, b) => a.date.localeCompare(b.date))

    if (sortedDays.length === 0) {
      if (typeof baseScopedBalance !== 'number' || Number.isNaN(baseScopedBalance)) return []
      return [
        {
          date: new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
          pnl: 0,
          balance: baseScopedBalance,
        },
      ]
    }

    const totalRealizedPnl = sortedDays.reduce((sum, point) => sum + point.pnl, 0)
    let rollingBalance = typeof baseScopedBalance === 'number'
      ? baseScopedBalance - totalRealizedPnl
      : 0

    return sortedDays.map((point) => {
      rollingBalance += point.pnl
      return {
        date: new Date(`${point.date}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        pnl: point.pnl,
        balance: rollingBalance,
      }
    })
  }, [scopedOrders, baseScopedBalance])

  const scopedTradeStats = useMemo(() => {
    const filled = scopedOrders.filter((order) => order.status === 'filled' && typeof order.pnl === 'number')
    const totalTrades = filled.length
    const winners = filled.filter((order) => (order.pnl || 0) > 0).length
    const winRate = totalTrades > 0 ? (winners / totalTrades) * 100 : 0
    const bestTrade = totalTrades > 0 ? Math.max(...filled.map((order) => order.pnl || 0)) : null
    const worstTrade = totalTrades > 0 ? Math.min(...filled.map((order) => order.pnl || 0)) : null
    return { totalTrades, winRate, bestTrade, worstTrade }
  }, [scopedOrders])

  const accountBalanceValue = isLoading && !selectedSlotDisabled && scopedBalance === null
    ? 'Loading...'
    : formatCurrencyNullable(scopedBalance, scopedCurrency)
  const accountBalanceChange = selectedSlotDisabled
    ? '--'
    : scopedTodayPnl !== null
      ? `${scopedTodayPnl >= 0 ? '+' : ''}${formatCurrency(scopedTodayPnl, scopedCurrency)} today`
      : 'Today P&L unavailable'
  const unrealizedValue = isLoading && !selectedSlotDisabled && scopedUnrealizedPnl === null
    ? 'Loading...'
    : formatCurrencyNullable(scopedUnrealizedPnl, scopedCurrency)
  const unrealizedChange = scopedOpenPositions === null ? '--' : `${scopedOpenPositions} positions`
  const openPositionsValue = scopedOpenPositions === null ? '--' : String(scopedOpenPositions)
  const openPositionsSubtext = selectedSlotDisabled
    ? '--'
    : scopedMarginUsed !== null
      ? `${formatCurrency(scopedMarginUsed, scopedCurrency)} margin`
      : 'Margin unavailable'
  const winRateValue = selectedSlotDisabled
    ? '--'
    : scopedTradeStats.totalTrades > 0
      ? `${scopedTradeStats.winRate.toFixed(1)}%`
      : isLoading
        ? '...'
        : '0%'
  const winRateSubtext = selectedSlotDisabled
    ? '--'
    : `${scopedTradeStats.totalTrades} trades`
  const footerTotalTrades = selectedSlotDisabled ? '--' : String(scopedTradeStats.totalTrades)
  const footerBestTrade = selectedSlotDisabled
    ? '--'
    : scopedTradeStats.bestTrade !== null
      ? formatCurrency(scopedTradeStats.bestTrade, scopedCurrency)
      : '$0.00'
  const footerWorstTrade = selectedSlotDisabled
    ? '--'
    : scopedTradeStats.worstTrade !== null
      ? formatCurrency(scopedTradeStats.worstTrade, scopedCurrency)
      : '$0.00'

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6 prometheus-page-shell prometheus-dashboard-shell"
    >
      {/* Asset Price Cards (top priority) */}
      <motion.div variants={itemVariants}>
        <PriceTicker selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
      </motion.div>

      <motion.div variants={itemVariants} className="prometheus-hero-card p-6 md:p-7">
        <div className="relative z-10 flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="prometheus-chip">
                <Flame size={12} />
                Command Center
              </span>
              <span className="prometheus-chip prometheus-chip-imperial">
                <Shield size={12} />
                {user?.is_superuser ? 'Superuser Access' : 'Licensed Access'}
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-semibold text-gradient-falange">Broker Workspaces</h1>
            <p className="text-sm md:text-base text-dark-300 mt-2 max-w-2xl">
              Switch between broker slots, monitor real-time metrics, and drive execution from one control surface.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 min-w-[260px]">
            <div className="prometheus-panel-surface p-3">
              <p className="text-xs uppercase tracking-wider text-dark-500">Total Slots</p>
              <p className="text-lg font-semibold text-primary-300 mt-1">{totalSlots}</p>
            </div>
            <div className="prometheus-panel-surface p-3">
              <p className="text-xs uppercase tracking-wider text-dark-500">Active Brokers</p>
              <p className="text-lg font-semibold text-imperial-300 mt-1">{brokers.length}</p>
            </div>
            <div className="prometheus-panel-surface p-3 col-span-2">
              <p className="text-xs uppercase tracking-wider text-dark-500">Focus</p>
              <p className="text-sm font-medium text-dark-100 mt-1 inline-flex items-center gap-2">
                <Sparkles size={14} className="text-primary-400" />
                {selectedBroker ? selectedBroker.name : 'Cross-account aggregate view'}
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wider text-dark-500">Workspace Panels</p>
            <h3 className="text-lg font-semibold text-dark-100">
              {selectedBroker ? `${selectedBroker.name} performance view` : 'Parallel broker performance'}
            </h3>
            <p className="text-xs text-dark-400 mt-1">
              Slots used: {brokers.length}/{totalSlots}. Click a panel to open its dedicated command center context.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setSelectedBrokerId(null)}
              className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                selectedBrokerId === null
                  ? 'bg-primary-500/20 border-primary-500/40 text-primary-300'
                  : 'bg-dark-900/60 border-dark-700 text-dark-300 hover:border-dark-500'
              }`}
            >
              All Accounts
            </button>
            <Link
              href={selectedBrokerId ? `/dashboard/settings?brokerId=${selectedBrokerId}` : '/dashboard/settings'}
              className="px-3 py-1.5 rounded-lg text-xs border bg-dark-900/60 border-dark-700 text-dark-300 hover:border-dark-500 inline-flex items-center gap-1.5"
            >
              <Settings size={14} />
              Configure
            </Link>
            <Link
              href={selectedBrokerId ? `/dashboard/bot?brokerId=${selectedBrokerId}` : '/dashboard/bot'}
              className="px-3 py-1.5 rounded-lg text-xs border bg-dark-900/60 border-dark-700 text-dark-300 hover:border-dark-500 inline-flex items-center gap-1.5"
            >
              <Bot size={14} />
              Auto Bot
            </Link>
          </div>
        </div>
        <div className={`grid ${workspaceGridCols} gap-4 w-full`}>
          {Array.from({ length: totalSlots }, (_, idx) => {
            const slot = idx + 1
            const broker = brokersBySlot.get(slot)
            if (!broker) {
              return (
                <div key={`empty-${slot}`} className="workspace-panel-card workspace-panel-empty w-full">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Slot {slot}</p>
                      <h4 className="text-xl font-semibold text-dark-300 mb-1">Empty Workspace</h4>
                      <p className="text-sm text-dark-500">Assign a broker in Settings to activate this panel.</p>
                    </div>
                    <CircleDashed size={20} className="text-dark-500" />
                  </div>
                  <Link href="/dashboard/settings" className="mt-6 inline-flex items-center gap-2 text-sm text-primary-300 hover:text-primary-200">
                    Configure broker
                    <ArrowRight size={15} />
                  </Link>
                </div>
              )
            }

            const snapshot = workspaceSnapshots[broker.id]
            const isSelected = selectedBrokerId === broker.id
            const isWorkspaceDisabled = !broker.is_enabled
            return (
              <div
                key={broker.id}
                role="button"
                tabIndex={0}
                onClick={() => setSelectedBrokerId(broker.id)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    setSelectedBrokerId(broker.id)
                  }
                }}
                className={`workspace-panel-card w-full text-left cursor-pointer ${isSelected ? 'workspace-panel-card-active' : ''}`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs uppercase tracking-wider text-dark-500">Slot {slot}</span>
                    <span className={`prometheus-chip ${
                      snapshot?.status === 'running'
                        ? ''
                        : snapshot?.status === 'paused'
                          ? 'prometheus-chip-imperial'
                          : 'prometheus-chip-soft'
                    }`}>
                      {snapshot?.status || (broker.is_enabled ? 'stopped' : 'disabled')}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[11px] px-2 py-0.5 rounded-full ${broker.is_enabled ? 'bg-profit/20 text-profit' : 'bg-dark-700 text-dark-400'}`}>
                      {broker.is_enabled ? 'Enabled' : 'Disabled'}
                    </span>
                    <button
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation()
                        void handleToggleWorkspace(broker.id)
                      }}
                      disabled={!!toggleLoadingByBroker[broker.id]}
                      className={`text-[11px] px-2 py-0.5 rounded-full border inline-flex items-center gap-1 ${
                        broker.is_enabled
                          ? 'border-primary-500/40 text-primary-300 bg-primary-500/10'
                          : 'border-profit/30 text-profit bg-profit/10'
                      } disabled:opacity-60`}
                    >
                      {toggleLoadingByBroker[broker.id] ? (
                        <>
                          <RefreshCw size={11} className="animate-spin" />
                          Saving
                        </>
                      ) : (
                        broker.is_enabled ? 'Disable Slot' : 'Enable Slot'
                      )}
                    </button>
                  </div>
                </div>

                <h4 className="text-2xl font-semibold text-white mb-2">{broker.name}</h4>
                <p className="text-xs text-dark-400 mb-4">{broker.broker_type.toUpperCase()} adapter</p>

                <div className="grid grid-cols-2 gap-3">
                  <div className="workspace-metric-block">
                    <p className="workspace-metric-label">Balance</p>
                    <p className="workspace-metric-value">
                      {isWorkspaceDisabled ? '--' : formatSigned(snapshot?.balance, snapshot?.currency || 'USD')}
                    </p>
                  </div>
                  <div className="workspace-metric-block">
                    <p className="workspace-metric-label">Equity</p>
                    <p className="workspace-metric-value">
                      {isWorkspaceDisabled ? '--' : formatSigned(snapshot?.equity, snapshot?.currency || 'USD')}
                    </p>
                  </div>
                  <div className="workspace-metric-block">
                    <p className="workspace-metric-label">Live P&L</p>
                    <p className={`workspace-metric-value ${
                      isWorkspaceDisabled
                        ? 'text-dark-300'
                        : (snapshot?.unrealizedPnl || 0) > 0
                          ? 'text-profit'
                          : (snapshot?.unrealizedPnl || 0) < 0
                            ? 'text-loss'
                            : 'text-dark-200'
                    }`}>
                      {isWorkspaceDisabled ? '--' : formatSigned(snapshot?.unrealizedPnl, snapshot?.currency || 'USD')}
                    </p>
                  </div>
                  <div className="workspace-metric-block">
                    <p className="workspace-metric-label">Margin Used</p>
                    <p className="workspace-metric-value">
                      {isWorkspaceDisabled ? '--' : formatSigned(snapshot?.marginUsed, snapshot?.currency || 'USD')}
                    </p>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2 mt-4">
                  {(broker.symbols || []).slice(0, 5).map((symbol) => (
                    <button
                      key={symbol}
                      type="button"
                      onClick={(event) => {
                        event.stopPropagation()
                        setSelectedSymbol(symbol)
                        if (typeof window !== 'undefined') {
                          window.dispatchEvent(
                            new CustomEvent<WorkspaceSymbolSelectionEventDetail>('workspace-symbol-selected', {
                              detail: { symbol },
                            }),
                          )
                        }
                      }}
                      className={`workspace-symbol-chip ${selectedSymbol === symbol ? 'workspace-symbol-chip-active' : 'workspace-symbol-chip-soft'}`}
                    >
                      {symbol}
                    </button>
                  ))}
                </div>

                <div className="mt-5 inline-flex items-center gap-2 text-sm text-primary-300">
                  Open scoped command view
                  <ArrowRight size={14} />
                </div>
              </div>
            )
          })}
        </div>
      </motion.div>

      {!selectedBrokerId && (
        <motion.div
          variants={itemVariants}
          className="prometheus-panel-surface p-6 text-center"
        >
          <p className="text-sm text-dark-300">
            Aggregate view active. Select a workspace card to scope metrics to one broker.
          </p>
        </motion.div>
      )}

      <>
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

          {/* Stats Row - Real Data (scoped to selected workspace) */}
          <motion.div
            variants={itemVariants}
            className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
          >
            <StatCard
              label="Account Balance"
              value={accountBalanceValue}
              change={accountBalanceChange}
              isPositive={selectedSlotDisabled ? undefined : (scopedTodayPnl !== null ? scopedTodayPnl >= 0 : undefined)}
              icon={DollarSign}
            />
            <StatCard
              label="Unrealized P&L"
              value={unrealizedValue}
              change={unrealizedChange}
              isPositive={selectedSlotDisabled ? undefined : (scopedUnrealizedPnl !== null ? scopedUnrealizedPnl >= 0 : undefined)}
              icon={
                scopedUnrealizedPnl === null || scopedUnrealizedPnl >= 0
                  ? TrendingUp
                  : TrendingDown
              }
            />
            <StatCard
              label="Open Positions"
              value={openPositionsValue}
              subtext={openPositionsSubtext}
              icon={Activity}
            />
            <StatCard
              label="Win Rate"
              value={winRateValue}
              subtext={winRateSubtext}
              icon={Target}
            />
          </motion.div>

          {/* TradingView Real-Time Chart - Full Width */}
          <motion.div variants={itemVariants}>
            <div className="prometheus-panel-surface p-3">
              <TradingViewWidget
                symbol={selectedSymbol}
                interval="60"
                height={500}
                theme="dark"
                allowSymbolChange={true}
                showToolbar={true}
                showDrawingTools={true}
              />
            </div>
          </motion.div>

          {/* Main Content Grid */}
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Performance Chart - Takes 2 columns */}
            <motion.div variants={itemVariants} className="xl:col-span-2">
              <PerformanceChart
                data={performanceData}
                title={selectedBroker ? `${selectedBroker.name} Performance` : 'Portfolio Performance'}
                height={350}
                isDisabled={selectedSlotDisabled}
              />
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
                  const pos = positions.find((p) => p.id === id)
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
              <OrderHistory orders={scopedOrders} isDisabled={selectedSlotDisabled} />
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
                <p className="font-mono font-bold text-lg text-gradient-gold">{footerTotalTrades}</p>
              </div>
            </div>
            <div className="card-gold p-5 flex items-center gap-4">
              <div className="p-3 bg-profit/20 rounded-xl">
                <TrendingUp size={22} className="text-profit" />
              </div>
              <div>
                <p className="text-xs text-dark-500 uppercase tracking-wider">Best Trade</p>
                <p className="font-mono font-bold text-lg text-profit">
                  {footerBestTrade}
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
                  {footerWorstTrade}
                </p>
              </div>
            </div>
          </motion.div>
      </>
    </motion.div>
  )
}
