'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'
import {
  CheckCircle,
  XCircle,
  Clock,
  TrendingUp,
  TrendingDown,
  Filter,
  Download,
} from 'lucide-react'

export interface Order {
  id: string
  symbol: string
  side: 'buy' | 'sell'
  type: 'market' | 'limit' | 'stop'
  size: string
  price: string
  status: 'filled' | 'cancelled' | 'pending' | 'rejected'
  pnl?: number
  closedAt?: string
  createdAt: string
}

interface OrderHistoryProps {
  orders?: Order[]
  isLoading?: boolean
}

// Demo orders
const demoOrders: Order[] = [
  {
    id: '1',
    symbol: 'EUR/USD',
    side: 'buy',
    type: 'market',
    size: '10,000',
    price: '1.0875',
    status: 'filled',
    pnl: 45.50,
    closedAt: '10:30 AM',
    createdAt: 'Today',
  },
  {
    id: '2',
    symbol: 'GBP/USD',
    side: 'sell',
    type: 'limit',
    size: '5,000',
    price: '1.2680',
    status: 'filled',
    pnl: -22.30,
    closedAt: '09:15 AM',
    createdAt: 'Today',
  },
  {
    id: '3',
    symbol: 'USD/JPY',
    side: 'buy',
    type: 'market',
    size: '20,000',
    price: '149.50',
    status: 'filled',
    pnl: 78.00,
    closedAt: 'Yesterday',
    createdAt: 'Yesterday',
  },
  {
    id: '4',
    symbol: 'XAU/USD',
    side: 'buy',
    type: 'stop',
    size: '1',
    price: '2050.00',
    status: 'cancelled',
    createdAt: 'Yesterday',
  },
  {
    id: '5',
    symbol: 'US30',
    side: 'sell',
    type: 'market',
    size: '2',
    price: '38,200',
    status: 'filled',
    pnl: 150.00,
    closedAt: '2 days ago',
    createdAt: '2 days ago',
  },
  {
    id: '6',
    symbol: 'NAS100',
    side: 'buy',
    type: 'limit',
    size: '1',
    price: '17,400',
    status: 'pending',
    createdAt: '2 days ago',
  },
]

const statusConfig = {
  filled: { icon: CheckCircle, color: 'text-neon-green', bg: 'bg-neon-green/20' },
  cancelled: { icon: XCircle, color: 'text-dark-400', bg: 'bg-dark-700' },
  pending: { icon: Clock, color: 'text-neon-yellow', bg: 'bg-neon-yellow/20' },
  rejected: { icon: XCircle, color: 'text-neon-red', bg: 'bg-neon-red/20' },
}

export function OrderHistory({ orders = demoOrders, isLoading = false }: OrderHistoryProps) {
  const [filter, setFilter] = useState<'all' | 'filled' | 'pending' | 'cancelled'>('all')

  const filteredOrders = filter === 'all' ? orders : orders.filter((o) => o.status === filter)

  // Calculate stats
  const filledOrders = orders.filter((o) => o.status === 'filled')
  const totalPnL = filledOrders.reduce((sum, o) => sum + (o.pnl || 0), 0)
  const winningTrades = filledOrders.filter((o) => (o.pnl || 0) > 0).length
  const winRate = filledOrders.length > 0 ? (winningTrades / filledOrders.length) * 100 : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-dark-700/50">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">Order History</h2>
            <p className="text-sm text-dark-400">{orders.length} total orders</p>
          </div>
          <button className="flex items-center gap-2 px-3 py-1.5 bg-dark-800 hover:bg-dark-700 rounded-lg text-sm transition-colors">
            <Download size={14} />
            Export
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className="p-3 bg-dark-800/50 rounded-lg">
            <p className="text-xs text-dark-400">Total P&L</p>
            <p className={`font-mono font-bold ${totalPnL >= 0 ? 'text-neon-green' : 'text-neon-red'}`}>
              {totalPnL >= 0 ? '+' : ''}${totalPnL.toFixed(2)}
            </p>
          </div>
          <div className="p-3 bg-dark-800/50 rounded-lg">
            <p className="text-xs text-dark-400">Win Rate</p>
            <p className="font-mono font-bold">{winRate.toFixed(1)}%</p>
          </div>
          <div className="p-3 bg-dark-800/50 rounded-lg">
            <p className="text-xs text-dark-400">Trades</p>
            <p className="font-mono font-bold">{filledOrders.length}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-2">
          {(['all', 'filled', 'pending', 'cancelled'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                filter === f
                  ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                  : 'bg-dark-800 text-dark-400 hover:text-dark-200'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Orders List */}
      <div className="divide-y divide-dark-700/30 max-h-[400px] overflow-y-auto">
        {filteredOrders.length === 0 ? (
          <div className="p-8 text-center text-dark-400">
            No orders found
          </div>
        ) : (
          filteredOrders.map((order, index) => {
            const StatusIcon = statusConfig[order.status].icon
            const isPositive = (order.pnl || 0) >= 0

            return (
              <motion.div
                key={order.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.03 }}
                className="p-4 hover:bg-dark-800/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  {/* Left: Symbol & Side */}
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg ${order.side === 'buy' ? 'bg-neon-green/20' : 'bg-neon-red/20'}`}>
                      {order.side === 'buy' ? (
                        <TrendingUp size={16} className="text-neon-green" />
                      ) : (
                        <TrendingDown size={16} className="text-neon-red" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{order.symbol}</span>
                        <span className="text-xs px-1.5 py-0.5 bg-dark-700 rounded text-dark-400">
                          {order.type}
                        </span>
                      </div>
                      <p className="text-xs text-dark-400">
                        {order.size} @ {order.price}
                      </p>
                    </div>
                  </div>

                  {/* Right: Status & P&L */}
                  <div className="flex items-center gap-4">
                    {order.pnl !== undefined && (
                      <div className={`text-right ${isPositive ? 'text-neon-green' : 'text-neon-red'}`}>
                        <p className="font-mono font-semibold">
                          {isPositive ? '+' : ''}${order.pnl.toFixed(2)}
                        </p>
                      </div>
                    )}
                    <div className={`flex items-center gap-1.5 px-2 py-1 rounded ${statusConfig[order.status].bg}`}>
                      <StatusIcon size={12} className={statusConfig[order.status].color} />
                      <span className={`text-xs font-medium ${statusConfig[order.status].color}`}>
                        {order.status}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Timestamp */}
                <div className="mt-2 text-xs text-dark-500">
                  {order.closedAt ? `Closed ${order.closedAt}` : `Created ${order.createdAt}`}
                </div>
              </motion.div>
            )
          })
        )}
      </div>
    </motion.div>
  )
}

export default OrderHistory
