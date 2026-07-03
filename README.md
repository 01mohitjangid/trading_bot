# Trading Bot — Binance USDT-M Futures Testnet

A small, well-structured Python trading bot that places orders on the
[Binance Futures Testnet](https://testnet.binancefuture.com) (USDT-M), with a
clean client/CLI separation, structured logging, robust validation, and error
handling.

## Features

**Core**
- Place **MARKET** and **LIMIT** orders, **BUY** and **SELL**
- Validated CLI input (symbol, side, type, quantity, price)
- Clear output: order request summary, response (`orderId`, `status`,
  `executedQty`, `avgPrice`), and a success/failure line
- Separated layers: REST **client** ↔ order/validation **domain** ↔ **CLI**
- All API requests, responses, and errors logged to a rotating file
- Exception handling for invalid input, API errors, and network failures

**Bonus**
- **TWAP** (Time-Weighted Average Price) — splits a large order into timed
  MARKET slices and reports the volume-weighted average fill
- **Enhanced CLI UX** — colored output, a `--dry-run` mode, and a `balance`
  command
- Unit tests (30, fully mocked — no network needed)

## Project structure

```
Trading/
├── bot/
│   ├── __init__.py
│   ├── config.py          # Settings & secret loading
│   ├── logging_config.py  # Console + rotating-file logging
│   ├── exceptions.py      # Custom exception hierarchy
│   ├── client.py          # Signed Binance REST client wrapper
│   ├── exchange.py        # Exchange-info parsing & symbol filters
│   ├── validators.py      # Decimal-based input validation
│   ├── orders.py          # OrderRequest/OrderResult + OrderService
│   ├── twap.py            # TWAP strategy (bonus)
│   ├── healthcheck.py     # Connectivity smoke test
│   └── cli.py             # Typer CLI entry point
├── tests/                 # pytest unit tests (mocked)
├── sample_logs/           # Deliverable logs: market / limit / twap
├── .env.example
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

   Register at <https://testnet.binancefuture.com>, open **API Management**,
   choose **System generated** (HMAC), and generate a key/secret. Then:

   ```bash
   cp .env.example .env
   # edit .env and paste BINANCE_API_KEY / BINANCE_API_SECRET
   ```

## Verify connectivity

```bash
python -m bot.healthcheck
```
Prints ping, server time, and (with keys configured) your USDT balance.

## Usage

See every option with `python -m bot.cli order --help`. Short flags:
`-s` symbol · `-t` type · `-q` quantity · `-p` price.

```bash
# MARKET buy (fills immediately; the bot re-queries so output shows the fill)
python -m bot.cli order --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.002

# LIMIT sell (rests until the price is reached)
python -m bot.cli order --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.002 --price 70000

# Validate only — shows the exact params without sending (no keys needed)
python -m bot.cli order -s BTCUSDT --side BUY -t LIMIT -q 0.002 -p 55000 --dry-run

# TWAP (bonus): split 0.006 into 3 MARKET slices, 1s apart
python -m bot.cli twap --symbol BTCUSDT --side BUY --quantity 0.006 --slices 3 --interval 1

# Quick signed-request check
python -m bot.cli balance
```

Each order prints a request summary, the response details, and a green
**SUCCESS** / red **FAILURE** line. Invalid input, API errors, and network
failures are reported as a single clean failure message (exit code 1), never a
stack trace.

## Tests

```bash
python -m pytest -q
```
All tests are fully mocked (no network / no keys), covering validators, order
building/serialization, market-order settlement, TWAP slicing + aggregation,
and the request signing.

## Logging

Everything is logged to `logs/trading_bot.log` (rotating, ~1 MB × 5) and echoed
to the console. Curated example logs for the deliverable live in
[`sample_logs/`](sample_logs/): `market_order.log`, `limit_order.log`, and
`twap_order.log`. The API secret and request signature are never written to the
logs.

## Design notes & assumptions

- **Direct REST over `requests`** (not `python-binance`) for full control of
  signing, logging, and error translation.
- **Secrets via environment** (`.env`, gitignored) — never committed.
- **Signing is done over the exact query string sent** — the string is built
  once, HMAC-SHA256 signed, and appended as `&signature=…`, so there is no
  client/library re-encoding mismatch.
- **`Decimal` everywhere for money/size math** — tick-size and step-size
  multiples are checked exactly, avoiding binary-float rounding bugs.
- **Live symbol filters** are fetched once and cached; validators enforce tick
  size, step size, min/max quantity, and min notional before any order is sent.
- **MARKET orders are re-queried** after placement (bounded retries) so the
  reported fill reflects the settled state, not the initial acknowledgement.
- **Assumes one-way position mode** (the account default), so orders do not send
  `positionSide`; a hedge-mode account would require it.
- **Bonus choice — TWAP (not Stop-Limit):** the Futures **testnet** rejects
  conditional orders (STOP / STOP_MARKET) on the order endpoint with
  `-4120 "Order type not supported for this endpoint"`. TWAP is built on plain
  MARKET orders, so it actually executes on the testnet.
