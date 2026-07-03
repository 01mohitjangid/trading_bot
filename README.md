# Trading Bot — Binance USDT-M Futures Testnet

A small, well-structured Python trading bot that places orders on the
[Binance Futures Testnet](https://testnet.binancefuture.com) (USDT-M), with a
clean client/CLI separation, structured logging, and robust error handling.

Built incrementally in **4 steps**:

| Step | Status | Scope |
|------|--------|-------|
| **1. Foundation & Infrastructure** | ✅ Done | Config/secrets, logging, exceptions, signed REST client, connectivity check |
| **2. Validation & Order Domain** | ✅ Done | Exchange filters, input validators, MARKET/LIMIT order service |
| **3. CLI & UX** | ✅ Done | Typer CLI, request/response output, `--dry-run`, end-to-end orders |
| **4. Bonus, Tests & Deliverables** | ⬜ Planned | Bonus order type, unit tests, full docs, sample logs |

---

## Project structure (so far)

```
Trading/
├── bot/
│   ├── __init__.py
│   ├── config.py          # Settings & secret loading            (Step 1)
│   ├── logging_config.py  # Console + rotating-file logging       (Step 1)
│   ├── exceptions.py      # Custom exception hierarchy            (Step 1)
│   ├── client.py          # Signed Binance REST client wrapper    (Step 1-2)
│   ├── healthcheck.py     # Connectivity smoke test               (Step 1)
│   ├── exchange.py        # Exchange-info parsing & symbol filters (Step 2)
│   ├── validators.py      # Decimal-based input validation        (Step 2)
│   ├── orders.py          # Order request/result + OrderService   (Step 2)
│   └── cli.py             # Typer CLI entry point                 (Step 3)
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

## Placing orders (Step 3 CLI)

The CLI lives in `bot/cli.py`. See all options with `python -m bot.cli order --help`.

```bash
# MARKET buy (fills immediately)
python -m bot.cli order --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.002

# LIMIT sell (rests until the price is reached)
python -m bot.cli order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 70000

# Validate only — shows the exact params without sending anything (no keys needed)
python -m bot.cli order -s BTCUSDT --side BUY -t LIMIT -q 0.002 -p 55000 --dry-run

# Quick signed-request check
python -m bot.cli balance
```

Short flags: `-s` symbol, `-t` type, `-q` quantity, `-p` price.

Every run prints an **order request summary**, the **order response**
(`orderId`, `status`, `executedQty`, `avgPrice`, …), and a green **SUCCESS** or
red **FAILURE** line. For MARKET orders the bot re-queries the order so the
output reflects the actual fill rather than the initial acknowledgement.

## Design notes / assumptions

- **Direct REST over `requests`** (not `python-binance`) for full control of
  signing, logging, and error translation.
- **Secrets via environment** (`.env`, gitignored) — never committed.
- **Requests are signed** with HMAC-SHA256; secrets are never logged and the
  signature is masked in logs.
- **One exception hierarchy** (`TradingBotError` and subclasses) so callers can
  distinguish config vs. validation vs. network vs. Binance-side failures.
- **`Decimal` everywhere for money/size math** — tick-size and step-size
  multiples are checked exactly, avoiding binary-float rounding bugs.
- **Live symbol filters** (`exchange.py`) are fetched once and cached; validators
  enforce tick size, step size, min/max qty, and min notional before any order
  leaves the process. `OrderService` (`orders.py`) is the reusable seam the CLI
  will sit on top of in Step 3.
