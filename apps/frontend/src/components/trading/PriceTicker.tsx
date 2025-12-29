'use client'

import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useEffect, useState } from 'react'

interface PriceData {
  symbol: string
  bid: string
  ask: string
  mid: string
  spread: string
  change: number
  changePercent: number
}

interface PriceTickerProps {
  prices?: PriceData[]
  onSelect?: (symbol: string) => void
  selectedSymbol?: string
}

// Demo prices
const demoPrices: PriceData[] = [
  { symbol: 'EUR/USD', bid: '1.0890', ask: '1.0892', mid: '1.0891', spread: '0.2', change: 0.0015, changePercent: 0.14 },
  { symbol: 'GBP/USD', bid: '1.2650', ask: '1.2653', mid: '1.2651', spread: '0.3', change: -0.0022, changePercent: -0.17 },
  { symbol: 'USD/JPY', bid: '149.85', ask: '149.88', mid: '149.86', spread: '0.3', change: 0.45, changePercent: 0.30 },
  { symbol: 'XAU/USD', bid: '2045.50', ask: '2046.20', mid: '2045.85', spread: '0.7', change: 12.30, changePercent: 0.60 },
  { symbol: 'US30', bid: '38250', ask: '38255', mid: '38252', spread: '5', change: -125, changePercent: -0.33 },
  { symbol: 'NAS100', bid: '17520', ask: '17525', mid: '17522', spread: '5', change: 85, changePercent: 0.49 },
]

function PriceCard({ price, isSelected, onClick }: { price: PriceData; isSelected: boolean; onClick: () => void }) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const isPositive = price.change >= 0

  // Simulate price flash animation
  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() > 0.7) {
        setFlash(Math.random() > 0.5 ? 'up' : 'down')
        setTimeout(() => setFlash(null), 300)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`
        relative p-4 rounded-xl cursor-pointer transition-all duration-200
        ${isSelected
          ? 'bg-primary-500/20 border-2 border-primary-500/50'
          : 'bg-dark-800/50 border border-dark-700/50 hover:border-dark-600'
        }
        ${flash === 'up' ? 'ring-2 ring-neon-green/50' : ''}
        ${flash === 'down' ? 'ring-2 ring-neon-red/50' : ''}
      `}
    >
      {/* Symbol & Change */}
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold">{price.symbol}</span>
        <div className={`flex items-center gap-1 text-sm ${isPositive ? 'text-neon-green' : 'text-neon-red'}`}>
          {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          <span>{isPositive ? '+' : ''}{price.changePercent.toFixed(2)}%</span>
        </div>
      </div>

      {/* Price */}
      <div className="flex items-baseline gap-2">
        <span className={`text-2xl font-mono font-bold ${flash === 'up' ? 'text-neon-green' : flash === 'down' ? 'text-neon-red' : ''}`}>
          {price.mid}
        </span>
      </div>

      {/* Bid/Ask */}
      <div className="flex items-center justify-between mt-2 text-xs text-dark-400">
        <span>Bid: {price.bid}</span>
        <span>Ask: {price.ask}</span>
      </div>

      {/* Spread */}
      <div className="absolute top-2 right-2">
        <span className="text-[10px] px-1.5 py-0.5 bg-dark-700 rounded text-dark-400">
          {price.spread} pip
        </span>
      </div>
    </motion.div>
  )
}

export function PriceTicker({ prices = demoPrices, onSelect, selectedSymbol }: PriceTickerProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {prices.map((price, index) => (
        <motion.div
          key={price.symbol}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05 }}
        >
          <PriceCard
            price={price}
            isSelected={selectedSymbol === price.symbol}
            onClick={() => onSelect?.(price.symbol)}
          />
        </motion.div>
      ))}
    </div>
  )
}

export function PriceTickerCompact({ prices = demoPrices }: { prices?: PriceData[] }) {
  return (
    <div className="flex gap-4 overflow-x-auto py-2 scrollbar-hide">
      {prices.map((price) => {
        const isPositive = price.change >= 0
        return (
          <div key={price.symbol} className="flex items-center gap-3 px-4 py-2 bg-dark-800/50 rounded-lg whitespace-nowrap">
            <span className="font-medium">{price.symbol}</span>
            <span className="font-mono">{price.mid}</span>
            <span className={`text-sm ${isPositive ? 'text-neon-green' : 'text-neon-red'}`}>
              {isPositive ? '+' : ''}{price.changePercent.toFixed(2)}%
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default PriceTicker
