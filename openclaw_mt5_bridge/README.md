# OpenClaw MT5 Bridge (Infrastructure Layer)

This service is **bridge infrastructure only**:
- MT5 EA/local writer produces files in `C:/MT5BridgeData`
- This bridge reads/normalizes files and exposes APIs
- OpenClaw remains the decision brain

## Core existing endpoints (unchanged)
- `GET /health`
- `GET /account`
- `GET /positions`
- `POST /order`

## New data endpoints
- `GET /symbols`
- `GET /market_bridge/latest`
- `GET /price/{symbol}`
- `GET /history/{symbol}?tf=M1&hours=6&limit=360`
- `POST /multi-history`

## New signal endpoints
- `POST /signal`
- `GET /signal/latest/{symbol}`
- `GET /signal/history/{symbol}?limit=20`

## New risk endpoint
- `POST /risk/check`

## Other existing extended endpoints
- `GET /candles`
- `GET /market_state`
- `GET /market_structure`
- `GET /config`
- `GET /config/draft`
- `POST /config/draft`
- `POST /config/apply`
- `POST /config/reset`
- `POST /close_position`
- `POST /modify_position`
- `POST /close_all_positions`
- `POST /modify_all_positions`

---

## Windows setup

```bash
pip install -r requirements.txt
# OpenClaw MT5 Bridge (FastAPI)

A beginner-friendly Windows API bridge so OpenClaw agents can call a local MetaTrader 5 terminal through HTTP.

## What this project does

- Connects to a local MT5 terminal on startup.
- Exposes HTTP endpoints to:
  - check bridge/MT5 health
  - read account info
  - read open positions
  - place buy/sell market orders
- Logs all trade requests, including `reason_payload` for structured AI reasoning.
- Rejects trading/account requests when MT5 is not connected.

---

## 1) Install Python (Windows)

1. Download Python 3.10+ from the official Python website.
2. During install, check **"Add Python to PATH"**.
3. Open **Command Prompt** and verify:

```bash
python --version
```

---

## 2) Install dependencies

From this project folder:

```bash
pip install -r requirements.txt
```

---

## 3) Configure `.env`

1. Copy `.env.example` to `.env`.
2. Fill in your broker credentials and MT5 terminal path.

Example:

```env
APP_NAME=OpenClaw-MT5-Bridge
APP_ENV=dev
APP_HOST=0.0.0.0
APP_PORT=8080

MT5_LOGIN=12345678
MT5_PASSWORD=yourpassword
MT5_SERVER=YourBroker-Server
MT5_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
MT5_TIMEOUT=10000
MT5_DEVIATION=20
MT5_MAGIC=910001
```

---

## 4) Start FastAPI server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

---

## File layout expected from MT5 local writer

```text
C:/MT5BridgeData/
  snapshots/
    JP225.jsonl
    USDJPY.jsonl
  bars/
    JP225_M1.csv
    USDJPY_M1.csv
  signals/
    latest_JP225.json
    history_JP225.jsonl
  logs/
```

### snapshots format (`*.jsonl`)
One JSON per line, newest at end.

### bars format (`*_M1.csv`)
Supported headers include:
- `time,open,high,low,close,volume,tick_volume,spread`
- or `time_utc,time_beijing,open,high,low,close,volume`

### signals format
- latest: `latest_{symbol}.json`
- history: `history_{symbol}.jsonl`

---

## Example requests

### Read latest price
```bash
curl http://127.0.0.1:8080/price/BTCUSD
```

### Read history
```bash
curl "http://127.0.0.1:8080/history/BTCUSD?tf=M1&hours=6&limit=200"
```

### Write signal
```bash
curl -X POST http://127.0.0.1:8080/signal \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSD",
    "signal": {
      "symbol": "BTCUSD",
      "side": "buy",
      "volume": 0.01,
      "reason_payload": {"source": "openclaw"}
    }
  }'
```

### Risk check
```bash
curl -X POST http://127.0.0.1:8080/risk/check \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSD","side":"buy","volume":0.01}'
```

---

## Boundary reminder
- Bridge does data I/O, normalization, storage, and hard-rule checks.
- OpenClaw does strategy, reasoning, and final trade decision.


## Symbol normalization note

Symbol names depend on the MT5 broker environment.
Examples from the current broker environment may include:
XAUUSD, XAGUSD,
XBRUSD, XTIUSD, XNGUSD,
EURUSD, USDJPY, GBPUSD, AUDUSD, USDCAD, USDCNH,
US30, US500, USTEC, US2000,
JP225, DE40, HK50, CHINA50, CHINAH, UK100,
BTCUSD, ETHUSD.

The bridge accepts common aliases such as `NAS100` / `USOIL`,
and normalizes them to the broker MT5 symbol before trading.
## 5) Verify MT5 connection

- Make sure MetaTrader 5 terminal is installed and can log in with your account.
- Keep the terminal running.
- Open:
  - `http://127.0.0.1:8080/health`

Expected format:

```json
{
  "status": "ok",
  "mt5_connected": true
}
```

---

## 6) Test endpoints

- `http://127.0.0.1:8080/health`
- `http://127.0.0.1:8080/account`
- `http://127.0.0.1:8080/positions`
- `http://127.0.0.1:8080/docs`

---

## 7) Example curl commands

### Health

```bash
curl http://127.0.0.1:8080/health
```

### Account

```bash
curl http://127.0.0.1:8080/account
```

### Positions

```bash
curl http://127.0.0.1:8080/positions
```

### Place order with reasoning

```bash
curl -X POST http://127.0.0.1:8080/order \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "EURUSD",
    "side": "buy",
    "volume": 0.01,
    "sl": 0,
    "tp": 0,
    "comment": "optional",
    "reason_payload": {
      "agent_id": "trend_agent",
      "strategy_type": "trend_following",
      "signal_source": "news",
      "confidence": 0.75,
      "reason_text": "USD weakening after dovish Fed comments"
    }
  }'
```

---

## Notes for reliability

- If MT5 is disconnected, `/account`, `/positions`, and `/order` return `503`.
- Startup tries to initialize MT5 once; monitor logs for connection status.
- Trade requests are logged with full `reason_payload` for auditability.
