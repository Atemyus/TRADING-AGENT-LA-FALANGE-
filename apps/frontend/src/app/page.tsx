'use client'

import { motion } from 'framer-motion'
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
} from 'lucide-react'
import { MusicPlayer } from '@/components/common/MusicPlayer'

export default function LandingPage() {
  return (
    <div className="min-h-screen overflow-hidden relative">
      {/* Fixed header with music and login */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          {/* Spacer for layout balance */}
          <div className="w-16" />

          {/* Right side - Music & Auth */}
          <div className="flex items-center gap-4">
            <MusicPlayer size="md" showLabel={false} />

            <Link
              href="/login"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-dark-800/50 border border-primary-500/20 hover:bg-dark-800 hover:border-primary-500/40 transition-all duration-300 text-dark-200 hover:text-primary-300"
            >
              <LogIn size={18} />
              <span className="hidden sm:inline font-medium">Login</span>
            </Link>
          </div>
        </div>
      </header>

      {/* Left border fire effect */}
      <div className="fixed left-0 top-0 bottom-0 w-16 pointer-events-none z-40">
        <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 to-transparent" />
        <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-gradient-to-b from-transparent via-primary-500/40 to-transparent" />
        <div className="absolute left-2 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-primary-500/20 to-transparent" />
        {/* Floating embers */}
        <motion.div
          animate={{
            y: ['100vh', '-10vh'],
            opacity: [0, 1, 1, 0],
            scale: [0.5, 1, 1, 0.5],
          }}
          transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
          className="absolute left-4 w-2 h-2 rounded-full bg-primary-400/60 blur-[2px]"
        />
        <motion.div
          animate={{
            y: ['100vh', '-10vh'],
            opacity: [0, 1, 1, 0],
          }}
          transition={{ duration: 12, repeat: Infinity, ease: 'linear', delay: 2 }}
          className="absolute left-6 w-1.5 h-1.5 rounded-full bg-imperial-400/50 blur-[1px]"
        />
        <motion.div
          animate={{
            y: ['100vh', '-10vh'],
            opacity: [0, 0.8, 0.8, 0],
          }}
          transition={{ duration: 10, repeat: Infinity, ease: 'linear', delay: 5 }}
          className="absolute left-3 w-1 h-1 rounded-full bg-primary-300/70 blur-[1px]"
        />
      </div>

      {/* Right border fire effect */}
      <div className="fixed right-0 top-0 bottom-0 w-16 pointer-events-none z-40">
        <div className="absolute inset-0 bg-gradient-to-l from-primary-500/5 to-transparent" />
        <div className="absolute right-0 top-0 bottom-0 w-[2px] bg-gradient-to-b from-transparent via-primary-500/40 to-transparent" />
        <div className="absolute right-2 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-primary-500/20 to-transparent" />
        {/* Floating embers */}
        <motion.div
          animate={{
            y: ['100vh', '-10vh'],
            opacity: [0, 1, 1, 0],
            scale: [0.5, 1, 1, 0.5],
          }}
          transition={{ duration: 9, repeat: Infinity, ease: 'linear', delay: 1 }}
          className="absolute right-4 w-2 h-2 rounded-full bg-primary-400/60 blur-[2px]"
        />
        <motion.div
          animate={{
            y: ['100vh', '-10vh'],
            opacity: [0, 1, 1, 0],
          }}
          transition={{ duration: 11, repeat: Infinity, ease: 'linear', delay: 4 }}
          className="absolute right-6 w-1.5 h-1.5 rounded-full bg-imperial-400/50 blur-[1px]"
        />
        <motion.div
          animate={{
            y: ['100vh', '-10vh'],
            opacity: [0, 0.8, 0.8, 0],
          }}
          transition={{ duration: 7, repeat: Infinity, ease: 'linear', delay: 3 }}
          className="absolute right-3 w-1 h-1 rounded-full bg-primary-300/70 blur-[1px]"
        />
      </div>
      {/* Hero Section */}
      <section className="relative min-h-screen flex flex-col items-center justify-center px-4 hero-gradient particles-bg">
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

        {/* Main content */}
        <div className="text-center max-w-5xl mx-auto z-10">
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

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center"
          >
            <Link
              href="/dashboard"
              className="btn-primary text-lg px-10 py-4 inline-flex items-center gap-3 group relative overflow-hidden"
            >
              <span className="relative z-10 flex items-center gap-2">
                Enter Command Center
                <ChevronRight className="w-5 h-5 transition-transform group-hover:translate-x-1" />
              </span>
              <div className="absolute inset-0 bg-gradient-to-r from-primary-400 to-primary-600 opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>

            <Link
              href="/dashboard/settings"
              className="btn-secondary text-lg px-8 py-4 inline-flex items-center gap-2"
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

      {/* Features Section */}
      <section className="py-32 px-4 relative">
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
      <section className="py-32 px-4">
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
            {[
              { name: 'ChatGPT', style: 'SMC Expert', color: 'from-green-500 to-emerald-600' },
              { name: 'Gemini', style: 'Price Action', color: 'from-blue-500 to-cyan-600' },
              { name: 'Grok', style: 'Momentum', color: 'from-orange-500 to-red-600' },
              { name: 'Qwen', style: 'Ichimoku', color: 'from-purple-500 to-violet-600' },
              { name: 'Llama', style: 'Bollinger', color: 'from-yellow-500 to-amber-600' },
              { name: 'ERNIE', style: 'Fibonacci', color: 'from-pink-500 to-rose-600' },
              { name: 'Kimi', style: 'Wave Theory', color: 'from-teal-500 to-cyan-600' },
              { name: 'Mistral', style: 'VWAP', color: 'from-indigo-500 to-blue-600' },
            ].map((model, index) => (
              <motion.div
                key={model.name}
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.4, delay: index * 0.05 }}
                className="card-glass p-5 text-center hover:border-primary-500/30 transition-all duration-300 group"
              >
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${model.color} mx-auto mb-3 flex items-center justify-center text-white font-bold text-lg group-hover:scale-110 transition-transform`}>
                  {model.name[0]}
                </div>
                <h3 className="font-semibold text-dark-100 mb-1">{model.name}</h3>
                <p className="text-xs text-dark-400">{model.style}</p>
              </motion.div>
            ))}
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
            className="btn-primary text-xl px-12 py-5 inline-flex items-center gap-3 group animate-warrior-pulse titan-pulse"
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
