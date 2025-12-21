'use client'

import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Target,
  AlertTriangle,
  Clock,
  DollarSign,
  Percent,
} from 'lucide-react'

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
  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      {/* Stats row */}
      <motion.div
        variants={itemVariants}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
      >
        <StatCard
          label="Account Balance"
          value="$10,000.00"
          change="+2.5%"
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
          subtext="$2,450 margin used"
          icon={Activity}
        />
        <StatCard
          label="Win Rate"
          value="68%"
          subtext="Last 50 trades"
          icon={Target}
        />
      </motion.div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart area */}
        <motion.div variants={itemVariants} className="lg:col-span-2">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">EUR/USD</h2>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-mono font-bold">1.0892</span>
                <span className="text-sm pnl-positive">+0.15%</span>
              </div>
            </div>
            {/* Placeholder for TradingView chart */}
            <div className="bg-dark-800/50 rounded-lg h-[400px] flex items-center justify-center">
              <p className="text-dark-400">TradingView Chart</p>
            </div>
          </div>
        </motion.div>

        {/* AI Reasoning panel */}
        <motion.div variants={itemVariants}>
          <div className="card p-6 h-full">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-8 h-8 rounded-lg bg-neon-purple/20 flex items-center justify-center">
                <span className="text-lg">🤖</span>
              </div>
              <h2 className="text-lg font-semibold">AI Analysis</h2>
            </div>

            <div className="space-y-4">
              {/* Current signal */}
              <div className="p-4 bg-neon-green/10 border border-neon-green/30 rounded-lg">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-neon-green">BUY Signal</span>
                  <span className="text-xs text-dark-400">2 min ago</span>
                </div>
                <p className="text-sm text-dark-300">
                  EUR/USD showing bullish momentum with RSI divergence and support at 1.0850
                </p>
              </div>

              {/* Confidence meter */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-dark-400">Confidence</span>
                  <span className="text-sm font-medium">78%</span>
                </div>
                <div className="h-2 bg-dark-800 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: '78%' }}
                    transition={{ duration: 1, delay: 0.5 }}
                    className="h-full bg-gradient-to-r from-primary-500 to-neon-blue rounded-full"
                  />
                </div>
              </div>

              {/* Key factors */}
              <div>
                <h3 className="text-sm font-medium mb-2">Key Factors</h3>
                <ul className="space-y-2 text-sm text-dark-300">
                  <li className="flex items-center gap-2">
                    <TrendingUp size={14} className="text-neon-green" />
                    RSI divergence detected
                  </li>
                  <li className="flex items-center gap-2">
                    <Activity size={14} className="text-neon-blue" />
                    Strong support level
                  </li>
                  <li className="flex items-center gap-2">
                    <Clock size={14} className="text-neon-yellow" />
                    London session open
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Positions table */}
      <motion.div variants={itemVariants}>
        <div className="card overflow-hidden">
          <div className="p-4 border-b border-dark-700/50">
            <h2 className="text-lg font-semibold">Open Positions</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-dark-800/50">
                  <th className="table-cell table-header text-left">Symbol</th>
                  <th className="table-cell table-header text-left">Side</th>
                  <th className="table-cell table-header text-right">Size</th>
                  <th className="table-cell table-header text-right">Entry</th>
                  <th className="table-cell table-header text-right">Current</th>
                  <th className="table-cell table-header text-right">P&L</th>
                  <th className="table-cell table-header text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                <PositionRow
                  symbol="EUR/USD"
                  side="long"
                  size="10,000"
                  entry="1.0875"
                  current="1.0892"
                  pnl="+$17.00"
                  pnlPercent="+0.16%"
                />
                <PositionRow
                  symbol="GBP/JPY"
                  side="short"
                  size="5,000"
                  entry="188.45"
                  current="188.20"
                  pnl="+$8.50"
                  pnlPercent="+0.13%"
                />
                <PositionRow
                  symbol="US30"
                  side="long"
                  size="1"
                  entry="38,250"
                  current="38,150"
                  pnl="-$100.00"
                  pnlPercent="-0.26%"
                  isNegative
                />
              </tbody>
            </table>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

function StatCard({
  label,
  value,
  change,
  subtext,
  isPositive,
  icon: Icon,
}: {
  label: string
  value: string
  change?: string
  subtext?: string
  isPositive?: boolean
  icon: React.ElementType
}) {
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-label">{label}</p>
          <p className={`stat-value ${isPositive ? 'pnl-positive' : ''}`}>{value}</p>
          {change && (
            <p className={`text-sm ${isPositive ? 'pnl-positive' : 'pnl-negative'}`}>
              {change}
            </p>
          )}
          {subtext && <p className="text-sm text-dark-400">{subtext}</p>}
        </div>
        <div className="p-2 bg-dark-800 rounded-lg">
          <Icon size={20} className="text-dark-400" />
        </div>
      </div>
    </div>
  )
}

function PositionRow({
  symbol,
  side,
  size,
  entry,
  current,
  pnl,
  pnlPercent,
  isNegative,
}: {
  symbol: string
  side: 'long' | 'short'
  size: string
  entry: string
  current: string
  pnl: string
  pnlPercent: string
  isNegative?: boolean
}) {
  return (
    <tr className="table-row">
      <td className="table-cell font-medium">{symbol}</td>
      <td className="table-cell">
        <span
          className={`
            px-2 py-1 rounded text-xs font-medium
            ${side === 'long' ? 'bg-neon-green/20 text-neon-green' : 'bg-neon-red/20 text-neon-red'}
          `}
        >
          {side.toUpperCase()}
        </span>
      </td>
      <td className="table-cell text-right font-mono">{size}</td>
      <td className="table-cell text-right font-mono">{entry}</td>
      <td className="table-cell text-right font-mono">{current}</td>
      <td className="table-cell text-right">
        <div className={isNegative ? 'pnl-negative' : 'pnl-positive'}>
          <span className="font-mono font-medium">{pnl}</span>
          <span className="text-xs ml-1">({pnlPercent})</span>
        </div>
      </td>
      <td className="table-cell text-right">
        <button className="btn-danger text-xs px-3 py-1">Close</button>
      </td>
    </tr>
  )
}
