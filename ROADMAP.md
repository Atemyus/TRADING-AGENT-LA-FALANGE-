# ROADMAP - Trading Platform CFD/Futures

> **Progetto:** Prometheus Trading Platform
> **Versione:** 2.0 (Ristrutturazione Completa)
> **Obiettivo:** Piattaforma di trading automatizzato per CFD/Futures con focus su Intraday/Scalping
> **Data Creazione:** 21 Dicembre 2024

---

## EXECUTIVE SUMMARY

### Stato Attuale
Il progetto attuale è un trading bot per criptovalute su Hyperliquid, funzionante ma con limitazioni architetturali significative per gli obiettivi futuri.

### Visione Futura
Trasformazione in una **piattaforma di trading professionale** per CFD/Futures con:
- Dashboard real-time moderna e animata
- Supporto multi-broker
- AI-driven decision making avanzato
- Backtesting integrato
- Risk management professionale

### Cambiamenti Chiave

| Aspetto | PRIMA | DOPO |
|---------|-------|------|
| **Mercato** | Crypto (Hyperliquid) | CFD/Futures (Multi-broker) |
| **Stile** | Position trading | Intraday/Scalping |
| **Timeframe** | 15 minuti | 1m - 15m |
| **Frontend** | Nessuno | Dashboard React moderna |
| **Architettura** | Monolitica | Microservizi |
| **Real-time** | Polling | WebSocket |
| **Backtesting** | Nessuno | Engine completo |

---

## ANALISI TECNICA PROGETTO ATTUALE

### Componenti Esistenti da Preservare (Logica)

| File | Funzione | Azione |
|------|----------|--------|
| `trading_agent.py` | AI Decision Making | Evolvere in AI Engine |
| `indicators.py` | Analisi Tecnica | Espandere indicatori |
| `sentiment.py` | Market Sentiment | Mantenere + nuove fonti |
| `news_feed.py` | News Aggregation | Mantenere + nuove fonti |
| `forecaster.py` | ML Predictions | Ottimizzare per scalping |
| `db_utils.py` | Database Layer | Migrare a SQLAlchemy |

### Componenti da Sostituire

| File | Motivo | Sostituzione |
|------|--------|--------------|
| `hyperliquid_trader.py` | Specifico per crypto | Broker abstraction layer |
| `main.py` | Monolitico | FastAPI application |
| `utils.py` | Generico | Utilities strutturate |

### Limitazioni Critiche Attuali

1. **Nessuna Dashboard** - Zero visibilità real-time
2. **Single Exchange** - Lock-in su Hyperliquid
3. **Timeframe Lento** - 15min inadatto per scalping
4. **No WebSocket** - Latenza troppo alta
5. **No Backtesting** - Impossibile validare strategie
6. **Testing Minimo** - Rischioso in produzione
7. **Config Hardcoded** - Poco flessibile

---

## STACK TECNOLOGICO TARGET

### Backend
```
Framework:      FastAPI (Python 3.11+)
Database:       PostgreSQL + TimescaleDB (time-series)
Cache:          Redis
Task Queue:     Celery + Redis
WebSocket:      FastAPI WebSocket / Socket.IO
ORM:            SQLAlchemy 2.0
Validation:     Pydantic v2
```

### Frontend
```
Framework:      Next.js 14 (App Router)
Language:       TypeScript
Styling:        Tailwind CSS
Animations:     Framer Motion
Charts:         TradingView Lightweight Charts
State:          Zustand / TanStack Query
Real-time:      WebSocket native
```

### Infrastructure
```
Containerization:   Docker + Docker Compose
CI/CD:              GitHub Actions
Hosting:            Railway / Vercel / VPS
Monitoring:         Grafana + Prometheus
Error Tracking:     Sentry
```

### AI/ML
```
LLM:            OpenAI GPT-4o / GPT-4o-mini
Local LLM:      Ollama (fallback)
ML Framework:   Prophet, scikit-learn
```

---

## ARCHITETTURA TARGET

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                 │
│                    Next.js 14 + TypeScript                       │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐       │
│  │ Dashboard │ │  Charts   │ │ Positions │ │ Analytics │       │
│  └───────────┘ └───────────┘ └───────────┘ └───────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ REST API + WebSocket
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY                                 │
│                   FastAPI + Authentication                       │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│   TRADING     │   │   DATA          │   │   AI          │
│   ENGINE      │   │   ENGINE        │   │   ENGINE      │
│ ────────────  │   │ ──────────────  │   │ ────────────  │
│ • Broker API  │   │ • Market Data   │   │ • GPT-4o      │
│ • Orders      │   │ • Indicators    │   │ • Strategies  │
│ • Positions   │   │ • News/Sent.    │   │ • Signals     │
│ • Risk Mgmt   │   │ • Forecasting   │   │ • Analysis    │
└───────┬───────┘   └────────┬────────┘   └───────┬───────┘
        │                    │                    │
        └─────────────────────┼─────────────────────┘
                              ▼
                 ┌─────────────────────┐
                 │   MESSAGE QUEUE     │
                 │   Redis + Celery    │
                 └──────────┬──────────┘
                            ▼
        ┌─────────────────────────────────────────┐
        │              DATABASE LAYER              │
        │  ┌─────────────┐    ┌─────────────┐     │
        │  │ PostgreSQL  │    │   Redis     │     │
        │  │ TimescaleDB │    │   Cache     │     │
        │  └─────────────┘    └─────────────┘     │
        └─────────────────────────────────────────┘
```

---

## STRUTTURA DIRECTORY TARGET

```
trading-platform/
│
├── apps/
│   ├── backend/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   │   ├── v1/
│   │   │   │   │   ├── routes/
│   │   │   │   │   │   ├── auth.py
│   │   │   │   │   │   ├── trading.py
│   │   │   │   │   │   ├── positions.py
│   │   │   │   │   │   ├── analytics.py
│   │   │   │   │   │   └── websocket.py
│   │   │   │   │   └── __init__.py
│   │   │   │   └── deps.py
│   │   │   │
│   │   │   ├── core/
│   │   │   │   ├── config.py
│   │   │   │   ├── security.py
│   │   │   │   └── exceptions.py
│   │   │   │
│   │   │   ├── engines/
│   │   │   │   ├── trading/
│   │   │   │   │   ├── base_broker.py
│   │   │   │   │   ├── oanda_broker.py
│   │   │   │   │   ├── ig_broker.py
│   │   │   │   │   ├── order_manager.py
│   │   │   │   │   └── risk_manager.py
│   │   │   │   │
│   │   │   │   ├── data/
│   │   │   │   │   ├── market_data.py
│   │   │   │   │   ├── indicators.py
│   │   │   │   │   ├── news_feed.py
│   │   │   │   │   ├── sentiment.py
│   │   │   │   │   └── forecaster.py
│   │   │   │   │
│   │   │   │   └── ai/
│   │   │   │       ├── agent.py
│   │   │   │       ├── strategies.py
│   │   │   │       ├── prompts.py
│   │   │   │       └── models.py
│   │   │   │
│   │   │   ├── models/
│   │   │   │   ├── user.py
│   │   │   │   ├── trade.py
│   │   │   │   ├── position.py
│   │   │   │   └── signal.py
│   │   │   │
│   │   │   ├── schemas/
│   │   │   │   ├── trading.py
│   │   │   │   ├── analytics.py
│   │   │   │   └── responses.py
│   │   │   │
│   │   │   ├── services/
│   │   │   │   ├── trading_service.py
│   │   │   │   ├── analytics_service.py
│   │   │   │   └── notification_service.py
│   │   │   │
│   │   │   ├── tasks/
│   │   │   │   ├── celery_app.py
│   │   │   │   └── trading_tasks.py
│   │   │   │
│   │   │   └── main.py
│   │   │
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── conftest.py
│   │   │
│   │   ├── alembic/
│   │   │   └── versions/
│   │   │
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   └── Dockerfile
│   │
│   └── frontend/
│       ├── src/
│       │   ├── app/
│       │   │   ├── (dashboard)/
│       │   │   │   ├── page.tsx
│       │   │   │   ├── positions/
│       │   │   │   ├── analytics/
│       │   │   │   ├── settings/
│       │   │   │   └── layout.tsx
│       │   │   ├── api/
│       │   │   ├── layout.tsx
│       │   │   └── globals.css
│       │   │
│       │   ├── components/
│       │   │   ├── ui/
│       │   │   │   ├── Button.tsx
│       │   │   │   ├── Card.tsx
│       │   │   │   ├── Modal.tsx
│       │   │   │   └── ...
│       │   │   ├── charts/
│       │   │   │   ├── TradingChart.tsx
│       │   │   │   ├── EquityCurve.tsx
│       │   │   │   └── PnLChart.tsx
│       │   │   ├── dashboard/
│       │   │   │   ├── Header.tsx
│       │   │   │   ├── Sidebar.tsx
│       │   │   │   ├── PositionsTable.tsx
│       │   │   │   └── AIReasoningCard.tsx
│       │   │   └── trading/
│       │   │       ├── OrderForm.tsx
│       │   │       └── SignalCard.tsx
│       │   │
│       │   ├── hooks/
│       │   │   ├── useWebSocket.ts
│       │   │   ├── usePrices.ts
│       │   │   └── usePositions.ts
│       │   │
│       │   ├── lib/
│       │   │   ├── api.ts
│       │   │   ├── websocket.ts
│       │   │   └── utils.ts
│       │   │
│       │   ├── stores/
│       │   │   ├── tradingStore.ts
│       │   │   └── uiStore.ts
│       │   │
│       │   └── types/
│       │       └── index.ts
│       │
│       ├── public/
│       ├── package.json
│       ├── tailwind.config.ts
│       ├── tsconfig.json
│       └── Dockerfile
│
├── packages/
│   └── shared/
│       ├── types/
│       └── constants/
│
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── nginx/
│       └── nginx.conf
│
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── DEPLOYMENT.md
│
├── scripts/
│   ├── setup.sh
│   ├── seed_db.py
│   └── backtest.py
│
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
│
├── .env.example
├── .gitignore
├── README.md
└── ROADMAP.md
```

---

## FASI DI SVILUPPO

---

## FASE 0: FOUNDATION & SETUP

### Obiettivo
Preparare l'ambiente di sviluppo e la struttura base del progetto.

### Tasks

#### 0.1 Repository Setup
- [ ] Creare nuova struttura directory
- [ ] Configurare Git hooks (pre-commit)
- [ ] Setup .gitignore completo
- [ ] Creare .env.example con tutte le variabili

#### 0.2 Docker Environment
- [ ] docker-compose.yml per sviluppo
- [ ] PostgreSQL + TimescaleDB container
- [ ] Redis container
- [ ] Dockerfile per backend
- [ ] Dockerfile per frontend

#### 0.3 Backend Foundation
- [ ] Inizializzare progetto FastAPI
- [ ] Configurare pyproject.toml / requirements.txt
- [ ] Setup SQLAlchemy 2.0 + Alembic
- [ ] Configurare Pydantic settings
- [ ] Struttura base API

#### 0.4 Frontend Foundation
- [ ] Inizializzare Next.js 14 con TypeScript
- [ ] Configurare Tailwind CSS
- [ ] Setup Framer Motion
- [ ] Struttura componenti base
- [ ] Configurare ESLint + Prettier

#### 0.5 CI/CD Pipeline
- [ ] GitHub Actions workflow per test
- [ ] GitHub Actions workflow per lint
- [ ] Setup deploy automation (Railway/Vercel)

### Deliverables
- Repository strutturata e funzionante
- Ambiente Docker pronto
- CI/CD pipeline attiva
- Progetto buildabile (frontend + backend)

---

## FASE 1: CORE TRADING ENGINE

### Obiettivo
Creare il motore di trading con supporto multi-broker e risk management.

### Tasks

#### 1.1 Broker Abstraction Layer
- [ ] Definire interfaccia `BaseBroker` (ABC)
- [ ] Metodi: connect, disconnect, get_account, place_order, cancel_order
- [ ] Metodi: get_positions, get_orders, stream_prices
- [ ] Gestione errori standardizzata
- [ ] Retry logic con exponential backoff

```python
# Interfaccia target
class BaseBroker(ABC):
    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def get_account_info(self) -> AccountInfo: ...

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResult: ...

    @abstractmethod
    async def get_positions(self) -> List[Position]: ...

    @abstractmethod
    async def stream_prices(self, symbols: List[str]) -> AsyncIterator[Tick]: ...

    @abstractmethod
    async def get_historical_data(
        self, symbol: str, timeframe: str, limit: int
    ) -> pd.DataFrame: ...
```

#### 1.2 Prima Implementazione Broker
- [ ] Scegliere broker primario (OANDA consigliato)
- [ ] Implementare `OANDABroker(BaseBroker)`
- [ ] Test su paper trading account
- [ ] Documentare limitazioni e quirks

#### 1.3 Order Manager
- [ ] OrderRequest / OrderResult schemas
- [ ] Validazione ordini pre-invio
- [ ] Order state machine (pending → filled → closed)
- [ ] Logging completo ordini

#### 1.4 Risk Manager
- [ ] Position sizing calculator
- [ ] Daily drawdown limits
- [ ] Max positions limit
- [ ] Correlation checker
- [ ] Stop-loss / Take-profit automation
- [ ] Trailing stop logic

```python
# Risk Manager target
class RiskManager:
    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float,
        stop_loss_pips: float,
        pip_value: float
    ) -> float: ...

    def check_daily_limits(self, daily_pnl: float) -> bool: ...

    def check_max_positions(self, current_count: int) -> bool: ...

    def validate_order(self, order: OrderRequest, account: AccountInfo) -> ValidationResult: ...
```

### Deliverables
- Broker abstraction funzionante
- Almeno 1 broker implementato (OANDA)
- Risk manager completo
- Test coverage > 80%

---

## FASE 2: DATA ENGINE

### Obiettivo
Sistema di raccolta e processamento dati di mercato real-time.

### Tasks

#### 2.1 Market Data Service
- [ ] Price streaming via WebSocket
- [ ] Historical data fetching
- [ ] Data normalization layer
- [ ] Caching con Redis
- [ ] Rate limiting handler

#### 2.2 Technical Indicators (Espansione)
Indicatori esistenti da mantenere:
- [ ] EMA (20, 50, 200)
- [ ] MACD
- [ ] RSI (7, 14)
- [ ] ATR (3, 14)
- [ ] Pivot Points

Nuovi indicatori per Scalping:
- [ ] VWAP (Volume Weighted Average Price)
- [ ] Bollinger Bands + Squeeze Detection
- [ ] Supertrend
- [ ] Stochastic RSI
- [ ] Order Flow Delta (se disponibile)
- [ ] Market Profile (POC, VAH, VAL)

#### 2.3 News & Sentiment (Espansione)
- [ ] Mantenere Fear & Greed Index
- [ ] Aggiungere fonti news (ForexFactory, Investing.com)
- [ ] Economic calendar integration
- [ ] High-impact news alerts

#### 2.4 Forecaster Optimization
- [ ] Adattare Prophet per timeframe brevi
- [ ] Aggiungere modelli alternativi (LSTM, XGBoost)
- [ ] Ensemble predictions
- [ ] Confidence intervals calibration

### Deliverables
- Market data real-time funzionante
- 15+ indicatori tecnici
- News/sentiment multi-source
- Forecaster ottimizzato per scalping

---

## FASE 3: AI ENGINE

### Obiettivo
Evolvere il sistema decisionale AI con strategie multiple.

### Tasks

#### 3.1 Multi-Model Architecture
- [ ] Model router (seleziona modello per task)
- [ ] GPT-4o per analisi complesse
- [ ] GPT-4o-mini per task veloci
- [ ] Fallback locale (Ollama)
- [ ] Cost tracking per API calls

#### 3.2 Prompt Engineering
- [ ] Template system per prompts
- [ ] Chain-of-Thought reasoning
- [ ] Few-shot examples per pattern
- [ ] Self-consistency checking
- [ ] Structured output con function calling

#### 3.3 Strategy Templates
```python
# Strategie target
class ScalpingStrategy(BaseStrategy):
    name = "Scalping 1M"
    timeframe = "1m"
    max_hold_time = timedelta(minutes=30)
    indicators = ["VWAP", "RSI", "BB"]

class MomentumIntraday(BaseStrategy):
    name = "Momentum 5M"
    timeframe = "5m"
    max_hold_time = timedelta(hours=4)
    indicators = ["EMA", "MACD", "ATR"]

class NewsTrading(BaseStrategy):
    name = "News Reaction"
    trigger = "high_impact_news"
    entry_delay = timedelta(seconds=30)
```

#### 3.4 Signal Generation
- [ ] Signal schema (entry, exit, confidence)
- [ ] Multi-timeframe confirmation
- [ ] Signal strength scoring
- [ ] Historical signal tracking

### Deliverables
- AI Engine multi-model
- 3+ strategie implementate
- Sistema prompts modulare
- Signal generation robusto

---

## FASE 4: DASHBOARD FRONTEND

### Obiettivo
Dashboard moderna, real-time, con animazioni professionali.

### Tasks

#### 4.1 Design System
- [ ] Color palette (dark theme)
- [ ] Typography scale
- [ ] Component library base
- [ ] Animation standards
- [ ] Responsive breakpoints

#### 4.2 Core Components
- [ ] Header (balance, P&L, status)
- [ ] Sidebar navigation
- [ ] Trading chart (TradingView)
- [ ] Positions table
- [ ] Orders panel
- [ ] AI Reasoning card

#### 4.3 Real-time Features
- [ ] WebSocket connection manager
- [ ] Price streaming display
- [ ] Live P&L updates
- [ ] Position updates
- [ ] Toast notifications

#### 4.4 Animazioni
- [ ] Number counters (P&L, balance)
- [ ] Pulse effect (profit positions)
- [ ] Shake effect (risk alerts)
- [ ] Smooth transitions (page/modal)
- [ ] Loading skeletons
- [ ] Micro-interactions

#### 4.5 Analytics Views
- [ ] Equity curve chart
- [ ] Drawdown visualization
- [ ] Win/Loss distribution
- [ ] Trade history table
- [ ] Performance metrics cards

### Deliverables
- Dashboard funzionante
- Real-time updates
- Animazioni professionali
- Analytics complete

---

## FASE 5: BACKTESTING ENGINE

### Obiettivo
Sistema di backtesting per validare strategie.

### Tasks

#### 5.1 Backtester Core
- [ ] Event-driven architecture
- [ ] Historical data loader
- [ ] Strategy executor
- [ ] Trade simulator
- [ ] Slippage/commission modeling

#### 5.2 Metrics Calculator
- [ ] Total return
- [ ] Sharpe ratio
- [ ] Sortino ratio
- [ ] Max drawdown
- [ ] Win rate
- [ ] Profit factor
- [ ] Expectancy
- [ ] Recovery factor

#### 5.3 Visualization
- [ ] Equity curve
- [ ] Drawdown chart
- [ ] Trade markers on chart
- [ ] Monthly returns heatmap
- [ ] Trade distribution

#### 5.4 Optimization
- [ ] Parameter grid search
- [ ] Walk-forward analysis
- [ ] Monte Carlo simulation
- [ ] Overfitting detection

### Deliverables
- Backtester funzionante
- Metriche complete
- Visualizzazioni
- Report esportabili

---

## FASE 6: PRODUCTION & POLISH

### Obiettivo
Preparare per produzione con monitoring e sicurezza.

### Tasks

#### 6.1 Security
- [ ] JWT authentication
- [ ] API rate limiting
- [ ] Input validation completa
- [ ] Secrets management
- [ ] Audit logging

#### 6.2 Monitoring
- [ ] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Sentry error tracking
- [ ] Health check endpoints
- [ ] Alerting rules

#### 6.3 Notifications
- [ ] Telegram bot integration
- [ ] Discord webhooks
- [ ] Email alerts
- [ ] In-app notifications

#### 6.4 Documentation
- [ ] API documentation (OpenAPI)
- [ ] Architecture docs
- [ ] Deployment guide
- [ ] User guide

### Deliverables
- Sistema production-ready
- Monitoring completo
- Documentazione

---

## BROKER OPTIONS

### Raccomandazione: OANDA

| Broker | Pro | Contro | API Quality |
|--------|-----|--------|-------------|
| **OANDA** | API moderna, paper trading, docs eccellenti | No azioni | ⭐⭐⭐⭐⭐ |
| **Interactive Brokers** | Tutto, commissioni basse | API complessa, setup difficile | ⭐⭐⭐ |
| **IG Markets** | Spread bassi, molti mercati | API limitata | ⭐⭐⭐ |
| **Alpaca** | Gratuito, moderno | Solo US stocks | ⭐⭐⭐⭐ |
| **MetaTrader 5** | Standard industria | Vecchio, Python wrapper | ⭐⭐ |

### OANDA - Dettagli
- **Mercati:** Forex (70+ coppie), CFD Indici, Commodities
- **Paper Trading:** Account demo gratuito illimitato
- **API:** REST + Streaming (WebSocket-like)
- **Documentazione:** Eccellente
- **Latenza:** Buona per retail
- **Costi:** Spread-based, no commissioni

---

## METRICHE DI SUCCESSO

### Fase 0-1 (Foundation)
- [ ] Build passa senza errori
- [ ] Test coverage > 70%
- [ ] Docker compose up funzionante
- [ ] Primo trade su paper account

### Fase 2-3 (Core)
- [ ] Latenza dati < 500ms
- [ ] 15+ indicatori funzionanti
- [ ] AI response time < 5s
- [ ] 3+ strategie implementate

### Fase 4 (Dashboard)
- [ ] Lighthouse score > 90
- [ ] Real-time update < 100ms perceived
- [ ] Mobile responsive
- [ ] Tutte le animazioni smooth (60fps)

### Fase 5-6 (Production)
- [ ] Uptime > 99%
- [ ] Error rate < 1%
- [ ] Backtest su 1 anno < 5 minuti
- [ ] Documentazione completa

---

## RISCHI E MITIGAZIONI

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| API broker changes | Media | Alto | Abstraction layer, tests |
| Rate limiting | Alta | Medio | Caching, request queuing |
| AI costs elevati | Media | Medio | Caching, modelli locali |
| Latenza trading | Media | Alto | WebSocket, VPS vicino a broker |
| Overfitting strategie | Alta | Alto | Walk-forward, out-of-sample |

---

## NOTE FINALI

### Priorità Assolute
1. **Broker abstraction** - Fondamentale per flessibilità
2. **Risk management** - Non negoziabile per trading reale
3. **Testing** - Ogni componente deve essere testato
4. **Logging** - Tutto deve essere tracciabile

### Filosofia di Sviluppo
- **Iterativo:** Rilasci frequenti, feedback continuo
- **Test-first:** Scrivere test prima del codice
- **Simple first:** Iniziare semplice, complicare se necessario
- **Document as you go:** Non lasciare docs per dopo

---

*Documento creato il 21 Dicembre 2024*
*Ultima modifica: 21 Dicembre 2024*
