'use client'

import { motion } from 'framer-motion'
import { Headphones, Volume2 } from 'lucide-react'
import { useMusic } from '@/contexts/MusicContext'

interface MusicPlayerProps {
  className?: string
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function MusicPlayer({ className = '', showLabel = true, size = 'md' }: MusicPlayerProps) {
  const { isPlaying, toggleMusic } = useMusic()

  const sizeClasses = {
    sm: 'p-2',
    md: 'p-3',
    lg: 'p-4',
  }

  const iconSizes = {
    sm: 18,
    md: 22,
    lg: 26,
  }

  return (
    <motion.button
      onClick={toggleMusic}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className={`relative ${sizeClasses[size]} rounded-xl transition-all duration-300 ${
        isPlaying
          ? 'bg-gradient-to-br from-primary-500/20 to-imperial-500/20 border border-primary-500/40 shadow-lg shadow-primary-500/20'
          : 'bg-dark-800/50 border border-primary-500/20 hover:bg-dark-800 hover:border-primary-500/40 hover:shadow-lg hover:shadow-primary-500/10'
      } ${className}`}
      title={isPlaying ? 'Pause epic music' : 'Play epic music'}
    >
      {/* Glow effect behind icon */}
      <div className={`absolute inset-0 rounded-xl transition-opacity duration-300 ${isPlaying ? 'opacity-100' : 'opacity-0'}`}>
        <div className="absolute inset-0 bg-primary-500/20 rounded-xl blur-md animate-pulse" />
      </div>

      {isPlaying ? (
        <Volume2 size={iconSizes[size]} className="relative z-10 text-primary-400 torch-glow" />
      ) : (
        <Headphones size={iconSizes[size]} className="relative z-10 text-primary-400 hover:text-primary-300 transition-colors" />
      )}

      {/* Animated ring when playing */}
      {isPlaying && (
        <>
          <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-gradient-to-br from-primary-400 to-primary-600"></span>
          </span>
          {/* Rotating fire ring */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
            className="absolute -inset-1 rounded-xl border border-primary-500/30 border-t-primary-500/60"
          />
        </>
      )}

      {/* Music label */}
      {showLabel && (
        <span className={`absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] font-semibold uppercase tracking-wider whitespace-nowrap transition-opacity ${
          isPlaying ? 'text-primary-400 opacity-100' : 'text-dark-500 opacity-70'
        }`}>
          {isPlaying ? 'Playing' : 'Music'}
        </span>
      )}
    </motion.button>
  )
}

export default MusicPlayer
