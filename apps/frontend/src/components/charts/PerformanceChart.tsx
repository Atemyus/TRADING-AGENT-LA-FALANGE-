'use client'

import { motion } from 'framer-motion'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { TrendingUp, TrendingDown, Calendar } from 'lucide-react'

interface PerformanceData {
  date: string
  pnl: number
  balance: number
}

interface PerformanceChartProps {
  data?: PerformanceData[]
  title?: string
  height?: number
}

export function PerformanceChart({
  data = [],
  title = 'Performance',
  height = 300,
}: PerformanceChartProps) {
  // Show empty state if no data
  if (data.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6"
      >
        <div className="flex items-center gap-3 mb-6">
          <div className="p-2 rounded-lg bg-dark-700">
            <TrendingUp className="w-5 h-5 text-dark-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold">{title}</h3>
            <p className="text-sm text-dark-400">No data available</p>
          </div>
        </div>
        <div className="flex items-center justify-center h-[200px] border border-dashed border-dark-700 rounded-lg">
          <div className="text-center">
            <Calendar className="w-12 h-12 mx-auto text-dark-500 mb-3" />
            <p className="text-dark-400">Connect your broker to see performance data</p>
          </div>
        </div>
      </motion.div>
    )
  }
  const totalPnL = data.reduce((sum, d) => sum + d.pnl, 0)
  const isPositive = totalPnL >= 0
  const trendColor = isPositive ? '#FFD700' : '#EF4444'
  const chartLineColor = '#00F5FF'
  const chartAreaOpacity = isPositive ? 0.28 : 0.2
  const startBalance = data[0]?.balance || 0
  const endBalance = data[data.length - 1]?.balance || 0
  const percentChange = startBalance > 0 ? ((endBalance - startBalance) / startBalance) * 100 : 0

  const gradientId = `pnlGradient-${Math.random().toString(36).substr(2, 9)}`

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card p-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-lg ${isPositive ? 'bg-profit/20' : 'bg-loss/20'}`}>
            {isPositive ? (
              <TrendingUp className="w-5 h-5 text-profit" />
            ) : (
              <TrendingDown className="w-5 h-5 text-loss" />
            )}
          </div>
          <div>
            <h3 className="text-lg font-semibold">{title}</h3>
            <p className="text-sm text-dark-400">Last 30 days</p>
          </div>
        </div>

        <div className="text-right">
          <p className={`text-2xl font-bold font-mono ${isPositive ? 'text-profit' : 'text-loss'}`}>
            {isPositive ? '+' : ''}${totalPnL.toFixed(2)}
          </p>
          <p className={`text-sm ${isPositive ? 'text-profit' : 'text-loss'}`}>
            {isPositive ? '+' : ''}{percentChange.toFixed(2)}%
          </p>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="5%"
                stopColor={chartLineColor}
                stopOpacity={chartAreaOpacity}
              />
              <stop
                offset="95%"
                stopColor={chartLineColor}
                stopOpacity={0}
              />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f3a46" opacity={0.65} />
          <XAxis
            dataKey="date"
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            stroke="#64748b"
            fontSize={12}
            tickLine={false}
            axisLine={false}
            tickFormatter={(value) => `$${value.toLocaleString()}`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f1724',
              border: '1px solid #1f3a46',
              borderRadius: '8px',
              boxShadow: '0 10px 40px rgba(0,0,0,0.5)',
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number, name: string) => [
              `$${value.toFixed(2)}`,
              name === 'balance' ? 'Balance' : 'P&L',
            ]}
          />
          <ReferenceLine y={startBalance} stroke="#ff8c00" strokeDasharray="3 3" />
          <Area
            type="monotone"
            dataKey="balance"
            stroke={chartLineColor}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            animationDuration={1500}
            animationEasing="ease-out"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-4 mt-6 pt-4 border-t border-dark-700/50">
        <div>
          <p className="text-xs text-dark-400">Start Balance</p>
          <p className="font-mono font-medium">${startBalance.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-dark-400">Current Balance</p>
          <p className="font-mono font-medium">${endBalance.toLocaleString()}</p>
        </div>
        <div>
          <p className="text-xs text-dark-400">Best Day</p>
          <p className="font-mono font-medium text-profit">
            +${Math.max(...data.map((d) => d.pnl)).toFixed(2)}
          </p>
        </div>
        <div>
          <p className="text-xs text-dark-400">Worst Day</p>
          <p className="font-mono font-medium text-loss">
            ${Math.min(...data.map((d) => d.pnl)).toFixed(2)}
          </p>
        </div>
      </div>
    </motion.div>
  )
}

export default PerformanceChart
