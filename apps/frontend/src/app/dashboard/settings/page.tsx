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
} from 'lucide-react'
import { settingsApi, type BrokerSettingsData } from '@/lib/api'

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
    models: ['ChatGPT 5.2', 'Gemini 3 Pro', 'DeepSeek V3.2', 'Grok 4.1 Fast', 'Qwen Max', 'GLM 4.7'],
    field: { key: 'AIML_API_KEY', label: 'API Key', placeholder: 'Your AIML API key' },
    badge: 'Recommended - 6 Models',
    description: 'Single API key for 6 top AI models via api.aimlapi.com',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    icon: '🤖',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'],
    field: { key: 'OPENAI_API_KEY', label: 'API Key', placeholder: 'sk-...' },
    description: 'Fallback provider',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    icon: '🧠',
    models: ['claude-3-5-sonnet', 'claude-3-haiku'],
    field: { key: 'ANTHROPIC_API_KEY', label: 'API Key', placeholder: 'sk-ant-...' },
    description: 'Fallback provider',
  },
  {
    id: 'google',
    name: 'Google AI',
    icon: '💎',
    models: ['gemini-1.5-flash', 'gemini-1.5-pro'],
    field: { key: 'GOOGLE_API_KEY', label: 'API Key', placeholder: 'AI...' },
    description: 'Fallback provider',
  },
  {
    id: 'groq',
    name: 'Groq',
    icon: '⚡',
    models: ['llama-3.3-70b', 'llama-3.1-8b', 'mixtral-8x7b'],
    field: { key: 'GROQ_API_KEY', label: 'API Key', placeholder: 'gsk_...' },
    badge: 'Ultra Fast',
    description: 'Fallback provider',
  },
  {
    id: 'mistral',
    name: 'Mistral',
    icon: '🌪️',
    models: ['mistral-large', 'mistral-small'],
    field: { key: 'MISTRAL_API_KEY', label: 'API Key', placeholder: 'Your Mistral key' },
    description: 'Fallback provider',
  },
  {
    id: 'ollama',
    name: 'Ollama',
    icon: '🦙',
    models: ['llama3.1:8b', 'qwen2.5:14b', 'mistral:7b'],
    field: { key: 'OLLAMA_BASE_URL', label: 'Base URL', placeholder: 'http://localhost:11434' },
    badge: 'Free & Local',
    description: 'Local inference - no API key needed',
  },
]

type SettingsSection = 'broker' | 'ai' | 'risk' | 'notifications'

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
        if (settings.ai.openai_api_key) {
          aiSettings.openai = { enabled: true, key: settings.ai.openai_api_key }
        }
        if (settings.ai.anthropic_api_key) {
          aiSettings.anthropic = { enabled: true, key: settings.ai.anthropic_api_key }
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
        openai: 'openai_api_key',
        anthropic: 'anthropic_api_key',
        google: 'google_api_key',
        groq: 'groq_api_key',
        mistral: 'mistral_api_key',
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
      {/* Info Banner for AIML */}
      <div className="p-4 bg-primary-500/10 border border-primary-500/30 rounded-xl flex items-start gap-3">
        <Info size={20} className="text-primary-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-primary-300 font-medium">Recommended: AIML API</p>
          <p className="text-xs text-dark-400 mt-1">
            AIML API provides access to 6 top AI models (ChatGPT 5.2, Gemini 3 Pro, DeepSeek V3.2, Grok 4.1, Qwen Max, GLM 4.7)
            with a single API key. Get your key at <a href="https://aimlapi.com" target="_blank" rel="noopener noreferrer" className="text-primary-400 hover:underline">aimlapi.com</a>
          </p>
        </div>
      </div>

      <div className="card p-6">
        <h2 className="text-xl font-semibold mb-2">AI Providers</h2>
        <p className="text-dark-400 mb-6">
          Configure which AI models to use for market analysis. Enable AIML API for best results.
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
