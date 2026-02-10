'use client'

import { useState } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import Link from 'next/link'
import {
  Flame,
  Lock,
  Eye,
  EyeOff,
  ArrowLeft,
  AlertCircle,
  CheckCircle,
  Check,
  KeyRound,
} from 'lucide-react'
import { MusicPlayer } from '@/components/common/MusicPlayer'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function ResetPasswordPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  const passwordRequirements = [
    { text: 'At least 8 characters', met: password.length >= 8 },
    { text: 'Contains a number', met: /\d/.test(password) },
    { text: 'Contains uppercase', met: /[A-Z]/.test(password) },
    { text: 'Passwords match', met: password === confirmPassword && confirmPassword !== '' },
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (password !== confirmPassword) {
      setStatus('error')
      setMessage('Passwords do not match')
      return
    }

    if (password.length < 8) {
      setStatus('error')
      setMessage('Password must be at least 8 characters')
      return
    }

    if (!token) {
      setStatus('error')
      setMessage('Invalid reset token')
      return
    }

    setStatus('loading')
    setMessage('')

    try {
      const response = await fetch(`${API_URL}/api/v1/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token, password }),
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
        setMessage(data.detail || 'An error occurred')
      }
    } catch {
      setStatus('error')
      setMessage('Network error. Please try again.')
    }
  }

  // No token provided
  if (!token) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-loss/10 rounded-full blur-3xl" />
        </div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md"
        >
          <div className="card p-8 border-loss/30">
            <div className="text-center">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-gradient-to-br from-loss to-red-600 flex items-center justify-center mb-4">
                <AlertCircle className="w-8 h-8 text-white" />
              </div>
              <h1 className="text-2xl font-bold text-loss mb-2">Invalid Link</h1>
              <p className="text-dark-400 mb-6">
                This password reset link is invalid or has expired.
              </p>
              <Link
                href="/forgot-password"
                className="btn-secondary w-full py-4 flex items-center justify-center gap-2"
              >
                <span>Request New Link</span>
              </Link>
            </div>
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] bg-imperial-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] bg-primary-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/login" className="flex items-center gap-3 group">
            <div className="p-2 rounded-lg bg-dark-800/50 border border-primary-500/20 hover:border-primary-500/40 transition-all">
              <ArrowLeft size={20} className="text-dark-300" />
            </div>
            <span className="text-dark-400 hidden sm:block">Back to login</span>
          </Link>
          <MusicPlayer size="md" showLabel={false} />
        </div>
      </header>

      {/* Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md mt-16"
      >
        <div className={`card p-8 ${status === 'success' ? 'border-profit/30' : 'border-imperial-500/30'}`}>
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="relative inline-block mb-4">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
                status === 'success'
                  ? 'bg-gradient-to-br from-profit to-green-600'
                  : 'bg-gradient-to-br from-imperial-500 to-primary-600'
              }`}>
                {status === 'success' ? (
                  <CheckCircle className="w-8 h-8 text-white" />
                ) : (
                  <KeyRound className="w-8 h-8 text-white" />
                )}
              </div>
              <div className={`absolute -inset-2 rounded-2xl blur-xl animate-pulse ${
                status === 'success' ? 'bg-profit/20' : 'bg-imperial-500/20'
              }`} />
            </div>
            <h1 className="font-imperial text-2xl font-bold tracking-wide">
              {status === 'success' ? (
                <span className="text-profit">PASSWORD RESET!</span>
              ) : (
                <span className="text-gradient-imperial">NEW PASSWORD</span>
              )}
            </h1>
            <p className="text-dark-400 mt-2">
              {status === 'success'
                ? 'Your password has been updated successfully'
                : 'Create a new secure password'
              }
            </p>
          </div>

          {/* Success Message */}
          {status === 'success' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-profit/10 border border-profit/30 rounded-xl"
            >
              <p className="text-profit text-center">{message}</p>
              <p className="text-dark-500 text-sm text-center mt-2">
                Redirecting to login in 3 seconds...
              </p>
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
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  New Password
                </label>
                <div className="relative">
                  <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input pl-11 pr-11"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-dark-500 hover:text-dark-300 transition-colors"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Confirm Password */}
              <div>
                <label className="block text-sm font-medium text-dark-300 mb-2">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="input pl-11 pr-11"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-dark-500 hover:text-dark-300 transition-colors"
                  >
                    {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Password Requirements */}
              <div className="grid grid-cols-2 gap-2 py-2">
                {passwordRequirements.map((req, index) => (
                  <div key={index} className="flex items-center gap-2">
                    <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
                      req.met ? 'bg-profit/20 text-profit' : 'bg-dark-700 text-dark-500'
                    }`}>
                      <Check size={10} />
                    </div>
                    <span className={`text-xs ${req.met ? 'text-profit' : 'text-dark-500'}`}>
                      {req.text}
                    </span>
                  </div>
                ))}
              </div>

              {/* Submit */}
              <button
                type="submit"
                disabled={status === 'loading'}
                className="btn-imperial w-full py-4 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {status === 'loading' ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                ) : (
                  <>
                    <KeyRound size={20} />
                    <span>Reset Password</span>
                  </>
                )}
              </button>
            </form>
          )}

          {/* Success - Go to Login */}
          {status === 'success' && (
            <Link
              href="/login"
              className="btn-primary w-full py-4 flex items-center justify-center gap-2"
            >
              <Flame size={20} />
              <span>Go to Login</span>
            </Link>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-dark-500 text-sm mt-6">
          Protected by the sacred fire
        </p>
      </motion.div>
    </div>
  )
}
