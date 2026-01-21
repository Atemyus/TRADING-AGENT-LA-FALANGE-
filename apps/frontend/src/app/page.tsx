'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'

export default function LandingPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      {/* Background gradient effects */}
      <div className="fixed inset-0 -z-10">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-neon-purple/20 rounded-full blur-3xl" />
      </div>

      {/* Logo / Title */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="text-center mb-12"
      >
        <h1 className="text-6xl font-bold mb-4">
          <span className="text-gradient">Prometheus</span>
        </h1>
        <p className="text-xl text-dark-400">
          AI-Powered Trading Platform
        </p>
      </motion.div>

      {/* Stats preview */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.2 }}
        className="grid grid-cols-3 gap-8 mb-12"
      >
        <div className="stat-card text-center">
          <span className="stat-label">Markets</span>
          <span className="stat-value text-neon-blue">Forex · Indices · CFD</span>
        </div>
        <div className="stat-card text-center">
          <span className="stat-label">Strategy</span>
          <span className="stat-value text-neon-purple">Intraday / Scalping</span>
        </div>
        <div className="stat-card text-center">
          <span className="stat-label">Powered By</span>
          <span className="stat-value text-neon-green">10+ AI Models</span>
        </div>
      </motion.div>

      {/* CTA Button */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.4 }}
      >
        <Link
          href="/dashboard"
          className="btn-primary text-lg px-8 py-4 inline-flex items-center gap-2 group"
        >
          Enter Dashboard
          <svg
            className="w-5 h-5 transition-transform group-hover:translate-x-1"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        </Link>
      </motion.div>

      {/* Feature cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.6 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-4xl"
      >
        <FeatureCard
          icon="🤖"
          title="Multi-AI Consensus"
          description="10+ AI models vote on trades - GPT-4o, Claude, Gemini, Llama & more"
        />
        <FeatureCard
          icon="📊"
          title="Real-time Analytics"
          description="Live charts, P&L tracking, and performance metrics"
        />
        <FeatureCard
          icon="🛡️"
          title="Risk Management"
          description="Automatic stop-loss, position sizing, and daily limits"
        />
      </motion.div>

      {/* Footer */}
      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.8 }}
        className="mt-16 text-dark-500 text-sm"
      >
        Version 2.0.0 · Multi-Broker CFD Platform
      </motion.footer>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: string
  title: string
  description: string
}) {
  return (
    <div className="card-hover p-6 text-center">
      <div className="text-4xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-dark-400 text-sm">{description}</p>
    </div>
  )
}
