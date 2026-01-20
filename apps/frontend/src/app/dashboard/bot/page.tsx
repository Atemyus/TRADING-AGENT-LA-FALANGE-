"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import {
  Play,
  Pause,
  Square,
  Settings,
  Activity,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Clock,
  Target,
  DollarSign,
  BarChart3,
  Zap,
  RefreshCw,
  CheckCircle,
  XCircle,
  Eye,
} from "lucide-react";

interface BotStatus {
  status: string;
  started_at: string | null;
  last_analysis_at: string | null;
  config: {
    symbols: string[];
    analysis_mode: string;
    min_confidence: number;
    risk_per_trade: number;
    max_positions: number;
  };
  statistics: {
    analyses_today: number;
    trades_today: number;
    daily_pnl: number;
    open_positions: number;
  };
  open_positions: Array<{
    symbol: string;
    direction: string;
    entry: number;
    sl: number;
    tp: number;
    confidence: number;
  }>;
  recent_errors: Array<{ timestamp: string; error: string }>;
}

interface BotConfig {
  symbols: string[];
  analysis_mode: string;
  analysis_interval_seconds: number;
  min_confidence: number;
  min_models_agree: number;
  min_confluence: number;
  risk_per_trade_percent: number;
  max_open_positions: number;
  max_daily_trades: number;
  max_daily_loss_percent: number;
  trading_start_hour: number;
  trading_end_hour: number;
  trade_on_weekends: boolean;
  telegram_enabled: boolean;
  discord_enabled: boolean;
}

const AVAILABLE_SYMBOLS = [
  "EUR/USD",
  "GBP/USD",
  "USD/JPY",
  "USD/CHF",
  "AUD/USD",
  "USD/CAD",
  "NZD/USD",
  "XAU/USD",
  "XAG/USD",
  "US30",
  "NAS100",
  "SPX500",
];

const ANALYSIS_MODES = [
  { value: "quick", label: "Quick", description: "1 timeframe, fastest models" },
  { value: "standard", label: "Standard", description: "2 timeframes, 3 models" },
  { value: "premium", label: "Premium", description: "3 timeframes + vision AI" },
  { value: "ultra", label: "Ultra", description: "5 timeframes + all models" },
];

export default function BotControlPage() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [config, setConfig] = useState<BotConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActioning, setIsActioning] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Demo data for visualization
  const demoStatus: BotStatus = {
    status: "stopped",
    started_at: null,
    last_analysis_at: null,
    config: {
      symbols: ["EUR/USD", "GBP/USD", "XAU/USD"],
      analysis_mode: "premium",
      min_confidence: 75,
      risk_per_trade: 1,
      max_positions: 3,
    },
    statistics: {
      analyses_today: 0,
      trades_today: 0,
      daily_pnl: 0,
      open_positions: 0,
    },
    open_positions: [],
    recent_errors: [],
  };

  const demoConfig: BotConfig = {
    symbols: ["EUR/USD", "GBP/USD", "XAU/USD"],
    analysis_mode: "premium",
    analysis_interval_seconds: 300,
    min_confidence: 75,
    min_models_agree: 6,
    min_confluence: 70,
    risk_per_trade_percent: 1,
    max_open_positions: 3,
    max_daily_trades: 10,
    max_daily_loss_percent: 5,
    trading_start_hour: 7,
    trading_end_hour: 21,
    trade_on_weekends: false,
    telegram_enabled: false,
    discord_enabled: false,
  };

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/bot/status");
      if (res.ok) {
        const data = await res.json();
        setStatus(data);
      } else {
        setStatus(demoStatus);
      }
    } catch {
      setStatus(demoStatus);
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/bot/config");
      if (res.ok) {
        const data = await res.json();
        setConfig(data);
      } else {
        setConfig(demoConfig);
      }
    } catch {
      setConfig(demoConfig);
    }
    setIsLoading(false);
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchConfig();

    // Poll status every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchConfig]);

  const handleAction = async (action: "start" | "stop" | "pause" | "resume") => {
    setIsActioning(true);
    setError(null);

    try {
      const res = await fetch(`/api/v1/bot/${action}`, { method: "POST" });
      if (res.ok) {
        await fetchStatus();
      } else {
        const data = await res.json();
        setError(data.detail || `Failed to ${action} bot`);
      }
    } catch (e) {
      setError(`Failed to ${action} bot`);
    }

    setIsActioning(false);
  };

  const handleConfigUpdate = async (updates: Partial<BotConfig>) => {
    try {
      const res = await fetch("/api/v1/bot/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updates),
      });

      if (res.ok) {
        await fetchConfig();
      }
    } catch (e) {
      console.error("Failed to update config:", e);
    }
  };

  const getStatusColor = (s: string) => {
    switch (s) {
      case "running":
        return "text-green-400";
      case "paused":
        return "text-yellow-400";
      case "stopped":
        return "text-slate-400";
      case "error":
        return "text-red-400";
      default:
        return "text-slate-400";
    }
  };

  const getStatusIcon = (s: string) => {
    switch (s) {
      case "running":
        return <Activity className="animate-pulse" />;
      case "paused":
        return <Pause />;
      case "stopped":
        return <Square />;
      case "error":
        return <AlertTriangle />;
      default:
        return <Square />;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 animate-spin text-indigo-500" />
      </div>
    );
  }

  const currentStatus = status || demoStatus;
  const currentConfig = config || demoConfig;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Auto Trading Bot</h1>
          <p className="text-slate-400">
            Fully autonomous AI-powered trading system
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowConfig(!showConfig)}
            className="btn-secondary flex items-center gap-2"
          >
            <Settings size={18} />
            Configure
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-500/20 border border-red-500 rounded-lg p-4 flex items-center gap-3"
        >
          <XCircle className="text-red-500" />
          <span>{error}</span>
          <button onClick={() => setError(null)} className="ml-auto">
            <XCircle size={18} />
          </button>
        </motion.div>
      )}

      {/* Main Status Card */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div
              className={`p-4 rounded-xl ${
                currentStatus.status === "running"
                  ? "bg-green-500/20"
                  : currentStatus.status === "paused"
                  ? "bg-yellow-500/20"
                  : "bg-slate-700"
              }`}
            >
              <span className={getStatusColor(currentStatus.status)}>
                {getStatusIcon(currentStatus.status)}
              </span>
            </div>
            <div>
              <h2 className="text-xl font-semibold capitalize">
                Bot {currentStatus.status}
              </h2>
              {currentStatus.started_at && (
                <p className="text-sm text-slate-400">
                  Started: {new Date(currentStatus.started_at).toLocaleString()}
                </p>
              )}
              {currentStatus.last_analysis_at && (
                <p className="text-sm text-slate-400">
                  Last analysis: {new Date(currentStatus.last_analysis_at).toLocaleString()}
                </p>
              )}
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex items-center gap-3">
            {currentStatus.status === "stopped" && (
              <button
                onClick={() => handleAction("start")}
                disabled={isActioning}
                className="btn-primary flex items-center gap-2 bg-green-600 hover:bg-green-700"
              >
                <Play size={18} />
                Start Bot
              </button>
            )}
            {currentStatus.status === "running" && (
              <>
                <button
                  onClick={() => handleAction("pause")}
                  disabled={isActioning}
                  className="btn-secondary flex items-center gap-2"
                >
                  <Pause size={18} />
                  Pause
                </button>
                <button
                  onClick={() => handleAction("stop")}
                  disabled={isActioning}
                  className="btn-primary flex items-center gap-2 bg-red-600 hover:bg-red-700"
                >
                  <Square size={18} />
                  Stop
                </button>
              </>
            )}
            {currentStatus.status === "paused" && (
              <>
                <button
                  onClick={() => handleAction("resume")}
                  disabled={isActioning}
                  className="btn-primary flex items-center gap-2"
                >
                  <Play size={18} />
                  Resume
                </button>
                <button
                  onClick={() => handleAction("stop")}
                  disabled={isActioning}
                  className="btn-secondary flex items-center gap-2 bg-red-600 hover:bg-red-700"
                >
                  <Square size={18} />
                  Stop
                </button>
              </>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-slate-900 rounded-lg p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Zap size={16} />
              <span className="text-sm">Analyses Today</span>
            </div>
            <p className="text-2xl font-bold">{currentStatus.statistics.analyses_today}</p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <BarChart3 size={16} />
              <span className="text-sm">Trades Today</span>
            </div>
            <p className="text-2xl font-bold">{currentStatus.statistics.trades_today}</p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <DollarSign size={16} />
              <span className="text-sm">Daily P&L</span>
            </div>
            <p
              className={`text-2xl font-bold ${
                currentStatus.statistics.daily_pnl >= 0
                  ? "text-green-400"
                  : "text-red-400"
              }`}
            >
              {currentStatus.statistics.daily_pnl >= 0 ? "+" : ""}$
              {currentStatus.statistics.daily_pnl.toFixed(2)}
            </p>
          </div>
          <div className="bg-slate-900 rounded-lg p-4">
            <div className="flex items-center gap-2 text-slate-400 mb-1">
              <Activity size={16} />
              <span className="text-sm">Open Positions</span>
            </div>
            <p className="text-2xl font-bold">
              {currentStatus.statistics.open_positions} / {currentConfig.max_open_positions}
            </p>
          </div>
        </div>
      </div>

      {/* Configuration Panel */}
      {showConfig && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="bg-slate-800 rounded-xl border border-slate-700 p-6"
        >
          <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
            <Settings size={20} />
            Bot Configuration
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Symbols */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Trading Symbols
              </label>
              <div className="grid grid-cols-3 gap-2">
                {AVAILABLE_SYMBOLS.map((symbol) => (
                  <button
                    key={symbol}
                    onClick={() => {
                      const newSymbols = currentConfig.symbols.includes(symbol)
                        ? currentConfig.symbols.filter((s) => s !== symbol)
                        : [...currentConfig.symbols, symbol];
                      handleConfigUpdate({ symbols: newSymbols });
                    }}
                    className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                      currentConfig.symbols.includes(symbol)
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                    }`}
                  >
                    {symbol}
                  </button>
                ))}
              </div>
            </div>

            {/* Analysis Mode */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Analysis Mode
              </label>
              <div className="space-y-2">
                {ANALYSIS_MODES.map((mode) => (
                  <button
                    key={mode.value}
                    onClick={() => handleConfigUpdate({ analysis_mode: mode.value })}
                    className={`w-full px-4 py-3 rounded-lg text-left transition-colors ${
                      currentConfig.analysis_mode === mode.value
                        ? "bg-indigo-600"
                        : "bg-slate-700 hover:bg-slate-600"
                    }`}
                  >
                    <div className="font-medium">{mode.label}</div>
                    <div className="text-xs text-slate-400">{mode.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Risk Settings */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Risk Management
              </label>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-400">
                    Risk per Trade: {currentConfig.risk_per_trade_percent}%
                  </label>
                  <input
                    type="range"
                    min="0.5"
                    max="5"
                    step="0.5"
                    value={currentConfig.risk_per_trade_percent}
                    onChange={(e) =>
                      handleConfigUpdate({
                        risk_per_trade_percent: parseFloat(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">
                    Max Daily Loss: {currentConfig.max_daily_loss_percent}%
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={currentConfig.max_daily_loss_percent}
                    onChange={(e) =>
                      handleConfigUpdate({
                        max_daily_loss_percent: parseFloat(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">
                    Max Open Positions: {currentConfig.max_open_positions}
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="10"
                    step="1"
                    value={currentConfig.max_open_positions}
                    onChange={(e) =>
                      handleConfigUpdate({
                        max_open_positions: parseInt(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Confidence Settings */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Entry Requirements
              </label>
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-slate-400">
                    Min Confidence: {currentConfig.min_confidence}%
                  </label>
                  <input
                    type="range"
                    min="50"
                    max="95"
                    step="5"
                    value={currentConfig.min_confidence}
                    onChange={(e) =>
                      handleConfigUpdate({
                        min_confidence: parseFloat(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">
                    Min Models Agree: {currentConfig.min_models_agree}
                  </label>
                  <input
                    type="range"
                    min="3"
                    max="10"
                    step="1"
                    value={currentConfig.min_models_agree}
                    onChange={(e) =>
                      handleConfigUpdate({
                        min_models_agree: parseInt(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">
                    Min Confluence: {currentConfig.min_confluence}%
                  </label>
                  <input
                    type="range"
                    min="50"
                    max="100"
                    step="5"
                    value={currentConfig.min_confluence}
                    onChange={(e) =>
                      handleConfigUpdate({
                        min_confluence: parseFloat(e.target.value),
                      })
                    }
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Trading Hours */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Trading Hours (UTC)
              </label>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <label className="text-xs text-slate-400">Start</label>
                  <select
                    value={currentConfig.trading_start_hour}
                    onChange={(e) =>
                      handleConfigUpdate({
                        trading_start_hour: parseInt(e.target.value),
                      })
                    }
                    className="input w-full"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>
                        {i.toString().padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-slate-400">End</label>
                  <select
                    value={currentConfig.trading_end_hour}
                    onChange={(e) =>
                      handleConfigUpdate({
                        trading_end_hour: parseInt(e.target.value),
                      })
                    }
                    className="input w-full"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>
                        {i.toString().padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <label className="flex items-center gap-2 mt-3">
                <input
                  type="checkbox"
                  checked={currentConfig.trade_on_weekends}
                  onChange={(e) =>
                    handleConfigUpdate({ trade_on_weekends: e.target.checked })
                  }
                  className="rounded"
                />
                <span className="text-sm">Trade on weekends</span>
              </label>
            </div>

            {/* Notifications */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Notifications
              </label>
              <div className="space-y-3">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={currentConfig.telegram_enabled}
                    onChange={(e) =>
                      handleConfigUpdate({ telegram_enabled: e.target.checked })
                    }
                    className="rounded"
                  />
                  <span className="text-sm">Telegram notifications</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={currentConfig.discord_enabled}
                    onChange={(e) =>
                      handleConfigUpdate({ discord_enabled: e.target.checked })
                    }
                    className="rounded"
                  />
                  <span className="text-sm">Discord notifications</span>
                </label>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Open Positions */}
      {currentStatus.open_positions.length > 0 && (
        <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Activity size={20} />
            Open Positions
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-400 text-sm">
                  <th className="pb-3">Symbol</th>
                  <th className="pb-3">Direction</th>
                  <th className="pb-3">Entry</th>
                  <th className="pb-3">SL</th>
                  <th className="pb-3">TP</th>
                  <th className="pb-3">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {currentStatus.open_positions.map((pos, i) => (
                  <tr key={i} className="border-t border-slate-700">
                    <td className="py-3 font-medium">{pos.symbol}</td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          pos.direction === "LONG"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-red-500/20 text-red-400"
                        }`}
                      >
                        {pos.direction}
                      </span>
                    </td>
                    <td className="py-3 font-mono">{pos.entry.toFixed(5)}</td>
                    <td className="py-3 font-mono text-red-400">{pos.sl.toFixed(5)}</td>
                    <td className="py-3 font-mono text-green-400">{pos.tp.toFixed(5)}</td>
                    <td className="py-3">{pos.confidence.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* How It Works */}
      <div className="bg-slate-800 rounded-xl border border-slate-700 p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Eye size={20} />
          Come Funziona
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-indigo-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
              <Clock className="text-indigo-400" />
            </div>
            <h4 className="font-medium mb-1">1. Analisi Periodica</h4>
            <p className="text-sm text-slate-400">
              Il bot analizza i mercati ogni 5 minuti automaticamente
            </p>
          </div>
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-purple-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
              <Eye className="text-purple-400" />
            </div>
            <h4 className="font-medium mb-1">2. AI Multi-Timeframe</h4>
            <p className="text-sm text-slate-400">
              10+ AI analizzano grafici su 3-5 timeframe diversi
            </p>
          </div>
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-green-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
              <Target className="text-green-400" />
            </div>
            <h4 className="font-medium mb-1">3. Consensus Voting</h4>
            <p className="text-sm text-slate-400">
              Trade solo se 80%+ AI concordano con alta confidence
            </p>
          </div>
          <div className="text-center p-4">
            <div className="w-12 h-12 bg-yellow-600/20 rounded-full flex items-center justify-center mx-auto mb-3">
              <Zap className="text-yellow-400" />
            </div>
            <h4 className="font-medium mb-1">4. Esecuzione Automatica</h4>
            <p className="text-sm text-slate-400">
              Ordini con SL/TP automatici sul tuo broker
            </p>
          </div>
        </div>
      </div>

      {/* Recent Errors */}
      {currentStatus.recent_errors.length > 0 && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-red-400">
            <AlertTriangle size={20} />
            Recent Errors
          </h3>
          <div className="space-y-2">
            {currentStatus.recent_errors.map((err, i) => (
              <div key={i} className="text-sm">
                <span className="text-slate-400">
                  {new Date(err.timestamp).toLocaleString()}:
                </span>{" "}
                <span className="text-red-300">{err.error}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}
