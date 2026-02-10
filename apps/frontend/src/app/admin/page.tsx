'use client'

import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'
import { useRouter } from 'next/navigation'
import {
  Shield,
  Key,
  Users,
  Plus,
  Trash2,
  Copy,
  Check,
  X,
  AlertCircle,
  Clock,
  Ban,
  RefreshCw,
  ChevronDown,
  ArrowLeft,
  LogOut,
  Calendar,
  Hash,
  UserCheck,
  UserX,
  Flame,
  Crown,
} from 'lucide-react'
import { MusicPlayer } from '@/components/common/MusicPlayer'
import { useAuth } from '@/contexts/AuthContext'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface License {
  id: number
  key: string
  name: string | null
  description: string | null
  status: string
  is_active: boolean
  max_uses: number
  current_uses: number
  expires_at: string | null
  created_at: string
  created_by: number | null
  is_valid: boolean
  is_expired: boolean
}

interface User {
  id: number
  email: string
  username: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  license_id: number | null
  license_key: string | null
  license_expires_at: string | null
  license_activated_at: string | null
  created_at: string
  last_login_at: string | null
}

interface Stats {
  total_users: number
  active_users: number
  verified_users: number
  total_licenses: number
  active_licenses: number
  used_licenses: number
  expired_licenses: number
}

export default function AdminPage() {
  const router = useRouter()
  const { user, logout, isLoading: authLoading } = useAuth()
  const [activeTab, setActiveTab] = useState<'licenses' | 'users'>('licenses')
  const [licenses, setLicenses] = useState<License[]>([])
  const [users, setUsers] = useState<User[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [copiedKey, setCopiedKey] = useState<string | null>(null)

  // Create license modal state
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createForm, setCreateForm] = useState({
    name: '',
    description: '',
    max_uses: 1,
    expires_in_days: 30,
  })
  const [isCreating, setIsCreating] = useState(false)

  // Bulk create state
  const [showBulkModal, setShowBulkModal] = useState(false)
  const [bulkForm, setBulkForm] = useState({
    count: 10,
    name_prefix: 'Demo License',
    max_uses: 1,
    expires_in_days: 30,
  })

  const getToken = () => localStorage.getItem('access_token')

  const fetchData = useCallback(async () => {
    const token = getToken()
    if (!token) return

    setIsLoading(true)
    try {
      const [statsRes, licensesRes, usersRes] = await Promise.all([
        fetch(`${API_URL}/api/v1/admin/stats`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/admin/licenses`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
        fetch(`${API_URL}/api/v1/admin/users`, {
          headers: { Authorization: `Bearer ${token}` },
        }),
      ])

      if (statsRes.status === 403 || licensesRes.status === 403) {
        setError('Access denied. Admin privileges required.')
        return
      }

      if (statsRes.ok) setStats(await statsRes.json())
      if (licensesRes.ok) setLicenses(await licensesRes.json())
      if (usersRes.ok) setUsers(await usersRes.json())
    } catch {
      setError('Failed to load admin data')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!authLoading && !user) {
      router.push('/login')
      return
    }
    if (user && !user.is_superuser) {
      router.push('/dashboard')
      return
    }
    if (user?.is_superuser) {
      fetchData()
    }
  }, [user, authLoading, router, fetchData])

  const createLicense = async () => {
    const token = getToken()
    if (!token) return

    setIsCreating(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/admin/licenses`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(createForm),
      })

      if (response.ok) {
        setShowCreateModal(false)
        setCreateForm({ name: '', description: '', max_uses: 1, expires_in_days: 30 })
        fetchData()
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to create license')
      }
    } catch {
      setError('Failed to create license')
    } finally {
      setIsCreating(false)
    }
  }

  const createBulkLicenses = async () => {
    const token = getToken()
    if (!token) return

    setIsCreating(true)
    try {
      const response = await fetch(`${API_URL}/api/v1/admin/licenses/bulk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(bulkForm),
      })

      if (response.ok) {
        setShowBulkModal(false)
        setBulkForm({ count: 10, name_prefix: 'Demo License', max_uses: 1, expires_in_days: 30 })
        fetchData()
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to create licenses')
      }
    } catch {
      setError('Failed to create licenses')
    } finally {
      setIsCreating(false)
    }
  }

  const revokeLicense = async (licenseId: number) => {
    const token = getToken()
    if (!token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/admin/licenses/${licenseId}/revoke`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        fetchData()
      }
    } catch {
      setError('Failed to revoke license')
    }
  }

  const deleteLicense = async (licenseId: number) => {
    const token = getToken()
    if (!token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/admin/licenses/${licenseId}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        fetchData()
      } else {
        const data = await response.json()
        setError(data.detail || 'Failed to delete license')
      }
    } catch {
      setError('Failed to delete license')
    }
  }

  const toggleUserActive = async (userId: number) => {
    const token = getToken()
    if (!token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/admin/users/${userId}/toggle-active`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        fetchData()
      }
    } catch {
      setError('Failed to update user')
    }
  }

  const toggleUserSuperuser = async (userId: number) => {
    const token = getToken()
    if (!token) return

    try {
      const response = await fetch(`${API_URL}/api/v1/admin/users/${userId}/toggle-superuser`, {
        method: 'PUT',
        headers: { Authorization: `Bearer ${token}` },
      })

      if (response.ok) {
        fetchData()
      }
    } catch {
      setError('Failed to update user')
    }
  }

  const copyToClipboard = (key: string) => {
    navigator.clipboard.writeText(key)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—'
    return new Date(dateString).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  }

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dark-abyss">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-dark-400">Loading admin panel...</p>
        </div>
      </div>
    )
  }

  if (error === 'Access denied. Admin privileges required.') {
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

  return (
    <div className="min-h-screen bg-dark-abyss">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-dark-950/90 backdrop-blur-xl border-b border-primary-500/20">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link href="/dashboard" className="p-2 hover:bg-dark-800 rounded-lg transition-colors">
                <ArrowLeft size={20} className="text-dark-400" />
              </Link>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/20 to-imperial-500/20 border border-primary-500/30 flex items-center justify-center">
                  <Shield size={20} className="text-primary-400" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-white">Admin Panel</h1>
                  <p className="text-xs text-dark-500">License & User Management</p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <MusicPlayer size="md" showLabel={false} />
              <button
                onClick={() => fetchData()}
                className="p-2 hover:bg-dark-800 rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw size={18} className="text-dark-400" />
              </button>
              {user && (
                <div className="flex items-center gap-3 pl-4 border-l border-dark-700">
                  <div className="flex items-center gap-2">
                    <Crown size={16} className="text-imperial-400" />
                    <span className="text-sm font-medium text-dark-200">{user.username}</span>
                  </div>
                  <button
                    onClick={logout}
                    className="p-2 hover:bg-loss/10 rounded-lg transition-colors text-dark-400 hover:text-loss"
                  >
                    <LogOut size={18} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Banner */}
        <AnimatePresence>
          {error && error !== 'Access denied. Admin privileges required.' && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6 p-4 bg-loss/10 border border-loss/30 rounded-xl flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <AlertCircle size={20} className="text-loss" />
                <p className="text-loss text-sm">{error}</p>
              </div>
              <button onClick={() => setError('')} className="text-loss hover:text-loss/70">
                <X size={18} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="card p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary-500/10 flex items-center justify-center">
                  <Key size={20} className="text-primary-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.total_licenses}</p>
                  <p className="text-xs text-dark-500">Total Licenses</p>
                </div>
              </div>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-profit/10 flex items-center justify-center">
                  <Check size={20} className="text-profit" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.active_licenses}</p>
                  <p className="text-xs text-dark-500">Active Licenses</p>
                </div>
              </div>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-imperial-500/10 flex items-center justify-center">
                  <Users size={20} className="text-imperial-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.total_users}</p>
                  <p className="text-xs text-dark-500">Total Users</p>
                </div>
              </div>
            </div>
            <div className="card p-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-loss/10 flex items-center justify-center">
                  <Clock size={20} className="text-loss" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.expired_licenses}</p>
                  <p className="text-xs text-dark-500">Expired</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-2 mb-6">
          <button
            onClick={() => setActiveTab('licenses')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'licenses'
                ? 'bg-primary-500 text-dark-950'
                : 'bg-dark-800 text-dark-400 hover:text-white'
            }`}
          >
            <span className="flex items-center gap-2">
              <Key size={18} />
              Licenses ({licenses.length})
            </span>
          </button>
          <button
            onClick={() => setActiveTab('users')}
            className={`px-4 py-2 rounded-lg font-medium transition-all ${
              activeTab === 'users'
                ? 'bg-primary-500 text-dark-950'
                : 'bg-dark-800 text-dark-400 hover:text-white'
            }`}
          >
            <span className="flex items-center gap-2">
              <Users size={18} />
              Users ({users.length})
            </span>
          </button>

          <div className="flex-1" />

          {activeTab === 'licenses' && (
            <div className="flex gap-2">
              <button
                onClick={() => setShowCreateModal(true)}
                className="btn-primary py-2 px-4 flex items-center gap-2"
              >
                <Plus size={18} />
                Create License
              </button>
              <button
                onClick={() => setShowBulkModal(true)}
                className="btn-secondary py-2 px-4 flex items-center gap-2"
              >
                <Hash size={18} />
                Bulk Create
              </button>
            </div>
          )}
        </div>

        {/* Licenses Tab */}
        {activeTab === 'licenses' && (
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-700">
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">License Key</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Name</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Status</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Uses</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Expires</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Created</th>
                    <th className="text-right p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {licenses.map((license) => (
                    <tr key={license.id} className="border-b border-dark-800 hover:bg-dark-800/50 transition-colors">
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <code className="text-sm font-mono text-primary-400">{license.key}</code>
                          <button
                            onClick={() => copyToClipboard(license.key)}
                            className="p-1 hover:bg-dark-700 rounded transition-colors"
                            title="Copy to clipboard"
                          >
                            {copiedKey === license.key ? (
                              <Check size={14} className="text-profit" />
                            ) : (
                              <Copy size={14} className="text-dark-500" />
                            )}
                          </button>
                        </div>
                      </td>
                      <td className="p-4 text-sm text-dark-300">{license.name || '—'}</td>
                      <td className="p-4">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                          license.is_valid
                            ? 'bg-profit/10 text-profit'
                            : license.is_expired
                            ? 'bg-loss/10 text-loss'
                            : 'bg-dark-700 text-dark-400'
                        }`}>
                          {license.is_valid ? (
                            <><Check size={12} /> Active</>
                          ) : license.is_expired ? (
                            <><Clock size={12} /> Expired</>
                          ) : (
                            <><Ban size={12} /> {license.status}</>
                          )}
                        </span>
                      </td>
                      <td className="p-4 text-sm">
                        <span className="text-dark-300">{license.current_uses}</span>
                        <span className="text-dark-600"> / {license.max_uses}</span>
                      </td>
                      <td className="p-4 text-sm text-dark-400">{formatDate(license.expires_at)}</td>
                      <td className="p-4 text-sm text-dark-400">{formatDate(license.created_at)}</td>
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          {license.is_active && (
                            <button
                              onClick={() => revokeLicense(license.id)}
                              className="p-2 hover:bg-loss/10 rounded-lg transition-colors text-dark-400 hover:text-loss"
                              title="Revoke License"
                            >
                              <Ban size={16} />
                            </button>
                          )}
                          {license.current_uses === 0 && (
                            <button
                              onClick={() => deleteLicense(license.id)}
                              className="p-2 hover:bg-loss/10 rounded-lg transition-colors text-dark-400 hover:text-loss"
                              title="Delete License"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {licenses.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-8 text-center text-dark-500">
                        No licenses found. Create your first license to get started.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-dark-700">
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">User</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Status</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">License</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Registered</th>
                    <th className="text-left p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Last Login</th>
                    <th className="text-right p-4 text-xs font-semibold text-dark-400 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="border-b border-dark-800 hover:bg-dark-800/50 transition-colors">
                      <td className="p-4">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                            u.is_superuser
                              ? 'bg-imperial-500/20 border border-imperial-500/30'
                              : 'bg-dark-700'
                          }`}>
                            {u.is_superuser ? (
                              <Crown size={14} className="text-imperial-400" />
                            ) : (
                              <Users size={14} className="text-dark-400" />
                            )}
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{u.username}</p>
                            <p className="text-xs text-dark-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="p-4">
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                            u.is_active ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'
                          }`}>
                            {u.is_active ? <UserCheck size={12} /> : <UserX size={12} />}
                            {u.is_active ? 'Active' : 'Disabled'}
                          </span>
                          {u.is_verified && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-primary-500/10 text-primary-400">
                              <Check size={10} /> Verified
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="p-4">
                        {u.license_key ? (
                          <div>
                            <code className="text-xs font-mono text-primary-400">{u.license_key.slice(0, 12)}...</code>
                            {u.license_expires_at && (
                              <p className="text-xs text-dark-500 mt-0.5">
                                Expires: {formatDate(u.license_expires_at)}
                              </p>
                            )}
                          </div>
                        ) : (
                          <span className="text-dark-500 text-sm">No license</span>
                        )}
                      </td>
                      <td className="p-4 text-sm text-dark-400">{formatDate(u.created_at)}</td>
                      <td className="p-4 text-sm text-dark-400">{formatDate(u.last_login_at)}</td>
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => toggleUserActive(u.id)}
                            className={`p-2 rounded-lg transition-colors ${
                              u.is_active
                                ? 'hover:bg-loss/10 text-dark-400 hover:text-loss'
                                : 'hover:bg-profit/10 text-dark-400 hover:text-profit'
                            }`}
                            title={u.is_active ? 'Disable User' : 'Enable User'}
                          >
                            {u.is_active ? <UserX size={16} /> : <UserCheck size={16} />}
                          </button>
                          <button
                            onClick={() => toggleUserSuperuser(u.id)}
                            className={`p-2 rounded-lg transition-colors ${
                              u.is_superuser
                                ? 'hover:bg-dark-700 text-imperial-400'
                                : 'hover:bg-imperial-500/10 text-dark-400 hover:text-imperial-400'
                            }`}
                            title={u.is_superuser ? 'Remove Admin' : 'Make Admin'}
                          >
                            <Crown size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {users.length === 0 && (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-dark-500">
                        No users found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* Create License Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowCreateModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="card-gold p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Key size={20} className="text-primary-400" />
                  Create License
                </h2>
                <button
                  onClick={() => setShowCreateModal(false)}
                  className="p-2 hover:bg-dark-800 rounded-lg transition-colors"
                >
                  <X size={18} className="text-dark-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">Name (optional)</label>
                  <input
                    type="text"
                    value={createForm.name}
                    onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
                    className="input"
                    placeholder="Demo License"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">Description (optional)</label>
                  <input
                    type="text"
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    className="input"
                    placeholder="For demo purposes"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-dark-300 mb-2">Max Uses</label>
                    <input
                      type="number"
                      value={createForm.max_uses}
                      onChange={(e) => setCreateForm({ ...createForm, max_uses: parseInt(e.target.value) || 1 })}
                      className="input"
                      min={1}
                      max={1000}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-dark-300 mb-2">Expires in (days)</label>
                    <input
                      type="number"
                      value={createForm.expires_in_days}
                      onChange={(e) => setCreateForm({ ...createForm, expires_in_days: parseInt(e.target.value) || 30 })}
                      className="input"
                      min={1}
                      max={3650}
                    />
                  </div>
                </div>

                <button
                  onClick={createLicense}
                  disabled={isCreating}
                  className="btn-primary w-full py-3 flex items-center justify-center gap-2"
                >
                  {isCreating ? (
                    <div className="w-5 h-5 border-2 border-dark-950 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <Plus size={18} />
                      Create License
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Bulk Create Modal */}
      <AnimatePresence>
        {showBulkModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={() => setShowBulkModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="card-gold p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-white flex items-center gap-2">
                  <Hash size={20} className="text-primary-400" />
                  Bulk Create Licenses
                </h2>
                <button
                  onClick={() => setShowBulkModal(false)}
                  className="p-2 hover:bg-dark-800 rounded-lg transition-colors"
                >
                  <X size={18} className="text-dark-400" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">Number of Licenses</label>
                  <input
                    type="number"
                    value={bulkForm.count}
                    onChange={(e) => setBulkForm({ ...bulkForm, count: parseInt(e.target.value) || 1 })}
                    className="input"
                    min={1}
                    max={100}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-dark-300 mb-2">Name Prefix</label>
                  <input
                    type="text"
                    value={bulkForm.name_prefix}
                    onChange={(e) => setBulkForm({ ...bulkForm, name_prefix: e.target.value })}
                    className="input"
                    placeholder="Demo License"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-dark-300 mb-2">Max Uses</label>
                    <input
                      type="number"
                      value={bulkForm.max_uses}
                      onChange={(e) => setBulkForm({ ...bulkForm, max_uses: parseInt(e.target.value) || 1 })}
                      className="input"
                      min={1}
                      max={1000}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-dark-300 mb-2">Expires in (days)</label>
                    <input
                      type="number"
                      value={bulkForm.expires_in_days}
                      onChange={(e) => setBulkForm({ ...bulkForm, expires_in_days: parseInt(e.target.value) || 30 })}
                      className="input"
                      min={1}
                      max={3650}
                    />
                  </div>
                </div>

                <button
                  onClick={createBulkLicenses}
                  disabled={isCreating}
                  className="btn-primary w-full py-3 flex items-center justify-center gap-2"
                >
                  {isCreating ? (
                    <div className="w-5 h-5 border-2 border-dark-950 border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <>
                      <Plus size={18} />
                      Create {bulkForm.count} Licenses
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
