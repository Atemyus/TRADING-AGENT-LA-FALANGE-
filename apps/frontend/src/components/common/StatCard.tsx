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
  const showNegative = isNegative || isPositive === false

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
            isPositive ? 'text-profit' : showNegative ? 'text-loss' : ''
          }`}>
            {value}
          </p>
          {change && (
            <p className={`text-sm mt-1 ${
              isPositive ? 'text-profit' : showNegative ? 'text-loss' : 'text-dark-400'
            }`}>
              {change}
            </p>
          )}
          {subtext && (
            <p className="text-xs text-dark-500 mt-1">{subtext}</p>
          )}
        </div>
        <div className={`p-3 rounded-xl ${
          isPositive ? 'bg-profit/10' : showNegative ? 'bg-loss/10' : 'bg-dark-800'
        }`}>
          <Icon size={22} className={`${
            isPositive ? 'text-profit' : showNegative ? 'text-loss' : 'text-dark-400'
          }`} />
        </div>
      </div>
    </Wrapper>
  )
}

export default StatCard
