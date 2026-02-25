# Piano: Broker Autodiscovery per Lottaggio e Riconoscimento Simboli

## Situazione Attuale

### Cosa funziona già (parzialmente):
1. **`_build_symbol_map()`** (metatrader_broker.py:1367) — scarica tutti i simboli del broker al connect e costruisce una mappa di lookup
2. **`_get_symbol_candidates()`** (metatrader_broker.py:1041) — scoring fuzzy per matchare i nostri simboli canonici ai nomi broker
3. **`broker_spec`** — viene già fetchato prima di ogni trade in auto_trader.py:1752 e usato per pip_value, volume constraints, SL/TP rounding

### Problemi attuali:
1. **Prefisso/suffisso non "imparati"** — `SYMBOL_ALIASES` è una lista statica di ~200 varianti hardcoded. Se un broker usa un pattern non previsto (es. `mEURUSD`, `EURUSD.std`, `EURUSD-Z`), non viene riconosciuto
2. **Pip value fallback hardcoded** — `_calculate_pip_info()` (auto_trader.py:290) ha ~50 righe di fallback hardcoded (pip_value per indici, oro, JPY, ecc.) che vengono usati quando il broker non fornisce tickValue/tickSize
3. **Nessun caching delle spec per tutti i simboli** — le spec vengono fetchate one-by-one al momento del trade, non al connect
4. **`trading_service.py`** usa `pip_value = Decimal("0.0001")` hardcoded (riga 323)
5. **Nessuna detection automatica del pattern di naming** — il bot non capisce che se il broker ha `EURUSD#` allora anche `GBPUSD#` avrà il `#`

## Piano di Implementazione

### Step 1: Broker Symbol Spec Cache (Batch Preload)
**File:** `metatrader_broker.py`

Al `connect()`, dopo `_build_symbol_map()`, precarica le specification per tutti i simboli che ci servono (quelli in SYMBOL_ALIASES + quelli configurati nel bot). Salva in `_symbol_spec_cache: dict[str, dict]`.

Nuovo metodo: `_preload_symbol_specifications(symbols: list[str])`
- Fetcha spec in batch (con rate limit awareness)
- Popola `_symbol_spec_cache`
- Espone metodo `get_cached_symbol_spec(symbol) -> dict | None`

### Step 2: Affix Pattern Autodiscovery
**File:** `metatrader_broker.py`

Dopo `_build_symbol_map()`, analizza i simboli matchati per detectare il pattern di naming del broker:

Nuovo metodo: `_detect_broker_affix_pattern()`
- Prende le coppie (canonical → broker_symbol) già risolte
- Per ogni coppia, estrae prefix e suffix (es. `EUR_USD → EURUSD#` → suffix=`#`)
- Conta la frequenza di ogni affix
- Salva il pattern dominante in `_broker_affix: dict` con `{"prefix": "", "suffix": "#"}`
- Quando `_get_symbol_candidates()` non trova match, genera candidati aggiungendo l'affix scoperto

### Step 3: Autodiscovery Pip Info dal Broker
**File:** `auto_trader.py`

Rifattorizza `_calculate_pip_info()` per usare SOLO dati broker quando disponibili e ridurre drasticamente i fallback hardcoded:

1. **Priorità 1**: `tickValue + tickSize` dal broker → pip_value esatto (già implementato)
2. **Priorità 2**: `contractSize + profitCurrency` dal broker → pip_value calcolato (già implementato)
3. **Priorità 3**: Nuova logica — usa `_symbol_spec_cache` per avere le spec anche senza fetch on-demand
4. **Rimuovi fallback hardcoded** per tutto ciò che il broker fornisce tramite spec

### Step 4: Fix `trading_service.py` Hardcoded Pip Value
**File:** `trading_service.py`

Sostituisci `pip_value = Decimal("0.0001")` con logica che usa le spec broker:
- Se il broker ha `get_symbol_specification()`, usalo
- Altrimenti fallback a pip_location dall'Instrument

### Step 5: Autodiscovery Volume Constraints
**File:** `auto_trader.py`

Nella sezione lot sizing (riga 1935-1948), le variabili `MIN_LOT`, `VOL_STEP`, `MAX_LOT_BROKER` vengono già lette dal broker_spec. Migliora questa logica:
- Usa le spec pre-cachate (Step 1) come fallback se il fetch on-demand fallisce
- Aggiungi logging più chiaro quando si usano valori dal broker vs fallback

### Step 6: Esponi Autodiscovery Info via API
**File:** `market.py` (routes)

Nuovo endpoint `GET /market/broker-discovery` che restituisce:
- Affix pattern detectato
- Simboli risolti con le loro spec
- Volume constraints per ogni simbolo
- Utile per debugging e dashboard
