'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  LineChart,
  Wallet,
  Settings,
  Activity,
  Bell,
  Menu,
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/dashboard/positions', label: 'Positions', icon: Wallet },
  { href: '/dashboard/analytics', label: 'Analytics', icon: LineChart },
  { href: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(true)

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
            <div className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
            <div className="flex-1">
              <p className="text-sm font-medium">System Online</p>
              <p className="text-xs text-dark-400">Connected to broker</p>
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
                  <p className="font-mono font-bold">$10,000.00</p>
                </div>
                <div>
                  <p className="text-xs text-dark-400">Today P&L</p>
                  <p className="font-mono font-bold pnl-positive">+$125.50</p>
                </div>
              </div>

              {/* Notifications */}
              <button className="relative p-2 hover:bg-dark-800 rounded-lg transition-colors">
                <Bell size={20} />
                <span className="absolute top-1 right-1 w-2 h-2 bg-neon-red rounded-full" />
              </button>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
