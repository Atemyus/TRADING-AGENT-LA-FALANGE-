'use client'

import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Wifi, WifiOff } from 'lucide-react'
import { useEffect, useState, useRef } from 'react'
import { usePriceStream } from '@/hooks/useWebSocket'

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

// Available trading symbols (WebSocket format)
const SYMBOLS = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'XAU_USD', 'US30', 'NAS100']

// Fallback demo prices (used when WebSocket is unavailable)
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
          <WifiOff size={12} className="text-dark-400" />
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
  const prevPricesRef = useRef<Record<string, number>>({})
  const basePricesRef = useRef<Record<string, number>>({})

  // Use WebSocket for real-time price streaming
  const { prices: streamPrices, isConnected } = usePriceStream(SYMBOLS)

  // Initialize base prices from demo data
  useEffect(() => {
    demoPrices.forEach(p => {
      basePricesRef.current[p.symbol.replace('/', '_')] = parseFloat(p.mid)
    })
  }, [])

  // Update prices from WebSocket stream
  useEffect(() => {
    if (Object.keys(streamPrices).length > 0) {
      const newPrices: PriceData[] = SYMBOLS.map(wsSymbol => {
        const displaySymbol = wsSymbol.replace('_', '/')
        const streamData = streamPrices[wsSymbol]

        if (streamData) {
          const mid = parseFloat(streamData.mid)
          const prevMid = prevPricesRef.current[wsSymbol] || mid
          const baseMid = basePricesRef.current[wsSymbol] || mid

          // Calculate change from previous tick (for flash effect)
          const tickChange = mid - prevMid
          // Calculate change from session start (for display)
          const sessionChange = mid - baseMid
          const changePercent = baseMid > 0 ? (sessionChange / baseMid) * 100 : 0

          // Update previous price for next tick
          prevPricesRef.current[wsSymbol] = mid

          return {
            symbol: displaySymbol,
            bid: streamData.bid,
            ask: streamData.ask,
            mid: streamData.mid,
            spread: streamData.spread,
            change: sessionChange,
            changePercent,
          }
        }

        // Fallback to demo price if no stream data
        const demo = demoPrices.find(d => d.symbol === displaySymbol)
        return demo || demoPrices[0]
      })

      setPrices(newPrices)
    }
  }, [streamPrices])

  return (
    <div className="space-y-2">
      {/* Connection status */}
      <div className="flex items-center justify-end gap-2 text-xs">
        {isConnected ? (
          <>
            <Wifi size={12} className="text-neon-green" />
            <span className="text-neon-green">Live</span>
          </>
        ) : (
          <>
            <WifiOff size={12} className="text-dark-400" />
            <span className="text-dark-400">Connecting...</span>
          </>
        )}
      </div>
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
              isLoading={!isConnected && index === 0}
            />
          </motion.div>
        ))}
      </div>
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
