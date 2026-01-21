"use client";

import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";

// TradingView Lightweight Charts types
interface CandlestickData {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface VolumeData {
  time: string;
  value: number;
  color: string;
}

interface ChartColors {
  background: string;
  text: string;
  grid: string;
  upColor: string;
  downColor: string;
  borderUpColor: string;
  borderDownColor: string;
  wickUpColor: string;
  wickDownColor: string;
}

interface TradingViewChartProps {
  symbol?: string;
  timeframe?: string;
  height?: number;
  showVolume?: boolean;
  showToolbar?: boolean;
  onTimeframeChange?: (tf: string) => void;
}

const TIMEFRAMES = [
  { label: "1m", value: "1" },
  { label: "5m", value: "5" },
  { label: "15m", value: "15" },
  { label: "1H", value: "60" },
  { label: "4H", value: "240" },
  { label: "1D", value: "D" },
];

const DARK_COLORS: ChartColors = {
  background: "#0f172a",
  text: "#94a3b8",
  grid: "#1e293b",
  upColor: "#22c55e",
  downColor: "#ef4444",
  borderUpColor: "#22c55e",
  borderDownColor: "#ef4444",
  wickUpColor: "#22c55e",
  wickDownColor: "#ef4444",
};

// Generate realistic demo candlestick data
function generateDemoData(
  symbol: string,
  timeframe: string,
  count: number = 200
): { candles: CandlestickData[]; volumes: VolumeData[] } {
  const candles: CandlestickData[] = [];
  const volumes: VolumeData[] = [];

  // Base prices for different symbols
  const basePrices: Record<string, number> = {
    "EUR/USD": 1.0856,
    "GBP/USD": 1.2654,
    "USD/JPY": 149.85,
    "XAU/USD": 2048.5,
    "US30": 38450,
    "NAS100": 17250,
    "SPX500": 4925,
    "BTCUSD": 43500,
  };

  let price = basePrices[symbol] || 100;
  const volatility = price * 0.0015; // 0.15% volatility per candle

  // Time intervals in minutes
  const intervals: Record<string, number> = {
    "1": 1,
    "5": 5,
    "15": 15,
    "60": 60,
    "240": 240,
    D: 1440,
  };

  const intervalMinutes = intervals[timeframe] || 60;
  const now = new Date();
  now.setMinutes(Math.floor(now.getMinutes() / intervalMinutes) * intervalMinutes);
  now.setSeconds(0);
  now.setMilliseconds(0);

  for (let i = count - 1; i >= 0; i--) {
    const time = new Date(now.getTime() - i * intervalMinutes * 60 * 1000);
    const dateStr = time.toISOString().split("T")[0];

    // Random walk with trend
    const trend = Math.sin(i / 50) * volatility * 2;
    const change = (Math.random() - 0.5) * volatility * 2 + trend * 0.1;

    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * volatility;
    const low = Math.min(open, close) - Math.random() * volatility;

    candles.push({
      time: dateStr,
      open: Number(open.toFixed(5)),
      high: Number(high.toFixed(5)),
      low: Number(low.toFixed(5)),
      close: Number(close.toFixed(5)),
    });

    const isUp = close >= open;
    volumes.push({
      time: dateStr,
      value: Math.floor(1000000 + Math.random() * 5000000),
      color: isUp ? "rgba(34, 197, 94, 0.5)" : "rgba(239, 68, 68, 0.5)",
    });

    price = close;
  }

  return { candles, volumes };
}

export default function TradingViewChart({
  symbol = "EUR/USD",
  timeframe = "60",
  height = 500,
  showVolume = true,
  showToolbar = true,
  onTimeframeChange,
}: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const candlestickSeriesRef = useRef<any>(null);
  const volumeSeriesRef = useRef<any>(null);

  const [selectedTimeframe, setSelectedTimeframe] = useState(timeframe);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [priceChange, setPriceChange] = useState<number>(0);
  const [priceChangePercent, setPriceChangePercent] = useState<number>(0);

  const initChart = useCallback(async () => {
    if (!chartContainerRef.current) return;

    // Dynamically import lightweight-charts
    const { createChart } = await import("lightweight-charts");

    // Clean up existing chart
    if (chartRef.current) {
      chartRef.current.remove();
    }

    // Create chart
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height - (showToolbar ? 60 : 0),
      layout: {
        background: { color: DARK_COLORS.background },
        textColor: DARK_COLORS.text,
      },
      grid: {
        vertLines: { color: DARK_COLORS.grid },
        horzLines: { color: DARK_COLORS.grid },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          width: 1,
          color: "#6366f1",
          style: 2,
        },
        horzLine: {
          width: 1,
          color: "#6366f1",
          style: 2,
        },
      },
      rightPriceScale: {
        borderColor: DARK_COLORS.grid,
        scaleMargins: {
          top: 0.1,
          bottom: showVolume ? 0.2 : 0.1,
        },
      },
      timeScale: {
        borderColor: DARK_COLORS.grid,
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: DARK_COLORS.upColor,
      downColor: DARK_COLORS.downColor,
      borderUpColor: DARK_COLORS.borderUpColor,
      borderDownColor: DARK_COLORS.borderDownColor,
      wickUpColor: DARK_COLORS.wickUpColor,
      wickDownColor: DARK_COLORS.wickDownColor,
    });

    candlestickSeriesRef.current = candlestickSeries;

    // Add volume series if enabled
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        color: "#6366f1",
        priceFormat: {
          type: "volume",
        },
        priceScaleId: "",
      });

      volumeSeries.priceScale().applyOptions({
        scaleMargins: {
          top: 0.8,
          bottom: 0,
        },
      });

      volumeSeriesRef.current = volumeSeries;
    }

    // Generate and set demo data
    const { candles, volumes } = generateDemoData(symbol, selectedTimeframe);
    candlestickSeries.setData(candles);

    if (showVolume && volumeSeriesRef.current) {
      volumeSeriesRef.current.setData(volumes);
    }

    // Update price info
    const lastCandle = candles[candles.length - 1];
    const firstCandle = candles[0];
    if (lastCandle && firstCandle) {
      setCurrentPrice(lastCandle.close);
      const change = lastCandle.close - firstCandle.open;
      setPriceChange(change);
      setPriceChangePercent((change / firstCandle.open) * 100);
    }

    // Fit content
    chart.timeScale().fitContent();

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener("resize", handleResize);

    setIsLoading(false);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
      }
    };
  }, [symbol, selectedTimeframe, height, showVolume, showToolbar]);

  useEffect(() => {
    initChart();
  }, [initChart]);

  // Simulate real-time updates
  useEffect(() => {
    // Don't start updates until chart is fully loaded
    if (isLoading) return;

    const updateInterval = setInterval(() => {
      try {
        if (!candlestickSeriesRef.current) return;

        const data = candlestickSeriesRef.current.data();
        if (!data || data.length === 0) return;

        const lastCandle = data[data.length - 1];
        if (!lastCandle || typeof lastCandle.close !== 'number') return;

        // Create a copy with updated values
        const updatedCandle = {
          time: lastCandle.time,
          open: lastCandle.open,
          high: lastCandle.high,
          low: lastCandle.low,
          close: lastCandle.close,
        };

        const volatility = updatedCandle.close * 0.0002;
        const change = (Math.random() - 0.5) * volatility * 2;

        updatedCandle.close = Number((updatedCandle.close + change).toFixed(5));
        updatedCandle.high = Number(Math.max(updatedCandle.high, updatedCandle.close).toFixed(5));
        updatedCandle.low = Number(Math.min(updatedCandle.low, updatedCandle.close).toFixed(5));

        candlestickSeriesRef.current.update(updatedCandle);
        setCurrentPrice(updatedCandle.close);

        const firstCandle = data[0];
        if (firstCandle && typeof firstCandle.open === 'number') {
          const priceChangeVal = updatedCandle.close - firstCandle.open;
          setPriceChange(priceChangeVal);
          setPriceChangePercent((priceChangeVal / firstCandle.open) * 100);
        }
      } catch (err) {
        // Silently ignore errors during real-time updates
        console.debug('Chart update skipped:', err);
      }
    }, 1000);

    return () => clearInterval(updateInterval);
  }, [isLoading]);

  const handleTimeframeChange = (tf: string) => {
    setSelectedTimeframe(tf);
    setIsLoading(true);
    onTimeframeChange?.(tf);
  };

  const formatPrice = (price: number) => {
    if (symbol.includes("JPY")) return price.toFixed(3);
    if (symbol.includes("XAU") || symbol.includes("US30") || symbol.includes("NAS") || symbol.includes("SPX")) {
      return price.toFixed(2);
    }
    return price.toFixed(5);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="bg-slate-900 rounded-xl border border-slate-700 overflow-hidden"
    >
      {/* Toolbar */}
      {showToolbar && (
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
          <div className="flex items-center gap-4">
            {/* Symbol */}
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-white">{symbol}</span>
              {currentPrice && (
                <span
                  className={`text-lg font-semibold ${
                    priceChange >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {formatPrice(currentPrice)}
                </span>
              )}
              {priceChange !== 0 && (
                <span
                  className={`text-sm ${
                    priceChange >= 0 ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {priceChange >= 0 ? "+" : ""}
                  {formatPrice(priceChange)} ({priceChangePercent >= 0 ? "+" : ""}
                  {priceChangePercent.toFixed(2)}%)
                </span>
              )}
            </div>
          </div>

          {/* Timeframe buttons */}
          <div className="flex items-center gap-1">
            {TIMEFRAMES.map((tf) => (
              <button
                key={tf.value}
                onClick={() => handleTimeframeChange(tf.value)}
                className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                  selectedTimeframe === tf.value
                    ? "bg-indigo-600 text-white"
                    : "text-slate-400 hover:text-white hover:bg-slate-700"
                }`}
              >
                {tf.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chart container */}
      <div className="relative" style={{ height: height - (showToolbar ? 60 : 0) }}>
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 z-10">
            <div className="flex items-center gap-3">
              <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-slate-400">Loading chart...</span>
            </div>
          </div>
        )}
        <div ref={chartContainerRef} className="w-full h-full" />
      </div>

      {/* Chart info */}
      <div className="px-4 py-2 border-t border-slate-700 flex items-center justify-between text-xs text-slate-500">
        <span>TradingView Lightweight Charts</span>
        <span>Demo data - Connect broker for live prices</span>
      </div>
    </motion.div>
  );
}
