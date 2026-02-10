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
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { analyticsApi } from '@/lib/api'
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
  const [accountData, setAccountData] = useState<{ balance: number; todayPnl: number } | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const { user, logout } = useAuth()

  useEffect(() => {
    const fetchAccountData = async () => {
      try {
        const data = await analyticsApi.getAccount()
        setAccountData({
          balance: parseFloat(data.balance) || 0,
          todayPnl: parseFloat(data.realized_pnl_today) || 0,
        })
        setIsConnected(true)
        setConnectionError(null)
      } catch {
        setIsConnected(false)
        setConnectionError('Unable to connect to backend')
        setAccountData(null)
      }
    }

    fetchAccountData()
    const interval = setInterval(fetchAccountData, 30000) // Update every 30s
    return () => clearInterval(interval)
  }, [])

  return (
    <ProtectedRoute>
    <div className="min-h-screen flex overflow-x-hidden max-w-[100vw] bg-dark-abyss">
      {/* Sidebar */}
      <motion.aside
        initial={{ x: -280 }}
        animate={{ x: sidebarOpen ? 0 : -280 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="fixed left-0 top-0 h-full w-[280px] z-40 overflow-hidden"
      >
        {/* Sidebar background with gradient */}
        <div className="absolute inset-0 bg-dark-950/95 backdrop-blur-2xl border-r border-primary-500/10" />

        {/* Gradient accent at top */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-500 via-imperial-500 to-primary-500" />

        {/* Rising flames effect on sidebar */}
        <div className="absolute bottom-0 left-0 right-0 h-64 pointer-events-none overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-t from-primary-500/5 via-primary-500/2 to-transparent" />
          {/* Animated flame particles */}
          <motion.div
            animate={{
              y: [0, -100, -200],
              opacity: [0.6, 0.3, 0],
              scale: [1, 1.2, 0.8],
            }}
            transition={{ duration: 4, repeat: Infinity, ease: 'easeOut' }}
            className="absolute bottom-0 left-[20%] w-3 h-8 bg-gradient-to-t from-primary-500/30 to-transparent rounded-full blur-sm"
          />
          <motion.div
            animate={{
              y: [0, -80, -160],
              opacity: [0.5, 0.25, 0],
            }}
            transition={{ duration: 3.5, repeat: Infinity, ease: 'easeOut', delay: 0.5 }}
            className="absolute bottom-0 left-[50%] w-2 h-6 bg-gradient-to-t from-imperial-500/25 to-transparent rounded-full blur-sm"
          />
          <motion.div
            animate={{
              y: [0, -120, -220],
              opacity: [0.7, 0.35, 0],
            }}
            transition={{ duration: 5, repeat: Infinity, ease: 'easeOut', delay: 1 }}
            className="absolute bottom-0 left-[75%] w-2.5 h-7 bg-gradient-to-t from-primary-400/30 to-transparent rounded-full blur-sm"
          />
        </div>

        {/* Glowing orb effect */}
        <motion.div
          animate={{
            opacity: [0.3, 0.5, 0.3],
            scale: [1, 1.1, 1],
          }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute top-1/3 -right-20 w-40 h-40 bg-primary-500/10 rounded-full blur-3xl pointer-events-none"
        />

        {/* Vertical accent line with glow */}
        <div className="absolute right-0 top-20 bottom-20 w-px pointer-events-none">
          <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary-500/30 to-transparent" />
          <motion.div
            animate={{ y: ['-100%', '100%'] }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            className="absolute w-full h-20 bg-gradient-to-b from-transparent via-primary-400/60 to-transparent"
          />
        </div>

        {/* Content */}
        <div className="relative z-10 flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-dark-800/50">
            <Link href="/" className="block group">
              <div className="relative">
                <Image
                  src="/images/logo.png"
                  alt="Prometheus AI Trading"
                  width={220}
                  height={66}
                  className="h-14 w-auto group-hover:scale-105 transition-transform mix-blend-screen"
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
                      href={item.href}
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
      </motion.aside>

      {/* Main content */}
      <div className={`flex-1 transition-all duration-300 overflow-x-hidden max-w-full ${sidebarOpen ? 'ml-[280px]' : 'ml-0'}`}>
        {/* Top header */}
        <header className="sticky top-0 z-30 bg-dark-950/80 backdrop-blur-2xl border-b border-dark-800/50 overflow-hidden">
          {/* Left decorative fire effect */}
          <div className="absolute left-0 top-0 bottom-0 w-32 pointer-events-none">
            <div className="absolute inset-0 bg-gradient-to-r from-primary-500/10 via-primary-500/5 to-transparent" />
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-16 bg-gradient-to-b from-transparent via-primary-500 to-transparent opacity-60 animate-pulse" />
            <div className="absolute left-4 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-primary-500/30 to-transparent" />
            {/* Floating ember left */}
            <motion.div
              animate={{
                y: [-20, -40, -20],
                opacity: [0.3, 0.7, 0.3],
                scale: [0.8, 1, 0.8],
              }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              className="absolute left-6 top-1/2 w-1.5 h-1.5 rounded-full bg-primary-400 blur-[1px]"
            />
            <motion.div
              animate={{
                y: [-10, -30, -10],
                opacity: [0.2, 0.5, 0.2],
              }}
              transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
              className="absolute left-10 top-1/3 w-1 h-1 rounded-full bg-imperial-400 blur-[1px]"
            />
          </div>

          {/* Right decorative fire effect */}
          <div className="absolute right-0 top-0 bottom-0 w-32 pointer-events-none">
            <div className="absolute inset-0 bg-gradient-to-l from-primary-500/10 via-primary-500/5 to-transparent" />
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-16 bg-gradient-to-b from-transparent via-primary-500 to-transparent opacity-60 animate-pulse" />
            <div className="absolute right-4 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-primary-500/30 to-transparent" />
            {/* Floating ember right */}
            <motion.div
              animate={{
                y: [-15, -35, -15],
                opacity: [0.3, 0.7, 0.3],
                scale: [0.8, 1, 0.8],
              }}
              transition={{ duration: 2.8, repeat: Infinity, ease: "easeInOut", delay: 0.3 }}
              className="absolute right-6 top-1/2 w-1.5 h-1.5 rounded-full bg-primary-400 blur-[1px]"
            />
            <motion.div
              animate={{
                y: [-5, -25, -5],
                opacity: [0.2, 0.5, 0.2],
              }}
              transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut", delay: 0.8 }}
              className="absolute right-10 top-2/3 w-1 h-1 rounded-full bg-imperial-400 blur-[1px]"
            />
          </div>

          {/* Top gradient line */}
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-primary-500/50 to-transparent" />

          <div className="relative flex items-center justify-between px-6 py-4">
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
                    {accountData
                      ? `$${accountData.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                      : '—'
                    }
                  </p>
                </div>

                <div className="w-px h-10 bg-dark-800" />

                <div className="text-right">
                  <p className="text-xs text-dark-500 uppercase tracking-wider mb-1">Today P&L</p>
                  <div className="flex items-center gap-2 justify-end">
                    {accountData && (
                      accountData.todayPnl >= 0
                        ? <TrendingUp size={18} className="text-profit" />
                        : <TrendingDown size={18} className="text-loss" />
                    )}
                    <p className={`text-xl font-bold font-mono ${accountData && accountData.todayPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
                      {accountData
                        ? `${accountData.todayPnl >= 0 ? '+' : ''}$${accountData.todayPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                        : '—'
                      }
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
        </header>

        {/* Connection error banner */}
        <AnimatePresence>
          {connectionError && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className="mx-6 mt-4"
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
        <main className="p-6 overflow-x-hidden">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
    </ProtectedRoute>
  )
}
