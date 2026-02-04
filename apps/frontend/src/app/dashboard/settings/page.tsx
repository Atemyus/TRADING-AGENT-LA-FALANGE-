'use client'

import { motion, AnimatePresence } from 'framer-motion'
import { useState, useEffect } from 'react'
import {
  Server,
  Brain,
  Shield,
  Bell,
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
import { settingsApi, brokerAccountsApi, type BrokerSettingsData, type BrokerAccountData, type BrokerAccountCreate } from '@/lib/api'

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

// Broker configurations
const BROKERS = [
  {
    id: 'oanda',
    name: 'OANDA',
    logo: '🏦',
    description: 'Forex & CFD trading via REST API',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'Your OANDA API key' },
      { key: 'account_id', label: 'Account ID', type: 'text', placeholder: '101-001-12345678-001' },
      { key: 'environment', label: 'Environment', type: 'select', options: ['practice', 'live'] },
    ],
  },
  {
    id: 'metatrader',
    name: 'MetaTrader 4/5',
    logo: '📊',
    description: 'MT4/MT5 via MetaApi.cloud',
    fields: [
      { key: 'meta_api_token', label: 'MetaApi Token', type: 'password', placeholder: 'Your MetaApi token' },
      { key: 'account_id', label: 'MT Account ID', type: 'text', placeholder: 'Your MetaApi account ID' },
      { key: 'platform', label: 'Platform', type: 'select', options: ['mt4', 'mt5'] },
    ],
    helpLink: 'https://metaapi.cloud',
  },
  {
    id: 'ig',
    name: 'IG Markets',
    logo: '🔴',
    description: 'Global CFD & Spread Betting',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'Your IG API key' },
      { key: 'username', label: 'Username', type: 'text', placeholder: 'Your IG username' },
      { key: 'password', label: 'Password', type: 'password', placeholder: 'Your IG password' },
      { key: 'account_id', label: 'Account ID', type: 'text', placeholder: 'Your account ID' },
      { key: 'environment', label: 'Environment', type: 'select', options: ['demo', 'live'] },
    ],
  },
  {
    id: 'interactive_brokers',
    name: 'Interactive Brokers',
    logo: '🟣',
    description: 'Stocks, Futures, Options & more',
    fields: [
      { key: 'host', label: 'TWS Host', type: 'text', placeholder: '127.0.0.1' },
      { key: 'port', label: 'TWS Port', type: 'text', placeholder: '7497 (paper) or 7496 (live)' },
      { key: 'client_id', label: 'Client ID', type: 'text', placeholder: '1' },
    ],
  },
  {
    id: 'alpaca',
    name: 'Alpaca',
    logo: '🦙',
    description: 'Commission-free US stocks',
    fields: [
      { key: 'api_key', label: 'API Key', type: 'password', placeholder: 'Your Alpaca API key' },
      { key: 'secret_key', label: 'Secret Key', type: 'password', placeholder: 'Your Alpaca secret key' },
      { key: 'paper', label: 'Paper Trading', type: 'select', options: ['true', 'false'] },
    ],
  },
]

// AI Provider configurations
const AI_PROVIDERS = [
  {
    id: 'aiml',
    name: 'AIML API',
    icon: '🚀',
    models: ['ChatGPT 5.2', 'Gemini 3 Pro', 'Grok 4.1 Fast', 'Qwen3 VL', 'Llama 4 Scout', 'ERNIE 4.5 VL'],
    field: { key: 'AIML_API_KEY', label: 'API Key', placeholder: 'Your AIML API key' },
    badge: '6 Models',
    description: 'Single API key for 6 AI models via api.aimlapi.com',
  },
  {
    id: 'nvidia',
    name: 'NVIDIA API',
    icon: '🟢',
    models: ['Kimi K2.5', 'Mistral Large 3'],
    field: { key: 'NVIDIA_API_KEY', label: 'API Key', placeholder: 'Your NVIDIA API key' },
    badge: '2 Models',
    description: 'Kimi K2.5 e Mistral Large 3 via integrate.api.nvidia.com',
  },
]

type SettingsSection = 'broker' | 'accounts' | 'ai' | 'risk' | 'notifications'

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingsSection>('broker')
  const [selectedBroker, setSelectedBroker] = useState<string>('metatrader')
  const [brokerCredentials, setBrokerCredentials] = useState<Record<string, string>>({})
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})
  const [testingConnection, setTestingConnection] = useState(false)
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'success' | 'error'>('idle')
  const [connectionMessage, setConnectionMessage] = useState<string>('')
  const [aiProviders, setAiProviders] = useState<Record<string, { enabled: boolean; key: string }>>({})
  const [saving, setSaving] = useState(false)
  const [saveMessage, setSaveMessage] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)

  // Load settings on mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const settings = await settingsApi.getAll()

        // Set broker type
        setSelectedBroker(settings.broker.broker_type || 'metatrader')

        // Map broker settings to credentials
        const creds: Record<string, string> = {}
        if (settings.broker.broker_type === 'metatrader') {
          creds.meta_api_token = settings.broker.metaapi_token || ''
          creds.account_id = settings.broker.metaapi_account_id || ''
          creds.platform = settings.broker.metaapi_platform || 'mt5'
        } else if (settings.broker.broker_type === 'oanda') {
          creds.api_key = settings.broker.oanda_api_key || ''
          creds.account_id = settings.broker.oanda_account_id || ''
          creds.environment = settings.broker.oanda_environment || 'practice'
        } else if (settings.broker.broker_type === 'ig') {
          creds.api_key = settings.broker.ig_api_key || ''
          creds.username = settings.broker.ig_username || ''
          creds.password = settings.broker.ig_password || ''
          creds.account_id = settings.broker.ig_account_id || ''
          creds.environment = settings.broker.ig_environment || 'demo'
        } else if (settings.broker.broker_type === 'alpaca') {
          creds.api_key = settings.broker.alpaca_api_key || ''
          creds.secret_key = settings.broker.alpaca_secret_key || ''
          creds.paper = settings.broker.alpaca_paper ? 'true' : 'false'
        }
        setBrokerCredentials(creds)

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
      } finally {
        setIsLoading(false)
      }
    }
    loadSettings()
  }, [])

  const handleTestConnection = async () => {
    setTestingConnection(true)
    setConnectionStatus('idle')
    setConnectionMessage('')

    try {
      // First save the current settings
      await handleSaveBroker()

      // Then test the connection
      const result = await settingsApi.testBroker()
      setConnectionStatus('success')
      setConnectionMessage(result.message + (result.account_name ? ` (${result.account_name})` : ''))
    } catch (error) {
      setConnectionStatus('error')
      setConnectionMessage(error instanceof Error ? error.message : 'Connection failed')
    } finally {
      setTestingConnection(false)
    }
  }

  const handleSaveBroker = async () => {
    setSaving(true)
    setSaveMessage('')

    try {
      // Build broker settings based on selected broker
      const brokerData: BrokerSettingsData = {
        broker_type: selectedBroker,
      }

      if (selectedBroker === 'metatrader') {
        brokerData.metaapi_token = brokerCredentials.meta_api_token
        brokerData.metaapi_account_id = brokerCredentials.account_id
        brokerData.metaapi_platform = brokerCredentials.platform || 'mt5'
      } else if (selectedBroker === 'oanda') {
        brokerData.oanda_api_key = brokerCredentials.api_key
        brokerData.oanda_account_id = brokerCredentials.account_id
        brokerData.oanda_environment = brokerCredentials.environment || 'practice'
      } else if (selectedBroker === 'ig') {
        brokerData.ig_api_key = brokerCredentials.api_key
        brokerData.ig_username = brokerCredentials.username
        brokerData.ig_password = brokerCredentials.password
        brokerData.ig_account_id = brokerCredentials.account_id
        brokerData.ig_environment = brokerCredentials.environment || 'demo'
      } else if (selectedBroker === 'alpaca') {
        brokerData.alpaca_api_key = brokerCredentials.api_key
        brokerData.alpaca_secret_key = brokerCredentials.secret_key
        brokerData.alpaca_paper = brokerCredentials.paper === 'true'
      }

      const result = await settingsApi.updateBroker(brokerData)
      setSaveMessage(result.message)
    } catch (error) {
      setSaveMessage(error instanceof Error ? error.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

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

  const handleSave = async () => {
    await handleSaveBroker()
  }

  const sections = [
    { id: 'broker', label: 'Broker', icon: Server },
    { id: 'accounts', label: 'Broker Accounts', icon: Users },
    { id: 'ai', label: 'AI Providers', icon: Brain },
    { id: 'risk', label: 'Risk Management', icon: Shield },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ] as const

  return (
    <div className="max-w-6xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-dark-400">Configure your trading platform</p>
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
            {activeSection === 'broker' && (
              <BrokerSettings
                key="broker"
                brokers={BROKERS}
                selectedBroker={selectedBroker}
                setSelectedBroker={setSelectedBroker}
                credentials={brokerCredentials}
                setCredentials={setBrokerCredentials}
                showPasswords={showPasswords}
                setShowPasswords={setShowPasswords}
                testingConnection={testingConnection}
                connectionStatus={connectionStatus}
                connectionMessage={connectionMessage}
                onTestConnection={handleTestConnection}
                onSave={handleSave}
                saving={saving}
                saveMessage={saveMessage}
              />
            )}

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

// Broker Settings Component
function BrokerSettings({
  brokers,
  selectedBroker,
  setSelectedBroker,
  credentials,
  setCredentials,
  showPasswords,
  setShowPasswords,
  testingConnection,
  connectionStatus,
  connectionMessage,
  onTestConnection,
  onSave,
  saving,
  saveMessage,
}: {
  brokers: typeof BROKERS
  selectedBroker: string
  setSelectedBroker: (id: string) => void
  credentials: Record<string, string>
  setCredentials: (creds: Record<string, string>) => void
  showPasswords: Record<string, boolean>
  setShowPasswords: (show: Record<string, boolean>) => void
  testingConnection: boolean
  connectionStatus: 'idle' | 'success' | 'error'
  connectionMessage: string
  onTestConnection: () => void
  onSave: () => void
  saving: boolean
  saveMessage: string
}) {
  const broker = brokers.find(b => b.id === selectedBroker)

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Broker Selection */}
      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-4">Select Broker</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {brokers.map((b) => (
            <button
              key={b.id}
              onClick={() => setSelectedBroker(b.id)}
              className={`p-4 rounded-xl border-2 transition-all text-left ${
                selectedBroker === b.id
                  ? 'border-primary-500 bg-primary-500/10'
                  : 'border-dark-700 hover:border-dark-600 bg-dark-800/50'
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{b.logo}</span>
                <span className="font-semibold">{b.name}</span>
                {selectedBroker === b.id && (
                  <Check size={16} className="ml-auto text-primary-500" />
                )}
              </div>
              <p className="text-sm text-dark-400">{b.description}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Broker Configuration */}
      {broker && (
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <span className="text-3xl">{broker.logo}</span>
              <div>
                <h2 className="text-xl font-semibold">{broker.name} Configuration</h2>
                <p className="text-sm text-dark-400">{broker.description}</p>
              </div>
            </div>
            {broker.helpLink && (
              <a
                href={broker.helpLink}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary-400 hover:text-primary-300 flex items-center gap-1"
              >
                <Info size={14} />
                Get API Key
              </a>
            )}
          </div>

          <div className="space-y-4">
            {broker.fields.map((field) => (
              <div key={field.key}>
                <label className="block text-sm font-medium mb-2">{field.label}</label>
                {field.type === 'select' ? (
                  <select
                    value={credentials[field.key] || field.options?.[0] || ''}
                    onChange={(e) => setCredentials({ ...credentials, [field.key]: e.target.value })}
                    className="input"
                  >
                    {field.options?.map((opt) => (
                      <option key={opt} value={opt}>{opt}</option>
                    ))}
                  </select>
                ) : (
                  <div className="relative">
                    <input
                      type={field.type === 'password' && !showPasswords[field.key] ? 'password' : 'text'}
                      value={credentials[field.key] || ''}
                      onChange={(e) => setCredentials({ ...credentials, [field.key]: e.target.value })}
                      placeholder={field.placeholder}
                      className="input pr-10"
                    />
                    {field.type === 'password' && (
                      <button
                        type="button"
                        onClick={() => setShowPasswords({ ...showPasswords, [field.key]: !showPasswords[field.key] })}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-dark-200"
                      >
                        {showPasswords[field.key] ? <EyeOff size={18} /> : <Eye size={18} />}
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Connection Status */}
          <AnimatePresence>
            {connectionStatus !== 'idle' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className={`mt-4 p-4 rounded-lg flex items-center gap-3 ${
                  connectionStatus === 'success'
                    ? 'bg-neon-green/20 text-neon-green'
                    : 'bg-neon-red/20 text-neon-red'
                }`}
              >
                {connectionStatus === 'success' ? (
                  <>
                    <CheckCircle size={20} />
                    <span>{connectionMessage || 'Connection successful! Broker is ready.'}</span>
                  </>
                ) : (
                  <>
                    <AlertCircle size={20} />
                    <span>{connectionMessage || 'Connection failed. Please check your credentials.'}</span>
                  </>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {/* Save Status */}
          {saveMessage && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={`mt-2 text-sm ${
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

          {/* Actions */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={onTestConnection}
              disabled={testingConnection}
              className="btn-secondary flex items-center gap-2"
            >
              {testingConnection ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <TestTube size={18} />
              )}
              Test Connection
            </button>
            <button
              onClick={onSave}
              disabled={saving}
              className="btn-primary flex items-center gap-2"
            >
              {saving ? <Loader2 size={18} className="animate-spin" /> : <Check size={18} />}
              Save Settings
            </button>
          </div>
        </div>
      )}
    </motion.div>
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
            <span className="text-2xl">📱</span>
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
            <span className="text-2xl">💬</span>
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
  const [accounts, setAccounts] = useState<BrokerAccountData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [editingAccount, setEditingAccount] = useState<BrokerAccountData | null>(null)
  const [actionLoading, setActionLoading] = useState<Record<number, string>>({})

  // Form state
  const [formData, setFormData] = useState<BrokerAccountCreate>({
    name: '',
    broker_type: 'metaapi',
    metaapi_account_id: '',
    metaapi_token: '',
    is_enabled: true,
    symbols: ['EUR/USD', 'XAU/USD'],
    risk_per_trade_percent: 1.0,
    max_open_positions: 3,
    analysis_mode: 'standard',
    analysis_interval_seconds: 300,
    min_confidence: 75.0,
    min_models_agree: 4,
    enabled_models: ['chatgpt', 'gemini', 'grok', 'qwen', 'llama', 'ernie', 'kimi', 'mistral'],
    trading_start_hour: 7,
    trading_end_hour: 21,
  })
  const [showToken, setShowToken] = useState(false)

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
      setActionLoading({ ...actionLoading, 0: 'creating' })
      await brokerAccountsApi.create(formData)
      setShowCreateForm(false)
      setFormData({
        name: '',
        broker_type: 'metaapi',
        metaapi_account_id: '',
        metaapi_token: '',
        is_enabled: true,
        symbols: ['EUR/USD', 'XAU/USD'],
        risk_per_trade_percent: 1.0,
        max_open_positions: 3,
        analysis_mode: 'standard',
        analysis_interval_seconds: 300,
        min_confidence: 75.0,
        min_models_agree: 4,
        enabled_models: ['chatgpt', 'gemini', 'grok', 'qwen', 'llama', 'ernie', 'kimi', 'mistral'],
        trading_start_hour: 7,
        trading_end_hour: 21,
      })
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
      setActionLoading({ ...actionLoading, [editingAccount.id]: 'updating' })
      await brokerAccountsApi.update(editingAccount.id, formData)
      setEditingAccount(null)
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
      await brokerAccountsApi.delete(id)
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
      alert(`${result.message}${result.account_name ? ` (${result.account_name})` : ''}`)
      await loadAccounts()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Connection test failed')
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
      alert(result.message)
      await loadAccounts()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start bot')
    } finally {
      setActionLoading({})
    }
  }

  const handleStopBot = async (id: number) => {
    try {
      setActionLoading({ ...actionLoading, [id]: 'stopping' })
      const result = await brokerAccountsApi.stopBot(id)
      alert(result.message)
      await loadAccounts()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to stop bot')
    } finally {
      setActionLoading({})
    }
  }

  const openEditForm = (account: BrokerAccountData) => {
    setEditingAccount(account)
    setFormData({
      name: account.name,
      broker_type: account.broker_type,
      metaapi_account_id: account.metaapi_account_id || '',
      metaapi_token: account.metaapi_token || '',
      is_enabled: account.is_enabled,
      symbols: account.symbols,
      risk_per_trade_percent: account.risk_per_trade_percent,
      max_open_positions: account.max_open_positions,
      analysis_mode: account.analysis_mode,
      analysis_interval_seconds: account.analysis_interval_seconds,
      min_confidence: account.min_confidence,
      min_models_agree: account.min_models_agree,
      enabled_models: account.enabled_models,
      trading_start_hour: account.trading_start_hour,
      trading_end_hour: account.trading_end_hour,
    })
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
          </div>
          <button
            onClick={() => {
              setShowCreateForm(true)
              setEditingAccount(null)
              setFormData({
                name: '',
                broker_type: 'metaapi',
                metaapi_account_id: '',
                metaapi_token: '',
                is_enabled: true,
                symbols: ['EUR/USD', 'XAU/USD'],
                risk_per_trade_percent: 1.0,
                max_open_positions: 3,
                analysis_mode: 'standard',
                analysis_interval_seconds: 300,
                min_confidence: 75.0,
                min_models_agree: 4,
                enabled_models: ['chatgpt', 'gemini', 'grok', 'qwen', 'llama', 'ernie', 'kimi', 'mistral'],
                trading_start_hour: 7,
                trading_end_hour: 21,
              })
            }}
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

        {/* Accounts List */}
        {accounts.length === 0 ? (
          <div className="text-center py-8 text-dark-400">
            <Users size={48} className="mx-auto mb-4 opacity-50" />
            <p>No broker accounts configured</p>
            <p className="text-sm">Add your first broker to start trading</p>
          </div>
        ) : (
          <div className="space-y-4">
            {accounts.map((account) => (
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
                    <span className="text-2xl">📊</span>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{account.name}</span>
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
                        {account.symbols.join(', ')} | {account.analysis_mode} mode | {account.analysis_interval_seconds / 60}min interval
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
            ))}
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
              {editingAccount ? `Edit: ${editingAccount.name}` : 'Add New Broker'}
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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

              {/* MetaApi Account ID */}
              <div>
                <label className="block text-sm font-medium mb-2">MetaApi Account ID</label>
                <input
                  type="text"
                  value={formData.metaapi_account_id}
                  onChange={(e) => setFormData({ ...formData, metaapi_account_id: e.target.value })}
                  placeholder="Your MetaApi account ID"
                  className="input"
                />
              </div>

              {/* MetaApi Token */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium mb-2">MetaApi Token</label>
                <div className="relative">
                  <input
                    type={showToken ? 'text' : 'password'}
                    value={formData.metaapi_token}
                    onChange={(e) => setFormData({ ...formData, metaapi_token: e.target.value })}
                    placeholder="Your MetaApi access token"
                    className="input pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-dark-400 hover:text-dark-200"
                  >
                    {showToken ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

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
                {editingAccount ? 'Update Broker' : 'Create Broker'}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
