'use client'

import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
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
  Zap,
  Flame,
  ChevronRight,
  Headphones,
  Volume2,
  VolumeX,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'
import { analyticsApi } from '@/lib/api'

// Epic background music hook
function useBackgroundMusic() {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)

  useEffect(() => {
    // Create audio element with epic orchestral music
    audioRef.current = new Audio('/audio/prometheus-theme.mp3')
    audioRef.current.loop = true
    audioRef.current.volume = 0.3

    audioRef.current.addEventListener('canplaythrough', () => {
      setIsLoaded(true)
    })

    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current = null
      }
    }
  }, [])

  const toggleMusic = () => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
    } else {
      audioRef.current.play().catch(() => {
        // Autoplay blocked, user needs to interact first
      })
      setIsPlaying(true)
    }
  }

  return { isPlaying, isLoaded, toggleMusic }
}

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
  const { isPlaying, toggleMusic } = useBackgroundMusic()

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
    <div className="min-h-screen flex overflow-x-hidden max-w-[100vw] bg-dark-abyss">
      {/* Sidebar */}
      <motion.aside
        initial={{ x: -280 }}
        animate={{ x: sidebarOpen ? 0 : -280 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="fixed left-0 top-0 h-full w-[280px] z-40"
      >
        {/* Sidebar background with gradient */}
        <div className="absolute inset-0 bg-dark-950/95 backdrop-blur-2xl border-r border-primary-500/10" />

        {/* Gradient accent at top */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-500 via-imperial-500 to-primary-500" />

        {/* Content */}
        <div className="relative z-10 flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-dark-800/50">
            <Link href="/" className="flex items-center gap-4 group">
              <div className="relative">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-imperial-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                  <Flame className="w-6 h-6 text-dark-950 animate-pulse" />
                </div>
                <div className="absolute -inset-1 bg-gradient-to-br from-primary-500/20 to-imperial-500/20 rounded-xl blur-md opacity-0 group-hover:opacity-100 transition-opacity" />
                {/* Fire glow effect */}
                <div className="absolute -inset-2 bg-primary-500/10 rounded-xl blur-lg animate-pulse-slow" />
              </div>
              <div>
                <h1 className="font-imperial text-xl font-bold text-gradient-gold tracking-wide">
                  PROMETHEUS
                </h1>
                <p className="text-xs text-dark-500 tracking-wider">BRINGER OF FIRE</p>
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
        <header className="sticky top-0 z-30 bg-dark-950/80 backdrop-blur-2xl border-b border-dark-800/50">
          <div className="flex items-center justify-between px-6 py-4">
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
              <button
                onClick={toggleMusic}
                className={`relative p-2.5 rounded-xl transition-all duration-200 border ${
                  isPlaying
                    ? 'bg-primary-500/10 border-primary-500/30 hover:bg-primary-500/20'
                    : 'hover:bg-dark-800 border-transparent hover:border-primary-500/20'
                }`}
                title={isPlaying ? 'Pause epic music' : 'Play epic music'}
              >
                {isPlaying ? (
                  <Volume2 size={20} className="text-primary-400 animate-pulse" />
                ) : (
                  <Headphones size={20} className="text-dark-400" />
                )}
                {isPlaying && (
                  <span className="absolute -top-1 -right-1 flex h-3 w-3">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-primary-500"></span>
                  </span>
                )}
              </button>

              {/* Notifications */}
              <button className="relative p-2.5 hover:bg-dark-800 rounded-xl transition-all duration-200 border border-transparent hover:border-primary-500/20">
                <Bell size={20} className="text-dark-400" />
                {connectionError && (
                  <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-loss rounded-full border-2 border-dark-950" />
                )}
              </button>
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
  )
}
