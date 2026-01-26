'use client'

import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Wifi, WifiOff, ChevronLeft, ChevronRight } from 'lucide-react'
import { useEffect, useState, useRef, useCallback } from 'react'
import { usePriceStream } from '@/hooks/useWebSocket'
import { ALL_SYMBOLS, CATEGORY_LABELS, type TradingSymbol } from '@/lib/symbols'

interface PriceData {
  symbol: string
  displayName: string
  label: string
  value: string
  tvSymbol: string
  category: TradingSymbol['category']
  bid: string
  ask: string
  mid: string
  spread: string
  change: number
  changePercent: number
}

interface PriceTickerProps {
  onSelect?: (symbol: string) => void
  selectedSymbol?: string
}

// Get WebSocket format symbols
const WS_SYMBOLS = ALL_SYMBOLS.map(s => s.value)

// Default fallback prices per category
const getDefaultPrice = (symbol: TradingSymbol): PriceData => {
  const defaultPrices: Record<string, { mid: string; spread: string }> = {
    // Forex
    'EUR_USD': { mid: '1.0891', spread: '0.2' },
    'GBP_USD': { mid: '1.2651', spread: '0.3' },
    'USD_JPY': { mid: '149.86', spread: '0.3' },
    'USD_CHF': { mid: '0.8825', spread: '0.3' },
    'AUD_USD': { mid: '0.6542', spread: '0.3' },
    'USD_CAD': { mid: '1.3568', spread: '0.3' },
    'NZD_USD': { mid: '0.6125', spread: '0.4' },
    // Metals
    'XAU_USD': { mid: '2045.85', spread: '0.7' },
    'XAG_USD': { mid: '23.45', spread: '0.05' },
    // Commodities
    'WTI_USD': { mid: '76.50', spread: '0.05' },
    'BRENT_USD': { mid: '81.20', spread: '0.05' },
    'NATGAS_USD': { mid: '2.85', spread: '0.01' },
    // Indices
    'US30': { mid: '38252', spread: '5' },
    'US500': { mid: '4925', spread: '0.5' },
    'NAS100': { mid: '17522', spread: '5' },
    'DE40': { mid: '17850', spread: '2' },
    'UK100': { mid: '7650', spread: '2' },
    'JP225': { mid: '38500', spread: '10' },
  }

  const defaultData = defaultPrices[symbol.value] || { mid: '100.00', spread: '0.5' }
  const mid = parseFloat(defaultData.mid)

  return {
    symbol: symbol.label,
    displayName: symbol.displayName,
    label: symbol.label,
    value: symbol.value,
    tvSymbol: symbol.tvSymbol,
    category: symbol.category,
    bid: (mid - 0.0001).toFixed(mid < 10 ? 4 : mid < 1000 ? 2 : 0),
    ask: (mid + 0.0001).toFixed(mid < 10 ? 4 : mid < 1000 ? 2 : 0),
    mid: defaultData.mid,
    spread: defaultData.spread,
    change: 0,
    changePercent: 0,
  }
}

function PriceCard({
  price,
  isSelected,
  onClick,
  isLoading,
  compact = false
}: {
  price: PriceData
  isSelected: boolean
  onClick: () => void
  isLoading?: boolean
  compact?: boolean
}) {
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

  const categoryColors: Record<TradingSymbol['category'], string> = {
    forex: 'bg-blue-500/20 text-blue-400',
    metals: 'bg-yellow-500/20 text-yellow-400',
    commodities: 'bg-orange-500/20 text-orange-400',
    indices: 'bg-purple-500/20 text-purple-400',
    futures: 'bg-cyan-500/20 text-cyan-400',
  }

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onClick}
      className={`
        relative p-4 rounded-xl cursor-pointer transition-all duration-200 min-w-[160px] flex-shrink-0
        ${isSelected
          ? 'bg-primary-500/20 border-2 border-primary-500/50'
          : 'bg-dark-800/50 border border-dark-700/50 hover:border-dark-600'
        }
        ${flash === 'up' ? 'ring-2 ring-neon-green/50' : ''}
        ${flash === 'down' ? 'ring-2 ring-neon-red/50' : ''}
      `}
    >
      {/* Category badge */}
      <div className="absolute top-2 left-2">
        <span className={`text-[9px] px-1.5 py-0.5 rounded ${categoryColors[price.category]}`}>
          {CATEGORY_LABELS[price.category]}
        </span>
      </div>

      {/* Loading indicator */}
      {isLoading && (
        <div className="absolute top-2 right-2">
          <WifiOff size={12} className="text-dark-400" />
        </div>
      )}

      {/* Symbol & Change */}
      <div className="flex items-center justify-between mb-2 mt-4">
        <span className="font-semibold text-sm">{price.displayName}</span>
        <div className={`flex items-center gap-1 text-xs ${isPositive ? 'text-neon-green' : 'text-neon-red'}`}>
          {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          <span>{isPositive ? '+' : ''}{price.changePercent.toFixed(2)}%</span>
        </div>
      </div>

      {/* Price */}
      <div className="flex items-baseline gap-2">
        <span className={`text-xl font-mono font-bold transition-colors duration-300 ${flash === 'up' ? 'text-neon-green' : flash === 'down' ? 'text-neon-red' : ''}`}>
          {price.mid}
        </span>
      </div>

      {/* Bid/Ask */}
      <div className="flex items-center justify-between mt-2 text-[10px] text-dark-400">
        <span>Bid: {price.bid}</span>
        <span>Ask: {price.ask}</span>
      </div>

      {/* Spread */}
      <div className="absolute bottom-2 right-2">
        <span className="text-[9px] px-1.5 py-0.5 bg-dark-700 rounded text-dark-400">
          {price.spread} pip
        </span>
      </div>
    </motion.div>
  )
}

export function PriceTicker({ onSelect, selectedSymbol }: PriceTickerProps) {
  const [prices, setPrices] = useState<PriceData[]>(() => ALL_SYMBOLS.map(getDefaultPrice))
  const [scrollPosition, setScrollPosition] = useState(0)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const prevPricesRef = useRef<Record<string, number>>({})
  const basePricesRef = useRef<Record<string, number>>({})

  // Use WebSocket for real-time price streaming
  const { prices: streamPrices, isConnected } = usePriceStream(WS_SYMBOLS)

  // Scroll handlers
  const scroll = useCallback((direction: 'left' | 'right') => {
    if (!scrollContainerRef.current) return
    const container = scrollContainerRef.current
    const scrollAmount = 340 // ~2 cards width
    const newPosition = direction === 'left'
      ? Math.max(0, scrollPosition - scrollAmount)
      : Math.min(container.scrollWidth - container.clientWidth, scrollPosition + scrollAmount)

    container.scrollTo({ left: newPosition, behavior: 'smooth' })
    setScrollPosition(newPosition)
  }, [scrollPosition])

  // Update scroll position on scroll
  const handleScroll = useCallback(() => {
    if (scrollContainerRef.current) {
      setScrollPosition(scrollContainerRef.current.scrollLeft)
    }
  }, [])

  // Check if we can scroll
  const canScrollLeft = scrollPosition > 0
  const canScrollRight = scrollContainerRef.current
    ? scrollPosition < scrollContainerRef.current.scrollWidth - scrollContainerRef.current.clientWidth - 10
    : true

  // Initialize base prices
  useEffect(() => {
    ALL_SYMBOLS.forEach(s => {
      const defaultPrice = getDefaultPrice(s)
      basePricesRef.current[s.value] = parseFloat(defaultPrice.mid)
    })
  }, [])

  // Update prices from WebSocket stream
  useEffect(() => {
    if (Object.keys(streamPrices).length > 0) {
      const newPrices: PriceData[] = ALL_SYMBOLS.map(symbol => {
        const streamData = streamPrices[symbol.value]

        if (streamData) {
          const mid = parseFloat(streamData.mid)
          const prevMid = prevPricesRef.current[symbol.value] || mid
          const baseMid = basePricesRef.current[symbol.value] || mid

          const sessionChange = mid - baseMid
          const changePercent = baseMid > 0 ? (sessionChange / baseMid) * 100 : 0

          prevPricesRef.current[symbol.value] = mid

          return {
            symbol: symbol.label,
            displayName: symbol.displayName,
            label: symbol.label,
            value: symbol.value,
            tvSymbol: symbol.tvSymbol,
            category: symbol.category,
            bid: streamData.bid,
            ask: streamData.ask,
            mid: streamData.mid,
            spread: streamData.spread,
            change: sessionChange,
            changePercent,
          }
        }

        return getDefaultPrice(symbol)
      })

      setPrices(newPrices)
    }
  }, [streamPrices])

  // Convert selected symbol format
  const selectedValue = selectedSymbol?.replace('/', '_')

  return (
    <>
      {/* Hide scrollbar for webkit browsers */}
      <style jsx>{`
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
      `}</style>
      <div className="space-y-2 w-full overflow-hidden">
      {/* Header with connection status */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-dark-400">
            {ALL_SYMBOLS.length} Assets
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs">
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
      </div>

      {/* Scrollable container with arrows on sides */}
      <div className="flex items-center gap-2 w-full">
        {/* Left Arrow - Fixed on left side */}
        <button
          onClick={() => scroll('left')}
          disabled={!canScrollLeft}
          className={`
            flex-shrink-0 w-10 h-10 rounded-full
            bg-dark-800 border-2 border-primary-500/50
            flex items-center justify-center
            transition-all duration-200 shadow-lg shadow-dark-900/50
            ${canScrollLeft
              ? 'opacity-100 hover:bg-primary-500/20 hover:border-primary-500 hover:scale-110 cursor-pointer'
              : 'opacity-40 cursor-not-allowed border-dark-600'
            }
          `}
        >
          <ChevronLeft size={20} className="text-white" />
        </button>

        {/* Scrollable Price Cards Container */}
        <div className="flex-1 overflow-hidden relative">
          <div
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="flex gap-3 overflow-x-scroll py-2 px-2 hide-scrollbar"
            style={{
              scrollBehavior: 'smooth',
              scrollbarWidth: 'none', /* Firefox */
              msOverflowStyle: 'none', /* IE/Edge */
            }}
          >
            {prices.map((price, index) => (
              <motion.div
                key={price.value}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: Math.min(index * 0.02, 0.5) }}
                className="flex-shrink-0"
              >
                <PriceCard
                  price={price}
                  isSelected={selectedValue === price.value}
                  onClick={() => onSelect?.(price.label)}
                  isLoading={!isConnected}
                />
              </motion.div>
            ))}
          </div>
          {/* Gradient fades for smooth edges */}
          <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-dark-900 to-transparent pointer-events-none z-10" />
          <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-dark-900 to-transparent pointer-events-none z-10" />
        </div>

        {/* Right Arrow - Fixed on right side */}
        <button
          onClick={() => scroll('right')}
          disabled={!canScrollRight}
          className={`
            flex-shrink-0 w-10 h-10 rounded-full
            bg-dark-800 border-2 border-primary-500/50
            flex items-center justify-center
            transition-all duration-200 shadow-lg shadow-dark-900/50
            ${canScrollRight
              ? 'opacity-100 hover:bg-primary-500/20 hover:border-primary-500 hover:scale-110 cursor-pointer'
              : 'opacity-40 cursor-not-allowed border-dark-600'
            }
          `}
        >
          <ChevronRight size={20} className="text-white" />
        </button>
      </div>
    </div>
    </>
  )
}

export function PriceTickerCompact({ onSelect, selectedSymbol }: { onSelect?: (symbol: string) => void; selectedSymbol?: string }) {
  const { prices: streamPrices, isConnected } = usePriceStream(WS_SYMBOLS.slice(0, 10))

  const prices = ALL_SYMBOLS.slice(0, 10).map(symbol => {
    const streamData = streamPrices[symbol.value]
    if (streamData) {
      return {
        ...getDefaultPrice(symbol),
        mid: streamData.mid,
        bid: streamData.bid,
        ask: streamData.ask,
      }
    }
    return getDefaultPrice(symbol)
  })

  return (
    <div className="flex gap-4 overflow-x-auto py-2 scrollbar-hide">
      {prices.map((price) => {
        const isPositive = price.change >= 0
        const isSelected = selectedSymbol?.replace('/', '_') === price.value
        return (
          <div
            key={price.value}
            onClick={() => onSelect?.(price.label)}
            className={`
              flex items-center gap-3 px-4 py-2 rounded-lg whitespace-nowrap cursor-pointer
              transition-colors duration-200
              ${isSelected ? 'bg-primary-500/20 border border-primary-500/50' : 'bg-dark-800/50 hover:bg-dark-700/50'}
            `}
          >
            <span className="font-medium">{price.displayName}</span>
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
