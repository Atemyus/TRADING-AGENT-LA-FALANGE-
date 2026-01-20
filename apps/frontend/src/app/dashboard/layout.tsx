'use client'

import { motion } from 'framer-motion'
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
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { analyticsApi } from '@/lib/api'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
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

  useEffect(() => {
    const fetchAccountData = async () => {
      try {
        const data = await analyticsApi.getAccountOverview()
        setAccountData({
          balance: data.balance || 0,
          todayPnl: data.daily_pnl || 0,
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
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <motion.aside
        initial={{ x: -250 }}
        animate={{ x: sidebarOpen ? 0 : -250 }}
        transition={{ duration: 0.3 }}
        className="fixed left-0 top-0 h-full w-64 bg-dark-900/80 backdrop-blur-xl border-r border-dark-700/50 z-40"
      >
        {/* Logo */}
        <div className="p-6 border-b border-dark-700/50">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-neon-blue flex items-center justify-center">
              <span className="text-xl font-bold">F</span>
            </div>
            <div>
              <h1 className="font-bold text-lg">La Falange</h1>
              <p className="text-xs text-dark-400">Trading Platform</p>
            </div>
          </Link>
        </div>

        {/* Navigation */}
        <nav className="p-4">
          <ul className="space-y-2">
            {navItems.map((item) => {
              const isActive = pathname === item.href
              const Icon = item.icon
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={`
                      flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                      ${isActive
                        ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                        : 'text-dark-300 hover:bg-dark-800 hover:text-dark-100'
                      }
                    `}
                  >
                    <Icon size={20} />
                    <span className="font-medium">{item.label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Status indicator */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-dark-700/50">
          <div className="flex items-center gap-3 px-4 py-3 bg-dark-800/50 rounded-lg">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-neon-green animate-pulse' : 'bg-neon-red'}`} />
            <div className="flex-1">
              <p className="text-sm font-medium">{isConnected ? 'System Online' : 'Disconnected'}</p>
              <p className="text-xs text-dark-400">{isConnected ? 'Connected to broker' : 'Configure broker in Settings'}</p>
            </div>
          </div>
        </div>
      </motion.aside>

      {/* Main content */}
      <div className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-0'}`}>
        {/* Top header */}
        <header className="sticky top-0 z-30 bg-dark-950/80 backdrop-blur-xl border-b border-dark-700/50">
          <div className="flex items-center justify-between px-6 py-4">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 hover:bg-dark-800 rounded-lg transition-colors"
              >
                <Menu size={20} />
              </button>
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-neon-green" />
                <span className="text-sm font-medium">Live Trading</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              {/* Account balance preview */}
              <div className="flex items-center gap-6 mr-4">
                <div>
                  <p className="text-xs text-dark-400">Balance</p>
                  <p className="font-mono font-bold">
                    {accountData ? `$${accountData.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-dark-400">Today P&L</p>
                  <p className={`font-mono font-bold ${accountData && accountData.todayPnl >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                    {accountData ? `${accountData.todayPnl >= 0 ? '+' : ''}$${accountData.todayPnl.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                  </p>
                </div>
              </div>

              {/* Notifications */}
              <button className="relative p-2 hover:bg-dark-800 rounded-lg transition-colors">
                <Bell size={20} />
                {connectionError && <span className="absolute top-1 right-1 w-2 h-2 bg-neon-red rounded-full" />}
              </button>
            </div>
          </div>
        </header>

        {/* Connection error banner */}
        {connectionError && (
          <div className="mx-6 mt-4 p-4 bg-dark-800/80 border border-amber-500/30 rounded-lg flex items-center gap-3">
            <AlertCircle size={20} className="text-amber-500" />
            <div className="flex-1">
              <p className="text-sm text-amber-400">{connectionError}. Configure broker in Settings.</p>
            </div>
          </div>
        )}

        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
