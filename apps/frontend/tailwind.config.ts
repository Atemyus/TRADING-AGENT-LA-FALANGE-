import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // LA FALANGE Theme - Imperial Warrior Colors

        // Primary: Molten gold / ember orange
        primary: {
          50: '#fff9eb',
          100: '#fff0cc',
          200: '#ffe0a1',
          300: '#ffd174',
          400: '#ffbb38',
          500: '#ff8c00',  // Main gold
          600: '#e97b00',
          700: '#c85f00',
          800: '#9f4700',
          900: '#733300',
          950: '#3f1b00',
        },

        // Accent: Electric cyan
        imperial: {
          50: '#e8feff',
          100: '#c8fcff',
          200: '#9bf9ff',
          300: '#62f6ff',
          400: '#25f2ff',
          500: '#00f5ff',  // Main purple
          600: '#00d5df',
          700: '#00aab3',
          800: '#007e85',
          900: '#05585d',
          950: '#013236',
        },

        // Falange accent colors
        falange: {
          gold: '#FFD700',
          amber: '#FF8C00',
          bronze: '#CD7F32',
          copper: '#B87333',
          imperial: '#00F5FF',
          violet: '#58F7FF',
          blood: '#DC2626',
          crimson: '#B91C1C',
          emerald: '#FFD700',
          jade: '#FFB347',
        },

        // Trading colors (profit/loss)
        profit: {
          light: '#ffe39a',
          DEFAULT: '#FFD700',
          dark: '#FFB347',
          glow: '#FFD70040',
        },
        loss: {
          light: '#F87171',
          DEFAULT: '#EF4444',
          dark: '#DC2626',
          glow: '#EF444440',
        },

        // Legacy aliases used in component classes
        neon: {
          blue: '#00F5FF',
          green: '#FFD700',
          yellow: '#FFD700',
          red: '#FF5A5A',
          purple: '#58F7FF',
        },

        // Dark theme backgrounds - obsidian deep space
        dark: {
          50: '#f6fbff',
          100: '#e0e4ea',
          200: '#c7ced8',
          300: '#aeb8c7',
          400: '#8d98aa',
          500: '#687487',
          600: '#4b5768',
          700: '#354252',
          800: '#242f3f',
          850: '#1c2636',
          900: '#141d2b',
          925: '#0f1724',
          950: '#0a0e17',
          abyss: '#070b12',
        },
      },
      fontFamily: {
        sans: ['Rajdhani', 'Exo 2', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
        display: ['Orbitron', 'Rajdhani', 'sans-serif'],
        accent: ['Exo 2', 'Rajdhani', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-gold': 'pulseGold 2s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'glow-gold': 'glowGold 2s ease-in-out infinite alternate',
        'glow-imperial': 'glowImperial 2s ease-in-out infinite alternate',
        'glow-profit': 'glowProfit 1.5s ease-in-out infinite alternate',
        'glow-loss': 'glowLoss 1.5s ease-in-out infinite alternate',
        'slide-up': 'slideUp 0.3s ease-out',
        'slide-down': 'slideDown 0.3s ease-out',
        'slide-left': 'slideLeft 0.3s ease-out',
        'slide-right': 'slideRight 0.3s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
        'fade-in-up': 'fadeInUp 0.4s ease-out',
        'shake': 'shake 0.5s cubic-bezier(.36,.07,.19,.97) both',
        'count-up': 'countUp 0.5s ease-out',
        'float': 'float 3s ease-in-out infinite',
        'shimmer': 'shimmer 2s linear infinite',
        'gradient-shift': 'gradientShift 3s ease infinite',
        'border-glow': 'borderGlow 2s ease-in-out infinite',
        'warrior-pulse': 'warriorPulse 2s ease-in-out infinite',
        'spin-slow': 'spin 8s linear infinite',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 5px rgba(245, 158, 11, 0.3)' },
          '100%': { boxShadow: '0 0 25px rgba(245, 158, 11, 0.6)' },
        },
        glowGold: {
          '0%': { boxShadow: '0 0 5px rgba(255, 215, 0, 0.4), 0 0 10px rgba(255, 215, 0, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(255, 215, 0, 0.8), 0 0 40px rgba(255, 215, 0, 0.4)' },
        },
        glowImperial: {
          '0%': { boxShadow: '0 0 5px rgba(0, 245, 255, 0.35), 0 0 10px rgba(0, 245, 255, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(0, 245, 255, 0.7), 0 0 40px rgba(0, 245, 255, 0.35)' },
        },
        glowProfit: {
          '0%': { boxShadow: '0 0 5px rgba(255, 215, 0, 0.4)' },
          '100%': { boxShadow: '0 0 20px rgba(255, 215, 0, 0.8)' },
        },
        glowLoss: {
          '0%': { boxShadow: '0 0 5px rgba(239, 68, 68, 0.4)' },
          '100%': { boxShadow: '0 0 20px rgba(239, 68, 68, 0.8)' },
        },
        pulseGold: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideDown: {
          '0%': { transform: 'translateY(-20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        slideLeft: {
          '0%': { transform: 'translateX(20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        slideRight: {
          '0%': { transform: 'translateX(-20px)', opacity: '0' },
          '100%': { transform: 'translateX(0)', opacity: '1' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(30px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shake: {
          '10%, 90%': { transform: 'translate3d(-1px, 0, 0)' },
          '20%, 80%': { transform: 'translate3d(2px, 0, 0)' },
          '30%, 50%, 70%': { transform: 'translate3d(-3px, 0, 0)' },
          '40%, 60%': { transform: 'translate3d(3px, 0, 0)' },
        },
        countUp: {
          '0%': { transform: 'translateY(100%)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        borderGlow: {
          '0%, 100%': { borderColor: 'rgba(245, 158, 11, 0.5)' },
          '50%': { borderColor: 'rgba(255, 215, 0, 1)' },
        },
        warriorPulse: {
          '0%, 100%': {
            transform: 'scale(1)',
            boxShadow: '0 0 0 0 rgba(245, 158, 11, 0.4)'
          },
          '50%': {
            transform: 'scale(1.02)',
            boxShadow: '0 0 20px 10px rgba(245, 158, 11, 0)'
          },
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-conic': 'conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))',
        'gradient-dark': 'linear-gradient(to bottom, #141d2b, #0a0e17)',
        'gradient-falange': 'linear-gradient(135deg, #FF8C00 0%, #00F5FF 50%, #FF8C00 100%)',
        'gradient-gold': 'linear-gradient(135deg, #FFD700 0%, #FF8C00 50%, #CD7F32 100%)',
        'gradient-imperial': 'linear-gradient(135deg, #00F5FF 0%, #7DFBFF 50%, #00F5FF 100%)',
        'gradient-warrior': 'linear-gradient(180deg, rgba(255,140,0,0.12) 0%, rgba(0,245,255,0.12) 50%, rgba(10,14,23,1) 100%)',
        'gradient-card': 'linear-gradient(180deg, rgba(20,29,43,0.84) 0%, rgba(10,14,23,0.94) 100%)',
        'shimmer-gold': 'linear-gradient(90deg, transparent 0%, rgba(255,215,0,0.3) 50%, transparent 100%)',
      },
      boxShadow: {
        'glow-gold': '0 0 20px rgba(255, 215, 0, 0.3)',
        'glow-gold-lg': '0 0 40px rgba(255, 215, 0, 0.4)',
        'glow-imperial': '0 0 20px rgba(0, 245, 255, 0.34)',
        'glow-imperial-lg': '0 0 40px rgba(0, 245, 255, 0.4)',
        'glow-profit': '0 0 15px rgba(255, 215, 0, 0.4)',
        'glow-loss': '0 0 15px rgba(239, 68, 68, 0.4)',
        'inner-gold': 'inset 0 0 20px rgba(255, 215, 0, 0.1)',
        'card': '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)',
        'card-hover': '0 10px 25px -5px rgba(0, 0, 0, 0.4), 0 8px 10px -5px rgba(0, 0, 0, 0.2)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
    },
  },
  plugins: [],
}

export default config

