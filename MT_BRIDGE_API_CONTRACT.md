# MetaTrader Bridge API Contract (MVP)

Questo documento descrive il contratto minimo che il nodo bridge MT4/MT5 deve esporre per essere compatibile con `MetaTraderBridgeBroker`.

## Auth
- Header opzionale:
  - `Authorization: Bearer <MT_BRIDGE_API_KEY>`
  - `X-Bridge-Key: <MT_BRIDGE_API_KEY>`

## 1) Connect Session
- `POST /api/v1/sessions/connect`
- Body:
```json
{
  "platform": "mt5",
  "login": "12345678",
  "account_number": "12345678",
  "password": "secret",
  "server": "Broker-Server",
  "server_name": "Broker-Server",
  "terminal_path": "C:\\MT5\\terminal64.exe",
  "data_path": "C:\\MT5\\Profiles\\node-1",
  "workspace_id": "workspace-42"
}
```
- Response:
```json
{
  "session_id": "sess_abc123"
}
```

## 2) Disconnect Session
- `POST /api/v1/sessions/{session_id}/disconnect`

## 3) Account Info
- `GET /api/v1/sessions/{session_id}/account`
- Response example:
```json
{
  "accountId": "12345678",
  "balance": 10234.55,
  "equity": 10110.21,
  "margin": 340.0,
  "freeMargin": 9770.21,
  "profit": -124.34,
  "currency": "USD",
  "leverage": 100
}
```

## 4) Positions
- `GET /api/v1/sessions/{session_id}/positions`
- Response: array
```json
[
  {
    "position_id": "987654",
    "symbol": "EURUSD",
    "side": "buy",
    "volume": 0.1,
    "open_price": 1.08234,
    "current_price": 1.08310,
    "profit": 7.6,
    "margin": 25.0,
    "stop_loss": 1.07950,
    "take_profit": 1.08700,
    "opened_at": "2026-02-13T10:00:00Z"
  }
]
```

## 5) Place Order
- `POST /api/v1/sessions/{session_id}/orders`
- Body:
```json
{
  "symbol": "EURUSD",
  "side": "buy",
  "order_type": "market",
  "volume": 0.1,
  "time_in_force": "gtc",
  "stop_loss": 1.0795,
  "take_profit": 1.087
}
```

## 6) Open Orders
- `GET /api/v1/sessions/{session_id}/orders/open`

## 7) Get One Order
- `GET /api/v1/sessions/{session_id}/orders/{order_id}`

## 8) Cancel Order
- `DELETE /api/v1/sessions/{session_id}/orders/{order_id}`

## 9) Close Position
- `POST /api/v1/sessions/{session_id}/positions/close`
- Body:
```json
{
  "symbol": "EURUSD",
  "volume": 0.1
}
```

## 10) Modify Position (SL/TP)
- `POST /api/v1/sessions/{session_id}/positions/modify`
- Body:
```json
{
  "symbol": "EURUSD",
  "stop_loss": 1.08,
  "take_profit": 1.09
}
```

## 11) Price
- `GET /api/v1/sessions/{session_id}/prices/{symbol}`
- Response:
```json
{
  "symbol": "EURUSD",
  "bid": 1.08234,
  "ask": 1.08245,
  "timestamp": "2026-02-13T10:01:00Z"
}
```

## 12) Candles
- `GET /api/v1/sessions/{session_id}/candles/{symbol}?timeframe=M5&count=100`
- Response: array
```json
[
  {
    "symbol": "EURUSD",
    "timestamp": "2026-02-13T10:00:00Z",
    "open": 1.0821,
    "high": 1.0826,
    "low": 1.0819,
    "close": 1.0824,
    "volume": 1234
  }
]
```

## Note
- Il backend supporta override endpoint tramite credentials (`mt_bridge_*_endpoint`).
- Il bridge deve restituire HTTP >=400 in caso di errore, con messaggio breve in body.
