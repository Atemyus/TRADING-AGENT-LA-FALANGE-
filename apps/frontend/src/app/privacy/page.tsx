'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'
import { ArrowLeft, Shield } from 'lucide-react'

export default function PrivacyPage() {
  return (
    <div className="min-h-screen px-4 py-12 relative overflow-hidden">
      {/* Background effects */}
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-1/4 right-1/4 w-[500px] h-[500px] bg-imperial-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-1/4 left-1/4 w-[400px] h-[400px] bg-primary-500/10 rounded-full blur-3xl" />
      </div>

      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 px-6 py-4 bg-dark-950/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="p-2 rounded-lg bg-dark-800/50 border border-primary-500/20 hover:border-primary-500/40 transition-all">
              <ArrowLeft size={20} className="text-dark-300" />
            </div>
            <span className="text-dark-400 hidden sm:block">Back to home</span>
          </Link>
        </div>
      </header>

      <div className="max-w-4xl mx-auto mt-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="card-imperial p-8"
        >
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="relative inline-block mb-4">
              <Image
                src="/images/logo.png"
                alt="Prometheus AI Trading"
                width={280}
                height={84}
                className="h-20 w-auto mix-blend-screen"
                priority
              />
            </div>
            <div className="flex items-center justify-center gap-2 text-imperial-400">
              <Shield size={24} />
              <h1 className="text-2xl font-bold">Privacy Policy</h1>
            </div>
            <p className="text-dark-400 mt-2">Last updated: February 2026</p>
          </div>

          <div className="prose prose-invert max-w-none space-y-6 text-dark-300">
            <section>
              <h2 className="text-xl font-semibold text-white mb-3">1. Information We Collect</h2>
              <p>
                Prometheus AI Trading collects information you provide directly, including:
              </p>
              <ul className="list-disc pl-6 space-y-2 mt-2">
                <li>Account information (email, username, password)</li>
                <li>Trading preferences and configurations</li>
                <li>License key information</li>
                <li>Usage data and analytics</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">2. How We Use Your Information</h2>
              <p>We use collected information to:</p>
              <ul className="list-disc pl-6 space-y-2 mt-2">
                <li>Provide and maintain our trading services</li>
                <li>Process transactions and manage your account</li>
                <li>Send important updates about our services</li>
                <li>Improve our platform and develop new features</li>
                <li>Ensure security and prevent fraud</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">3. Data Security</h2>
              <p>
                We implement industry-standard security measures to protect your personal information.
                Your data is encrypted in transit and at rest. We never store your trading account
                credentials directly - all connections to trading platforms are made through secure,
                temporary sessions.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">4. Third-Party Services</h2>
              <p>
                We may use third-party services for payment processing (Whop), analytics, and
                infrastructure. These services have their own privacy policies governing the use
                of your information.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">5. Your Rights</h2>
              <p>You have the right to:</p>
              <ul className="list-disc pl-6 space-y-2 mt-2">
                <li>Access your personal data</li>
                <li>Request correction of inaccurate data</li>
                <li>Request deletion of your account</li>
                <li>Export your data</li>
                <li>Opt out of marketing communications</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">6. Contact Us</h2>
              <p>
                If you have any questions about this Privacy Policy, please contact us through
                our support channels.
              </p>
            </section>
          </div>

          {/* Back to Register */}
          <div className="mt-8 pt-6 border-t border-dark-700">
            <Link
              href="/register"
              className="btn-secondary w-full py-3 flex items-center justify-center gap-2"
            >
              <ArrowLeft size={18} />
              <span>Back to Registration</span>
            </Link>
          </div>
        </motion.div>
      </div>
    </div>
  )
}
