'use client'

import { ReactNode } from 'react'
import { AuthProvider } from '@/contexts/AuthContext'
import { MusicProvider } from '@/contexts/MusicContext'

interface ProvidersProps {
  children: ReactNode
}

export function Providers({ children }: ProvidersProps) {
  return (
    <AuthProvider>
      <MusicProvider>
        {children}
      </MusicProvider>
    </AuthProvider>
  )
}

export default Providers
