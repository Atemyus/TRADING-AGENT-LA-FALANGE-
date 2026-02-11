import type { Metadata } from 'next'
import './globals.css'
import { Providers } from '@/components/providers/Providers'

export const metadata: Metadata = {
  title: 'Prometheus | AI Trading Platform',
  description: 'AI-Powered CFD/Futures Trading Platform',
  icons: {
    icon: '/images/logo.svg',
    apple: '/images/logo.png',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-gradient-dark">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
