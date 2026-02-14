# MT Bridge Service (Windows Node)

Servizio bridge per sessioni MT4/MT5 usato dal backend Prometheus quando `METATRADER_CONNECTION_MODE=bridge`.

## Avvio rapido

```powershell
cd apps/mt-bridge
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn src.main:app --host 0.0.0.0 --port 9000
```

## Provider mode

- `MT_BRIDGE_PROVIDER_MODE=mock`:
  - modalita sviluppo/demo, nessun terminale reale.
- `MT_BRIDGE_PROVIDER_MODE=mt5`:
  - MT5: usa libreria `MetaTrader5` e terminale MT5 sul nodo Windows.
  - MT4: usa un adapter HTTP locale (EA/plugin/agent) configurato con `MT_BRIDGE_MT4_ADAPTER_BASE_URL`.

## MT4 adapter

MT4 non ha un package Python ufficiale come MT5.
Per questo il provider MT4 delega a un adapter HTTP locale che espone API compatibili:

- `POST /api/v1/sessions/connect`
- `POST /api/v1/sessions/{session_id}/disconnect`
- `GET /api/v1/sessions/{session_id}/account`
- `GET /api/v1/sessions/{session_id}/positions`
- `POST /api/v1/sessions/{session_id}/orders`
- `GET /api/v1/sessions/{session_id}/orders/open`
- `GET /api/v1/sessions/{session_id}/orders/{order_id}`
- `DELETE /api/v1/sessions/{session_id}/orders/{order_id}`
- `POST /api/v1/sessions/{session_id}/positions/close`
- `POST /api/v1/sessions/{session_id}/positions/modify`
- `GET /api/v1/sessions/{session_id}/prices/{symbol}`
- `GET /api/v1/sessions/{session_id}/candles/{symbol}`

Variabili utili:

- `MT_BRIDGE_MT4_ADAPTER_BASE_URL=http://127.0.0.1:9100`
- `MT_BRIDGE_MT4_ADAPTER_API_KEY=...` (opzionale)
- `MT_BRIDGE_MT4_ADAPTER_TIMEOUT_SECONDS=20`

## MT5 auto server discovery

Per MT5 il `server` puo essere opzionale nel payload di connect.

- `MT_BRIDGE_MT5_AUTO_SERVER_DISCOVERY=true`:
  - tenta login con server esplicito (se fornito)
  - poi tenta login senza server (account/server gia noti nel terminale)
  - poi prova eventuali candidati
- `MT_BRIDGE_MT5_SERVER_CANDIDATES=Broker-Live,Broker-Demo` (opzionale, fallback globale)

Nel payload `POST /api/v1/sessions/connect` puoi anche passare:
- `server_candidates: ["Broker-Live", "Broker-Demo"]`

## Auto launch terminale (opzionale)

Se vuoi che il bridge avvii automaticamente il terminale quando arriva una `connect`:

- `MT_BRIDGE_TERMINAL_AUTO_LAUNCH=true`
- `MT_BRIDGE_TERMINAL_SHUTDOWN_ON_DISCONNECT=true`
- `MT_BRIDGE_TERMINAL_LAUNCH_TIMEOUT_SECONDS=10`
- `MT_BRIDGE_TERMINAL_DEFAULT_ARGUMENTS=` (argomenti opzionali)

Con auto-launch attivo:

- il terminale viene avviato solo se `terminal_path` e presente nel payload di connect
- PID del terminale viene esposto in `GET /api/v1/sessions`
- in disconnect il processo viene chiuso se `MT_BRIDGE_TERMINAL_SHUTDOWN_ON_DISCONNECT=true`

## Endpoint principali

- `POST /api/v1/sessions/connect`
- `POST /api/v1/sessions/{session_id}/disconnect`
- `GET /api/v1/sessions/{session_id}/account`
- `GET /api/v1/sessions/{session_id}/positions`
- `POST /api/v1/sessions/{session_id}/orders`
- `GET /api/v1/sessions/{session_id}/orders/open`
- `GET /api/v1/sessions/{session_id}/orders/{order_id}`
- `DELETE /api/v1/sessions/{session_id}/orders/{order_id}`
- `POST /api/v1/sessions/{session_id}/positions/close`
- `POST /api/v1/sessions/{session_id}/positions/modify`
- `GET /api/v1/sessions/{session_id}/prices/{symbol}`
- `GET /api/v1/sessions/{session_id}/candles/{symbol}`
- `GET /api/v1/sessions`
- `GET /api/v1/health`

Per payload/response usa `MT_BRIDGE_API_CONTRACT.md` in root.
