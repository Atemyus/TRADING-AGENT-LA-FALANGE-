# La Falange Trading Platform

**AI-Powered CFD/Futures Trading Platform with Multi-Model Consensus**

Una piattaforma di trading professionale per CFD e Futures con analisi AI multi-modello e sistema di votazione consensus.

## Caratteristiche Principali

### Multi-AI Consensus System
- **10+ modelli AI** analizzano simultaneamente il mercato
- **Sistema di votazione** con metodi configurabili (weighted, majority, unanimous)
- **Aggregazione intelligente** di confidence, stop-loss e take-profit
- Supporto per: GPT-4o, Claude, Gemini, Groq (Llama 3.3), Mistral, Ollama

### Multi-Broker Support
- **OANDA** - Forex e CFD (implementato)
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
- Tema dark con accenti neon
- Animazioni fluide con Framer Motion
- Real-time updates via WebSocket

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
- **Recharts** per grafici

### AI Providers
| Provider | Modelli | Velocità |
|----------|---------|----------|
| OpenAI | GPT-4o, GPT-4o-mini | Medio |
| Anthropic | Claude Sonnet, Haiku | Medio |
| Google | Gemini Flash, Pro | Veloce |
| Groq | Llama 3.3 70B | Ultra-veloce |
| Mistral | Large, Small | Medio |
| Ollama | Qualsiasi | Locale/Gratis |

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker (opzionale)

### Con Docker

```bash
docker-compose up -d
```

### Sviluppo Locale

```bash
# Backend
cd apps/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload

# Frontend
cd apps/frontend
npm install
npm run dev
```

### Configurazione

Copia `.env.example` in `.env` e configura:

```env
# Broker
OANDA_API_KEY=your-api-key
OANDA_ACCOUNT_ID=your-account-id

# AI Providers (almeno uno richiesto)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GROQ_API_KEY=gsk_...

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/trading_db
```

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

## Struttura Progetto

```
├── apps/
│   ├── backend/          # FastAPI backend
│   │   └── src/
│   │       ├── api/      # REST endpoints
│   │       ├── engines/  # Trading, AI, Data engines
│   │       ├── services/ # Business logic
│   │       └── core/     # Config, database
│   └── frontend/         # Next.js frontend
│       └── src/
│           ├── app/      # Pages (App Router)
│           └── components/
├── docker/               # Docker configs
├── docs/                 # Documentazione
└── scripts/              # Utility scripts
```

## Roadmap

- [x] **Fase 0**: Foundation & Setup
- [x] **Fase 1**: Core Trading Engine (OANDA)
- [x] **Fase 2**: AI Engine (Multi-AI Consensus)
- [ ] **Fase 3**: Dashboard UI
- [ ] **Fase 4**: Risk Management Avanzato
- [ ] **Fase 5**: Backtesting & Paper Trading
- [ ] **Fase 6**: Multi-Broker Expansion

Vedi [ROADMAP.md](ROADMAP.md) per i dettagli completi.

## Licenza

MIT License - vedi [LICENSE](LICENSE)
