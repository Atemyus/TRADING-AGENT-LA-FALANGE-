"use client";

import React, { useEffect, useRef, memo } from "react";

interface TradingViewWidgetProps {
  symbol?: string;
  interval?: string;
  theme?: "dark" | "light";
  height?: number;
  autosize?: boolean;
  allowSymbolChange?: boolean;
  showToolbar?: boolean;
  showDrawingTools?: boolean;
}

// Symbol mapping: Our format -> TradingView format
const SYMBOL_MAP: Record<string, string> = {
  "EUR/USD": "FX:EURUSD",
  "GBP/USD": "FX:GBPUSD",
  "USD/JPY": "FX:USDJPY",
  "USD/CHF": "FX:USDCHF",
  "AUD/USD": "FX:AUDUSD",
  "USD/CAD": "FX:USDCAD",
  "NZD/USD": "FX:NZDUSD",
  "XAU/USD": "TVC:GOLD",
  "XAG/USD": "TVC:SILVER",
  "US30": "TVC:DJI",
  "NAS100": "NASDAQ:NDX",
  "SPX500": "SP:SPX",
  "BTCUSD": "BINANCE:BTCUSDT",
  "ETHUSD": "BINANCE:ETHUSDT",
};

// Interval mapping
const INTERVAL_MAP: Record<string, string> = {
  "1": "1",
  "5": "5",
  "15": "15",
  "30": "30",
  "60": "60",
  "240": "240",
  "D": "D",
  "W": "W",
  "M": "M",
};

function TradingViewWidget({
  symbol = "EUR/USD",
  interval = "60",
  theme = "dark",
  height = 500,
  autosize = false,
  allowSymbolChange = true,
  showToolbar = true,
  showDrawingTools = true,
}: TradingViewWidgetProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const scriptRef = useRef<HTMLScriptElement | null>(null);

  useEffect(() => {
    // Clean up previous widget
    if (containerRef.current) {
      containerRef.current.innerHTML = "";
    }

    // Map symbol to TradingView format
    const tvSymbol = SYMBOL_MAP[symbol] || `FX:${symbol.replace("/", "")}`;
    const tvInterval = INTERVAL_MAP[interval] || "60";

    // Create widget container
    const widgetContainer = document.createElement("div");
    widgetContainer.className = "tradingview-widget-container";
    widgetContainer.style.height = "100%";
    widgetContainer.style.width = "100%";

    const widgetDiv = document.createElement("div");
    widgetDiv.className = "tradingview-widget-container__widget";
    widgetDiv.style.height = autosize ? "100%" : `${height}px`;
    widgetDiv.style.width = "100%";

    widgetContainer.appendChild(widgetDiv);

    // Create and configure script
    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.type = "text/javascript";
    script.async = true;
    script.innerHTML = JSON.stringify({
      autosize: autosize,
      height: autosize ? "100%" : height,
      width: "100%",
      symbol: tvSymbol,
      interval: tvInterval,
      timezone: "Etc/UTC",
      theme: theme,
      style: "1", // Candlesticks
      locale: "en",
      enable_publishing: false,
      allow_symbol_change: allowSymbolChange,
      hide_top_toolbar: !showToolbar,
      hide_legend: false,
      save_image: true,
      hide_volume: false,
      support_host: "https://www.tradingview.com",
      // Drawing tools
      drawings_access: {
        type: showDrawingTools ? "all" : "none",
      },
      // Studies/Indicators
      studies: [
        "STD;EMA",
        "STD;RSI",
      ],
      // Custom colors for dark theme
      backgroundColor: theme === "dark" ? "rgba(15, 23, 42, 1)" : "rgba(255, 255, 255, 1)",
      gridColor: theme === "dark" ? "rgba(30, 41, 59, 1)" : "rgba(240, 240, 240, 1)",
      // Toolbar settings
      withdateranges: true,
      hide_side_toolbar: !showDrawingTools,
      details: true,
      hotlist: false,
      calendar: false,
    });

    widgetContainer.appendChild(script);
    scriptRef.current = script;

    if (containerRef.current) {
      containerRef.current.appendChild(widgetContainer);
    }

    return () => {
      if (containerRef.current) {
        containerRef.current.innerHTML = "";
      }
    };
  }, [symbol, interval, theme, height, autosize, allowSymbolChange, showToolbar, showDrawingTools]);

  return (
    <div
      ref={containerRef}
      className="tradingview-widget-wrapper rounded-xl overflow-hidden border border-slate-700"
      style={{ height: autosize ? "100%" : `${height}px` }}
    />
  );
}

export default memo(TradingViewWidget);
