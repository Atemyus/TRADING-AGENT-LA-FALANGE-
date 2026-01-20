# La Falange Trading Platform

**AI-Powered CFD/Futures Trading Platform with Multi-Model Consensus**

Una piattaforma di trading professionale per CFD e Futures con analisi AI multi-modello, sistema di votazione consensus, e grafici TradingView.

## Caratteristiche Principali

### Multi-AI Consensus System
- **10+ modelli AI** analizzano simultaneamente il mercato
- **Sistema di votazione** con metodi configurabili (weighted, majority, unanimous)
- **Aggregazione intelligente** di confidence, stop-loss e take-profit
- Supporto per: GPT-4o, Claude, Gemini, Groq (Llama 3.3), Mistral, Ollama

### Multi-Broker Support
- **OANDA** - Forex e CFD (implementato)
- **MetaTrader 4/5** - via MetaApi.cloud (implementato)
- **IG Markets** - CFD globali (prossimamente)
- **Interactive Brokers** - Futures e opzioni (prossimamente)
- **Alpaca** - Azioni US (prossimamente)

### Analisi Tecnica Avanzata
- 15+ indicatori tecnici (RSI, MACD, Bollinger, Supertrend, ecc.)
- Supporto multi-timeframe
- Identificazione automatica supporti/resistenze
- Integrazione Alpha Vantage per dati di mercato

### Dashboard Moderna
- Next.js 14 con App Router
- **Grafici candlestick TradingView** interattivi
- Tema dark con accenti neon
- Animazioni fluide con Framer Motion
- Real-time updates via WebSocket
- Pagina dedicata AI Analysis

## Tech Stack

### Backend
- **FastAPI** (Python 3.11+)
- **SQLAlchemy 2.0** con PostgreSQL
- **Redis** per caching
- **Celery** per task asincroni

### Frontend
- **Next.js 14** con TypeScript
- **Tailwind CSS** per styling
- **Framer Motion** per animazioni
- **TradingView Lightweight Charts** per grafici candlestick
- **Recharts** per grafici performance

### AI Providers
| Provider | Modelli | Velocità | Costo |
|----------|---------|----------|-------|
| OpenAI | GPT-4o, GPT-4o-mini | Medio | $$ |
| Anthropic | Claude Sonnet, Haiku | Medio | $$ |
| Google | Gemini Flash, Pro | Veloce | $ |
| Groq | Llama 3.3 70B | Ultra-veloce | $ |
| Mistral | Large, Small | Medio | $ |
| Ollama | Qualsiasi modello | Locale | GRATIS |

---

## Deployment Guide

### Opzione 1: Docker (Consigliato per Produzione)

```bash
# 1. Clona il repository
git clone https://github.com/yourusername/la-falange-trading.git
cd la-falange-trading

# 2. Copia e configura l'environment
cp .env.example .env
nano .env  # Configura le tue API keys

# 3. Avvia con Docker Compose
docker-compose up -d

# 4. Verifica lo status
docker-compose ps
docker-compose logs -f
```

La piattaforma sarà disponibile su:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### Opzione 2: Sviluppo Locale

#### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

#### Backend Setup

```bash
cd apps/backend

# Crea virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oppure: venv\Scripts\activate  # Windows

# Installa dipendenze
pip install -r requirements.txt

# Crea database
createdb trading_db

# Avvia il server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup

```bash
cd apps/frontend

# Installa dipendenze
npm install

# Avvia in development
npm run dev

# Oppure build per produzione
npm run build
npm start
```

### Opzione 3: Cloud Deployment

#### Vercel (Frontend)

```bash
# 1. Installa Vercel CLI
npm i -g vercel

# 2. Deploy
cd apps/frontend
vercel

# 3. Configura environment variables su Vercel Dashboard
NEXT_PUBLIC_API_URL=https://your-backend-url.com
```

#### Railway / Render (Backend)

1. Connetti il repository GitHub
2. Seleziona `apps/backend` come root directory
3. Configura le environment variables
4. Deploy automatico su ogni push

#### DigitalOcean / AWS

```bash
# Usa Docker su un VPS
ssh user@your-server
git clone https://github.com/yourusername/la-falange-trading.git
cd la-falange-trading
docker-compose -f docker-compose.prod.yml up -d
```

---

## API Keys Necessarie

### Obbligatorie (almeno una)

#### 1. Broker (scegli uno)

**OANDA** (Consigliato per iniziare)
```env
BROKER_TYPE=oanda
OANDA_API_KEY=your-api-key
OANDA_ACCOUNT_ID=your-account-id
OANDA_ENVIRONMENT=practice  # practice per demo, live per reale
```
- Registrati su: https://www.oanda.com
- Crea un account Practice (demo) gratuito
- Vai su "Manage API Access" per generare l'API key

**MetaTrader 4/5** (via MetaApi.cloud)
```env
BROKER_TYPE=metatrader
METAAPI_ACCESS_TOKEN=your-metaapi-token
METAAPI_ACCOUNT_ID=your-metaapi-account-id
```
- Registrati su: https://metaapi.cloud
- Connetti il tuo account MT4/MT5 esistente
- Ottieni access token e account ID dalla dashboard

#### 2. AI Provider (almeno uno)

**OpenAI** (GPT-4o)
```env
OPENAI_API_KEY=sk-your-openai-api-key
```
- Registrati su: https://platform.openai.com
- Crea API key in "API Keys"
- Costo: ~$0.01-0.03 per analisi

**Anthropic** (Claude)
```env
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key
```
- Registrati su: https://console.anthropic.com
- Crea API key
- Costo: ~$0.01-0.02 per analisi

**Groq** (Llama 3.3 - Ultra veloce!)
```env
GROQ_API_KEY=gsk_your-groq-api-key
```
- Registrati su: https://console.groq.com
- API key gratuita con limiti generosi
- Costo: GRATIS (rate limited)

**Google Gemini**
```env
GOOGLE_API_KEY=your-google-api-key
```
- Vai su: https://makersuite.google.com/app/apikey
- Genera API key
- Costo: Free tier disponibile

**Mistral**
```env
MISTRAL_API_KEY=your-mistral-api-key
```
- Registrati su: https://console.mistral.ai
- Costo: ~$0.002-0.02 per analisi

**Ollama** (Locale - GRATIS)
```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
```
- Installa: https://ollama.ai
- Esegui: `ollama pull llama3.1:8b`
- Costo: GRATIS (usa la tua GPU/CPU)

### Opzionali

**Alpha Vantage** (Dati di mercato extra)
```env
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-api-key
```
- Registrati su: https://www.alphavantage.co/support/#api-key
- Free tier: 25 richieste/giorno

**Notifiche Telegram**
```env
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id
```
1. Cerca @BotFather su Telegram
2. Crea un nuovo bot con /newbot
3. Ottieni il token
4. Avvia il bot e ottieni chat_id da @userinfobot

**Notifiche Discord**
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```
- Server Settings > Integrations > Webhooks > New Webhook

---

## Configurazione Minima

Per iniziare rapidamente, hai bisogno solo di:

```env
# .env minimo
BROKER_TYPE=oanda
OANDA_API_KEY=your-key
OANDA_ACCOUNT_ID=your-account
OANDA_ENVIRONMENT=practice

# Almeno un AI provider
GROQ_API_KEY=gsk_your-key  # Gratis e velocissimo!

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trading_db
REDIS_URL=redis://localhost:6379/0
```

---

## API Endpoints

### AI Analysis
- `POST /api/v1/ai/analyze` - Analisi multi-AI con consensus
- `GET /api/v1/ai/status` - Status dei provider
- `GET /api/v1/ai/health` - Health check

### Trading
- `POST /api/v1/trading/orders` - Crea ordine
- `GET /api/v1/positions` - Lista posizioni
- `POST /api/v1/trading/close/{symbol}` - Chiudi posizione

### Market Data
- `GET /api/v1/trading/price/{symbol}` - Prezzo corrente
- `GET /api/v1/analytics/indicators/{symbol}` - Indicatori tecnici

---

## Struttura Progetto

```
├── apps/
│   ├── backend/              # FastAPI backend
│   │   └── src/
│   │       ├── api/          # REST endpoints
│   │       ├── engines/      # Trading, AI, Data engines
│   │       │   ├── ai/       # AI providers + consensus
│   │       │   ├── trading/  # Broker implementations
│   │       │   └── data/     # Market data sources
│   │       ├── services/     # Business logic
│   │       └── core/         # Config, database
│   └── frontend/             # Next.js frontend
│       └── src/
│           ├── app/          # Pages (App Router)
│           │   ├── (dashboard)/
│           │   │   ├── page.tsx        # Dashboard principale
│           │   │   ├── ai-analysis/    # Pagina AI Analysis
│           │   │   └── settings/       # Impostazioni
│           └── components/
│               ├── charts/   # TradingView, Performance
│               ├── ai/       # AI Consensus Panel
│               └── trading/  # Positions, Orders, Ticker
├── docker/                   # Docker configs
├── docs/                     # Documentazione
└── scripts/                  # Utility scripts
```

---

## Roadmap

- [x] **Fase 0**: Foundation & Setup
- [x] **Fase 1**: Core Trading Engine (OANDA)
- [x] **Fase 2**: AI Engine (Multi-AI Consensus)
- [x] **Fase 3**: Dashboard UI + TradingView Charts
- [ ] **Fase 4**: Risk Management Avanzato
- [ ] **Fase 5**: Backtesting & Paper Trading
- [ ] **Fase 6**: Multi-Broker Expansion

---

## Troubleshooting

### Il frontend non si connette al backend
```bash
# Verifica che NEXT_PUBLIC_API_URL sia corretto
echo $NEXT_PUBLIC_API_URL

# Verifica CORS nel backend
# In config.py: CORS_ORIGINS deve includere l'URL del frontend
```

### Errore "No AI providers configured"
Assicurati di avere almeno una API key configurata:
```bash
# Verifica le variabili d'ambiente
env | grep -E "(OPENAI|ANTHROPIC|GROQ|GOOGLE|MISTRAL)_API_KEY"
```

### Database connection refused
```bash
# Verifica che PostgreSQL sia in esecuzione
pg_isready -h localhost -p 5432

# Crea il database se non esiste
createdb trading_db
```

---

## Licenza

MIT License - vedi [LICENSE](LICENSE)
