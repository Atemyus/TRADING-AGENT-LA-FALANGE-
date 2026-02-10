'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'
import {
  Flame,
  CheckCircle,
  XCircle,
  Loader2,
  ArrowLeft,
} from 'lucide-react'
import { MusicPlayer } from '@/components/common/MusicPlayer'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function VerifyEmailContent() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = searchParams.get('token')

  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('No verification token provided')
      return
    }

    const verifyEmail = async () => {
      try {
        const response = await fetch(`${API_URL}/api/v1/auth/verify-email`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ token }),
        })

        const data = await response.json()

        if (response.ok) {
          setStatus('success')
          setMessage(data.message)
          // Redirect to login after 3 seconds
          setTimeout(() => {
            router.push('/login')
          }, 3000)
        } else {
          setStatus('error')
          setMessage(data.detail || 'Verification failed')
        }
      } catch {
        setStatus('error')
        setMessage('An error occurred. Please try again.')
      }
    }

    verifyEmail()
  }, [token, router])

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-primary-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-imperial-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="p-2 rounded-lg bg-dark-800/50 border border-primary-500/20 hover:border-primary-500/40 transition-all">
              <ArrowLeft size={20} className="text-dark-300" />
            </div>
            <Image
              src="/images/logo.png"
              alt="Prometheus AI Trading"
              width={150}
              height={45}
              className="h-8 w-auto hidden sm:block mix-blend-screen"
            />
          </Link>
          <MusicPlayer size="md" showLabel={false} />
        </div>
      </header>

      {/* Verification Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className={`card p-8 ${status === 'success' ? 'border-profit/30' : status === 'error' ? 'border-loss/30' : 'border-primary-500/30'}`}>
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="relative inline-block mb-4">
              <div className={`w-20 h-20 rounded-2xl flex items-center justify-center ${
                status === 'loading' ? 'bg-gradient-to-br from-primary-500 to-imperial-600' :
                status === 'success' ? 'bg-gradient-to-br from-profit to-green-600' :
                'bg-gradient-to-br from-loss to-red-600'
              }`}>
                {status === 'loading' && (
                  <Loader2 className="w-10 h-10 text-white animate-spin" />
                )}
                {status === 'success' && (
                  <CheckCircle className="w-10 h-10 text-white" />
                )}
                {status === 'error' && (
                  <XCircle className="w-10 h-10 text-white" />
                )}
              </div>
              <div className={`absolute -inset-2 rounded-2xl blur-xl animate-pulse ${
                status === 'loading' ? 'bg-primary-500/20' :
                status === 'success' ? 'bg-profit/20' :
                'bg-loss/20'
              }`} />
            </div>

            <h1 className="font-imperial text-2xl font-bold tracking-wide mb-2">
              {status === 'loading' && 'Verifying Email...'}
              {status === 'success' && (
                <span className="text-profit">Email Verified!</span>
              )}
              {status === 'error' && (
                <span className="text-loss">Verification Failed</span>
              )}
            </h1>

            <p className="text-dark-400 mt-4">
              {message || (status === 'loading' ? 'Please wait while we verify your email...' : '')}
            </p>

            {status === 'success' && (
              <p className="text-dark-500 text-sm mt-4">
                Redirecting to login in 3 seconds...
              </p>
            )}
          </div>

          {/* Actions */}
          {status === 'success' && (
            <Link
              href="/login"
              className="btn-primary w-full py-4 flex items-center justify-center gap-2"
            >
              <Flame size={20} />
              <span>Go to Login</span>
            </Link>
          )}

          {status === 'error' && (
            <div className="space-y-3">
              <Link
                href="/login"
                className="btn-secondary w-full py-4 flex items-center justify-center gap-2"
              >
                <span>Try Login</span>
              </Link>
              <p className="text-center text-dark-500 text-sm">
                or <Link href="/register" className="text-primary-400 hover:text-primary-300">create a new account</Link>
              </p>
            </div>
          )}
        </div>
      </motion.div>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <Loader2 className="w-10 h-10 text-primary-500 animate-spin" />
    </div>
  )
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <VerifyEmailContent />
    </Suspense>
  )
}
