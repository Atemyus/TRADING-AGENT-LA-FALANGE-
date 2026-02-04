'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import {
  TrendingUp,
  TrendingDown,
  X,
  Edit2,
  MoreVertical,
  AlertTriangle,
} from 'lucide-react'

export interface Position {
  id: string
  symbol: string
  side: 'long' | 'short'
  size: string
  entryPrice: string
  currentPrice: string
  pnl: number
  pnlPercent: number
  stopLoss?: string
  takeProfit?: string
  leverage: number
  marginUsed: string
  openedAt: string
  // Multi-broker support
  brokerId?: number
  brokerName?: string
}

interface PositionsTableProps {
  positions?: Position[]
  onClose?: (id: string) => void
  onModify?: (id: string) => void
  isLoading?: boolean
}

function PositionRow({ position, onClose, onModify }: { position: Position; onClose?: () => void; onModify?: () => void }) {
  const [showActions, setShowActions] = useState(false)
  const isPositive = position.pnl >= 0

  return (
    <motion.tr
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className="border-b border-dark-700/30 hover:bg-dark-800/30 transition-colors"
    >
      {/* Symbol */}
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="font-semibold">{position.symbol}</span>
          <span className={`
            text-xs px-2 py-0.5 rounded font-medium
            ${position.side === 'long' ? 'bg-neon-green/20 text-neon-green' : 'bg-neon-red/20 text-neon-red'}
          `}>
            {position.side.toUpperCase()}
          </span>
        </div>
        {position.brokerName && (
          <div className="text-xs text-dark-400 mt-0.5">
            {position.brokerName}
          </div>
        )}
      </td>

      {/* Size */}
      <td className="px-4 py-3">
        <div className="font-mono">{position.size}</div>
        <div className="text-xs text-dark-400">{position.leverage}x leverage</div>
      </td>

      {/* Entry Price */}
      <td className="px-4 py-3 font-mono text-right">{position.entryPrice}</td>

      {/* Current Price */}
      <td className="px-4 py-3 font-mono text-right">
        <motion.span
          key={position.currentPrice}
          initial={{ scale: 1.1 }}
          animate={{ scale: 1 }}
        >
          {position.currentPrice}
        </motion.span>
      </td>

      {/* SL/TP */}
      <td className="px-4 py-3 text-right">
        <div className="text-xs">
          <div className="text-neon-red">SL: {position.stopLoss || '-'}</div>
          <div className="text-neon-green">TP: {position.takeProfit || '-'}</div>
        </div>
      </td>

      {/* P&L */}
      <td className="px-4 py-3 text-right">
        <div className={`flex items-center justify-end gap-1 ${isPositive ? 'text-neon-green' : 'text-neon-red'}`}>
          {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          <div>
            <div className="font-mono font-semibold">
              {isPositive ? '+' : ''}${position.pnl.toFixed(2)}
            </div>
            <div className="text-xs">
              {isPositive ? '+' : ''}{position.pnlPercent.toFixed(2)}%
            </div>
          </div>
        </div>
      </td>

      {/* Actions */}
      <td className="px-4 py-3 text-right">
        <div className="flex items-center justify-end gap-2">
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onModify}
            className="p-2 hover:bg-dark-700 rounded-lg transition-colors"
            title="Modify"
          >
            <Edit2 size={16} className="text-dark-400" />
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.1 }}
            whileTap={{ scale: 0.9 }}
            onClick={onClose}
            className="p-2 hover:bg-neon-red/20 rounded-lg transition-colors group"
            title="Close Position"
          >
            <X size={16} className="text-dark-400 group-hover:text-neon-red" />
          </motion.button>
        </div>
      </td>
    </motion.tr>
  )
}

export function PositionsTable({
  positions = [],
  onClose,
  onModify,
  isLoading = false,
}: PositionsTableProps) {
  const totalPnL = positions.reduce((sum, p) => sum + p.pnl, 0)
  const isPositive = totalPnL >= 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="card overflow-hidden"
    >
      {/* Header */}
      <div className="p-4 border-b border-dark-700/50 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Open Positions</h2>
          <p className="text-sm text-dark-400">{positions.length} active positions</p>
        </div>
        <div className="text-right">
          <p className="text-sm text-dark-400">Total P&L</p>
          <p className={`text-xl font-mono font-bold ${isPositive ? 'text-neon-green' : 'text-neon-red'}`}>
            {isPositive ? '+' : ''}${totalPnL.toFixed(2)}
          </p>
        </div>
      </div>

      {/* Table */}
      {positions.length === 0 ? (
        <div className="p-12 text-center">
          <AlertTriangle className="w-12 h-12 mx-auto text-dark-500 mb-4" />
          <h3 className="font-semibold mb-2">No Open Positions</h3>
          <p className="text-sm text-dark-400">Your open positions will appear here</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-dark-800/50 text-left text-xs text-dark-400 uppercase tracking-wider">
                <th className="px-4 py-3">Symbol</th>
                <th className="px-4 py-3">Size</th>
                <th className="px-4 py-3 text-right">Entry</th>
                <th className="px-4 py-3 text-right">Current</th>
                <th className="px-4 py-3 text-right">SL/TP</th>
                <th className="px-4 py-3 text-right">P&L</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {positions.map((position) => (
                  <PositionRow
                    key={position.id}
                    position={position}
                    onClose={() => onClose?.(position.id)}
                    onModify={() => onModify?.(position.id)}
                  />
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  )
}

export default PositionsTable
