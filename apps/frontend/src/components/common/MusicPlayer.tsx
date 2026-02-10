'use client'

import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Headphones, Volume2, VolumeX } from 'lucide-react'

// Epic orchestral music - royalty free from Pixabay
const MUSIC_URL = 'https://cdn.pixabay.com/audio/2022/10/25/audio_052a2d6021.mp3'

export function useMusicPlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const [volume, setVolume] = useState(0.3)

  useEffect(() => {
    // Create audio element
    const audio = new Audio(MUSIC_URL)
    audio.loop = true
    audio.volume = volume
    audio.preload = 'auto'
    audioRef.current = audio

    audio.addEventListener('canplaythrough', () => {
      setIsLoaded(true)
    })

    audio.addEventListener('error', (e) => {
      console.warn('Audio failed to load:', e)
    })

    // Check if music was playing before (persist state)
    const wasPlaying = localStorage.getItem('prometheus-music-playing') === 'true'
    if (wasPlaying) {
      audio.play().then(() => setIsPlaying(true)).catch(() => {})
    }

    return () => {
      audio.pause()
      audio.src = ''
      audioRef.current = null
    }
  }, [])

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume
    }
  }, [volume])

  const toggleMusic = () => {
    if (!audioRef.current) return

    if (isPlaying) {
      audioRef.current.pause()
      setIsPlaying(false)
      localStorage.setItem('prometheus-music-playing', 'false')
    } else {
      audioRef.current.play().then(() => {
        setIsPlaying(true)
        localStorage.setItem('prometheus-music-playing', 'true')
      }).catch((err) => {
        console.warn('Autoplay blocked:', err)
      })
    }
  }

  return { isPlaying, isLoaded, toggleMusic, volume, setVolume }
}

interface MusicPlayerProps {
  className?: string
  showLabel?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export function MusicPlayer({ className = '', showLabel = true, size = 'md' }: MusicPlayerProps) {
  const { isPlaying, toggleMusic } = useMusicPlayer()

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
