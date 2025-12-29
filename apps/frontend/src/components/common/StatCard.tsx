'use client'

import { motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'

interface StatCardProps {
  label: string
  value: string
  change?: string
  subtext?: string
  isPositive?: boolean
  isNegative?: boolean
  icon: LucideIcon
  trend?: 'up' | 'down' | 'neutral'
  animate?: boolean
}

export function StatCard({
  label,
  value,
  change,
  subtext,
  isPositive,
  isNegative,
  icon: Icon,
  trend,
  animate = true,
}: StatCardProps) {
  const Wrapper = animate ? motion.div : 'div'
  const wrapperProps = animate
    ? {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        whileHover: { scale: 1.02 },
      }
    : {}

  return (
    <Wrapper
      {...wrapperProps}
      className="card p-4 hover:border-dark-600 transition-colors"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-dark-400 mb-1">{label}</p>
          <p className={`text-2xl font-bold font-mono ${
            isPositive ? 'text-neon-green' : isNegative ? 'text-neon-red' : ''
          }`}>
            {value}
          </p>
          {change && (
            <p className={`text-sm mt-1 ${
              isPositive ? 'text-neon-green' : isNegative ? 'text-neon-red' : 'text-dark-400'
            }`}>
              {change}
            </p>
          )}
          {subtext && (
            <p className="text-xs text-dark-500 mt-1">{subtext}</p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${
          isPositive ? 'bg-neon-green/10' : isNegative ? 'bg-neon-red/10' : 'bg-dark-800'
        }`}>
          <Icon size={22} className={`${
            isPositive ? 'text-neon-green' : isNegative ? 'text-neon-red' : 'text-dark-400'
          }`} />
        </div>
      </div>
    </Wrapper>
  )
}

export default StatCard
