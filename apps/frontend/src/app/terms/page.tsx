'use client'

import { motion } from 'framer-motion'
import Link from 'next/link'
import Image from 'next/image'
import { ArrowLeft, FileText } from 'lucide-react'

export default function TermsPage() {
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
              <FileText size={24} />
              <h1 className="text-2xl font-bold">Terms of Service</h1>
            </div>
            <p className="text-dark-400 mt-2">Last updated: February 2026</p>
          </div>

          <div className="prose prose-invert max-w-none space-y-6 text-dark-300">
            <section>
              <h2 className="text-xl font-semibold text-white mb-3">1. Acceptance of Terms</h2>
              <p>
                By accessing and using Prometheus AI Trading ("the Service"), you agree to be bound
                by these Terms of Service. If you do not agree to these terms, please do not use
                our services.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">2. Service Description</h2>
              <p>
                Prometheus AI Trading provides automated trading analysis and execution tools.
                The Service is designed to assist with trading decisions but does not guarantee
                any specific financial outcomes.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">3. Risk Disclaimer</h2>
              <p className="text-imperial-400 font-semibold">
                IMPORTANT: Trading in financial markets involves substantial risk of loss and is
                not suitable for all investors.
              </p>
              <ul className="list-disc pl-6 space-y-2 mt-2">
                <li>Past performance is not indicative of future results</li>
                <li>You may lose some or all of your invested capital</li>
                <li>You should only trade with money you can afford to lose</li>
                <li>The Service does not provide financial advice</li>
                <li>You are solely responsible for your trading decisions</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">4. License and Access</h2>
              <p>
                Access to the Service requires a valid license key. Each license is:
              </p>
              <ul className="list-disc pl-6 space-y-2 mt-2">
                <li>Non-transferable and personal to the registered user</li>
                <li>Valid for the duration specified at purchase</li>
                <li>Subject to revocation for violation of these terms</li>
                <li>Limited to the number of users specified in the license type</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">5. Prohibited Activities</h2>
              <p>You agree not to:</p>
              <ul className="list-disc pl-6 space-y-2 mt-2">
                <li>Share your license key or account with others</li>
                <li>Attempt to reverse engineer or modify the Service</li>
                <li>Use the Service for illegal activities</li>
                <li>Interfere with the operation of the Service</li>
                <li>Resell or redistribute access to the Service</li>
              </ul>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">6. Limitation of Liability</h2>
              <p>
                To the maximum extent permitted by law, Prometheus AI Trading and its operators
                shall not be liable for any indirect, incidental, special, consequential, or
                punitive damages, including but not limited to loss of profits, data, or other
                intangible losses resulting from your use of the Service.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">7. Modifications</h2>
              <p>
                We reserve the right to modify these terms at any time. Continued use of the
                Service after changes constitutes acceptance of the new terms. We will notify
                users of significant changes via email or through the platform.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">8. Termination</h2>
              <p>
                We may terminate or suspend your access to the Service immediately, without
                prior notice, for conduct that we believe violates these Terms or is harmful
                to other users, us, or third parties, or for any other reason at our sole
                discretion.
              </p>
            </section>

            <section>
              <h2 className="text-xl font-semibold text-white mb-3">9. Contact</h2>
              <p>
                For questions about these Terms of Service, please contact us through our
                support channels.
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
