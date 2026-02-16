'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect, useMemo, useRef } from 'react'
import {
  Brain,
  Shield,
  Bell,
  ChevronLeft,
  ChevronRight,
  Check,
  Eye,
  EyeOff,
  TestTube,
  Loader2,
  AlertCircle,
  CheckCircle,
  Info,
  Plus,
  Trash2,
  Edit3,
  Play,
  Square,
  RefreshCw,
  Users,
} from 'lucide-react'
import { settingsApi, brokerAccountsApi, type BrokerAccountData, type BrokerAccountCreate } from '@/lib/api'
import {
  BROKER_DIRECTORY,
  getBrokerTypeByPlatform,
  getMetaTraderServerPresets,
  inferBrokerFromAccountName,
  inferPlatformFromAccountName,
  getLogoCandidates,
} from '@/lib/brokerCatalog'
import { useAuth } from '@/contexts/AuthContext'

// Reusable Toggle Component
function Toggle({
  enabled,
  onChange,
  color = 'primary',
}: {
  enabled: boolean
  onChange: () => void
  color?: 'primary' | 'green'
}) {
  const bgColor = enabled
    ? color === 'green'
      ? 'bg-neon-green'
      : 'bg-primary-500'
    : 'bg-dark-600'

  return (
    <button
      type="button"
      role="switch"
      aria-checked={enabled}
      onClick={onChange}
      className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 focus:ring-offset-dark-900 ${bgColor}`}
    >
      <span
        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
          enabled ? 'translate-x-5' : 'translate-x-0'
        }`}
      />
    </button>
  )
}

function BrokerLogo({
  name,
  domain,
  logoUrl,
  className = 'h-9 w-9',
}: {
  name: string
  domain?: string
  logoUrl?: string
  className?: string
}) {
  const logoCandidates = useMemo(() => getLogoCandidates(domain, logoUrl), [domain, logoUrl])
  const [logoIndex, setLogoIndex] = useState(0)
  const logoSrc = logoCandidates[logoIndex] || ''

  useEffect(() => {
    setLogoIndex(0)
  }, [domain, logoUrl])

  if (!logoSrc) {
    return (
      <div className={`${className} rounded-lg bg-dark-700 border border-dark-600 flex items-center justify-center text-xs font-semibold text-dark-200`}>
        {name.split(' ').map((chunk) => chunk[0]).join('').slice(0, 2).toUpperCase()}
      </div>
    )
  }

  return (
    <img
      src={logoSrc}
      alt={`${name} logo`}
      className={`${className} rounded-lg object-contain border border-dark-600 bg-white/90 p-1`}
      onError={() => setLogoIndex((prev) => prev + 1)}
      loading="lazy"
    />
  )
}

// AI Provider configurations
const AI_PROVIDERS = [
  {
    id: 'aiml',
    name: 'AIML API',
    icon: 'AI',
    models: ['ChatGPT 5.2', 'Gemini 3 Pro', 'Grok 4.1 Fast', 'Qwen3 VL', 'Llama 4 Scout', 'ERNIE 4.5 VL'],
    field: { key: 'AIML_API_KEY', label: 'API Key', placeholder: 'Your AIML API key' },
    badge: '6 Models',
    description: 'Single API key for 6 AI models via api.aimlapi.com',
  },
  {
    id: 'nvidia',
    name: 'NVIDIA API',
    icon: 'NV',
    models: ['Kimi K2.5', 'Mistral Large 3'],
    field: { key: 'NVIDIA_API_KEY', label: 'API Key', placeholder: 'Your NVIDIA API key' },
    badge: '2 Models',
    description: 'Kimi K2.5 e Mistral Large 3 via integrate.api.nvidia.com',
  },
]

type SettingsSection = 'accounts' | 'ai' | 'risk' | 'notifications'

const DEFAULT_BROKER_SYMBOLS = ['EUR/USD', 'XAU/USD']
const DEFAULT_ENABLED_MODELS = ['chatgpt', 'gemini', 'grok', 'qwen', 'llama', 'ernie', 'kimi', 'mistral']

const createDefaultBrokerFormData = (): BrokerAccountCreate => ({
  name: '',
  broker_type: 'metaapi',
  is_enabled: true,
  symbols: [...DEFAULT_BROKER_SYMBOLS],
  risk_per_trade_percent: 1.0,
  max_open_positions: 3,
  max_daily_trades: 10,
  max_daily_loss_percent: 5.0,
  analysis_mode: 'standard',
  analysis_interval_seconds: 300,
  min_confidence: 75.0,
  min_models_agree: 4,
  enabled_models: [...DEFAULT_ENABLED_MODELS],
  trading_start_hour: 7,
  trading_end_hour: 21,
})

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingsSection>('accounts')
  const [aiProviders, setAiProviders] = useState<Record<string, { enabled: boolean; key: string }>>({})
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string>('')

  // Load settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const settings = await settingsApi.getAll()

        // Set AI providers
        const aiSettings: Record<string, { enabled: boolean; key: string }> = {}
        if (settings.ai.aiml_api_key) {
          aiSettings.aiml = { enabled: true, key: settings.ai.aiml_api_key }
        }
        if (settings.ai.nvidia_api_key) {
          aiSettings.nvidia = { enabled: true, key: settings.ai.nvidia_api_key }
        }
        setAiProviders(aiSettings)

      } catch (error) {
        console.error('Failed to load settings:', error)
      }
    }
    loadSettings()
  }, [])

  const handleSaveAI = async () => {
    setSaving(true)
    setSaveMessage('')

    try {
      // Build AI settings from provider settings
      const aiData: Record<string, string | undefined> = {}

      // Map provider IDs to API key names
      const keyMapping: Record<string, string> = {
        aiml: 'aiml_api_key',
        nvidia: 'nvidia_api_key',
      }

      for (const [providerId, settings] of Object.entries(aiProviders)) {
        if (settings.enabled && settings.key) {
          const keyName = keyMapping[providerId]
          if (keyName) {
            aiData[keyName] = settings.key
          }
        }
      }

      const result = await settingsApi.updateAI(aiData)
      setSaveMessage(result.message || 'AI settings saved successfully!')
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : 'Failed to save AI settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveRisk = async (riskData: {
    maxPositions: number
    maxDailyTrades: number
    maxDailyLossPercent: number
    riskPerTrade: number
    defaultLeverage: number
    enableTrading: boolean
  }) => {
    setSaving(true)
    setSaveMessage('')

    try {
      const result = await settingsApi.updateRisk({
        max_positions: riskData.maxPositions,
        max_daily_trades: riskData.maxDailyTrades,
        max_daily_loss_percent: riskData.maxDailyLossPercent,
        risk_per_trade: riskData.riskPerTrade,
        default_leverage: riskData.defaultLeverage,
        trading_enabled: riskData.enableTrading,
      })
      setSaveMessage(result.message || 'Risk settings saved successfully!')
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : 'Failed to save risk settings')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveNotifications = async (notifData: {
    telegramEnabled: boolean
    telegramBotToken: string
    telegramChatId: string
    discordEnabled: boolean
    discordWebhook: string
  }) => {
    setSaving(true)
    setSaveMessage('')

    try {
      const result = await settingsApi.updateNotifications({
        telegram_enabled: notifData.telegramEnabled,
        telegram_bot_token: notifData.telegramBotToken || undefined,
        telegram_chat_id: notifData.telegramChatId || undefined,
        discord_enabled: notifData.discordEnabled,
        discord_webhook: notifData.discordWebhook || undefined,
      })
      setSaveMessage(result.message || 'Notification settings saved successfully!')
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : 'Failed to save notification settings')
    } finally {
      setSaving(false)
    }
  }

  const sections = [
    { id: 'accounts', label: 'Broker Accounts', icon: Users },
    { id: 'ai', label: 'AI Providers', icon: Brain },
    { id: 'risk', label: 'Risk Management', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ] as const

  return (
    <div className="max-w-6xl mx-auto space-y-6 prometheus-page-shell">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="prometheus-hero-card p-6 md:p-7"
      >
        <div className="relative z-10">
          <span className="prometheus-chip mb-3">
            <Shield size={12} />
            Configuration Core
          </span>
          <h1 className="text-3xl font-bold mb-2 text-gradient-falange">Settings</h1>
          <p className="text-dark-300">Manage broker workspaces, AI providers, and risk controls</p>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-1"
        >
          <nav className="card p-2 space-y-1">
            {sections.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveSection(id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                  activeSection === id
                    ? 'bg-primary-500/20 text-primary-400'
                    : 'text-dark-400 hover:bg-dark-800 hover:text-dark-200'
                }`}
              >
                <Icon size={20} />
                <span className="font-medium">{label}</span>
                <ChevronRight size={16} className="ml-auto" />
              </button>
            ))}
          </nav>
        </motion.div>

        {/* Content */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="lg:col-span-3"
        >
          <AnimatePresence mode="wait">
            {activeSection === 'accounts' && (
              <BrokerAccountsSettings key="accounts" />
            )}

            {activeSection === 'ai' && (
              <AIProvidersSettings
                key="ai"
                providers={AI_PROVIDERS}
                providerSettings={aiProviders}
                setProviderSettings={setAiProviders}
                onSave={handleSaveAI}
                saving={saving}
                saveMessage={saveMessage}
              />
            )}

            {activeSection === 'risk' && (
              <RiskSettings key="risk" onSave={handleSaveRisk} saving={saving} saveMessage={saveMessage} />
            )}

            {activeSection === 'notifications' && (
              <NotificationSettings key="notifications" onSave={handleSaveNotifications} saving={saving} saveMessage={saveMessage} />
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </div>
  )
}

// AI Providers Settings Component
function AIProvidersSettings({
  providers,
  providerSettings,
  setProviderSettings,
  onSave,
  saving,
  saveMessage,
}: {
  providers: typeof AI_PROVIDERS
  providerSettings: Record<string, { enabled: boolean; key: string }>
  setProviderSettings: (settings: Record<string, { enabled: boolean; key: string }>) => void
  onSave: () => void
  saving: boolean
  saveMessage?: string
}) {
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({})

  const toggleProvider = (id: string) => {
    setProviderSettings({
      ...providerSettings,
      [id]: {
        ...providerSettings[id],
        enabled: !providerSettings[id]?.enabled,
      },
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Info Banner for AI Providers */}
      <div className="p-4 bg-primary-500/10 border border-primary-500/30 rounded-xl flex items-start gap-3">
        <Info size={20} className="text-primary-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-primary-300 font-medium">8 Modelli AI - 2 Provider</p>
          <p className="text-xs text-dark-400 mt-1">
            6 modelli via <a href="https://aimlapi.com" target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">AIML API</a> (ChatGPT 5.2, Gemini 3 Pro, Grok 4.1 Fast, Qwen3 VL, Llama 4 Scout, ERNIE 4.5 VL)
            + 2 modelli via <a href="https://build.nvidia.com" target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">NVIDIA API</a> (Kimi K2.5, Mistral Large 3)
          </p>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-2">AI Providers</h2>
        <p className="text-dark-400 mb-6">
          Configura le chiavi API per i modelli di analisi AI (8 modelli totali).
        </p>

        <div className="space-y-4">
          {providers.map((provider) => (
            <div
              key={provider.id}
              className={`p-4 rounded-xl border transition-all ${
                providerSettings[provider.id]?.enabled
                  ? provider.id === 'aiml'
                    ? 'border-neon-green/50 bg-neon-green/5'
                    : 'border-primary-500/50 bg-primary-500/5'
                  : 'border-dark-700 bg-dark-800/50'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span className="text-2xl">{provider.icon}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold">{provider.name}</span>
                      {provider.badge && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          provider.id === 'aiml'
                            ? 'bg-neon-green/20 text-neon-green'
                            : 'bg-primary-500/20 text-primary-400'
                        }`}>
                          {provider.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-dark-400">
                      {provider.description || `Models: ${provider.models.join(', ')}`}
                    </p>
                  </div>
                </div>
                <Toggle
                  enabled={providerSettings[provider.id]?.enabled || false}
                  onChange={() => toggleProvider(provider.id)}
                  color={provider.id === 'aiml' ? 'green' : 'primary'}
                />
              </div>

              {providerSettings[provider.id]?.enabled && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="mt-3"
                >
                  {provider.id === 'aiml' && (
                    <p className="text-xs text-dark-400 mb-2">
                      Models: {provider.models.join(', ')}
                    </p>
                  )}
                  <label className="block text-sm font-medium mb-2">{provider.field.label}</label>
                  <div className="relative">
                    <input
                      type={showKeys[provider.id] ? 'text' : 'password'}
                      value={providerSettings[provider.id]?.key || ''}
                      onChange={(e) =>
                        setProviderSettings({
                          ...providerSettings,
                          [provider.id]: {
                            ...providerSettings[provider.id],
                            key: e.target.value,
                          },
                        })
                      }
                      placeholder={provider.field.placeholder}
                      className="input pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowKeys({ ...showKeys, [provider.id]: !showKeys[provider.id] })}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-dark-200"
                    >
                      {showKeys[provider.id] ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </motion.div>
              )}
            </div>
          ))}
        </div>

        {/* Save Status */}
        {saveMessage && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`mt-4 text-sm ${
              saveMessage.toLowerCase().includes('error') ||
              saveMessage.toLowerCase().includes('failed') ||
              saveMessage.toLowerCase().includes('cannot') ||
              saveMessage.toLowerCase().includes('unavailable')
                ? 'text-red-400'
                : 'text-neon-green'
            }`}
          >
            {saveMessage}
          </motion.div>
        )}

        <div className="mt-6">
          <button
            onClick={onSave}
            disabled={saving}
            className="btn-primary flex items-center gap-2"
          >
            {saving ? <Loader2 size={18} className="animate-spin" /> : <Check size={18} />}
            Save AI Settings
          </button>
        </div>
      </div>
    </motion.div>
  )
}

// Risk Settings Component
function RiskSettings({
  onSave,
  saving,
  saveMessage,
}: {
  onSave: (data: {
    maxPositions: number
    maxDailyTrades: number
    maxDailyLossPercent: number
    riskPerTrade: number
    defaultLeverage: number
    enableTrading: boolean
  }) => void
  saving: boolean
  saveMessage?: string
}) {
  const [settings, setSettings] = useState({
    maxPositions: 5,
    maxDailyTrades: 50,
    maxDailyLossPercent: 5,
    riskPerTrade: 1,
    defaultLeverage: 10,
    enableTrading: false,
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="card p-6"
    >
      <h2 className="text-xl font-semibold mb-6">Risk Management</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium mb-2">Max Open Positions</label>
          <input
            type="number"
            value={settings.maxPositions}
            onChange={(e) => setSettings({ ...settings, maxPositions: parseInt(e.target.value) || 0 })}
            className="input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Max Daily Trades</label>
          <input
            type="number"
            value={settings.maxDailyTrades}
            onChange={(e) => setSettings({ ...settings, maxDailyTrades: parseInt(e.target.value) || 0 })}
            className="input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Max Daily Loss (%)</label>
          <input
            type="number"
            value={settings.maxDailyLossPercent}
            onChange={(e) => setSettings({ ...settings, maxDailyLossPercent: parseFloat(e.target.value) || 0 })}
            className="input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Risk Per Trade (%)</label>
          <input
            type="number"
            value={settings.riskPerTrade}
            onChange={(e) => setSettings({ ...settings, riskPerTrade: parseFloat(e.target.value) || 0 })}
            className="input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-2">Default Leverage</label>
          <input
            type="number"
            value={settings.defaultLeverage}
            onChange={(e) => setSettings({ ...settings, defaultLeverage: parseInt(e.target.value) || 1 })}
            className="input"
          />
        </div>
        <div className="flex items-center gap-3 self-end">
          <Toggle
            enabled={settings.enableTrading}
            onChange={() => setSettings({ ...settings, enableTrading: !settings.enableTrading })}
            color="green"
          />
          <label className="text-sm font-medium">Enable Live Trading</label>
        </div>
      </div>

      {/* Save Status */}
      {saveMessage && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`mt-4 text-sm ${
            saveMessage.toLowerCase().includes('error') ||
            saveMessage.toLowerCase().includes('failed') ||
            saveMessage.toLowerCase().includes('cannot') ||
            saveMessage.toLowerCase().includes('unavailable')
              ? 'text-red-400'
              : 'text-neon-green'
          }`}
        >
          {saveMessage}
        </motion.div>
      )}

      <div className="mt-6">
        <button onClick={() => onSave(settings)} disabled={saving} className="btn-primary flex items-center gap-2">
          {saving ? <Loader2 size={18} className="animate-spin" /> : <Check size={18} />}
          Save Risk Settings
        </button>
      </div>
    </motion.div>
  )
}

// Notification Settings Component
function NotificationSettings({
  onSave,
  saving,
  saveMessage,
}: {
  onSave: (data: {
    telegramEnabled: boolean
    telegramBotToken: string
    telegramChatId: string
    discordEnabled: boolean
    discordWebhook: string
  }) => void
  saving: boolean
  saveMessage?: string
}) {
  const [settings, setSettings] = useState({
    telegramEnabled: false,
    telegramBotToken: '',
    telegramChatId: '',
    discordEnabled: false,
    discordWebhook: '',
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Telegram */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">TG</span>
            <div>
              <h3 className="font-semibold">Telegram</h3>
              <p className="text-sm text-dark-400">Get notifications via Telegram bot</p>
            </div>
          </div>
          <Toggle
            enabled={settings.telegramEnabled}
            onChange={() => setSettings({ ...settings, telegramEnabled: !settings.telegramEnabled })}
          />
        </div>
        {settings.telegramEnabled && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="space-y-4"
          >
            <div>
              <label className="block text-sm font-medium mb-2">Bot Token</label>
              <input
                type="password"
                value={settings.telegramBotToken}
                onChange={(e) => setSettings({ ...settings, telegramBotToken: e.target.value })}
                placeholder="123456789:ABC..."
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Chat ID</label>
              <input
                type="text"
                value={settings.telegramChatId}
                onChange={(e) => setSettings({ ...settings, telegramChatId: e.target.value })}
                placeholder="Your chat ID"
                className="input"
              />
            </div>
          </motion.div>
        )}
      </div>

      {/* Discord */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <span className="text-2xl">DS</span>
            <div>
              <h3 className="font-semibold">Discord</h3>
              <p className="text-sm text-dark-400">Get notifications via Discord webhook</p>
            </div>
          </div>
          <Toggle
            enabled={settings.discordEnabled}
            onChange={() => setSettings({ ...settings, discordEnabled: !settings.discordEnabled })}
          />
        </div>
        {settings.discordEnabled && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}>
            <label className="block text-sm font-medium mb-2">Webhook URL</label>
            <input
              type="text"
              value={settings.discordWebhook}
              onChange={(e) => setSettings({ ...settings, discordWebhook: e.target.value })}
              placeholder="https://discord.com/api/webhooks/..."
              className="input"
            />
          </motion.div>
        )}
      </div>

      {/* Save Status */}
      {saveMessage && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className={`text-sm ${
            saveMessage.toLowerCase().includes('error') ||
            saveMessage.toLowerCase().includes('failed') ||
            saveMessage.toLowerCase().includes('cannot') ||
            saveMessage.toLowerCase().includes('unavailable')
              ? 'text-red-400'
              : 'text-neon-green'
          }`}
        >
          {saveMessage}
        </motion.div>
      )}

      <button onClick={() => onSave(settings)} disabled={saving} className="btn-primary flex items-center gap-2">
        {saving ? <Loader2 size={18} className="animate-spin" /> : <Check size={18} />}
        Save Notification Settings
      </button>
    </motion.div>
  )
}

// Broker Accounts Settings Component (Multi-Broker Support)
function BrokerAccountsSettings() {
  const { user } = useAuth()
  const [accounts, setAccounts] = useState<BrokerAccountData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusBanner, setStatusBanner] = useState<{
    type: 'success' | 'error' | 'info'
    message: string
  } | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingAccount, setEditingAccount] = useState<BrokerAccountData | null>(null)
  const [actionLoading, setActionLoading] = useState<Record<number, string>>({})

  // Form state
  const [formData, setFormData] = useState<BrokerAccountCreate>(createDefaultBrokerFormData())
  const [platformCredentials, setPlatformCredentials] = useState<Record<string, string>>({})
  const [secretVisibility, setSecretVisibility] = useState<Record<string, boolean>>({})
  const [catalogQuery, setCatalogQuery] = useState('')
  const [selectedCatalogBrokerId, setSelectedCatalogBrokerId] = useState(BROKER_DIRECTORY[0]?.id || '')
  const [selectedPlatformId, setSelectedPlatformId] = useState(BROKER_DIRECTORY[0]?.platforms[0]?.id || '')
  const catalogRailRef = useRef<HTMLDivElement | null>(null)

  const filteredBrokerDirectory = useMemo(() => {
    const query = catalogQuery.trim().toLowerCase()
    if (!query) return BROKER_DIRECTORY
    return BROKER_DIRECTORY.filter((entry) => {
      const inName = entry.name.toLowerCase().includes(query)
      const inKind = entry.kind.toLowerCase().includes(query)
      const inPlatform = entry.platforms.some((platform) =>
        `${platform.label} ${platform.id}`.toLowerCase().includes(query),
      )
      return inName || inKind || inPlatform
    })
  }, [catalogQuery])

  const selectedCatalogBroker = useMemo(
    () => BROKER_DIRECTORY.find((entry) => entry.id === selectedCatalogBrokerId) || BROKER_DIRECTORY[0],
    [selectedCatalogBrokerId],
  )
  const selectedPlatform = useMemo(
    () => selectedCatalogBroker?.platforms.find((platform) => platform.id === selectedPlatformId) || selectedCatalogBroker?.platforms[0] || null,
    [selectedCatalogBroker, selectedPlatformId],
  )
  const isMetaTraderPlatformSelected = selectedPlatform?.id === 'mt4' || selectedPlatform?.id === 'mt5'
  const mtServerPresets = useMemo(
    () => getMetaTraderServerPresets(selectedCatalogBroker?.id, selectedPlatform?.id),
    [selectedCatalogBroker?.id, selectedPlatform?.id],
  )
  const mtServerPresetValues = useMemo(
    () => new Set(mtServerPresets.map((preset) => preset.value.toLowerCase())),
    [mtServerPresets],
  )

  useEffect(() => {
    if (!selectedCatalogBroker) return
    if (!selectedCatalogBroker.platforms.some((platform) => platform.id === selectedPlatformId)) {
      setSelectedPlatformId(selectedCatalogBroker.platforms[0]?.id || '')
    }
  }, [selectedCatalogBroker, selectedPlatformId])

  useEffect(() => {
    if (!selectedPlatform) return
    const validKeys = new Set(selectedPlatform.credentials.map((field) => field.key))
    setPlatformCredentials((previous) => {
      const next: Record<string, string> = {}
      for (const [key, value] of Object.entries(previous)) {
        if (validKeys.has(key)) {
          next[key] = value
        }
      }
      return next
    })
  }, [selectedPlatform])

  const maxSlots = user?.is_superuser ? Math.max(10, accounts.length) : Math.max(1, user?.license_broker_slots || 1)
  const takenSlots = new Set(accounts.map((a) => a.slot_index).filter((s): s is number => typeof s === 'number' && s > 0))
  const usedSlots = takenSlots.size
  const canAddMore = user?.is_superuser ? true : usedSlots < maxSlots

  const scrollCatalog = (direction: 'left' | 'right') => {
    if (!catalogRailRef.current) return
    catalogRailRef.current.scrollBy({
      left: direction === 'left' ? -340 : 340,
      behavior: 'smooth',
    })
  }

  const resetBrokerForm = () => {
    setFormData(createDefaultBrokerFormData())
    setPlatformCredentials({})
    setSecretVisibility({})
    setCatalogQuery('')
    setSelectedCatalogBrokerId(BROKER_DIRECTORY[0]?.id || '')
    setSelectedPlatformId(BROKER_DIRECTORY[0]?.platforms[0]?.id || '')
  }

  const platformIdFromBrokerType = (brokerType: string) => {
    if (brokerType === 'oanda') return 'oanda_api'
    if (brokerType === 'ig') return 'ig_api'
    if (brokerType === 'alpaca') return 'alpaca_api'
    if (brokerType === 'interactive_brokers') return 'ib_api'
    if (brokerType === 'ctrader') return 'ctrader'
    if (brokerType === 'dxtrade') return 'dxtrade'
    if (brokerType === 'matchtrader') return 'matchtrader'
    if (brokerType === 'mt4') return 'mt4'
    if (brokerType === 'mt5') return 'mt5'
    return null
  }

  const buildAccountPayload = () => {
    setError(null)
    if (!selectedCatalogBroker || !selectedPlatform) {
      setError('Select a broker and a platform first.')
      return null
    }

    const normalizedCredentials = Object.fromEntries(
      Object.entries(platformCredentials)
        .map(([key, value]) => [key, (value || '').trim()])
        .filter(([, value]) => value.length > 0),
    )

    const isMetaTraderPlatform = selectedPlatform.id === 'mt4' || selectedPlatform.id === 'mt5'
    const hasLegacyMetaApiId = Boolean((editingAccount?.metaapi_account_id || '').trim())
    const hasProvidedMetaApiId = Boolean((normalizedCredentials.metaapi_account_id || '').trim())
    const hasAnyMetaApiId = hasLegacyMetaApiId || hasProvidedMetaApiId
    const mtLoginCredentialKeys = ['account_number', 'account_password', 'server_name']
    const hasAnyMtLoginCredential = mtLoginCredentialKeys.some((key) => Boolean(normalizedCredentials[key]))
    const hasAllRequiredMtCredentials = mtLoginCredentialKeys.every((key) => Boolean(normalizedCredentials[key]))

    const missingFields = selectedPlatform.credentials.filter((field) => {
      if (field.required === false) return false
      if (normalizedCredentials[field.key]) return false
      if (
        isMetaTraderPlatform &&
        hasAnyMetaApiId &&
        mtLoginCredentialKeys.includes(field.key)
      ) {
        return false
      }
      return true
    })

    if (isMetaTraderPlatform && hasAnyMtLoginCredential && !hasAllRequiredMtCredentials) {
      setError(
        hasAnyMetaApiId
          ? 'Complete all MT login fields (Account Number, Password, Server Name) or clear them and use only MetaApi Account ID.'
          : selectedPlatform.id === 'mt4'
            ? 'For MT4 complete all fields: Account Number, Password, Server Name.'
            : 'For MT5 complete all fields: Account Number, Password, Server Name.',
      )
      return null
    }

    if (missingFields.length > 0) {
      setError(`Missing required fields: ${missingFields.map((field) => field.label).join(', ')}`)
      return null
    }

    const generatedName = `${selectedCatalogBroker?.name || 'Broker'} ${selectedPlatform?.label || ''}`.trim()

    return {
      ...formData,
      broker_type: getBrokerTypeByPlatform(selectedPlatform.id),
      broker_catalog_id: selectedCatalogBroker.id,
      platform_id: selectedPlatform.id,
      name: (formData.name || '').trim() || generatedName,
      metaapi_account_id: undefined,
      metaapi_token: undefined,
      credentials: normalizedCredentials,
    } as BrokerAccountCreate
  }

  // Load accounts
  useEffect(() => {
    loadAccounts()
  }, [])

  const loadAccounts = async () => {
    try {
      setIsLoading(true)
      const data = await brokerAccountsApi.list()
      setAccounts(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load accounts')
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async () => {
    try {
      const payload = buildAccountPayload()
      if (!payload) return
      setActionLoading({ ...actionLoading, 0: 'creating' })
      await brokerAccountsApi.create(payload)
      setShowCreateForm(false)
      setStatusBanner({
        type: 'success',
        message: `Broker workspace "${payload.name}" created successfully.`,
      })
      resetBrokerForm()
      await loadAccounts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create account')
    } finally {
      setActionLoading({})
    }
  }

  const handleUpdate = async () => {
    if (!editingAccount) return
    try {
      const payload = buildAccountPayload()
      if (!payload) return
      setActionLoading({ ...actionLoading, [editingAccount.id]: 'updating' })
      await brokerAccountsApi.update(editingAccount.id, payload)
      setStatusBanner({
        type: 'success',
        message: `Broker workspace "${payload.name}" updated successfully.`,
      })
      setEditingAccount(null)
      setShowCreateForm(false)
      resetBrokerForm()
      await loadAccounts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update account')
    } finally {
      setActionLoading({})
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this broker account?')) return
    try {
      setActionLoading({ ...actionLoading, [id]: 'deleting' })
      const result = await brokerAccountsApi.delete(id)
      setStatusBanner({
        type: 'success',
        message: result.message || 'Broker account deleted.',
      })
      await loadAccounts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete account')
    } finally {
      setActionLoading({})
    }
  }

  const handleTestConnection = async (id: number) => {
    try {
      setActionLoading({ ...actionLoading, [id]: 'testing' })
      const result = await brokerAccountsApi.testConnection(id)
      setStatusBanner({
        type: 'success',
        message: `${result.message}${result.account_name ? ` (${result.account_name})` : ''}`,
      })
      await loadAccounts()
    } catch (err) {
      setStatusBanner({
        type: 'error',
        message: err instanceof Error ? err.message : 'Connection test failed',
      })
    } finally {
      setActionLoading({})
    }
  }

  const handleToggle = async (id: number) => {
    try {
      setActionLoading({ ...actionLoading, [id]: 'toggling' })
      await brokerAccountsApi.toggle(id)
      await loadAccounts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to toggle account')
    } finally {
      setActionLoading({})
    }
  }

  const handleStartBot = async (id: number) => {
    try {
      setActionLoading({ ...actionLoading, [id]: 'starting' })
      const result = await brokerAccountsApi.startBot(id)
      setStatusBanner({
        type: 'success',
        message: result.message || 'Bot started.',
      })
      await loadAccounts()
    } catch (err) {
      setStatusBanner({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to start bot',
      })
    } finally {
      setActionLoading({})
    }
  }

  const handleStopBot = async (id: number) => {
    try {
      setActionLoading({ ...actionLoading, [id]: 'stopping' })
      const result = await brokerAccountsApi.stopBot(id)
      setStatusBanner({
        type: 'info',
        message: result.message || 'Bot stopped.',
      })
      await loadAccounts()
    } catch (err) {
      setStatusBanner({
        type: 'error',
        message: err instanceof Error ? err.message : 'Failed to stop bot',
      })
    } finally {
      setActionLoading({})
    }
  }

  const openEditForm = (account: BrokerAccountData) => {
    const brokerByCatalogId = BROKER_DIRECTORY.find((entry) => entry.id === account.broker_catalog_id) || null
    const inferredBroker = brokerByCatalogId || inferBrokerFromAccountName(account.name)
    const inferredPlatformId = inferPlatformFromAccountName(account.name, inferredBroker)
    const platformFromBrokerType = platformIdFromBrokerType(account.broker_type)
    const resolvedPlatformId =
      account.platform_id ||
      inferredPlatformId ||
      platformFromBrokerType ||
      inferredBroker?.platforms[0]?.id ||
      BROKER_DIRECTORY[0]?.platforms[0]?.id ||
      ''
    const resolvedBrokerId =
      inferredBroker?.id ||
      BROKER_DIRECTORY.find((entry) => entry.platforms.some((platform) => platform.id === resolvedPlatformId))?.id ||
      BROKER_DIRECTORY[0]?.id ||
      ''

    setEditingAccount(account)
    setFormData({
      name: account.name,
      broker_type: account.broker_type,
      broker_catalog_id: account.broker_catalog_id,
      platform_id: account.platform_id,
      slot_index: account.slot_index,
      is_enabled: account.is_enabled,
      symbols: account.symbols,
      risk_per_trade_percent: account.risk_per_trade_percent,
      max_open_positions: account.max_open_positions,
      max_daily_trades: account.max_daily_trades,
      max_daily_loss_percent: account.max_daily_loss_percent,
      analysis_mode: account.analysis_mode,
      analysis_interval_seconds: account.analysis_interval_seconds,
      min_confidence: account.min_confidence,
      min_models_agree: account.min_models_agree,
      enabled_models: account.enabled_models,
      trading_start_hour: account.trading_start_hour,
      trading_end_hour: account.trading_end_hour,
      trade_on_weekends: account.trade_on_weekends,
    })
    setPlatformCredentials(account.credentials || {})
    setSecretVisibility({})
    setSelectedCatalogBrokerId(resolvedBrokerId)
    setSelectedPlatformId(resolvedPlatformId)
    setShowCreateForm(false)
  }

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6 flex items-center justify-center"
      >
        <Loader2 className="animate-spin mr-2" /> Loading broker accounts...
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold">Broker Accounts</h2>
            <p className="text-sm text-dark-400">Manage multiple broker connections for parallel trading</p>
            {!user?.is_superuser && (
              <p className="text-xs text-dark-500 mt-1">
                License slots used: <span className="text-dark-200 font-medium">{usedSlots}</span> / <span className="text-dark-200 font-medium">{maxSlots}</span>
              </p>
            )}
          </div>
          <button
            onClick={() => {
              if (!canAddMore) {
                setError(`All ${maxSlots} license slots are occupied. Remove a broker or upgrade the license.`)
                return
              }
              setShowCreateForm(true)
              setEditingAccount(null)
              setStatusBanner(null)
              resetBrokerForm()
            }}
            disabled={!canAddMore}
            className="btn-primary flex items-center gap-2"
          >
            <Plus size={18} /> Add Broker
          </button>
        </div>

        {error && (
          <div className="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 mb-4 flex items-center gap-2">
            <AlertCircle size={18} /> {error}
          </div>
        )}

        {statusBanner && (
          <div
            className={`p-3 rounded-lg mb-4 flex items-center gap-2 border ${
              statusBanner.type === 'success'
                ? 'bg-neon-green/15 border-neon-green/40 text-neon-green'
                : statusBanner.type === 'error'
                ? 'bg-red-500/15 border-red-500/40 text-red-300'
                : 'bg-primary-500/15 border-primary-500/40 text-primary-300'
            }`}
          >
            {statusBanner.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle size={18} />}
            <span>{statusBanner.message}</span>
          </div>
        )}

        {/* Accounts List */}
        {accounts.length === 0 ? (
          <div className="text-center py-8 text-dark-400">
            <Users size={48} className="mx-auto mb-4 opacity-50" />
            <p>No broker accounts configured</p>
            <p className="text-sm">Add your first broker to start trading</p>
          </div>
        ) : (
          <div className="space-y-4">
            {accounts.map((account) => {
              const brokerFromCatalog = BROKER_DIRECTORY.find((entry) => entry.id === account.broker_catalog_id) || null
              const inferredBroker = brokerFromCatalog || inferBrokerFromAccountName(account.name)
              const inferredPlatformId = account.platform_id || inferPlatformFromAccountName(account.name, inferredBroker)
              const inferredPlatform = inferredBroker?.platforms.find((platform) => platform.id === inferredPlatformId) || null

              return (
              <div
                key={account.id}
                className={`p-4 rounded-xl border transition-all ${
                  account.is_enabled
                    ? account.is_connected
                      ? 'border-neon-green/50 bg-neon-green/5'
                      : 'border-primary-500/50 bg-primary-500/5'
                    : 'border-dark-700 bg-dark-800/50 opacity-60'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <BrokerLogo
                      name={inferredBroker?.name || account.name}
                      domain={inferredBroker?.logoDomain}
                      logoUrl={inferredBroker?.logoUrl}
                      className="h-10 w-10"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{account.name}</span>
                        {inferredBroker && (
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            inferredBroker.kind === 'prop'
                              ? 'bg-purple-500/20 text-purple-300'
                              : 'bg-sky-500/20 text-sky-300'
                          }`}>
                            {inferredBroker.kind === 'prop' ? 'Prop Firm' : 'Broker'}
                          </span>
                        )}
                        {account.slot_index && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-dark-700 text-dark-300">
                            Slot {account.slot_index}
                          </span>
                        )}
                        {account.is_connected && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-neon-green/20 text-neon-green">
                            Connected
                          </span>
                        )}
                        {!account.is_enabled && (
                          <span className="text-xs px-2 py-0.5 rounded-full bg-dark-600 text-dark-400">
                            Disabled
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-dark-400">
                        {(inferredBroker?.name || 'Custom Workspace')}{inferredPlatform ? ` (${inferredPlatform.label})` : ''} | {account.symbols.join(', ')} | {account.analysis_mode} mode | {account.analysis_interval_seconds / 60}min interval
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    {/* Bot Control */}
                    <button
                      onClick={() => handleStartBot(account.id)}
                      disabled={!!actionLoading[account.id] || !account.is_enabled}
                      className="p-2 rounded-lg bg-neon-green/20 text-neon-green hover:bg-neon-green/30 disabled:opacity-50"
                      title="Start Bot"
                    >
                      {actionLoading[account.id] === 'starting' ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Play size={16} />
                      )}
                    </button>
                    <button
                      onClick={() => handleStopBot(account.id)}
                      disabled={!!actionLoading[account.id]}
                      className="p-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50"
                      title="Stop Bot"
                    >
                      {actionLoading[account.id] === 'stopping' ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Square size={16} />
                      )}
                    </button>

                    {/* Test Connection */}
                    <button
                      onClick={() => handleTestConnection(account.id)}
                      disabled={!!actionLoading[account.id]}
                      className="p-2 rounded-lg bg-dark-700 hover:bg-dark-600 disabled:opacity-50"
                      title="Test Connection"
                    >
                      {actionLoading[account.id] === 'testing' ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <TestTube size={16} />
                      )}
                    </button>

                    {/* Edit */}
                    <button
                      onClick={() => openEditForm(account)}
                      disabled={!!actionLoading[account.id]}
                      className="p-2 rounded-lg bg-dark-700 hover:bg-dark-600 disabled:opacity-50"
                      title="Edit"
                    >
                      <Edit3 size={16} />
                    </button>

                    {/* Toggle */}
                    <button
                      onClick={() => handleToggle(account.id)}
                      disabled={!!actionLoading[account.id]}
                      className={`p-2 rounded-lg ${
                        account.is_enabled
                          ? 'bg-primary-500/20 text-primary-400'
                          : 'bg-dark-700 text-dark-400'
                      } hover:opacity-80 disabled:opacity-50`}
                      title={account.is_enabled ? 'Disable' : 'Enable'}
                    >
                      {actionLoading[account.id] === 'toggling' ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <RefreshCw size={16} />
                      )}
                    </button>

                    {/* Delete */}
                    <button
                      onClick={() => handleDelete(account.id)}
                      disabled={!!actionLoading[account.id]}
                      className="p-2 rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 disabled:opacity-50"
                      title="Delete"
                    >
                      {actionLoading[account.id] === 'deleting' ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Trash2 size={16} />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            )})}
          </div>
        )}
      </div>

      {/* Create/Edit Form */}
      <AnimatePresence>
        {(showCreateForm || editingAccount) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="card p-6"
          >
            <h3 className="text-lg font-semibold mb-4">
              {editingAccount ? `Edit: ${editingAccount.name}` : 'Add New Workspace'}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2 p-4 rounded-xl border border-dark-700 bg-dark-900/40">
                <div className="flex items-center justify-between gap-3 mb-3">
                  <div>
                    <p className="text-sm font-medium text-dark-100">Broker Catalog</p>
                    <p className="text-xs text-dark-400">Select broker or prop firm, then choose platform and credentials.</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => scrollCatalog('left')}
                      className="p-2 rounded-lg border border-dark-700 bg-dark-950/70 hover:border-dark-500"
                      aria-label="Scroll brokers left"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <button
                      type="button"
                      onClick={() => scrollCatalog('right')}
                      className="p-2 rounded-lg border border-dark-700 bg-dark-950/70 hover:border-dark-500"
                      aria-label="Scroll brokers right"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>

                <div className="mb-3">
                  <input
                    type="text"
                    value={catalogQuery}
                    onChange={(e) => setCatalogQuery(e.target.value)}
                    placeholder="Search broker or prop firm (e.g. FTMO, RoboForex, Match-Trader...)"
                    className="input"
                  />
                </div>

                <div ref={catalogRailRef} className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                  {filteredBrokerDirectory.map((entry) => (
                    <button
                      type="button"
                      key={entry.id}
                      onClick={() => {
                        setSelectedCatalogBrokerId(entry.id)
                        setSelectedPlatformId(entry.platforms[0]?.id || '')
                        setPlatformCredentials({})
                        setSecretVisibility({})
                        setFormData((previous) => {
                          if (previous.name) return previous
                          return {
                            ...previous,
                            name: `${entry.name} ${entry.platforms[0]?.label || ''}`.trim(),
                          }
                        })
                      }}
                      className={`min-w-[220px] p-3 rounded-xl border text-left transition-all ${
                        selectedCatalogBrokerId === entry.id
                          ? 'border-primary-500 bg-primary-500/10'
                          : 'border-dark-700 bg-dark-900/70 hover:border-dark-500'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <BrokerLogo name={entry.name} domain={entry.logoDomain} logoUrl={entry.logoUrl} />
                        <div>
                          <span className="text-sm font-semibold text-dark-100">{entry.name}</span>
                          <p className={`text-[10px] ${
                            entry.kind === 'prop' ? 'text-purple-300' : 'text-sky-300'
                          }`}>
                            {entry.kind === 'prop' ? 'Prop Firm' : 'Broker'}
                          </p>
                        </div>
                      </div>
                      <p className="text-[11px] text-dark-500">
                        {entry.platforms.length} platform options
                      </p>
                    </button>
                  ))}
                </div>
                {filteredBrokerDirectory.length === 0 && (
                  <p className="text-xs text-dark-500 mt-3">No brokers/props found for this search.</p>
                )}
              </div>

              <div className="md:col-span-2">
                <label className="block text-sm font-medium mb-2">Platform</label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {(selectedCatalogBroker?.platforms || []).map((platform) => (
                    <button
                      type="button"
                      key={platform.id}
                      onClick={() => setSelectedPlatformId(platform.id)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        selectedPlatformId === platform.id
                          ? 'border-primary-500 bg-primary-500/10'
                          : 'border-dark-700 bg-dark-900/70 hover:border-dark-500'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <BrokerLogo
                          name={platform.label}
                          domain={platform.logoDomain}
                          logoUrl={platform.logoUrl}
                          className="h-8 w-8"
                        />
                        <span className="text-sm font-medium text-dark-100">{platform.label}</span>
                      </div>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-dark-500 mt-1">
                  Current selection: {selectedCatalogBroker?.name || 'Broker'} {selectedPlatform ? `(${selectedPlatform.label})` : ''}
                </p>
              </div>

              {/* Name */}
              <div>
                <label className="block text-sm font-medium mb-2">Account Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Ultima Markets Demo"
                  className="input"
                />
              </div>

              <div className="md:col-span-2 p-3 rounded-xl border border-primary-500/30 bg-primary-500/5">
                <p className="text-sm font-medium text-primary-300">
                  Metrics available for {selectedPlatform?.label || 'this platform'}
                </p>
                <div className="flex flex-wrap gap-2 mt-2">
                  {(selectedPlatform?.metrics || []).map((metric) => (
                    <span
                      key={metric}
                      className="px-2 py-1 rounded-full text-xs bg-dark-800 border border-dark-600 text-dark-200"
                    >
                      {metric}
                    </span>
                  ))}
                </div>
              </div>

              {(selectedPlatform?.credentials || []).map((field) => {
                const fieldValue = platformCredentials[field.key] || ''
                const isPassword = field.type === 'password'
                const isNumber = field.type === 'number'
                const isSelect = field.type === 'select'
                const isVisible = secretVisibility[field.key] || false
                const isMtServerField = isMetaTraderPlatformSelected && field.key === 'server_name'
                const serverSelectValue = isMtServerField
                  ? (mtServerPresetValues.has(fieldValue.toLowerCase()) ? fieldValue : '__manual__')
                  : ''

                return (
                  <div key={field.key} className={field.fullWidth ? 'md:col-span-2' : ''}>
                    <label className="block text-sm font-medium mb-2">
                      {field.label}
                      {field.required !== false && <span className="text-red-400 ml-1">*</span>}
                    </label>

                    {isMtServerField ? (
                      <div className="space-y-2">
                        {mtServerPresets.length > 0 && (
                          <select
                            value={serverSelectValue}
                            onChange={(e) =>
                              setPlatformCredentials((previous) => {
                                const next = { ...previous }
                                const value = e.target.value
                                if (value === '__manual__') {
                                  return next
                                }
                                next[field.key] = value
                                return next
                              })
                            }
                            className="input"
                          >
                            {mtServerPresets.map((preset) => (
                              <option key={preset.value} value={preset.value}>
                                {preset.label}
                              </option>
                            ))}
                            <option value="__manual__">Custom server (manual input)</option>
                          </select>
                        )}

                        <input
                          type="text"
                          value={fieldValue}
                          onChange={(e) =>
                            setPlatformCredentials((previous) => ({
                              ...previous,
                              [field.key]: e.target.value,
                            }))
                          }
                          placeholder={field.placeholder}
                          className="input"
                        />
                        <p className="text-xs text-dark-500">
                          Official/common presets are preloaded where available. Always verify exact server name from your MT terminal.
                        </p>
                      </div>
                    ) : isSelect ? (
                      <select
                        value={fieldValue}
                        onChange={(e) =>
                          setPlatformCredentials((previous) => ({
                            ...previous,
                            [field.key]: e.target.value,
                          }))
                        }
                        className="input"
                      >
                        <option value="">{field.placeholder || `Select ${field.label}`}</option>
                        {(field.options || []).map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="relative">
                        <input
                          type={isPassword ? (isVisible ? 'text' : 'password') : isNumber ? 'number' : 'text'}
                          value={fieldValue}
                          onChange={(e) =>
                            setPlatformCredentials((previous) => ({
                              ...previous,
                              [field.key]: e.target.value,
                            }))
                          }
                          placeholder={field.placeholder}
                          className={isPassword ? 'input pr-10' : 'input'}
                        />
                        {isPassword && (
                          <button
                            type="button"
                            onClick={() =>
                              setSecretVisibility((previous) => ({
                                ...previous,
                                [field.key]: !isVisible,
                              }))
                            }
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-dark-200"
                          >
                            {isVisible ? <EyeOff size={18} /> : <Eye size={18} />}
                          </button>
                        )}
                      </div>
                    )}
                    {!isMtServerField && <p className="text-xs text-dark-500 mt-1">{field.help}</p>}
                  </div>
                )
              })}

              {/* Symbols */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium mb-2">Symbols (comma-separated)</label>
                <input
                  type="text"
                  value={formData.symbols?.join(', ')}
                  onChange={(e) => setFormData({
                    ...formData,
                    symbols: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  })}
                  placeholder="EUR/USD, XAU/USD, GBP/USD"
                  className="input"
                />
              </div>

              {/* Analysis Mode */}
              <div>
                <label className="block text-sm font-medium mb-2">Analysis Mode</label>
                <select
                  value={formData.analysis_mode}
                  onChange={(e) => setFormData({ ...formData, analysis_mode: e.target.value })}
                  className="input"
                >
                  <option value="quick">Quick (1 TF, fast)</option>
                  <option value="standard">Standard (2 TF)</option>
                  <option value="premium">Premium (3 TF)</option>
                  <option value="ultra">Ultra (4 TF)</option>
                </select>
              </div>

              {/* Analysis Interval */}
              <div>
                <label className="block text-sm font-medium mb-2">Analysis Interval</label>
                <select
                  value={formData.analysis_interval_seconds}
                  onChange={(e) => setFormData({ ...formData, analysis_interval_seconds: parseInt(e.target.value) })}
                  className="input"
                >
                  <option value={300}>5 minutes</option>
                  <option value={600}>10 minutes</option>
                  <option value={900}>15 minutes</option>
                  <option value={1800}>30 minutes</option>
                  <option value={3600}>1 hour</option>
                  <option value={7200}>2 hours</option>
                </select>
              </div>

              {/* Risk per Trade */}
              <div>
                <label className="block text-sm font-medium mb-2">Risk per Trade (%)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  max="10"
                  value={formData.risk_per_trade_percent}
                  onChange={(e) => setFormData({ ...formData, risk_per_trade_percent: parseFloat(e.target.value) || 1.0 })}
                  className="input"
                />
              </div>

              {/* Max Positions */}
              <div>
                <label className="block text-sm font-medium mb-2">Max Open Positions</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={formData.max_open_positions}
                  onChange={(e) => setFormData({ ...formData, max_open_positions: parseInt(e.target.value) || 3 })}
                  className="input"
                />
              </div>

              {/* Min Confidence */}
              <div>
                <label className="block text-sm font-medium mb-2">Min Confidence (%)</label>
                <input
                  type="number"
                  min="50"
                  max="100"
                  value={formData.min_confidence}
                  onChange={(e) => setFormData({ ...formData, min_confidence: parseFloat(e.target.value) || 75.0 })}
                  className="input"
                />
              </div>

              {/* Min Models Agree */}
              <div>
                <label className="block text-sm font-medium mb-2">Min Models Agree</label>
                <input
                  type="number"
                  min="1"
                  max="8"
                  value={formData.min_models_agree}
                  onChange={(e) => setFormData({ ...formData, min_models_agree: parseInt(e.target.value) || 4 })}
                  className="input"
                />
              </div>

              {/* AI Models Selector */}
              <div className="col-span-2">
                <label className="block text-sm font-medium mb-3">Enabled AI Models</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { id: 'chatgpt', name: 'ChatGPT', color: 'bg-green-500' },
                    { id: 'gemini', name: 'Gemini', color: 'bg-blue-500' },
                    { id: 'grok', name: 'Grok', color: 'bg-red-500' },
                    { id: 'qwen', name: 'Qwen', color: 'bg-purple-500' },
                    { id: 'llama', name: 'Llama', color: 'bg-indigo-500' },
                    { id: 'ernie', name: 'ERNIE', color: 'bg-cyan-500' },
                    { id: 'kimi', name: 'Kimi K2.5', color: 'bg-orange-500' },
                    { id: 'mistral', name: 'Mistral', color: 'bg-amber-500' },
                  ].map((model) => {
                    const enabledModels = formData.enabled_models || []
                    const isEnabled = enabledModels.includes(model.id)
                    return (
                      <label
                        key={model.id}
                        className={`
                          flex items-center gap-2 p-3 rounded-lg border cursor-pointer transition-all
                          ${isEnabled
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50 bg-surface'
                          }
                        `}
                      >
                        <input
                          type="checkbox"
                          checked={isEnabled}
                          onChange={(e) => {
                            const newModels = e.target.checked
                              ? [...enabledModels, model.id]
                              : enabledModels.filter(m => m !== model.id)
                            setFormData({ ...formData, enabled_models: newModels })
                          }}
                          className="sr-only"
                        />
                        <div className={`w-3 h-3 rounded-full ${model.color}`} />
                        <span className={`text-sm ${isEnabled ? 'text-primary font-medium' : 'text-secondary'}`}>
                          {model.name}
                        </span>
                        {isEnabled && (
                          <Check size={14} className="ml-auto text-primary" />
                        )}
                      </label>
                    )
                  })}
                </div>
                <p className="text-xs text-secondary mt-2">
                  Select which AI models will analyze charts for this broker. More models = more comprehensive analysis.
                </p>
              </div>

              {/* Trading Hours */}
              <div>
                <label className="block text-sm font-medium mb-2">Trading Start Hour (UTC)</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={formData.trading_start_hour}
                  onChange={(e) => setFormData({ ...formData, trading_start_hour: parseInt(e.target.value) || 7 })}
                  className="input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">Trading End Hour (UTC)</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  value={formData.trading_end_hour}
                  onChange={(e) => setFormData({ ...formData, trading_end_hour: parseInt(e.target.value) || 21 })}
                  className="input"
                />
              </div>
            </div>

            {/* Form Actions */}
            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowCreateForm(false)
                  setEditingAccount(null)
                  resetBrokerForm()
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={editingAccount ? handleUpdate : handleCreate}
                disabled={!!actionLoading[editingAccount?.id || 0]}
                className="btn-primary flex items-center gap-2"
              >
                {actionLoading[editingAccount?.id || 0] ? (
                  <Loader2 size={18} className="animate-spin" />
                ) : (
                  <Check size={18} />
                )}
                {editingAccount ? 'Update Workspace' : 'Create Workspace'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
