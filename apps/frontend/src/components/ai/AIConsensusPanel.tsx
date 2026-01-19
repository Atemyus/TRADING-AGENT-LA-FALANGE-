'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState } from 'react'
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle,
  XCircle,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Zap,
  DollarSign,
  Clock,
} from 'lucide-react'
import type { ConsensusResult, AIVote } from '@/lib/api'

interface AIConsensusPanelProps {
  result?: ConsensusResult | null
  isLoading?: boolean
  onAnalyze?: () => void
}

// Provider icons/colors mapping for AIML API models
// These match the provider names returned by the backend
const providerStyles: Record<string, { color: string; icon: string }> = {
  // The 6 AIML models we use
  'OpenAI': { color: '#10a37f', icon: '💬' },      // ChatGPT 5.2
  'Google': { color: '#4285f4', icon: '💎' },      // Gemini 3 Pro
  'DeepSeek': { color: '#0ea5e9', icon: '🔍' },    // DeepSeek V3.2
  'xAI': { color: '#ef4444', icon: '⚡' },          // Grok 4.1 Fast
  'Alibaba': { color: '#f97316', icon: '🌟' },     // Qwen Max
  'Zhipu': { color: '#8b5cf6', icon: '🧪' },       // GLM 4.7
  // Lowercase fallbacks
  openai: { color: '#10a37f', icon: '💬' },
  google: { color: '#4285f4', icon: '💎' },
  deepseek: { color: '#0ea5e9', icon: '🔍' },
  xai: { color: '#ef4444', icon: '⚡' },
  alibaba: { color: '#f97316', icon: '🌟' },
  zhipu: { color: '#8b5cf6', icon: '🧪' },
}

function DirectionBadge({ direction }: { direction: string }) {
  const config = {
    BUY: { color: 'bg-neon-green/20 text-neon-green border-neon-green/30', icon: TrendingUp },
    SELL: { color: 'bg-neon-red/20 text-neon-red border-neon-red/30', icon: TrendingDown },
    HOLD: { color: 'bg-neon-yellow/20 text-neon-yellow border-neon-yellow/30', icon: Minus },
  }[direction] || { color: 'bg-dark-700 text-dark-300', icon: Minus }

  const Icon = config.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border ${config.color} font-semibold text-sm`}>
      <Icon size={14} />
      {direction}
    </span>
  )
}

function VoteCard({ vote, index }: { vote: AIVote; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const style = providerStyles[vote.provider] || { color: '#64748b', icon: '🤖' }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.05 }}
      className={`p-3 rounded-lg border ${
        vote.is_valid ? 'bg-dark-800/50 border-dark-700/50' : 'bg-neon-red/5 border-neon-red/20'
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-lg">{style.icon}</span>
          <div>
            <p className="font-medium text-sm">{vote.model}</p>
            <p className="text-xs text-dark-400">{vote.provider}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {vote.is_valid ? (
            <>
              <DirectionBadge direction={vote.direction} />
              <div className="text-right">
                <p className="font-mono font-bold">{vote.confidence}%</p>
              </div>
            </>
          ) : (
            <span className="flex items-center gap-1 text-neon-red text-sm">
              <XCircle size={14} />
              Failed
            </span>
          )}

          <button
            onClick={() => setExpanded(!expanded)}
            className="p-1 hover:bg-dark-700 rounded transition-colors"
          >
            {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          </button>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-3 pt-3 border-t border-dark-700/50"
          >
            <p className="text-sm text-dark-300">
              {vote.error || vote.reasoning}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function AIConsensusPanel({
  result,
  isLoading = false,
  onAnalyze,
}: AIConsensusPanelProps) {
  const [showAllVotes, setShowAllVotes] = useState(false)

  if (!result && !isLoading) {
    return (
      <div className="card p-6">
        <div className="text-center py-8">
          <Brain className="w-12 h-12 mx-auto text-dark-500 mb-4" />
          <h3 className="font-semibold mb-2">No Analysis Yet</h3>
          <p className="text-sm text-dark-400 mb-4">Run AI analysis to get trading signals</p>
          <button onClick={onAnalyze} className="btn-primary">
            Analyze Market
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="card overflow-hidden">
      {/* Header */}
      <div className="p-4 bg-gradient-to-r from-primary-500/10 to-neon-purple/10 border-b border-dark-700/50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-neon-purple flex items-center justify-center">
              <Brain className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-semibold">AI Consensus</h2>
              <p className="text-xs text-dark-400">
                {result?.valid_votes} of {result?.total_votes} models voted
              </p>
            </div>
          </div>

          {result && (
            <DirectionBadge direction={result.direction} />
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="p-8 text-center">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
            className="w-12 h-12 mx-auto mb-4 rounded-full border-2 border-primary-500 border-t-transparent"
          />
          <p className="text-dark-400">Analyzing with multiple AI models...</p>
        </div>
      ) : result && (
        <>
          {/* Confidence & Agreement */}
          <div className="p-4 space-y-4">
            {/* Confidence Bar */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-dark-400">Confidence</span>
                <span className="font-mono font-bold text-lg">{result.confidence.toFixed(1)}%</span>
              </div>
              <div className="h-3 bg-dark-800 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${result.confidence}%` }}
                  transition={{ duration: 1, ease: 'easeOut' }}
                  className={`h-full rounded-full ${
                    result.confidence >= 70
                      ? 'bg-gradient-to-r from-neon-green to-neon-blue'
                      : result.confidence >= 50
                      ? 'bg-gradient-to-r from-neon-yellow to-neon-green'
                      : 'bg-gradient-to-r from-neon-red to-neon-yellow'
                  }`}
                />
              </div>
            </div>

            {/* Vote Distribution */}
            <div>
              <p className="text-sm text-dark-400 mb-2">Vote Distribution</p>
              <div className="flex gap-2 h-8">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(result.votes_buy / result.valid_votes) * 100}%` }}
                  className="bg-neon-green/30 rounded-l-lg flex items-center justify-center text-xs font-medium text-neon-green"
                >
                  {result.votes_buy} BUY
                </motion.div>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(result.votes_hold / result.valid_votes) * 100}%` }}
                  className="bg-neon-yellow/30 flex items-center justify-center text-xs font-medium text-neon-yellow"
                >
                  {result.votes_hold > 0 && `${result.votes_hold} HOLD`}
                </motion.div>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(result.votes_sell / result.valid_votes) * 100}%` }}
                  className="bg-neon-red/30 rounded-r-lg flex items-center justify-center text-xs font-medium text-neon-red"
                >
                  {result.votes_sell > 0 && `${result.votes_sell} SELL`}
                </motion.div>
              </div>
            </div>

            {/* Trade Parameters */}
            {result.should_trade && (
              <div className="grid grid-cols-3 gap-3 p-3 bg-dark-800/50 rounded-lg">
                <div>
                  <p className="text-xs text-dark-400">Entry</p>
                  <p className="font-mono font-medium">{result.suggested_entry}</p>
                </div>
                <div>
                  <p className="text-xs text-dark-400">Stop Loss</p>
                  <p className="font-mono font-medium text-neon-red">{result.suggested_stop_loss}</p>
                </div>
                <div>
                  <p className="text-xs text-dark-400">Take Profit</p>
                  <p className="font-mono font-medium text-neon-green">{result.suggested_take_profit}</p>
                </div>
              </div>
            )}

            {/* Key Factors */}
            <div>
              <p className="text-sm font-medium mb-2">Key Factors</p>
              <ul className="space-y-1.5">
                {result.key_factors.slice(0, 4).map((factor, i) => (
                  <motion.li
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="flex items-start gap-2 text-sm text-dark-300"
                  >
                    <CheckCircle size={14} className="text-neon-green mt-0.5 flex-shrink-0" />
                    {factor}
                  </motion.li>
                ))}
              </ul>
            </div>

            {/* Risks */}
            {result.risks.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Risks</p>
                <ul className="space-y-1.5">
                  {result.risks.map((risk, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-dark-400">
                      <AlertCircle size={14} className="text-neon-yellow mt-0.5 flex-shrink-0" />
                      {risk}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Individual Votes */}
          <div className="border-t border-dark-700/50">
            <button
              onClick={() => setShowAllVotes(!showAllVotes)}
              className="w-full p-3 flex items-center justify-between hover:bg-dark-800/30 transition-colors"
            >
              <span className="text-sm font-medium">Individual Votes</span>
              {showAllVotes ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>

            <AnimatePresence>
              {showAllVotes && (
                <motion.div
                  initial={{ height: 0 }}
                  animate={{ height: 'auto' }}
                  exit={{ height: 0 }}
                  className="overflow-hidden"
                >
                  <div className="p-3 pt-0 space-y-2 max-h-[300px] overflow-y-auto">
                    {result.votes.map((vote, i) => (
                      <VoteCard key={`${vote.provider}-${vote.model}`} vote={vote} index={i} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Footer Stats */}
          <div className="p-3 bg-dark-800/30 border-t border-dark-700/50 flex items-center justify-between text-xs text-dark-400">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {(result.processing_time_ms / 1000).toFixed(2)}s
              </span>
              <span className="flex items-center gap-1">
                <Zap size={12} />
                {result.total_tokens.toLocaleString()} tokens
              </span>
            </div>
            <span className="flex items-center gap-1">
              <DollarSign size={12} />
              ${result.total_cost_usd.toFixed(4)}
            </span>
          </div>
        </>
      )}
    </div>
  )
}

export default AIConsensusPanel
