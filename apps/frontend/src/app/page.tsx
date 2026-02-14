'use client'

import { motion } from 'framer-motion'
import { AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import {
  Flame,
  Cpu,
  TrendingUp,
  Users,
  Zap,
  BarChart3,
  Target,
  Bot,
  Lock,
  Globe,
  ChevronRight,
  Sparkles,
  Shield,
  LogIn,
  Hammer,
  BookOpen,
  Eye,
  Layers3,
  Compass,
  Fingerprint,
  HelpCircle,
  LifeBuoy,
  FileText,
  UserPlus,
  ArrowUpRight,
} from 'lucide-react'
import { MusicPlayer } from '@/components/common/MusicPlayer'
import { LEGION_MODELS } from './legionModels'

const EDGE_PARTICLES = [
  { x: 26, size: 5, duration: 7.5, delay: 0.2, opacity: 0.48 },
  { x: 44, size: 3, duration: 9.5, delay: 1.6, opacity: 0.36 },
  { x: 62, size: 4, duration: 10.2, delay: 2.4, opacity: 0.4 },
  { x: 74, size: 2, duration: 8.6, delay: 3.1, opacity: 0.42 },
  { x: 34, size: 3, duration: 11, delay: 4.3, opacity: 0.34 },
]

const PROMETHEAN_PILLARS = [
  {
    icon: Hammer,
    title: 'The Forge',
    subtitle: 'Market structure tempered by live data',
    description:
      'Every cycle fuses raw price action, volatility and indicator state into a structured battlefield context.',
  },
  {
    icon: Eye,
    title: 'The Oracle',
    subtitle: 'Multi-model tactical reasoning',
    description:
      'Independent AI agents challenge each other. Consensus is formed only when conviction and alignment are strong.',
  },
  {
    icon: Fingerprint,
    title: 'The Covenant',
    subtitle: 'Identity, license and execution discipline',
    description:
      'Slot-based licensing and risk rules protect the system before a single order touches your broker.',
  },
]

const RITUAL_FLOW = [
  {
    icon: Layers3,
    title: 'Signal Layering',
    body: 'Timeframe structure, liquidity zones and directional momentum are stacked before entries are evaluated.',
  },
  {
    icon: Compass,
    title: 'Route Selection',
    body: 'The engine rejects weak setups and only deploys when risk profile, confidence and alignment are coherent.',
  },
  {
    icon: BookOpen,
    title: 'Execution Chronicle',
    body: 'Every decision is logged with context, so you can audit behavior instead of trading in the dark.',
  },
]

const NAV_ITEMS = [
  { label: 'Features', href: '#features' },
  { label: 'Models', href: '#models' },
  { label: 'FAQ', href: '#faq' },
  { label: 'Help', href: '#help' },
]

const FAQ_ITEMS = [
  {
    question: 'How does Prometheus decide when to execute a trade?',
    answer: 'Each setup is filtered by multi-model consensus, risk rules, and broker context before execution is allowed.',
  },
  {
    question: 'Can I use more than one broker account?',
    answer: 'Yes. Workspace slots are license-driven, so you can run multiple broker panels in parallel from one command center.',
  },
  {
    question: 'Do I need to keep the dashboard open for automation?',
    answer: 'No. The backend executes autonomously; dashboard access is used for control, monitoring, and audit.',
  },
  {
    question: 'How is risk controlled?',
    answer: 'Position sizing, SL/TP logic, daily loss constraints, and trade filters are enforced before orders are sent.',
  },
]

const HELP_LINKS = [
  {
    icon: HelpCircle,
    title: 'FAQ Center',
    description: 'Quick answers on setup, slots, and execution logic.',
    href: '#faq',
  },
  {
    icon: UserPlus,
    title: 'Create Account',
    description: 'Activate your license and onboard in minutes.',
    href: '/register',
  },
  {
    icon: FileText,
    title: 'Policy & Terms',
    description: 'Review platform rules, privacy and compliance.',
    href: '/terms',
  },
  {
    icon: LifeBuoy,
    title: 'Access Support',
    description: 'Use the login flow and resend verification if needed.',
    href: '/login',
  },
]

export default function LandingPage() {
  const visibleLegionModels = LEGION_MODELS.filter((model) => model.visible)
  const [showArrivalOverlay, setShowArrivalOverlay] = useState(false)
  const [isNavScrolled, setIsNavScrolled] = useState(false)
  const [isNavCompressed, setIsNavCompressed] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return
    const seen = localStorage.getItem('prometheus_arrival_seen')
    if (seen) return
    setShowArrivalOverlay(true)
    localStorage.setItem('prometheus_arrival_seen', '1')
    const timer = window.setTimeout(() => setShowArrivalOverlay(false), 3200)
    return () => window.clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return

    let lastScrollY = window.scrollY
    const handleScroll = () => {
      const currentY = window.scrollY
      const scrollingDown = currentY > lastScrollY + 3

      setIsNavScrolled(currentY > 18)
      setIsNavCompressed(currentY > 90 && scrollingDown)

      if (!scrollingDown && currentY < 90) {
        setIsNavCompressed(false)
      }

      lastScrollY = currentY
    }

    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <div className="min-h-screen overflow-hidden relative prometheus-home-shell">
      <AnimatePresence>
        {showArrivalOverlay && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[60] flex items-center justify-center px-4 prometheus-arrival-overlay"
          >
            <motion.div
              initial={{ y: 24, scale: 0.97, opacity: 0 }}
              animate={{ y: 0, scale: 1, opacity: 1 }}
              exit={{ y: -18, scale: 0.98, opacity: 0 }}
              transition={{ duration: 0.45 }}
              className="prometheus-arrival-shell max-w-xl w-full px-6 py-7 text-center"
            >
              <p className="text-xs uppercase tracking-[0.22em] text-primary-300 mb-2">Prometheus Protocol</p>
              <h2 className="text-3xl font-imperial text-gradient-falange mb-3">Welcome To The Fire</h2>
              <p className="text-dark-300 text-sm md:text-base mb-5">
                AI consensus, broker slots, and autonomous execution are ready.
              </p>
              <button
                onClick={() => setShowArrivalOverlay(false)}
                className="btn-primary btn-square px-8 py-3"
              >
                Enter The Platform
              </button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Top navigation */}
      <header
        className={`prometheus-top-header-shell fixed top-0 left-0 right-0 z-50 px-2 md:px-3 transition-all duration-300 ${
          isNavScrolled ? 'py-3 md:py-4' : 'py-5 md:py-6'
        } ${isNavCompressed ? '-translate-y-[1px]' : 'translate-y-0'}`}
      >
        <div className="max-w-[1840px] mx-auto">
          <div className={`prometheus-top-nav prometheus-top-nav-double ${isNavScrolled ? 'prometheus-top-nav-scrolled' : ''} ${isNavCompressed ? 'prometheus-top-nav-compressed' : ''}`}>
            <Link href="/" className="prometheus-nav-brand">
              <Image
                src="/images/logo.png"
                alt="Prometheus AI Trading"
                width={140}
                height={44}
                className="h-10 w-auto mix-blend-screen"
                priority
              />
              <span className="prometheus-nav-brand-caption hidden xl:block">
                Command Surface
              </span>
            </Link>

            <nav className="hidden lg:flex items-center gap-2">
              {NAV_ITEMS.map((item) => (
                <a key={item.label} href={item.href} className="prometheus-nav-link prometheus-nav-link-hero">
                  <span className="prometheus-nav-link-hero-text">{item.label}</span>
                </a>
              ))}
            </nav>

            <div className="flex items-center gap-2 md:gap-3">
              <MusicPlayer size="md" showLabel={false} />
              <Link href="/login" className="btn-secondary btn-square px-4 py-2.5 inline-flex items-center gap-2">
                <LogIn size={16} />
                <span className="hidden sm:inline">Login</span>
              </Link>
              <Link href="/register" className="btn-primary btn-square px-4 py-2.5 inline-flex items-center gap-2">
                <UserPlus size={16} />
                <span className="hidden sm:inline">Registrati</span>
              </Link>
            </div>
          </div>
        </div>
      </header>

      <EdgeFireRail side="left" />
      <EdgeFireRail side="right" />
      {/* Hero Section */}
      <section id="home" className="relative min-h-screen flex flex-col items-center justify-center px-4 pt-32 md:pt-36 pb-16 hero-gradient particles-bg prometheus-hero-theater">
        <div className="pointer-events-none absolute inset-0 overflow-hidden">
          <div className="prometheus-hero-grid-lines" />
          <div className="prometheus-hero-scan-beam" />
          <div className="prometheus-hero-arc prometheus-hero-arc-left" />
          <div className="prometheus-hero-arc prometheus-hero-arc-right" />
        </div>

        {/* Animated background orbs */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <motion.div
            className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(255, 215, 0, 0.15) 0%, transparent 70%)',
            }}
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.3, 0.5, 0.3],
            }}
            transition={{
              duration: 8,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
          <motion.div
            className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] rounded-full"
            style={{
              background: 'radial-gradient(circle, rgba(124, 58, 237, 0.15) 0%, transparent 70%)',
            }}
            animate={{
              scale: [1.2, 1, 1.2],
              opacity: [0.3, 0.5, 0.3],
            }}
            transition={{
              duration: 10,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        </div>

        <div className="pointer-events-none absolute inset-0 hidden 2xl:block">
          <motion.div
            initial={{ opacity: 0, x: -22 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.9 }}
            className="absolute left-5 top-[22%] prometheus-side-module"
          >
            <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Neural Forge</p>
            <p className="text-sm text-dark-200">Signal maps and macro pressure fused into one tactical read.</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: -26 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 1.05 }}
            className="absolute left-8 bottom-[21%] prometheus-side-module-cyan"
          >
            <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Latency Gate</p>
            <p className="text-sm text-dark-200">Execution rails and slippage checks synchronized in real time.</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 22 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.95 }}
            className="absolute right-5 top-[26%] prometheus-side-module"
          >
            <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Consensus Core</p>
            <p className="text-sm text-dark-200">Only high-conviction model alignment unlocks order execution.</p>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, x: 28 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 1.1 }}
            className="absolute right-8 bottom-[20%] prometheus-side-module-cyan"
          >
            <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Reliability Layer</p>
            <p className="text-sm text-dark-200">Verification, licensing and safeguards enforce platform discipline.</p>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, x: -18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.75 }}
          className="hidden xl:block absolute left-10 top-[34%] z-10"
        >
          <div className="prometheus-panel-surface px-4 py-3 max-w-[220px]">
            <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">Realtime Layer</p>
            <p className="text-sm text-dark-200">AI consensus + execution telemetry synchronized every cycle.</p>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 18 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.7, delay: 0.85 }}
          className="hidden xl:block absolute right-10 top-[40%] z-10"
        >
          <div className="prometheus-panel-surface px-4 py-3 max-w-[240px]">
            <p className="text-xs uppercase tracking-wider text-dark-500 mb-1">License System</p>
            <p className="text-sm text-dark-200">Slot-based access for multi-broker workspaces and scalable onboarding.</p>
          </div>
        </motion.div>

        {/* Main content */}
        <div className="text-center max-w-5xl mx-auto z-10 px-6 py-10 rounded-3xl hero-content-shell prometheus-hero-card forge-pattern">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary-500/30 bg-primary-500/10 mb-8"
          >
            <Sparkles className="w-4 h-4 text-primary-400" />
            <span className="text-sm font-medium text-primary-300">
              Powered by 10+ AI Models
            </span>
          </motion.div>

          {/* Logo Image */}
          <motion.div
            initial={{ opacity: 0, scale: 0.5 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.1 }}
            className="mb-6 relative"
          >
            <div className="relative inline-block fire-glow">
              <Image
                src="/images/logo.png"
                alt="Prometheus AI Trading"
                width={700}
                height={210}
                className="w-auto h-48 md:h-56 mix-blend-screen"
                priority
              />
              <div className="absolute inset-0 bg-primary-500/20 blur-3xl rounded-full animate-pulse -z-10" />
              {/* Ember particles effect */}
              <div className="absolute -inset-4 ember-particles" />
            </div>
          </motion.div>

          {/* Epic Subtitle */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="mb-6"
          >
            <span className="text-2xl md:text-3xl font-imperial text-imperial-400 tracking-[0.3em] uppercase">
              Bringer of Market Fire
            </span>
          </motion.div>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-xl md:text-2xl text-dark-300 mb-4 font-light"
          >
            The Titan Among Trading Platforms
          </motion.p>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="text-lg text-dark-400 max-w-2xl mx-auto mb-12"
          >
            Like Prometheus brought fire to humanity, we bring the power of AI to traders.
            <br />
            Multi-broker support. Real-time analysis. Automated execution.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.55 }}
            className="flex flex-wrap items-center justify-center gap-3 mb-10"
          >
            <span className="prometheus-chip">
              <Shield size={12} />
              License Slots
            </span>
            <span className="prometheus-chip prometheus-chip-imperial">
              <Users size={12} />
              Multi Broker
            </span>
            <span className="prometheus-chip prometheus-chip-soft">
              <BarChart3 size={12} />
              Live Execution
            </span>
          </motion.div>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <Link
              href="/dashboard"
              className="btn-primary btn-square text-lg px-10 py-4 inline-flex items-center gap-3 group relative overflow-hidden"
            >
              <span className="relative z-10 flex items-center gap-2">
                Enter Command Center
                <ChevronRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-primary-400 to-primary-600 opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>

            <Link
              href="/dashboard/settings"
              className="btn-secondary btn-square text-lg px-8 py-4 inline-flex items-center gap-2"
            >
              <Flame className="w-5 h-5" />
              Ignite Trading
            </Link>
          </motion.div>
        </div>

        {/* Stats Section */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-6 mt-20 max-w-4xl w-full px-4"
        >
          <StatCard number="10+" label="AI Models" icon={<Bot className="w-5 h-5" />} />
          <StatCard number="24/7" label="Trading" icon={<TrendingUp className="w-5 h-5" />} />
          <StatCard number="Multi" label="Broker" icon={<Globe className="w-5 h-5" />} />
          <StatCard number="Real-time" label="Analysis" icon={<Zap className="w-5 h-5" />} />
        </motion.div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.5 }}
          className="absolute bottom-10 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 10, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-6 h-10 border-2 border-primary-500/30 rounded-full flex items-start justify-center p-2"
          >
            <motion.div
              animate={{ height: ['20%', '80%', '20%'] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="w-1 bg-primary-500 rounded-full"
            />
          </motion.div>
        </motion.div>
      </section>

      <section className="py-24 px-4 relative">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55 }}
            className="text-center mb-10"
          >
            <span className="myth-badge mb-4">
              <Sparkles size={12} />
              Prometheus Protocol
            </span>
            <h2 className="font-imperial text-3xl md:text-5xl mb-4">
              <span className="text-gradient-falange">Forged For System Traders</span>
            </h2>
            <p className="text-dark-400 max-w-3xl mx-auto text-sm md:text-base">
              This is not a cosmetic dashboard. It is a tactical layer where model consensus,
              risk architecture and broker execution work as a single command surface.
            </p>
          </motion.div>

          <div className="rune-divider mb-10" />

          <div className="grid md:grid-cols-3 gap-5 mb-10">
            {PROMETHEAN_PILLARS.map((pillar, index) => {
              const Icon = pillar.icon
              return (
                <motion.article
                  key={pillar.title}
                  initial={{ opacity: 0, y: 22 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.55, delay: index * 0.08 }}
                  className="story-grid-card forge-pattern"
                >
                  <div className="w-12 h-12 rounded-2xl forge-ring flex items-center justify-center mb-4 text-primary-300">
                    <Icon size={20} />
                  </div>
                  <h3 className="text-xl text-dark-50 mb-1">{pillar.title}</h3>
                  <p className="text-xs uppercase tracking-[0.12em] text-primary-300/80 mb-3">
                    {pillar.subtitle}
                  </p>
                  <p className="text-sm text-dark-400 leading-relaxed">{pillar.description}</p>
                </motion.article>
              )
            })}
          </div>

          <div className="grid md:grid-cols-3 gap-4">
            {RITUAL_FLOW.map((item, index) => {
              const Icon = item.icon
              return (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.45, delay: index * 0.08 }}
                  className="card-glass p-5 border border-dark-700/60"
                >
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 rounded-lg bg-primary-500/10 border border-primary-500/20">
                      <Icon size={16} className="text-primary-300" />
                    </div>
                    <p className="font-semibold text-dark-100">{item.title}</p>
                  </div>
                  <p className="text-sm text-dark-400 leading-relaxed">{item.body}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-32 px-4 relative">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-20"
          >
            <h2 className="font-imperial text-4xl md:text-5xl font-bold mb-6 flex items-center justify-center gap-4">
              <Flame className="w-10 h-10 text-primary-400 torch-glow hidden md:block" />
              <span className="text-gradient-falange">The Titan&apos;s Arsenal</span>
              <Flame className="w-10 h-10 text-primary-400 torch-glow hidden md:block" />
            </h2>
            <p className="text-lg text-dark-400 max-w-2xl mx-auto">
              A complete suite of tools designed for the modern trader warrior.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Cpu className="w-8 h-8" />}
              title="Multi-AI Consensus"
              description="10+ AI models including GPT-4, Claude, Gemini, and Llama vote on every trade for maximum accuracy."
              delay={0.1}
            />
            <FeatureCard
              icon={<BarChart3 className="w-8 h-8" />}
              title="TradingView Integration"
              description="Real-time charts with AI-driven analysis. Each model adds indicators and draws on live charts."
              delay={0.2}
            />
            <FeatureCard
              icon={<Target className="w-8 h-8" />}
              title="Precision Execution"
              description="Automatic order placement with smart SL/TP calculation based on risk management rules."
              delay={0.3}
            />
            <FeatureCard
              icon={<Users className="w-8 h-8" />}
              title="Multi-Broker Support"
              description="Connect multiple brokers simultaneously. MetaTrader, OANDA, and more with independent configs."
              delay={0.4}
            />
            <FeatureCard
              icon={<Shield className="w-8 h-8" />}
              title="Risk Management"
              description="Automatic position sizing, daily loss limits, break-even triggers, and trailing stops."
              delay={0.5}
            />
            <FeatureCard
              icon={<Lock className="w-8 h-8" />}
              title="News Filter"
              description="Automatically pauses trading before and after high-impact economic events."
              delay={0.6}
            />
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-32 px-4 bg-dark-950/50">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-20"
          >
            <h2 className="font-imperial text-4xl md:text-5xl font-bold mb-6">
              <span className="text-gradient-imperial">Battle Strategy</span>
            </h2>
            <p className="text-lg text-dark-400 max-w-2xl mx-auto">
              How Prometheus conquers the markets.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-8">
            <StepCard
              number="01"
              title="Analyze"
              description="AI models analyze real TradingView charts with indicators"
              delay={0.1}
            />
            <StepCard
              number="02"
              title="Vote"
              description="Each AI votes on direction, entry, SL/TP with confidence"
              delay={0.2}
            />
            <StepCard
              number="03"
              title="Consensus"
              description="System calculates median values when majority agrees"
              delay={0.3}
            />
            <StepCard
              number="04"
              title="Execute"
              description="Order placed automatically with risk-adjusted position size"
              delay={0.4}
            />
          </div>
        </div>
      </section>

      {/* AI Models Section */}
      <section id="models" className="py-32 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="font-imperial text-4xl md:text-5xl font-bold mb-6 flex items-center justify-center gap-4">
              <Flame className="w-10 h-10 text-primary-400 torch-glow hidden md:block" />
              <span className="text-gradient-gold">The Titan&apos;s Legion</span>
              <Flame className="w-10 h-10 text-primary-400 torch-glow hidden md:block" />
            </h2>
            <p className="text-lg text-dark-400 max-w-2xl mx-auto">
              Our army of AI models, each with unique trading expertise.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="grid grid-cols-2 md:grid-cols-4 gap-4"
          >
            {visibleLegionModels.map((model, index) => (
              <motion.div
                key={model.id}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
                className="card-glass p-5 text-center legion-card group"
              >
                <div className={`w-14 h-14 rounded-2xl border bg-gradient-to-br ${model.accentClass} mx-auto mb-3 flex items-center justify-center transition-transform duration-300 group-hover:scale-105`}>
                  <Image
                    src={model.logoSrc}
                    alt={model.logoAlt}
                    width={28}
                    height={28}
                    className="w-7 h-7 object-contain legion-logo-mark"
                  />
                </div>
                <h3 className="font-semibold text-dark-100">{model.name}</h3>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* FAQ Section */}
      <section id="faq" className="py-28 px-4 bg-dark-950/55 relative">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55 }}
            className="text-center mb-14"
          >
            <h2 className="font-imperial text-4xl md:text-5xl mb-5">
              <span className="text-gradient-imperial">FAQ & Support Intel</span>
            </h2>
            <p className="text-dark-400 max-w-2xl mx-auto">
              Everything needed to onboard fast, verify access, and run your command center with confidence.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 gap-4">
            {FAQ_ITEMS.map((item, index) => (
              <motion.article
                key={item.question}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.45, delay: index * 0.07 }}
                className="prometheus-faq-card"
              >
                <h3 className="text-lg text-dark-100 mb-2">{item.question}</h3>
                <p className="text-sm text-dark-400 leading-relaxed">{item.answer}</p>
              </motion.article>
            ))}
          </div>
        </div>
      </section>

      {/* Help Section */}
      <section id="help" className="py-24 px-4">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="prometheus-help-shell p-6 md:p-10"
          >
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-5 mb-8">
              <div>
                <p className="text-xs uppercase tracking-[0.16em] text-primary-300 mb-2">Help Center</p>
                <h2 className="font-imperial text-3xl md:text-4xl text-gradient-falange mb-2">
                  Need Assistance Before Ignition?
                </h2>
                <p className="text-dark-300 max-w-2xl">
                  Use these quick paths for account setup, verification flow, and legal/security references.
                </p>
              </div>
            </div>

            <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
              {HELP_LINKS.map((item, index) => {
                const Icon = item.icon
                const isAnchor = item.href.startsWith('#')
                return (
                  <motion.div
                    key={item.title}
                    initial={{ opacity: 0, y: 16 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.45, delay: index * 0.06 }}
                  >
                    {isAnchor ? (
                      <a href={item.href} className="prometheus-help-link">
                        <div className="w-10 h-10 rounded-lg bg-primary-500/15 border border-primary-500/30 flex items-center justify-center text-primary-300">
                          <Icon size={18} />
                        </div>
                        <div>
                          <p className="text-sm text-dark-100 font-semibold mb-1">{item.title}</p>
                          <p className="text-xs text-dark-400">{item.description}</p>
                        </div>
                        <ArrowUpRight size={16} className="text-primary-300 ml-auto" />
                      </a>
                    ) : (
                      <Link href={item.href} className="prometheus-help-link">
                        <div className="w-10 h-10 rounded-lg bg-primary-500/15 border border-primary-500/30 flex items-center justify-center text-primary-300">
                          <Icon size={18} />
                        </div>
                        <div>
                          <p className="text-sm text-dark-100 font-semibold mb-1">{item.title}</p>
                          <p className="text-xs text-dark-400">{item.description}</p>
                        </div>
                        <ArrowUpRight size={16} className="text-primary-300 ml-auto" />
                      </Link>
                    )}
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 px-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-primary-500/5 to-imperial-500/5" />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl mx-auto text-center relative z-10"
        >
          <h2 className="font-imperial text-4xl md:text-5xl font-bold mb-6">
            <span className="text-gradient-falange">Embrace The Fire</span>
          </h2>
          <p className="text-lg text-dark-400 mb-10">
            Start your journey to autonomous trading excellence.
            <br />
            Connect your broker and let the Titan's fire forge your profits.
          </p>

          <Link
            href="/dashboard"
            className="btn-primary btn-square text-xl px-12 py-5 inline-flex items-center gap-3 group animate-warrior-pulse titan-pulse"
          >
            <Flame className="w-6 h-6 torch-glow" />
            <span>Enter Command Center</span>
            <ChevronRight className="w-6 h-6 transition-transform group-hover:translate-x-1" />
          </Link>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-dark-800/50">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Image
              src="/images/logo.png"
              alt="Prometheus AI Trading"
              width={200}
              height={60}
              className="h-12 w-auto mix-blend-screen"
            />
            <span className="text-dark-500">·</span>
            <span className="text-dark-500 text-sm">v2.0.0</span>
          </div>
          <p className="text-dark-500 text-sm">
            The Titan of AI Trading
          </p>
        </div>
      </footer>
    </div>
  )
}

function EdgeFireRail({ side }: { side: 'left' | 'right' }) {
  const isLeft = side === 'left'

  return (
    <div
      className={`fixed top-0 bottom-0 w-16 pointer-events-none z-40 edge-fire-rail ${
        isLeft ? 'left-0 edge-fire-rail-left' : 'right-0 edge-fire-rail-right'
      }`}
    >
      <div className="edge-rail-backdrop" />
      <div className="edge-rail-line edge-rail-line-main" />
      <div className="edge-rail-line edge-rail-line-soft" />
      <div className="edge-rail-energy" />
      <div className="edge-rail-energy edge-rail-energy-soft" />
      {EDGE_PARTICLES.map((particle, index) => {
        const x = isLeft ? particle.x : 100 - particle.x
        return (
          <span
            key={`${side}-${index}`}
            className="edge-rail-particle"
            style={
              {
                '--particle-x': `${x}%`,
                '--particle-size': `${particle.size}px`,
                '--particle-duration': `${particle.duration}s`,
                '--particle-delay': `${particle.delay}s`,
                '--particle-opacity': particle.opacity,
              } as React.CSSProperties
            }
          />
        )
      })}
    </div>
  )
}

function StatCard({
  number,
  label,
  icon
}: {
  number: string
  label: string
  icon: React.ReactNode
}) {
  return (
    <div className="card-glass p-6 text-center group hover:border-primary-500/30 transition-all duration-300">
      <div className="flex items-center justify-center gap-2 text-primary-400 mb-2">
        {icon}
      </div>
      <div className="text-3xl font-bold text-gradient-gold mb-1">{number}</div>
      <div className="text-sm text-dark-400 uppercase tracking-wider">{label}</div>
    </div>
  )
}

function FeatureCard({
  icon,
  title,
  description,
  delay = 0,
}: {
  icon: React.ReactNode
  title: string
  description: string
  delay?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay }}
      className="card-hover p-8 group"
    >
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-500/20 to-imperial-500/20 flex items-center justify-center mb-6 text-primary-400 group-hover:text-primary-300 transition-colors group-hover:scale-110 transform duration-300">
        {icon}
      </div>
      <h3 className="text-xl font-semibold mb-3 text-dark-100 group-hover:text-primary-300 transition-colors">
        {title}
      </h3>
      <p className="text-dark-400 leading-relaxed">{description}</p>
    </motion.div>
  )
}

function StepCard({
  number,
  title,
  description,
  delay = 0,
}: {
  number: string
  title: string
  description: string
  delay?: number
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay }}
      className="text-center group"
    >
      <div className="relative mb-6">
        <div className="w-20 h-20 rounded-full border-2 border-primary-500/30 flex items-center justify-center mx-auto group-hover:border-primary-500 transition-colors">
          <span className="font-imperial text-2xl text-gradient-gold">{number}</span>
        </div>
        <div className="hidden md:block absolute top-1/2 left-full w-full h-0.5 bg-gradient-to-r from-primary-500/30 to-transparent -translate-y-1/2" />
      </div>
      <h3 className="text-lg font-semibold mb-2 text-dark-100">{title}</h3>
      <p className="text-sm text-dark-400">{description}</p>
    </motion.div>
  )
}

