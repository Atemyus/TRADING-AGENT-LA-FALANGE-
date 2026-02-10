'use client'

import { createContext, useContext, useState, useRef, useEffect, ReactNode } from 'react'

// Music file - use local file in public/audio/
// Add your own epic music file at: public/audio/prometheus-theme.mp3
const MUSIC_URL = '/audio/prometheus-theme.mp3'

interface MusicContextType {
  isPlaying: boolean
  isLoaded: boolean
  volume: number
  toggleMusic: () => void
  setVolume: (volume: number) => void
}

const MusicContext = createContext<MusicContextType | undefined>(undefined)

export function MusicProvider({ children }: { children: ReactNode }) {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [isLoaded, setIsLoaded] = useState(false)
  const [volume, setVolumeState] = useState(0.3)

  useEffect(() => {
    // Only create audio once on client side
    if (typeof window === 'undefined') return

    const audio = new Audio(MUSIC_URL)
    audio.loop = true
    audio.volume = volume
    audio.preload = 'auto'
    audioRef.current = audio

    const handleCanPlay = () => {
      setIsLoaded(true)
      console.log('🎵 Music loaded and ready')
    }

    const handleError = (e: Event) => {
      console.warn('Audio failed to load:', e)
    }

    const handleEnded = () => {
      // Should not happen with loop=true, but just in case
      if (audioRef.current) {
        audioRef.current.currentTime = 0
        audioRef.current.play().catch(() => {})
      }
    }

    audio.addEventListener('canplaythrough', handleCanPlay)
    audio.addEventListener('error', handleError)
    audio.addEventListener('ended', handleEnded)

    // Try to restore previous state
    const wasPlaying = localStorage.getItem('prometheus-music-playing') === 'true'
    if (wasPlaying) {
      audio.play()
        .then(() => {
          setIsPlaying(true)
          console.log('🎵 Music auto-resumed')
        })
        .catch(() => {
          console.log('🎵 Auto-play blocked by browser, waiting for user interaction')
        })
    }

    return () => {
      audio.removeEventListener('canplaythrough', handleCanPlay)
      audio.removeEventListener('error', handleError)
      audio.removeEventListener('ended', handleEnded)
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
    const audio = audioRef.current
    if (!audio) {
      console.warn('Audio not initialized')
      return
    }

    if (isPlaying) {
      audio.pause()
      setIsPlaying(false)
      localStorage.setItem('prometheus-music-playing', 'false')
      console.log('🎵 Music paused')
    } else {
      audio.play()
        .then(() => {
          setIsPlaying(true)
          localStorage.setItem('prometheus-music-playing', 'true')
          console.log('🎵 Music playing')
        })
        .catch((err) => {
          console.warn('Play failed:', err)
          // Try creating a new audio element as fallback
          const newAudio = new Audio(MUSIC_URL)
          newAudio.loop = true
          newAudio.volume = volume
          audioRef.current = newAudio
          newAudio.play()
            .then(() => {
              setIsPlaying(true)
              localStorage.setItem('prometheus-music-playing', 'true')
              console.log('🎵 Music playing (fallback)')
            })
            .catch((e) => {
              console.error('Fallback also failed:', e)
            })
        })
    }
  }

  const setVolume = (newVolume: number) => {
    setVolumeState(newVolume)
  }

  return (
    <MusicContext.Provider value={{ isPlaying, isLoaded, volume, toggleMusic, setVolume }}>
      {children}
    </MusicContext.Provider>
  )
}

export function useMusic() {
  const context = useContext(MusicContext)
  if (context === undefined) {
    throw new Error('useMusic must be used within a MusicProvider')
  }
  return context
}
