'use client'

import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Settings,
  Activity,
  Bell,
  Menu,
  Bot,
  Brain,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Flame,
  ChevronRight,
  Shield,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { brokerAccountsApi } from '@/lib/api'
import { MusicPlayer } from '@/components/common/MusicPlayer'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { useAuth } from '@/contexts/AuthContext'
import { LogOut, User } from 'lucide-react'

const navItems = [
  { href: '/dashboard', label: 'Command Center', icon: LayoutDashboard },
  { href: '/dashboard/bot', label: 'Auto Bot', icon: Bot },
  { href: '/dashboard/ai-analysis', label: 'AI Analysis', icon: Brain },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [accountData, setAccountData] = useState<{ balance: number | null; todayPnl: number | null } | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [selectedBrokerId, setSelectedBrokerId] = useState<number | null>(null)
  const [selectedBrokerSnapshot, setSelectedBrokerSnapshot] = useState<{
    brokerId: number
    isDisabled: boolean
    balance: number | null
    todayPnl: number | null
  } | null>(null)
  const { user, logout } = useAuth()

  useEffect(() => {
    if (typeof window === 'undefined') return
    const updateSelectedBroker = () => {
      const raw = localStorage.getItem('selected_broker_id')
      const parsed = Number(raw || '')
      if (!Number.isNaN(parsed) && parsed > 0) {
        setSelectedBrokerId(parsed)
      } else {
        setSelectedBrokerId(null)
      }

      const rawSnapshot = localStorage.getItem('selected_broker_snapshot')
      if (!rawSnapshot) {
        setSelectedBrokerSnapshot(null)
        return
      }

      try {
        const parsedSnapshot = JSON.parse(rawSnapshot) as {
          brokerId?: number
          isDisabled?: boolean
          balance?: number | null
          todayPnl?: number | null
        }
        if (
          parsedSnapshot &&
          typeof parsedSnapshot.brokerId === 'number' &&
          parsedSnapshot.brokerId > 0 &&
          typeof parsedSnapshot.balance !== 'undefined' &&
          typeof parsedSnapshot.todayPnl !== 'undefined'
        ) {
          setSelectedBrokerSnapshot({
            brokerId: parsedSnapshot.brokerId,
            isDisabled: Boolean(parsedSnapshot.isDisabled),
            balance: parsedSnapshot.balance ?? null,
            todayPnl: parsedSnapshot.todayPnl ?? null,
          })
        } else {
          setSelectedBrokerSnapshot(null)
        }
      } catch {
        setSelectedBrokerSnapshot(null)
      }
    }
    updateSelectedBroker()
    window.addEventListener('storage', updateSelectedBroker)
    window.addEventListener('selected-broker-changed', updateSelectedBroker)
    window.addEventListener('selected-broker-snapshot-changed', updateSelectedBroker)
    return () => {
      window.removeEventListener('storage', updateSelectedBroker)
      window.removeEventListener('selected-broker-changed', updateSelectedBroker)
      window.removeEventListener('selected-broker-snapshot-changed', updateSelectedBroker)
    }
  }, [pathname])

  const withBrokerContext = (href: string) => {
    if (!selectedBrokerId) return href
    return `${href}?brokerId=${selectedBrokerId}`
  }

  useEffect(() => {
    const fetchAccountData = async () => {
      if (selectedBrokerId) {
        const fallbackSnapshot = selectedBrokerSnapshot?.brokerId === selectedBrokerId
          ? selectedBrokerSnapshot
          : null

        try {
          const brokers = await brokerAccountsApi.list()
          const selectedBroker = brokers.find((broker) => broker.id === selectedBrokerId)
          const workspaceIsDisabled = selectedBroker ? !selectedBroker.is_enabled : Boolean(fallbackSnapshot?.isDisabled)

          const [accountResult, statusResult] = await Promise.allSettled([
            brokerAccountsApi.getAccountInfo(selectedBrokerId),
            brokerAccountsApi.getBotStatus(selectedBrokerId),
          ])

          const scopedAccount = accountResult.status === 'fulfilled' ? accountResult.value : null
          const scopedStatus = statusResult.status === 'fulfilled' ? statusResult.value : null

          const resolvedBalance = scopedAccount?.balance ?? fallbackSnapshot?.balance ?? null
          const resolvedTodayPnl =
            scopedStatus?.statistics?.daily_pnl ??
            scopedAccount?.realized_pnl_today ??
            scopedAccount?.unrealized_pnl ??
            fallbackSnapshot?.todayPnl ??
            null

          setAccountData({
            balance: resolvedBalance,
            todayPnl: resolvedTodayPnl,
          })

          const hasAnyMetric = resolvedBalance !== null || resolvedTodayPnl !== null
          if (hasAnyMetric) {
            setIsConnected(true)
            setConnectionError(null)
          } else {
            setIsConnected(false)
            setConnectionError(
              workspaceIsDisabled
                ? 'Selected workspace is disabled and has no available metrics'
                : 'No live metrics for selected workspace',
            )
          }
        } catch {
          setAccountData(null)
          setIsConnected(false)
          setConnectionError('Unable to load workspace metrics')
        }
        return
      }

      try {
        const brokers = await brokerAccountsApi.list()
        if (brokers.length === 0) {
          setAccountData({ balance: null, todayPnl: null })
          setIsConnected(false)
          setConnectionError('No configured workspaces')
          return
        }

        const [aggregated, allStatuses] = await Promise.all([
          brokerAccountsApi.getAggregatedAccount().catch(() => null),
          brokerAccountsApi.getAllStatuses().catch(() => null),
        ])

        let aggregateBalance = aggregated && aggregated.broker_count > 0
          ? aggregated.total_balance
          : null
        let aggregateDailyPnl = allStatuses?.brokers?.reduce((sum, broker) => {
          const pnl = broker.statistics?.daily_pnl
          return typeof pnl === 'number' && Number.isFinite(pnl) ? sum + pnl : sum
        }, 0) ?? null

        if (aggregateBalance === null || aggregateDailyPnl === null) {
          const accountResults = await Promise.allSettled(
            brokers.map((broker) => brokerAccountsApi.getAccountInfo(broker.id)),
          )
          const availableAccounts: Array<Awaited<ReturnType<typeof brokerAccountsApi.getAccountInfo>>> = []
          for (const result of accountResults) {
            if (result.status === 'fulfilled') {
              availableAccounts.push(result.value)
            }
          }

          if (aggregateBalance === null) {
            const balances = availableAccounts
              .map((account) => account.balance)
              .filter((balance): balance is number => typeof balance === 'number')
            aggregateBalance = balances.length > 0
              ? balances.reduce((sum, balance) => sum + balance, 0)
              : null
          }

          if (aggregateDailyPnl === null) {
            const dailyPnls = availableAccounts.map((account) => {
              if (typeof account.realized_pnl_today === 'number') return account.realized_pnl_today
              if (typeof account.unrealized_pnl === 'number') return account.unrealized_pnl
              return null
            }).filter((pnl): pnl is number => pnl !== null)

            aggregateDailyPnl = dailyPnls.length > 0
              ? dailyPnls.reduce((sum, pnl) => sum + pnl, 0)
              : null
          }
        }

        if (aggregateBalance === null && aggregateDailyPnl === null) {
          setAccountData({ balance: null, todayPnl: null })
          setIsConnected(false)
          setConnectionError('Workspaces have no available metrics')
          return
        }

        setAccountData({
          balance: aggregateBalance,
          todayPnl: aggregateDailyPnl,
        })
        setIsConnected(true)
        setConnectionError(null)
      } catch {
        setIsConnected(false)
        setConnectionError('Unable to load workspace metrics')
        setAccountData(null)
      }
    }

    fetchAccountData()
    const interval = setInterval(fetchAccountData, 10000) // Update every 10s
    return () => clearInterval(interval)
  }, [selectedBrokerId, selectedBrokerSnapshot])

  const selectedSnapshotPreview =
    selectedBrokerSnapshot && selectedBrokerId === selectedBrokerSnapshot.brokerId
      ? selectedBrokerSnapshot
      : null
  const previewIsDisabled = Boolean(selectedSnapshotPreview?.isDisabled)
  const balanceValue = previewIsDisabled
    ? null
    : (selectedSnapshotPreview?.balance ?? accountData?.balance ?? null)
  const todayPnlValue = previewIsDisabled
    ? null
    : (selectedSnapshotPreview?.todayPnl ?? accountData?.todayPnl ?? null)
  const hasBalanceValue = typeof balanceValue === 'number'
  const hasTodayPnlValue = typeof todayPnlValue === 'number'

  return (
    <ProtectedRoute>
    <div className="min-h-screen flex w-full overflow-x-hidden bg-dark-abyss prometheus-page-shell">
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-full w-[280px] z-40 overflow-hidden transform-gpu will-change-transform transition-transform duration-300 ease-out prometheus-sidebar-shell ${sidebarOpen ? 'translate-x-0' : '-translate-x-[280px]'}`}
      >
        {/* Sidebar background with gradient */}
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(21,15,10,0.98)_0%,rgba(10,8,6,0.98)_100%)] backdrop-blur-2xl border-r border-primary-500/20" />
        <div className="absolute inset-0 prometheus-sidebar-runes pointer-events-none" />

        {/* Gradient accent at top */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-400 via-primary-600 to-imperial-500" />

        {/* Rising flames effect on sidebar */}
        <div className="absolute bottom-0 left-0 right-0 h-64 pointer-events-none overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-t from-primary-500/12 via-primary-500/5 to-transparent" />
          <div className="sidebar-flame-particle sidebar-flame-particle-one" />
          <div className="sidebar-flame-particle sidebar-flame-particle-two" />
          <div className="sidebar-flame-particle sidebar-flame-particle-three" />
        </div>

        {/* Glowing orb effect */}
        <div className="absolute top-1/3 -right-20 w-40 h-40 bg-primary-500/15 rounded-full blur-3xl pointer-events-none sidebar-orb-pulse" />

        {/* Vertical accent line with glow */}
        <div className="absolute right-0 top-20 bottom-20 w-px pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary-500/45 to-transparent" />
          <div className="absolute w-full h-20 bg-gradient-to-b from-transparent via-primary-300/70 to-transparent sidebar-energy-sweep" />
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-dark-800/50">
            <Link href="/" className="block group">
              <div className="relative prometheus-logo-shell">
                <Image
                  src="/images/logo.png"
                  alt="Prometheus AI Trading"
                  width={420}
                  height={128}
                  className="h-24 md:h-28 w-auto group-hover:scale-[1.04] transition-transform duration-300 mix-blend-screen prometheus-logo-ignite"
                  priority
                />
                <div className="absolute -inset-2 bg-primary-500/10 rounded-xl blur-lg opacity-0 group-hover:opacity-100 transition-opacity" />
              </div>
            </Link>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 overflow-y-auto">
            <p className="px-4 py-2 text-xs font-semibold text-dark-500 uppercase tracking-widest">
              Navigation
            </p>
            <ul className="space-y-1 mt-2">
              {navItems.map((item) => {
                const isActive = pathname === item.href
                const Icon = item.icon
                return (
                  <li key={item.href}>
                    <Link
                      href={withBrokerContext(item.href)}
                      className={`
                        nav-link relative
                        ${isActive ? 'active' : ''}
                      `}
                    >
                      <Icon size={20} />
                      <span className="font-medium flex-1">{item.label}</span>
                      {isActive && (
                        <ChevronRight size={16} className="text-primary-400" />
                      )}
                    </Link>
                  </li>
                )
              })}
            </ul>

            {/* Admin Section - Only for superusers */}
            {user?.is_superuser && (
              <>
                <p className="px-4 py-2 mt-6 text-xs font-semibold text-imperial-400 uppercase tracking-widest">
                  Admin
                </p>
                <ul className="space-y-1 mt-2">
                  <li>
                    <Link
                      href="/admin"
                      className="nav-link relative group"
                    >
                      <Shield size={20} className="text-imperial-400" />
                      <span className="font-medium flex-1 text-imperial-300">Admin Panel</span>
                      <ChevronRight size={16} className="text-imperial-400 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </Link>
                  </li>
                </ul>
              </>
            )}
          </nav>

          {/* Status indicator */}
          <div className="p-4 border-t border-dark-800/50">
            <div className={`relative overflow-hidden rounded-xl p-4 ${isConnected ? 'bg-profit/5 border border-profit/20' : 'bg-loss/5 border border-loss/20'}`}>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-profit' : 'bg-loss'}`} />
                  {isConnected && (
                    <div className="absolute inset-0 w-3 h-3 rounded-full bg-profit animate-ping opacity-50" />
                  )}
                </div>
                <div className="flex-1">
                  <p className={`text-sm font-semibold ${isConnected ? 'text-profit' : 'text-loss'}`}>
                    {isConnected ? 'Fire Burning' : 'Fire Dormant'}
                  </p>
                  <p className="text-xs text-dark-500">
                    {isConnected ? 'Titan connected' : 'Ignite your broker'}
                  </p>
                </div>
                <Flame size={16} className={isConnected ? 'text-profit animate-pulse' : 'text-loss'} />
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Sidebar -> Main blending seam */}
      <div
        aria-hidden="true"
        className={`pointer-events-none fixed top-0 bottom-0 left-[280px] w-20 z-[35] transform-gpu will-change-[opacity,transform] transition-[opacity,transform] duration-300 ease-out ${sidebarOpen ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-[280px]'}`}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-dark-950/85 via-primary-500/10 to-transparent" />
        <div className="absolute inset-y-0 left-0 w-px bg-gradient-to-b from-transparent via-primary-400/45 to-transparent" />
        <div className="absolute inset-y-0 left-0 w-9 bg-[radial-gradient(circle_at_left,rgba(245,158,11,0.2),transparent_72%)] blur-md" />
      </div>

      {/* Main content */}
      <div className={`flex-1 overflow-x-hidden max-w-full transform-gpu will-change-[margin-left] transition-[margin-left] duration-300 ${sidebarOpen ? 'ml-[280px]' : 'ml-0'}`}>
        {/* Top header */}
        <header className="sticky top-0 z-30 bg-dark-950/80 backdrop-blur-2xl border-b border-dark-800/50 overflow-hidden">
          {/* Left decorative fire effect */}
          <div className="absolute left-0 top-0 bottom-0 w-32 pointer-events-none">
            <div className="absolute inset-0 bg-gradient-to-r from-primary-500/10 via-primary-500/5 to-transparent" />
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-16 bg-gradient-to-b from-transparent via-primary-500 to-transparent opacity-60 animate-pulse" />
            <div className="absolute left-4 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-primary-500/30 to-transparent" />
            <div className="absolute left-6 top-1/2 w-1.5 h-1.5 rounded-full bg-primary-400 blur-[1px] header-ember header-ember-left-1" />
            <div className="absolute left-10 top-1/3 w-1 h-1 rounded-full bg-imperial-400 blur-[1px] header-ember header-ember-left-2" />
          </div>

          {/* Right decorative fire effect */}
          <div className="absolute right-0 top-0 bottom-0 w-32 pointer-events-none">
            <div className="absolute inset-0 bg-gradient-to-l from-primary-500/10 via-primary-500/5 to-transparent" />
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-16 bg-gradient-to-b from-transparent via-primary-500 to-transparent opacity-60 animate-pulse" />
            <div className="absolute right-4 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-primary-500/30 to-transparent" />
            <div className="absolute right-6 top-1/2 w-1.5 h-1.5 rounded-full bg-primary-400 blur-[1px] header-ember header-ember-right-1" />
            <div className="absolute right-10 top-2/3 w-1 h-1 rounded-full bg-imperial-400 blur-[1px] header-ember header-ember-right-2" />
          </div>

          {/* Top gradient line */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-primary-500/50 to-transparent" />

          <div className="relative px-4 py-4 md:px-6">
            <div className="mx-auto flex w-full max-w-[1720px] items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2.5 hover:bg-dark-800 rounded-xl transition-all duration-200 border border-transparent hover:border-primary-500/20"
              >
                <Menu size={20} className="text-dark-400" />
              </button>

              <div className="hidden sm:flex items-center gap-2 px-4 py-2 rounded-xl bg-profit/5 border border-profit/20">
                <Activity size={16} className="text-profit" />
                <span className="text-sm font-medium text-profit">Live Trading</span>
              </div>
            </div>

            <div className="flex items-center gap-6">
              {/* Account balance preview */}
              <div className="hidden md:flex items-center gap-8">
                <div className="text-right">
                  <p className="text-xs text-dark-500 uppercase tracking-wider mb-1">Balance</p>
                  <p className="text-xl font-bold font-mono text-gradient-gold">
                    {hasBalanceValue
                      ? `$${balanceValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                      : '--'}
                  </p>
                </div>

                <div className="w-px h-10 bg-dark-800" />

                <div className="text-right">
                  <p className="text-xs text-dark-500 uppercase tracking-wider mb-1">Today P&L</p>
                  <div className="flex items-center gap-2 justify-end">
                    {hasTodayPnlValue && (
                      todayPnlValue >= 0
                        ? <TrendingUp size={18} className="text-profit" />
                        : <TrendingDown size={18} className="text-loss" />
                    )}
                    <p className={`text-xl font-bold font-mono ${
                      hasTodayPnlValue
                        ? (todayPnlValue >= 0 ? 'text-profit' : 'text-loss')
                        : 'text-dark-300'
                    }`}>
                      {hasTodayPnlValue
                        ? `${todayPnlValue >= 0 ? '+' : ''}$${todayPnlValue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : '--'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Music Toggle */}
              <MusicPlayer size="md" showLabel={true} />

              {/* Notifications */}
              <button className="relative p-2.5 hover:bg-dark-800 rounded-xl transition-all duration-200 border border-transparent hover:border-primary-500/20">
                <Bell size={20} className="text-dark-400" />
                {connectionError && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-loss rounded-full border-2 border-dark-950" />
                )}
              </button>

              {/* User Menu */}
              {user && (
                <div className="flex items-center gap-3 pl-4 border-l border-dark-700">
                  <div className="hidden sm:flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500/20 to-imperial-500/20 border border-primary-500/30 flex items-center justify-center">
                      <User size={16} className="text-primary-400" />
                    </div>
                    <span className="text-sm font-medium text-dark-200">{user.username}</span>
                  </div>
                  <button
                    onClick={logout}
                    className="p-2 hover:bg-loss/10 rounded-lg transition-all duration-200 text-dark-400 hover:text-loss"
                    title="Logout"
                  >
                    <LogOut size={18} />
                  </button>
                </div>
              )}
            </div>
            </div>
          </div>
        </header>

        {/* Connection error banner */}
        <AnimatePresence>
          {connectionError && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-auto mt-4 w-full max-w-[1720px] px-4 md:px-6"
            >
              <div className="p-4 bg-primary-500/5 border border-primary-500/20 rounded-2xl flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-primary-500/10 flex items-center justify-center">
                  <AlertCircle size={20} className="text-primary-400" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-primary-300">Connection Required</p>
                  <p className="text-xs text-dark-400 mt-0.5">{connectionError}. Configure your broker in Settings to start trading.</p>
                </div>
                <Link
                  href="/dashboard/settings"
                  className="btn-primary py-2 px-4 text-sm"
                >
                  Configure
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Page content */}
        <main className="overflow-x-hidden px-4 pb-6 pt-6 md:px-6">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mx-auto w-full max-w-[1720px]"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
    </ProtectedRoute>
  )
}
