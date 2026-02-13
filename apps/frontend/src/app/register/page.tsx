'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'
import {
  Flame,
  Mail,
  Lock,
  User,
  Eye,
  EyeOff,
  UserPlus,
  ArrowLeft,
  AlertCircle,
  Check,
  Key,
} from 'lucide-react'
import { MusicPlayer } from '@/components/common/MusicPlayer'
import { useAuth } from '@/contexts/AuthContext'

export default function RegisterPage() {
  const { register } = useAuth()
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    licenseKey: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const passwordRequirements = [
    { text: 'At least 8 characters', met: formData.password.length >= 8 },
    { text: 'Contains a number', met: /\d/.test(formData.password) },
    { text: 'Contains uppercase', met: /[A-Z]/.test(formData.password) },
    { text: 'Passwords match', met: formData.password === formData.confirmPassword && formData.confirmPassword !== '' },
  ]

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate password strength
    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }

    setIsLoading(true)

    try {
      await register({
        email: formData.email,
        username: formData.username,
        password: formData.password,
        full_name: formData.fullName || undefined,
        license_key: formData.licenseKey,
      })
      setSuccess('Registration completed. Verify your email before logging in. Check spam/promotions if needed.')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12 relative overflow-hidden prometheus-auth-shell">
      {/* Background effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] bg-imperial-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] bg-primary-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between prometheus-auth-header px-3 py-2">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="p-2 rounded-lg bg-dark-800/50 border border-primary-500/20 hover:border-primary-500/40 transition-all">
              <ArrowLeft size={20} className="text-dark-300" />
            </div>
            <span className="text-dark-400 hidden sm:block">Back to home</span>
          </Link>
          <MusicPlayer size="md" showLabel={false} />
        </div>
      </header>

      {/* Register Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md mt-16"
      >
        <div className="card-imperial p-8 prometheus-auth-card forge-pattern">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="relative inline-block mb-4">
              <Image
                src="/images/logo.png"
                alt="Prometheus AI Trading"
                width={380}
                height={114}
                className="h-28 w-auto mix-blend-screen"
                priority
              />
              <div className="absolute -inset-4 bg-imperial-500/15 rounded-2xl blur-xl animate-pulse -z-10" />
            </div>
            <p className="text-dark-400 mt-2">Receive the gift of market fire</p>
          </div>

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-loss/10 border border-loss/30 rounded-xl flex items-center gap-3"
            >
              <AlertCircle size={20} className="text-loss flex-shrink-0" />
              <p className="text-loss text-sm">{error}</p>
            </motion.div>
          )}

          {success && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-profit/10 border border-profit/30 rounded-xl"
            >
              <p className="text-profit text-sm">{success}</p>
            </motion.div>
          )}

          {/* Form */}
          {!success && (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* License Key - Required */}
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                License Key <span className="text-imperial-400">*</span>
              </label>
              <div className="relative">
                <Key size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                <input
                  type="text"
                  name="licenseKey"
                  value={formData.licenseKey}
                  onChange={handleChange}
                  className="input pl-11 uppercase font-mono tracking-wider"
                  placeholder="LIC-XXXX-XXXX-XXXX-XXXX"
                  required
                />
              </div>
              <p className="text-xs text-dark-500 mt-1">Enter your license key to register</p>
            </div>

            {/* Full Name (Optional) */}
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Full Name <span className="text-dark-500">(optional)</span>
              </label>
              <div className="relative">
                <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                <input
                  type="text"
                  name="fullName"
                  value={formData.fullName}
                  onChange={handleChange}
                  className="input pl-11"
                  placeholder="Prometheus Titan"
                />
              </div>
            </div>

            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Username
              </label>
              <div className="relative">
                <User size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleChange}
                  className="input pl-11"
                  placeholder="titan_trader"
                  pattern="^[a-zA-Z0-9_]+$"
                  title="Only letters, numbers, and underscores"
                  required
                />
              </div>
              <p className="text-xs text-dark-500 mt-1">Only letters, numbers, and underscores</p>
            </div>

            {/* Email */}
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Email Address
              </label>
              <div className="relative">
                <Mail size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  className="input pl-11"
                  placeholder="titan@prometheus.io"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-dark-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-dark-500" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  name="password"
                  value={formData.password}
                  onChange={handleChange}
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
                  name="confirmPassword"
                  value={formData.confirmPassword}
                  onChange={handleChange}
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
            <div className="grid grid-cols-2 gap-2">
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

            {/* Terms */}
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                required
                className="mt-1 w-4 h-4 rounded border-dark-600 bg-dark-800 text-imperial-500 focus:ring-imperial-500 focus:ring-offset-0"
              />
              <span className="text-sm text-dark-400">
                I accept the{' '}
                <Link href="/terms" className="text-imperial-400 hover:text-imperial-300">
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link href="/privacy" className="text-imperial-400 hover:text-imperial-300">
                  Privacy Policy
                </Link>
              </span>
            </label>

            {/* Submit */}
            <button
              type="submit"
              disabled={isLoading}
              className="btn-imperial w-full py-4 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <>
                  <UserPlus size={20} />
                  <span>Begin Your Ascension</span>
                </>
              )}
            </button>
          </form>
          )}

          {success && (
            <Link
              href="/login"
              className="btn-primary w-full py-4 flex items-center justify-center gap-2"
            >
              <Flame size={20} />
              <span>Go to Login</span>
            </Link>
          )}

          {/* Divider */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-dark-700" />
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 bg-dark-900 text-dark-500 text-sm">
                Already a Titan?
              </span>
            </div>
          </div>

          {/* Login Link */}
          <Link
            href="/login"
            className="btn-secondary w-full py-4 flex items-center justify-center gap-2"
          >
            <Flame size={20} />
            <span>Return to the Realm</span>
          </Link>
        </div>

        {/* Footer */}
        <p className="text-center text-dark-500 text-sm mt-6">
          The fire of knowledge shall set you free
        </p>
      </motion.div>
    </div>
  )
}
