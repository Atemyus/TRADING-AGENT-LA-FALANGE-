'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'
import {
  Flame,
  Mail,
  ArrowLeft,
  AlertCircle,
  CheckCircle,
  Send,
} from 'lucide-react'
import { MusicPlayer } from '@/components/common/MusicPlayer'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setStatus('loading')
    setMessage('')

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/forgot-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      })

      const data = await response.json()

      if (response.ok) {
        setStatus('success')
        setMessage(data.message)
      } else {
        setStatus('error')
        setMessage(data.detail || 'An error occurred')
      }
    } catch {
      setStatus('error')
      setMessage('Network error. Please try again.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-imperial-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-primary-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/login" className="flex items-center gap-3 group">
            <div className="p-2 rounded-lg bg-dark-800/50 border border-primary-500/20 hover:border-primary-500/40 transition-all">
              <ArrowLeft size={20} className="text-dark-300" />
            </div>
            <Image
              src="/images/logo.png"
              alt="Prometheus AI Trading"
              width={200}
              height={60}
              className="h-12 w-auto hidden sm:block mix-blend-screen"
            />
          </Link>
          <MusicPlayer size="md" showLabel={false} />
        </div>
      </header>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <div className="card-imperial p-8">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="relative inline-block mb-4">
              <Image
                src="/images/logo.png"
                alt="Prometheus AI Trading"
                width={340}
                height={102}
                className="h-24 w-auto mix-blend-screen"
                priority
              />
              <div className="absolute -inset-4 bg-imperial-500/15 rounded-2xl blur-xl animate-pulse -z-10" />
            </div>
            <h2 className="font-imperial text-xl font-bold text-gradient-imperial tracking-wide mt-4">
              FORGOT PASSWORD
            </h2>
            <p className="text-dark-400 mt-2">
              Enter your email to receive a reset link
            </p>
          </div>

          {/* Success Message */}
          {status === 'success' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-profit/10 border border-profit/30 rounded-xl"
            >
              <div className="flex items-start gap-3">
                <CheckCircle size={20} className="text-profit flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-profit font-medium">Check your email!</p>
                  <p className="text-dark-400 text-sm mt-1">{message}</p>
                </div>
              </div>
            </motion.div>
          )}

          {/* Error Message */}
          {status === 'error' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-loss/10 border border-loss/30 rounded-xl flex items-center gap-3"
            >
              <AlertCircle size={20} className="text-loss flex-shrink-0" />
              <p className="text-loss text-sm">{message}</p>
            </motion.div>
          )}

          {/* Form */}
          {status !== 'success' && (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input pl-11"
                    placeholder="titan@prometheus.io"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={status === 'loading'}
                className="btn-imperial w-full py-4 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {status === 'loading' ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <Send size={20} />
                    <span>Send Reset Link</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* Back to login */}
          {status === 'success' && (
            <Link
              href="/login"
              className="btn-secondary w-full py-4 flex items-center justify-center gap-2"
            >
              <ArrowLeft size={20} />
              <span>Back to Login</span>
            </Link>
          )}

          {/* Divider */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-dark-700" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 bg-dark-900 text-dark-500 text-sm">
                Remember your password?
              </span>
            </div>
          </div>

          {/* Login Link */}
          <Link
            href="/login"
            className="btn-secondary w-full py-4 flex items-center justify-center gap-2"
          >
            <Flame size={20} />
            <span>Back to Login</span>
          </Link>
        </div>

        {/* Footer */}
        <p className="text-center text-dark-500 text-sm mt-6">
          The fire never dies
        </p>
      </motion.div>
    </div>
  )
}
