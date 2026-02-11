'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Link from 'next/link'
import { Shield, Flame } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

interface AdminLayoutProps {
  children: React.ReactNode
}

function AdminProtection({ children }: AdminLayoutProps) {
  const { user, isLoading } = useAuth()
  const router = useRouter()
  const [isChecking, setIsChecking] = useState(true)

  useEffect(() => {
    if (!isLoading) {
      if (user && !user.is_superuser) {
        router.push('/dashboard')
      } else {
        setIsChecking(false)
      }
    }
  }, [user, isLoading, router])

  // Show loading while checking auth and superuser status
  if (isLoading || isChecking) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-abyss">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="text-center"
        >
          <div className="relative inline-block mb-6">
            <motion.div
              animate={{
                scale: [1, 1.1, 1],
                opacity: [0.5, 1, 0.5],
              }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-20 h-20 rounded-2xl bg-gradient-to-br from-imperial-500 to-primary-600 flex items-center justify-center"
            >
              <Shield className="w-10 h-10 text-dark-950" />
            </motion.div>
            <div className="absolute -inset-4 bg-imperial-500/20 rounded-3xl blur-2xl animate-pulse" />
          </div>
          <h2 className="font-imperial text-2xl text-gradient-gold mb-2">
            ADMIN PANEL
          </h2>
          <p className="text-dark-400">Verifying admin privileges...</p>
        </motion.div>
      </div>
    )
  }

  // User is not a superuser - this should redirect but show fallback just in case
  if (!user?.is_superuser) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-abyss px-4">
        <div className="text-center max-w-md">
          <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-loss/10 flex items-center justify-center">
            <Shield size={40} className="text-loss" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
          <p className="text-dark-400 mb-6">You do not have admin privileges to access this page.</p>
          <Link href="/dashboard" className="btn-primary">
            Return to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return <>{children}</>
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <ProtectedRoute>
      <AdminProtection>
        {children}
      </AdminProtection>
    </ProtectedRoute>
  )
}
