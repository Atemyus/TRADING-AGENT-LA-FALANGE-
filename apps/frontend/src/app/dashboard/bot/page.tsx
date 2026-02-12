"use client";

import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import dynamic from "next/dynamic";
import { useSearchParams } from "next/navigation";
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
  Brain,
  MessageSquare,
  Ban,
  Newspaper,
  ArrowUpCircle,
  Users,
  Server,
  Loader2,
  Flame,
  Sparkles,
} from "lucide-react";
import {
  botApi,
  brokerAccountsApi,
  BrokerAccountData,
  BrokerAccountInfo,
  BrokerBotStatus,
  BrokerPositionData,
} from "@/lib/api";

// Dynamic import for TradingView widget
const TradingViewWidget = dynamic(
  () => import("@/components/charts/TradingViewWidget"),
  { ssr: false, loading: () => <div className="h-[300px] bg-dark-900 rounded-xl animate-pulse" /> }
);

// ============ AI Reasoning Panel ============

interface AnalysisLog {
  timestamp: string;
  symbol: string;
  type: string;
  message: string;
  details: Record<string, unknown> | null;
}

interface AIReasoningPanelProps {
  brokerId?: number;
  brokerName?: string;
  compact?: boolean;
}

function AIReasoningPanel({ brokerId, brokerName, compact = false }: AIReasoningPanelProps) {
  const [logs, setLogs] = React.useState<AnalysisLog[]>([]);
  const [autoScroll, setAutoScroll] = React.useState(true);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const prevLengthRef = React.useRef(0);

  // Poll for logs every 3 seconds
  React.useEffect(() => {
    const fetchLogs = async () => {
      try {
        // Use broker-specific logs if brokerId is provided
        if (brokerId) {
          const data = await brokerAccountsApi.getLogs(brokerId, 50);
          setLogs(data.logs);
        } else {
          const data = await botApi.getLogs(50);
          setLogs(data.logs);
        }
      } catch {
        // silently ignore
      }
    };
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [brokerId]);

  // Auto-scroll to bottom when new logs arrive
  React.useEffect(() => {
    if (autoScroll && scrollRef.current && logs.length > prevLengthRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
    prevLengthRef.current = logs.length;
  }, [logs, autoScroll]);

  const getLogIcon = (type: string) => {
    switch (type) {
      case 'analysis': return <Brain size={14} className="text-purple-400" />;
      case 'trade': return <ArrowUpCircle size={14} className="text-green-400" />;
      case 'skip': return <Ban size={14} className="text-yellow-400" />;
      case 'error': return <XCircle size={14} className="text-red-400" />;
      case 'news': return <Newspaper size={14} className="text-orange-400" />;
      default: return <MessageSquare size={14} className="text-slate-400" />;
    }
  };

  const getLogColor = (type: string) => {
    switch (type) {
      case 'analysis': return 'text-purple-300';
      case 'trade': return 'text-green-300';
      case 'skip': return 'text-yellow-300';
      case 'error': return 'text-red-300';
      case 'news': return 'text-orange-300';
      default: return 'text-slate-300';
    }
  };

  return (
    <div className={`prometheus-panel-surface ${compact ? 'p-4' : 'p-6'}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className={`${compact ? 'text-sm' : 'text-lg'} font-semibold flex items-center gap-2`}>
          <Brain size={compact ? 16 : 20} className="text-purple-400" />
          {brokerName ? `AI Reasoning - ${brokerName}` : 'AI Reasoning - Analisi in Tempo Reale'}
        </h3>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400">{logs.length} log</span>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`text-xs px-2 py-1 rounded ${autoScroll ? 'bg-purple-500/20 text-purple-400' : 'bg-slate-700 text-slate-400'}`}
          >
            Auto-scroll {autoScroll ? 'ON' : 'OFF'}
          </button>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-xs text-green-400">Live</span>
          </div>
        </div>
      </div>
      <div
        ref={scrollRef}
        className={`bg-dark-900/80 rounded-lg p-3 ${compact ? 'max-h-[250px]' : 'max-h-[400px]'} overflow-y-auto font-mono text-xs space-y-1 border border-dark-700/50`}
        onScroll={() => {
          if (scrollRef.current) {
            const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
            setAutoScroll(scrollHeight - scrollTop - clientHeight < 50);
          }
        }}
      >
        {logs.length === 0 ? (
          <div className={`text-center text-slate-500 ${compact ? 'py-4' : 'py-8'}`}>
            <Brain size={compact ? 24 : 32} className="mx-auto mb-2 opacity-50" />
            <p>In attesa delle analisi AI...</p>
            <p className="text-xs mt-1">I log appariranno quando il bot inizia l&apos;analisi</p>
          </div>
        ) : (
          logs.map((log, i) => (
            <div
              key={`${log.timestamp}-${i}`}
              className={`flex items-start gap-2 py-1 px-2 rounded hover:bg-slate-800/50 ${
                log.type === 'trade' ? 'bg-green-500/5 border-l-2 border-green-500' :
                log.type === 'error' ? 'bg-red-500/5 border-l-2 border-red-500' :
                ''
              }`}
            >
              <span className="flex-shrink-0 mt-0.5">{getLogIcon(log.type)}</span>
              <span className="text-slate-500 flex-shrink-0">
                {new Date(log.timestamp).toLocaleTimeString('it-IT')}
              </span>
              <span className="text-cyan-400 flex-shrink-0 font-bold">
                [{log.symbol}]
              </span>
              <span className={getLogColor(log.type)}>
                {log.message}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// Reusable Toggle Component
function Toggle({
  enabled,
  onChange,
  disabled = false,
}: {
  enabled: boolean;
  onChange: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={onChange}
      disabled={disabled}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${
        enabled ? "bg-indigo-600" : "bg-slate-600"
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          enabled ? "translate-x-5" : "translate-x-0"
        }`}
      />
    </button>
  );
}

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
  // TradingView AI Agent (always enabled - the only analysis method)
  tradingview_headless: boolean;
  tradingview_max_indicators: number;
  // AI Models
  enabled_models: string[];
}

const AVAILABLE_SYMBOLS = [
  // ============ FOREX MAJORS ============
  "EUR/USD",
  "GBP/USD",
  "USD/JPY",
  "USD/CHF",
  "AUD/USD",
  "USD/CAD",
  "NZD/USD",
  // ============ FOREX CROSS ============
  "EUR/GBP",
  "EUR/JPY",
  "GBP/JPY",
  "EUR/CHF",
  "EUR/AUD",
  "EUR/CAD",
  "GBP/CHF",
  "GBP/AUD",
  "AUD/JPY",
  "AUD/CAD",
  "AUD/NZD",
  "CAD/JPY",
  "NZD/JPY",
  "CHF/JPY",
  // ============ METALS ============
  "XAU/USD",
  "XAG/USD",
  // ============ COMMODITIES ============
  "WTI/USD",
  "BRENT/USD",
  // ============ US INDICES ============
  "US30",
  "US500",
  "NAS100",
  // ============ EUROPEAN INDICES ============
  "DE40",
  "UK100",
  "FR40",
  "EU50",
  // ============ ASIAN INDICES ============
  "JP225",
  "HK50",
  "AU200",
];

const ANALYSIS_MODES = [
  { value: "quick", label: "Quick", description: "1 timeframe, fastest models" },
  { value: "standard", label: "Standard", description: "2 timeframes, 3 models" },
  { value: "premium", label: "Premium", description: "3 timeframes + vision AI" },
  { value: "ultra", label: "Ultra", description: "5 timeframes + all models" },
];

export default function BotControlPage() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [config, setConfig] = useState<BotConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActioning, setIsActioning] = useState(false);
  const [showConfig, setShowConfig] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewSymbol, setPreviewSymbol] = useState<string>("EUR/USD");

  // Multi-broker state
  const [brokers, setBrokers] = useState<BrokerAccountData[]>([]);
  const [brokerStatuses, setBrokerStatuses] = useState<Record<number, BrokerBotStatus>>({});
  const [brokerAccountInfo, setBrokerAccountInfo] = useState<Record<number, BrokerAccountInfo>>({});
  const [brokerPositions, setBrokerPositions] = useState<Record<number, BrokerPositionData[]>>({});
  const [brokerBalances, setBrokerBalances] = useState<Record<number, { balance: number | null; equity: number | null }>>({});
  const [selectedBrokerId, setSelectedBrokerId] = useState<number | null>(null);
  const [brokerLoading, setBrokerLoading] = useState<Record<number, boolean>>({});

  useEffect(() => {
    const brokerIdParam = Number(searchParams.get("brokerId") || "");
    if (!Number.isNaN(brokerIdParam) && brokerIdParam > 0) {
      setSelectedBrokerId(brokerIdParam);
      return;
    }

    if (typeof window !== "undefined") {
      const stored = Number(localStorage.getItem("selected_broker_id") || "");
      if (!Number.isNaN(stored) && stored > 0) {
        setSelectedBrokerId(stored);
      }
    }
  }, [searchParams]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    if (selectedBrokerId && selectedBrokerId > 0) {
      localStorage.setItem("selected_broker_id", String(selectedBrokerId));
    } else {
      localStorage.removeItem("selected_broker_id");
    }
    window.dispatchEvent(new Event("selected-broker-changed"));
  }, [selectedBrokerId]);

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
    // TradingView AI Agent - full browser control (always enabled)
    tradingview_headless: true,
    tradingview_max_indicators: 2,  // TradingView Free plan limit
    enabled_models: ["chatgpt", "gemini", "grok", "qwen", "llama", "ernie", "kimi", "mistral"],
  };

  const resolveDailyPnl = (brokerId: number, statusData?: BrokerBotStatus | null) => {
    const statusPnl = statusData?.statistics?.daily_pnl;
    if (typeof statusPnl === "number" && Number.isFinite(statusPnl)) {
      return statusPnl;
    }

    const accountInfo = brokerAccountInfo[brokerId];
    if (typeof accountInfo?.realized_pnl_today === "number" && Number.isFinite(accountInfo.realized_pnl_today)) {
      return accountInfo.realized_pnl_today;
    }
    if (typeof accountInfo?.unrealized_pnl === "number" && Number.isFinite(accountInfo.unrealized_pnl)) {
      return accountInfo.unrealized_pnl;
    }

    return 0;
  };

  const resolveOpenPositions = (brokerId: number, statusData?: BrokerBotStatus | null) => {
    const livePositions = brokerPositions[brokerId];
    if (Array.isArray(livePositions)) {
      return livePositions.length;
    }

    const statusPositions = statusData?.statistics?.open_positions;
    if (typeof statusPositions === "number" && Number.isFinite(statusPositions)) {
      return statusPositions;
    }

    const accountPositions = brokerAccountInfo[brokerId]?.open_positions;
    if (typeof accountPositions === "number" && Number.isFinite(accountPositions)) {
      return accountPositions;
    }

    return 0;
  };

  const fetchStatus = useCallback(async () => {
    try {
      const data = await botApi.getStatus();
      // API returns: status, started_at, last_analysis_at, config, statistics, open_positions, recent_errors
      setStatus({
        status: data.status || 'stopped',
        started_at: data.started_at || null,
        last_analysis_at: data.last_analysis_at || null,
        config: data.config || {
          symbols: ['EUR/USD'],
          analysis_mode: 'standard',
          min_confidence: 75,
          risk_per_trade: 1,
          max_positions: 3,
        },
        statistics: data.statistics || {
          analyses_today: 0,
          trades_today: 0,
          daily_pnl: 0,
          open_positions: 0,
        },
        open_positions: data.open_positions || [],
        recent_errors: data.recent_errors || [],
      });
    } catch {
      setStatus(demoStatus);
    }
  }, []);

  const fetchConfig = useCallback(async () => {
    try {
      const data = await botApi.getConfig() as BotConfig;
      setConfig(data);
    } catch {
      setConfig(demoConfig);
    }
    setIsLoading(false);
  }, []);

  // Fetch all broker accounts
  const fetchBrokers = useCallback(async () => {
    try {
      const data = await brokerAccountsApi.list();
      setBrokers(data);

      // Fetch status, account and positions for every broker (enabled or disabled)
      const statuses: Record<number, BrokerBotStatus> = {};
      const accounts: Record<number, BrokerAccountInfo> = {};
      const positionsByBroker: Record<number, BrokerPositionData[]> = {};
      const balances: Record<number, { balance: number | null; equity: number | null }> = {};

      const entries = await Promise.all(
        data.map(async (broker) => {
          const [statusResult, accountResult, positionsResult] = await Promise.allSettled([
            brokerAccountsApi.getBotStatus(broker.id),
            brokerAccountsApi.getAccountInfo(broker.id),
            brokerAccountsApi.getPositions(broker.id),
          ]);

          return {
            broker,
            status: statusResult.status === "fulfilled" ? statusResult.value : null,
            account: accountResult.status === "fulfilled" ? accountResult.value : null,
            positions:
              positionsResult.status === "fulfilled"
                ? (positionsResult.value.positions || [])
                : [],
          };
        }),
      );

      for (const entry of entries) {
        const { broker, status, account, positions } = entry;
        const derivedDailyPnl =
          typeof status?.statistics?.daily_pnl === "number"
            ? status.statistics.daily_pnl
            : typeof account?.realized_pnl_today === "number"
              ? account.realized_pnl_today
              : (account?.unrealized_pnl ?? 0);
        const derivedOpenPositions =
          positions.length > 0
            ? positions.length
            : typeof status?.statistics?.open_positions === "number"
              ? status.statistics.open_positions
              : (account?.open_positions ?? 0);

        statuses[broker.id] = status || {
          broker_id: broker.id,
          name: broker.name,
          status: broker.is_enabled ? "stopped" : "disabled",
          is_enabled: broker.is_enabled,
          is_connected: broker.is_connected,
          statistics: {
            analyses_today: 0,
            trades_today: 0,
            daily_pnl: derivedDailyPnl,
            open_positions: derivedOpenPositions,
          },
          config: {
            symbols: broker.symbols,
            analysis_mode: broker.analysis_mode,
            analysis_interval: broker.analysis_interval_seconds,
            enabled_models: broker.enabled_models,
          },
        };

        if (account) {
          accounts[broker.id] = account;
          balances[broker.id] = {
            balance: account.balance ?? null,
            equity: account.equity ?? null,
          };
        }
        positionsByBroker[broker.id] = positions;
      }

      setBrokerStatuses(statuses);
      setBrokerAccountInfo(accounts);
      setBrokerPositions(positionsByBroker);
      setBrokerBalances(balances);
    } catch {
      setBrokers([]);
      setBrokerStatuses({});
      setBrokerAccountInfo({});
      setBrokerPositions({});
      setBrokerBalances({});
    }
  }, []);

  // Start a specific broker
  const handleStartBroker = async (brokerId: number) => {
    setBrokerLoading(prev => ({ ...prev, [brokerId]: true }));
    try {
      await brokerAccountsApi.startBot(brokerId);
      await fetchBrokers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start broker");
    }
    setBrokerLoading(prev => ({ ...prev, [brokerId]: false }));
  };

  // Stop a specific broker
  const handleStopBroker = async (brokerId: number) => {
    setBrokerLoading(prev => ({ ...prev, [brokerId]: true }));
    try {
      await brokerAccountsApi.stopBot(brokerId);
      await fetchBrokers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop broker");
    }
    setBrokerLoading(prev => ({ ...prev, [brokerId]: false }));
  };

  // Pause a specific broker (stops new trades, keeps monitoring)
  const handlePauseBroker = async (brokerId: number) => {
    setBrokerLoading(prev => ({ ...prev, [brokerId]: true }));
    try {
      await brokerAccountsApi.pauseBot(brokerId);
      await fetchBrokers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to pause broker");
    }
    setBrokerLoading(prev => ({ ...prev, [brokerId]: false }));
  };

  // Resume a specific broker after pause
  const handleResumeBroker = async (brokerId: number) => {
    setBrokerLoading(prev => ({ ...prev, [brokerId]: true }));
    try {
      await brokerAccountsApi.resumeBot(brokerId);
      await fetchBrokers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to resume broker");
    }
    setBrokerLoading(prev => ({ ...prev, [brokerId]: false }));
  };

  // Start all enabled brokers
  const handleStartAllBrokers = async () => {
    setIsActioning(true);
    try {
      await brokerAccountsApi.startAll();
      await fetchBrokers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start all brokers");
    }
    setIsActioning(false);
  };

  // Stop all brokers
  const handleStopAllBrokers = async () => {
    setIsActioning(true);
    try {
      await brokerAccountsApi.stopAll();
      await fetchBrokers();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to stop all brokers");
    }
    setIsActioning(false);
  };

  useEffect(() => {
    fetchStatus();
    fetchConfig();
    fetchBrokers();

    // Poll status every 5 seconds
    const interval = setInterval(() => {
      fetchStatus();
      fetchBrokers();
    }, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchConfig, fetchBrokers]);

  useEffect(() => {
    if (!selectedBrokerId) return;
    if (brokers.length > 0 && !brokers.some((b) => b.id === selectedBrokerId)) {
      setSelectedBrokerId(null);
    }
  }, [brokers, selectedBrokerId]);

  const handleConfigUpdate = async (updates: Partial<BotConfig>) => {
    try {
      await botApi.updateConfig(updates);
      await fetchConfig();
    } catch (e) {
      console.error("Failed to update config:", e);
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
  const scopedLivePositions = selectedBrokerId
    ? (brokerPositions[selectedBrokerId] || [])
    : Object.values(brokerPositions).flat();
  const scopedTodayPnl = selectedBrokerId
    ? resolveDailyPnl(selectedBrokerId, brokerStatuses[selectedBrokerId])
    : brokers.reduce((sum, broker) => sum + resolveDailyPnl(broker.id, brokerStatuses[broker.id]), 0);
  const scopedOpenPositions = selectedBrokerId
    ? resolveOpenPositions(selectedBrokerId, brokerStatuses[selectedBrokerId])
    : scopedLivePositions.length;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="space-y-6 prometheus-page-shell"
    >
      {/* Header */}
      <div className="prometheus-hero-card p-6 md:p-7">
        <div className="relative z-10 flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="prometheus-chip">
                <Flame size={12} />
                Auto Bot
              </span>
              <span className="prometheus-chip prometheus-chip-imperial">
                <Sparkles size={12} />
                Multi Broker Engine
              </span>
            </div>
            <h1 className="text-3xl font-bold text-gradient-falange mb-2">Autonomous Execution Hub</h1>
            <p className="text-dark-300 max-w-2xl">
              Control runtime status, broker-level execution, risk rules and AI model orchestration from one panel.
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="prometheus-panel-surface p-4">
          <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Scope</p>
          <p className="text-lg font-semibold text-dark-100">
            {selectedBrokerId
              ? (brokers.find((broker) => broker.id === selectedBrokerId)?.name || "Selected broker")
              : "All broker workspaces"}
          </p>
        </div>
        <div className="prometheus-panel-surface p-4">
          <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Today P&L</p>
          <p className={`text-2xl font-bold font-mono ${scopedTodayPnl >= 0 ? "text-profit" : "text-loss"}`}>
            {scopedTodayPnl >= 0 ? "+" : ""}${scopedTodayPnl.toFixed(2)}
          </p>
        </div>
        <div className="prometheus-panel-surface p-4">
          <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Open Positions</p>
          <p className="text-2xl font-bold font-mono text-dark-100">{scopedOpenPositions}</p>
        </div>
      </div>

      {/* Multi-Broker Panel */}
      {brokers.length > 0 && (
        <div className="prometheus-panel-surface p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-indigo-500/20 rounded-lg">
                <Server size={20} className="text-indigo-400" />
              </div>
              <div className="text-left">
                <h3 className="font-semibold flex items-center gap-2">
                  Broker Accounts
                  <span className="text-xs px-2 py-0.5 bg-slate-700 rounded-full text-slate-300">
                    {brokers.length} configurati
                  </span>
                </h3>
                <p className="text-sm text-slate-400">
                  {Object.values(brokerStatuses).filter(s => s?.status === 'running').length} in esecuzione
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={handleStartAllBrokers}
                disabled={isActioning}
                className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
              >
                <Play size={14} />
                Avvia Tutti
              </button>
              <button
                onClick={handleStopAllBrokers}
                disabled={isActioning}
                className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
              >
                <Square size={14} />
                Ferma Tutti
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {brokers.map((broker) => {
              const brokerStatus = brokerStatuses[broker.id];
              const isRunning = brokerStatus?.status === 'running';
              const isPaused = brokerStatus?.status === 'paused';
              const isLoading = brokerLoading[broker.id];
              const isSelected = selectedBrokerId === broker.id;
              const brokerDailyPnl = resolveDailyPnl(broker.id, brokerStatus);
              const brokerOpenPositions = resolveOpenPositions(broker.id, brokerStatus);

              return (
                <motion.div
                  key={broker.id}
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`p-4 rounded-lg border transition-colors cursor-pointer ${
                    isSelected
                      ? 'bg-indigo-500/10 border-indigo-500'
                      : 'bg-dark-900/70 border-dark-700 hover:border-primary-500/35'
                  }`}
                  onClick={() => setSelectedBrokerId(isSelected ? null : broker.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-3 h-3 rounded-full ${
                        isRunning ? 'bg-green-500 animate-pulse' :
                        isPaused ? 'bg-yellow-500' :
                        broker.is_enabled ? 'bg-slate-500' : 'bg-slate-700'
                      }`} />

                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium">{broker.name}</h4>
                          {!broker.is_enabled && (
                            <span className="text-xs px-1.5 py-0.5 bg-slate-700 rounded text-slate-400">
                              Disabilitato
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          {broker.symbols.slice(0, 3).join(', ')}
                          {broker.symbols.length > 3 && ` +${broker.symbols.length - 3}`}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3">
                      {brokerBalances[broker.id]?.balance != null && (
                        <div className="text-center px-3 py-1 bg-indigo-500/10 rounded-lg border border-indigo-500/30">
                          <p className="text-indigo-400 text-xs">Balance</p>
                          <p className="font-bold text-indigo-300">
                            ${brokerBalances[broker.id].balance?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </p>
                        </div>
                      )}

                      {brokerStatus && (
                        <div className="flex items-center gap-4 text-sm">
                          <div className="text-center">
                            <p className="text-slate-400 text-xs">Analisi</p>
                            <p className="font-medium">{brokerStatus.statistics?.analyses_today || 0}</p>
                          </div>
                          <div className="text-center">
                            <p className="text-slate-400 text-xs">Trade</p>
                            <p className="font-medium">{brokerStatus.statistics?.trades_today || 0}</p>
                          </div>
                          <div className="text-center">
                            <p className="text-slate-400 text-xs">P&L</p>
                            <p className={`font-medium ${
                              brokerDailyPnl >= 0 ? 'text-profit' : 'text-loss'
                            }`}>
                              {brokerDailyPnl >= 0 ? "+" : ""}${brokerDailyPnl.toFixed(2)}
                            </p>
                          </div>
                        </div>
                      )}

                      {broker.is_enabled && (
                        <div className="flex items-center gap-2">
                          {isRunning ? (
                            <>
                              <button
                                onClick={(e) => { e.stopPropagation(); handlePauseBroker(broker.id); }}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                              >
                                {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Pause size={14} />}
                                Pause
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleStopBroker(broker.id); }}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                              >
                                {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Square size={14} />}
                                Stop
                              </button>
                            </>
                          ) : isPaused ? (
                            <>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleResumeBroker(broker.id); }}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                              >
                                {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                                Resume
                              </button>
                              <button
                                onClick={(e) => { e.stopPropagation(); handleStopBroker(broker.id); }}
                                disabled={isLoading}
                                className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                              >
                                {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Square size={14} />}
                                Stop
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={(e) => { e.stopPropagation(); handleStartBroker(broker.id); }}
                              disabled={isLoading}
                              className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg flex items-center gap-1.5 disabled:opacity-50"
                            >
                              {isLoading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
                              Start
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {isSelected && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="mt-4 pt-4 border-t border-slate-700"
                    >
                      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 mb-4">
                        <div className="bg-slate-800 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-slate-400 mb-1">
                            <Zap size={14} />
                            <span className="text-xs">Analisi Oggi</span>
                          </div>
                          <p className="text-xl font-bold">{brokerStatus?.statistics?.analyses_today || 0}</p>
                        </div>
                        <div className="bg-slate-800 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-slate-400 mb-1">
                            <BarChart3 size={14} />
                            <span className="text-xs">Trade Oggi</span>
                          </div>
                          <p className="text-xl font-bold">{brokerStatus?.statistics?.trades_today || 0}</p>
                        </div>
                        <div className="bg-slate-800 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-slate-400 mb-1">
                            <DollarSign size={14} />
                            <span className="text-xs">P&L Giornaliero</span>
                          </div>
                          <p className={`text-xl font-bold ${
                            brokerDailyPnl >= 0 ? 'text-profit' : 'text-loss'
                          }`}>
                            {brokerDailyPnl >= 0 ? "+" : ""}${brokerDailyPnl.toFixed(2)}
                          </p>
                        </div>
                        <div className="bg-slate-800 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-slate-400 mb-1">
                            <Activity size={14} />
                            <span className="text-xs">Posizioni Aperte</span>
                          </div>
                          <p className="text-xl font-bold">{brokerOpenPositions}</p>
                        </div>
                        <div className="bg-slate-800 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-slate-400 mb-1">
                            <Clock size={14} />
                            <span className="text-xs">Intervallo</span>
                          </div>
                          <p className="text-xl font-bold">{brokerStatus?.config?.analysis_interval ? `${Math.floor(brokerStatus.config.analysis_interval / 60)}m` : '-'}</p>
                        </div>
                        <div className="bg-slate-800 rounded-lg p-3">
                          <div className="flex items-center gap-2 text-slate-400 mb-1">
                            <Brain size={14} />
                            <span className="text-xs">Modelli AI</span>
                          </div>
                          <p className="text-xl font-bold">{brokerStatus?.config?.enabled_models?.length || 8}</p>
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2 mb-4">
                        <span className="px-2 py-1 bg-purple-500/20 text-purple-300 text-xs rounded-full capitalize">
                          Modalita: {brokerStatus?.config?.analysis_mode || broker.analysis_mode}
                        </span>
                        <span className="px-2 py-1 bg-blue-500/20 text-blue-300 text-xs rounded-full">
                          Risk: {broker.risk_per_trade_percent}%
                        </span>
                        <span className="px-2 py-1 bg-green-500/20 text-green-300 text-xs rounded-full">
                          Max Posizioni: {broker.max_open_positions}
                        </span>
                        <span className="px-2 py-1 bg-orange-500/20 text-orange-300 text-xs rounded-full">
                          Orario: {broker.trading_start_hour}:00 - {broker.trading_end_hour}:00 UTC
                        </span>
                      </div>

                      {brokerStatus?.last_error && (
                        <div className="mb-4 p-2 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
                          <AlertTriangle size={14} className="inline mr-1" />
                          {brokerStatus.last_error}
                        </div>
                      )}

                      {isRunning && (
                        <div className="mt-4">
                          <AIReasoningPanel
                            brokerId={broker.id}
                            brokerName={broker.name}
                            compact={true}
                          />
                        </div>
                      )}
                    </motion.div>
                  )}
                </motion.div>
              );
            })}

            {brokers.filter(b => b.is_enabled).length === 0 && (
              <div className="text-center py-6 text-slate-400">
                <Users size={32} className="mx-auto mb-2 opacity-50" />
                <p>Nessun broker abilitato</p>
                <p className="text-sm">Vai su Settings -&gt; Broker Accounts per configurare</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Chart Preview */}
      <div className="prometheus-panel-surface p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <BarChart3 size={20} />
            Chart Preview
          </h3>
          <div className="flex items-center gap-2">
            {currentConfig.symbols.map((symbol) => (
              <button
                key={symbol}
                onClick={() => setPreviewSymbol(symbol)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  previewSymbol === symbol
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                }`}
              >
                {symbol}
              </button>
            ))}
          </div>
        </div>
        <TradingViewWidget
          symbol={previewSymbol}
          interval="15"
          height={350}
          theme="dark"
          allowSymbolChange={false}
          showToolbar={true}
          showDrawingTools={false}
        />
      </div>

      {/* Configuration Panel */}
      {showConfig && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          className="prometheus-panel-surface p-6"
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
                  <label className="text-xs text-slate-400 block mb-1">
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
                    className="range-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
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
                    className="range-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
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
                    className="range-input"
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
                  <label className="text-xs text-slate-400 block mb-1">
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
                    className="range-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
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
                    className="range-input"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400 block mb-1">
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
                    className="range-input"
                  />
                </div>
              </div>
            </div>

            {/* Analysis Interval */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Intervallo Analisi
              </label>
              <p className="text-xs text-slate-400 mb-3">
                Frequenza con cui il bot analizza i mercati (riduce consumo API)
              </p>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { value: 300, label: "5 min", desc: "Piu reattivo" },
                  { value: 600, label: "10 min", desc: "Bilanciato" },
                  { value: 900, label: "15 min", desc: "Moderato" },
                  { value: 1800, label: "30 min", desc: "Economico" },
                  { value: 3600, label: "1 ora", desc: "Risparmio" },
                  { value: 7200, label: "2 ore", desc: "Minimo" },
                ].map((interval) => (
                  <button
                    key={interval.value}
                    onClick={() => handleConfigUpdate({ analysis_interval_seconds: interval.value })}
                    className={`px-3 py-2 rounded-lg text-sm transition-colors ${
                      currentConfig.analysis_interval_seconds === interval.value
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-700 text-slate-300 hover:bg-slate-600"
                    }`}
                  >
                    <div className="font-medium">{interval.label}</div>
                    <div className="text-[10px] opacity-70">{interval.desc}</div>
                  </button>
                ))}
              </div>
              <p className="text-xs text-slate-500 mt-2">
                Nota: i simboli con posizioni aperte vengono automaticamente saltati
              </p>
            </div>

            {/* Trading Hours */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Trading Hours (UTC)
              </label>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <label className="text-xs text-slate-400 block mb-1">Start</label>
                  <select
                    value={currentConfig.trading_start_hour}
                    onChange={(e) =>
                      handleConfigUpdate({
                        trading_start_hour: parseInt(e.target.value),
                      })
                    }
                    className="select-input"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>
                        {i.toString().padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex-1">
                  <label className="text-xs text-slate-400 block mb-1">End</label>
                  <select
                    value={currentConfig.trading_end_hour}
                    onChange={(e) =>
                      handleConfigUpdate({
                        trading_end_hour: parseInt(e.target.value),
                      })
                    }
                    className="select-input"
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>
                        {i.toString().padStart(2, "0")}:00
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="flex items-center gap-3 mt-3">
                <Toggle
                  enabled={currentConfig.trade_on_weekends}
                  onChange={() =>
                    handleConfigUpdate({ trade_on_weekends: !currentConfig.trade_on_weekends })
                  }
                />
                <span className="text-sm">Trade on weekends</span>
              </div>
            </div>

            {/* TradingView AI Agent - Always Enabled */}
            <div className="md:col-span-2 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
              <div className="flex items-center gap-3 mb-3">
                <BarChart3 size={20} className="text-purple-400" />
                <div>
                  <label className="block text-sm font-medium">
                    TradingView AI Agent
                  </label>
                  <p className="text-xs text-slate-400">
                    AI controls real TradingView charts via browser automation
                  </p>
                </div>
              </div>
              <div className="mt-3 pt-3 border-t border-purple-500/30 space-y-4">
                {/* TradingView Free Plan Info */}
                <div>
                  <label className="block text-xs text-slate-400 mb-2">
                    TradingView Free Plan - Max 2 Indicators
                  </label>
                  <div className="bg-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300">
                    Ogni AI puo aggiungere fino a 2 indicatori sul grafico (limite piano Free)
                  </div>
                </div>

                {/* Headless Mode */}
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm">Headless Mode</span>
                    <p className="text-xs text-slate-500">Run browser in background (faster)</p>
                  </div>
                  <Toggle
                    enabled={currentConfig.tradingview_headless}
                    onChange={() =>
                      handleConfigUpdate({ tradingview_headless: !currentConfig.tradingview_headless })
                    }
                  />
                </div>

                <p className="text-xs text-slate-500 mt-2">
                  AI can add indicators, draw zones/trendlines, and take screenshots on TradingView.com
                </p>

                {/* AI Models Toggle */}
                <div className="mt-4 pt-3 border-t border-purple-500/30">
                  <label className="block text-sm font-medium mb-3">
                    Modelli AI Attivi
                  </label>
                  <div className="space-y-2">
                    {[
                      { key: "chatgpt", name: "ChatGPT 5.2", style: "SMC / Order Blocks", provider: "AIML" },
                      { key: "gemini", name: "Gemini 3 Pro", style: "Trend / MACD", provider: "AIML" },
                      { key: "grok", name: "Grok 4.1 Fast", style: "Volatility / Bollinger", provider: "AIML" },
                      { key: "qwen", name: "Qwen3 VL", style: "Ichimoku / RSI", provider: "AIML" },
                      { key: "llama", name: "Llama 4 Scout", style: "Momentum / Stochastic", provider: "AIML" },
                      { key: "ernie", name: "ERNIE 4.5 VL", style: "Price Action / Volume", provider: "AIML" },
                      { key: "kimi", name: "Kimi K2.5", style: "Multi-Strategy / Adaptive", provider: "NVIDIA" },
                      { key: "mistral", name: "Mistral Large 3", style: "Quantitative / Statistical", provider: "NVIDIA" },
                    ].map((model) => {
                      const ALL_MODELS = ["chatgpt", "gemini", "grok", "qwen", "llama", "ernie", "kimi", "mistral"];
                      const currentModels = currentConfig.enabled_models && currentConfig.enabled_models.length > 0
                        ? currentConfig.enabled_models
                        : ALL_MODELS;
                      const isEnabled = currentModels.includes(model.key);
                      const isLastEnabled = isEnabled && currentModels.length <= 1;

                      return (
                        <div key={model.key} className="flex items-center justify-between py-1.5 px-2 rounded-lg hover:bg-slate-700/50">
                          <div className="flex flex-col">
                            <div className="flex items-center gap-2">
                              <span className={`text-sm font-medium ${isEnabled ? "text-white" : "text-slate-500 line-through"}`}>
                                {model.name}
                              </span>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                                model.provider === "NVIDIA"
                                  ? "bg-green-500/20 text-green-400"
                                  : "bg-blue-500/20 text-blue-400"
                              }`}>
                                {model.provider}
                              </span>
                            </div>
                            <span className={`text-xs ${isEnabled ? "text-slate-400" : "text-slate-600"}`}>
                              {model.style}
                            </span>
                          </div>
                          <Toggle
                            enabled={isEnabled}
                            disabled={isLastEnabled}
                            onChange={() => {
                              if (isLastEnabled) return;
                              const updated = isEnabled
                                ? currentModels.filter((k: string) => k !== model.key)
                                : [...currentModels, model.key];
                              handleConfigUpdate({ enabled_models: updated });
                            }}
                          />
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    Almeno 1 modello deve restare attivo. I modelli disabilitati non verranno utilizzati nelle analisi.
                  </p>
                </div>
              </div>
            </div>

            {/* Notifications */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Notifications
              </label>
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <Toggle
                    enabled={currentConfig.telegram_enabled}
                    onChange={() =>
                      handleConfigUpdate({ telegram_enabled: !currentConfig.telegram_enabled })
                    }
                  />
                  <span className="text-sm">Telegram notifications</span>
                </div>
                <div className="flex items-center gap-3">
                  <Toggle
                    enabled={currentConfig.discord_enabled}
                    onChange={() =>
                      handleConfigUpdate({ discord_enabled: !currentConfig.discord_enabled })
                    }
                  />
                  <span className="text-sm">Discord notifications</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* AI Reasoning Panel - Live Analysis Logs */}
      {currentStatus.status === 'running' && (
        <AIReasoningPanel />
      )}

      {/* Open Positions */}
      <div className="prometheus-panel-surface p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity size={20} />
          Open Positions (Live Broker Feed)
        </h3>

        {scopedLivePositions.length === 0 ? (
          <div className="rounded-xl border border-dark-700/70 bg-dark-950/40 p-6 text-center">
            <p className="text-sm text-dark-300">No open positions for the current scope.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-slate-400 text-sm">
                  <th className="pb-3">Symbol</th>
                  <th className="pb-3">Broker</th>
                  <th className="pb-3">Direction</th>
                  <th className="pb-3">Entry</th>
                  <th className="pb-3">Current</th>
                  <th className="pb-3">Size</th>
                  <th className="pb-3 text-right">Unrealized P&L</th>
                  <th className="pb-3 text-right">P&L %</th>
                </tr>
              </thead>
              <tbody>
                {scopedLivePositions.map((pos) => {
                  const pnl = Number.parseFloat(pos.unrealized_pnl || "0");
                  const pnlPercent = Number.parseFloat(pos.unrealized_pnl_percent || "0");
                  const isProfit = pnl >= 0;
                  const direction = String(pos.side).toUpperCase().includes("LONG") ? "LONG" : "SHORT";

                  return (
                    <tr key={`${pos.broker_id}-${pos.position_id}`} className="border-t border-slate-700">
                      <td className="py-3 font-medium">{pos.symbol}</td>
                      <td className="py-3 text-slate-400">{pos.broker_name}</td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-1 rounded text-xs ${
                            direction === "LONG"
                              ? "bg-profit/20 text-profit"
                              : "bg-loss/20 text-loss"
                          }`}
                        >
                          {direction}
                        </span>
                      </td>
                      <td className="py-3 font-mono">{Number(pos.entry_price).toFixed(5)}</td>
                      <td className="py-3 font-mono">{Number(pos.current_price).toFixed(5)}</td>
                      <td className="py-3 font-mono">{Number(pos.size).toFixed(2)}</td>
                      <td className={`py-3 text-right font-mono font-semibold ${isProfit ? "text-profit" : "text-loss"}`}>
                        {isProfit ? "+" : ""}${pnl.toFixed(2)}
                      </td>
                      <td className={`py-3 text-right font-mono ${isProfit ? "text-profit" : "text-loss"}`}>
                        {pnlPercent >= 0 ? "+" : ""}{pnlPercent.toFixed(2)}%
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* How It Works */}
      <div className="prometheus-panel-surface p-6">
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

