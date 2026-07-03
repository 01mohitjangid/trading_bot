# Trading Bot — Binance USDT-M Futures Testnet

A small, well-structured Python trading bot that places orders on the
[Binance Futures Testnet](https://testnet.binancefuture.com) (USDT-M), with a
clean client/CLI separation, structured logging, and robust error handling.

Built incrementally in **4 steps**:

| Step | Status | Scope |
|------|--------|-------|
| **1. Foundation & Infrastructure** | ✅ Done | Config/secrets, logging, exceptions, signed REST client, connectivity check |
| **2. Validation & Order Domain** | ⬜ Planned | Exchange filters, input validators, MARKET/LIMIT order service |
| **3. CLI & UX** | ⬜ Planned | Typer CLI, request/response output, end-to-end orders |
| **4. Bonus, Tests & Deliverables** | ⬜ Planned | Bonus order type, unit tests, full docs, sample logs |

---

## Project structure (so far)

```
Trading/
├── bot/
│   ├── __init__.py
│   ├── config.py          # Settings & secret loading
│   ├── logging_config.py  # Console + rotating-file logging
│   ├── exceptions.py      # Custom exception hierarchy
│   ├── client.py          # Signed Binance REST client wrapper
│   └── healthcheck.py     # Connectivity smoke test
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup

1. **Create and activate a virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**

   Register at <https://testnet.binancefuture.com>, generate an API key/secret,
   then:

   ```bash
   cp .env.example .env
   # edit .env and paste your BINANCE_API_KEY / BINANCE_API_SECRET
   ```

## Verify the foundation (Step 1)

```bash
python -m bot.healthcheck
```

Expected output (with credentials configured):

```
✓ Ping OK
✓ Server time: 1751558400000
✓ USDT balance: 15000.00000000 (available: 15000.00000000)

Step 1 foundation is working. ✅
```

Without credentials it still verifies connectivity (ping + server time) and
skips the balance check. All requests, responses, and errors are logged to
`logs/trading_bot.log`.

## Design notes / assumptions

- **Direct REST over `requests`** (not `python-binance`) for full control of
  signing, logging, and error translation.
- **Secrets via environment** (`.env`, gitignored) — never committed.
- **Requests are signed** with HMAC-SHA256; secrets are never logged and the
  signature is masked in logs.
- **One exception hierarchy** (`TradingBotError` and subclasses) so callers can
  distinguish config vs. validation vs. network vs. Binance-side failures.
