'use client'

import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import { useEffect, useState, useCallback } from 'react'
import { tradingApi } from '@/lib/api'

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

// Available trading symbols
const SYMBOLS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'XAU/USD', 'US30', 'NAS100']

// Fallback demo prices (used when API is unavailable)
const demoPrices: PriceData[] = [
  { symbol: 'EUR/USD', bid: '1.0890', ask: '1.0892', mid: '1.0891', spread: '0.2', change: 0.0015, changePercent: 0.14 },
  { symbol: 'GBP/USD', bid: '1.2650', ask: '1.2653', mid: '1.2651', spread: '0.3', change: -0.0022, changePercent: -0.17 },
  { symbol: 'USD/JPY', bid: '149.85', ask: '149.88', mid: '149.86', spread: '0.3', change: 0.45, changePercent: 0.30 },
  { symbol: 'XAU/USD', bid: '2045.50', ask: '2046.20', mid: '2045.85', spread: '0.7', change: 12.30, changePercent: 0.60 },
  { symbol: 'US30', bid: '38250', ask: '38255', mid: '38252', spread: '5', change: -125, changePercent: -0.33 },
  { symbol: 'NAS100', bid: '17520', ask: '17525', mid: '17522', spread: '5', change: 85, changePercent: 0.49 },
]

function PriceCard({ price, isSelected, onClick, isLoading }: { price: PriceData; isSelected: boolean; onClick: () => void; isLoading?: boolean }) {
  const [flash, setFlash] = useState<'up' | 'down' | null>(null)
  const [prevMid, setPrevMid] = useState(price.mid)
  const isPositive = price.change >= 0

  // Flash animation when price changes
  useEffect(() => {
    if (price.mid !== prevMid) {
      const newMid = parseFloat(price.mid)
      const oldMid = parseFloat(prevMid)
      if (newMid > oldMid) {
        setFlash('up')
      } else if (newMid < oldMid) {
        setFlash('down')
      }
      setPrevMid(price.mid)
      const timer = setTimeout(() => setFlash(null), 500)
      return () => clearTimeout(timer)
    }
  }, [price.mid, prevMid])

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
      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute top-2 left-2">
          <RefreshCw size={12} className="animate-spin text-dark-400" />
        </div>
      )}

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
        <span className={`text-2xl font-mono font-bold transition-colors duration-300 ${flash === 'up' ? 'text-neon-green' : flash === 'down' ? 'text-neon-red' : ''}`}>
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

export function PriceTicker({ onSelect, selectedSymbol }: PriceTickerProps) {
  const [prices, setPrices] = useState<PriceData[]>(demoPrices)
  const [isLoading, setIsLoading] = useState(true)
  const [prevPrices, setPrevPrices] = useState<Record<string, number>>({})

  // Fetch prices from backend
  const fetchPrices = useCallback(async () => {
    try {
      const response = await tradingApi.getPrices(SYMBOLS)

      if (response.prices && response.prices.length > 0) {
        const newPrices: PriceData[] = response.prices.map(p => {
          const mid = parseFloat(p.mid)
          const prevMid = prevPrices[p.symbol] || mid
          const change = mid - prevMid
          const changePercent = prevMid > 0 ? (change / prevMid) * 100 : 0

          return {
            symbol: p.symbol.replace('_', '/'),
            bid: p.bid,
            ask: p.ask,
            mid: p.mid,
            spread: p.spread,
            change,
            changePercent,
          }
        })

        // Update previous prices for next calculation
        const newPrevPrices: Record<string, number> = {}
        newPrices.forEach(p => {
          newPrevPrices[p.symbol] = parseFloat(p.mid)
        })
        setPrevPrices(newPrevPrices)

        setPrices(newPrices)
      }
    } catch (error) {
      console.error('Failed to fetch prices:', error)
      // Keep showing demo prices on error
    } finally {
      setIsLoading(false)
    }
  }, [prevPrices])

  // Initial fetch
  useEffect(() => {
    fetchPrices()
  }, []) // Only run once on mount

  // Periodic refresh every 3 seconds
  useEffect(() => {
    const interval = setInterval(fetchPrices, 3000)
    return () => clearInterval(interval)
  }, [fetchPrices])

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
            isLoading={isLoading && index === 0}
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
