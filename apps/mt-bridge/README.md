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
  - usa libreria `MetaTrader5` e terminale MT5 sul nodo Windows.

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
- `GET /api/v1/health`

Per payload/response usa `MT_BRIDGE_API_CONTRACT.md` in root.
