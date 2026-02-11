export type LegionModel = {
  id: string
  name: string
  logoSrc: string
  logoAlt: string
  accentClass: string
  visible: boolean
}

export const LEGION_MODELS: LegionModel[] = [
  {
    id: 'chatgpt',
    name: 'ChatGPT',
    logoSrc: '/images/ai-logos/chatgpt.svg',
    logoAlt: 'ChatGPT logo',
    accentClass: 'from-emerald-500/25 to-emerald-700/20 border-emerald-400/40',
    visible: true,
  },
  {
    id: 'gemini',
    name: 'Gemini',
    logoSrc: '/images/ai-logos/gemini.svg',
    logoAlt: 'Gemini logo',
    accentClass: 'from-blue-500/25 to-cyan-600/20 border-blue-400/40',
    visible: true,
  },
  {
    id: 'grok',
    name: 'Grok',
    logoSrc: '/images/ai-logos/grok.svg',
    logoAlt: 'Grok logo',
    accentClass: 'from-zinc-500/30 to-slate-700/25 border-zinc-300/35',
    visible: true,
  },
  {
    id: 'qwen',
    name: 'Qwen',
    logoSrc: '/images/ai-logos/qwen.svg',
    logoAlt: 'Qwen logo',
    accentClass: 'from-orange-500/25 to-amber-700/20 border-orange-400/40',
    visible: true,
  },
  {
    id: 'llama',
    name: 'Llama',
    logoSrc: '/images/ai-logos/llama.svg',
    logoAlt: 'Llama logo',
    accentClass: 'from-sky-500/25 to-blue-700/20 border-sky-400/40',
    visible: true,
  },
  {
    id: 'ernie',
    name: 'ERNIE',
    logoSrc: '/images/ai-logos/ernie.svg',
    logoAlt: 'ERNIE logo',
    accentClass: 'from-rose-500/25 to-red-700/20 border-rose-400/40',
    visible: true,
  },
  {
    id: 'kimi',
    name: 'Kimi',
    logoSrc: '/images/ai-logos/kimi.svg',
    logoAlt: 'Kimi logo',
    accentClass: 'from-teal-500/25 to-cyan-700/20 border-teal-400/40',
    visible: false,
  },
  {
    id: 'mistral',
    name: 'Mistral',
    logoSrc: '/images/ai-logos/mistral.svg',
    logoAlt: 'Mistral logo',
    accentClass: 'from-amber-500/25 to-yellow-700/20 border-amber-400/40',
    visible: true,
  },
]
