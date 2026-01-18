'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import dynamic from 'next/dynamic'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  DollarSign,
  Percent,
  Zap,
  BarChart3,
} from 'lucide-react'

import { PerformanceChart } from '@/components/charts/PerformanceChart'
import { AIConsensusPanel } from '@/components/ai/AIConsensusPanel'
import { PriceTicker } from '@/components/trading/PriceTicker'
import { PositionsTable } from '@/components/trading/PositionsTable'
import { OrderHistory } from '@/components/trading/OrderHistory'
import { StatCard } from '@/components/common/StatCard'

// Dynamic import for TradingView chart to avoid SSR issues
const TradingViewChart = dynamic(
  () => import('@/components/charts/TradingViewChart'),
  { ssr: false, loading: () => <div className="h-[400px] bg-slate-900 rounded-xl animate-pulse" /> }
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

  const handleAnalyze = async () => {
    setIsAnalyzing(true)
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 3000))
    setIsAnalyzing(false)
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Price Ticker Row */}
      <motion.div variants={itemVariants}>
        <PriceTicker selectedSymbol={selectedSymbol} onSelect={setSelectedSymbol} />
      </motion.div>

      {/* Stats Row */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <StatCard
          label="Account Balance"
          value="$10,245.50"
          change="+$245.50 today"
          isPositive
          icon={DollarSign}
        />
        <StatCard
          label="Today's P&L"
          value="+$125.50"
          change="+1.26%"
          isPositive
          icon={TrendingUp}
        />
        <StatCard
          label="Open Positions"
          value="3"
          subtext="$4,629 margin used"
          icon={Activity}
        />
        <StatCard
          label="Win Rate"
          value="68%"
          subtext="Last 50 trades"
          icon={Target}
        />
      </motion.div>

      {/* TradingView Candlestick Chart - Full Width */}
      <motion.div variants={itemVariants}>
        <TradingViewChart
          symbol={selectedSymbol}
          timeframe="60"
          height={450}
          showVolume={true}
          showToolbar={true}
        />
      </motion.div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Performance Chart - Takes 2 columns */}
        <motion.div variants={itemVariants} className="xl:col-span-2">
          <PerformanceChart height={350} />
        </motion.div>

        {/* AI Consensus Panel */}
        <motion.div variants={itemVariants}>
          <AIConsensusPanel isLoading={isAnalyzing} onAnalyze={handleAnalyze} />
        </motion.div>
      </div>

      {/* Positions & Orders Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Positions Table */}
        <motion.div variants={itemVariants}>
          <PositionsTable
            onClose={(id) => console.log('Close position:', id)}
            onModify={(id) => console.log('Modify position:', id)}
          />
        </motion.div>

        {/* Order History */}
        <motion.div variants={itemVariants}>
          <OrderHistory />
        </motion.div>
      </div>

      {/* Quick Stats Footer */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-purple/20 rounded-lg">
            <Zap size={20} className="text-neon-purple" />
          </div>
          <div>
            <p className="text-xs text-dark-400">AI Analyses</p>
            <p className="font-mono font-bold">127</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-blue/20 rounded-lg">
            <BarChart3 size={20} className="text-neon-blue" />
          </div>
          <div>
            <p className="text-xs text-dark-400">Total Trades</p>
            <p className="font-mono font-bold">89</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-green/20 rounded-lg">
            <TrendingUp size={20} className="text-neon-green" />
          </div>
          <div>
            <p className="text-xs text-dark-400">Best Trade</p>
            <p className="font-mono font-bold text-neon-green">+$342.00</p>
          </div>
        </div>
        <div className="card p-4 flex items-center gap-3">
          <div className="p-2 bg-neon-red/20 rounded-lg">
            <TrendingDown size={20} className="text-neon-red" />
          </div>
          <div>
            <p className="text-xs text-dark-400">Worst Trade</p>
            <p className="font-mono font-bold text-neon-red">-$128.50</p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}
