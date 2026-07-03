# Trading Bot — Binance USDT-M Futures Testnet

A simple Python trading bot that places **MARKET**, **LIMIT**, and **TWAP**
orders on the [Binance Futures Testnet](https://testnet.binancefuture.com)
(USDT-M), with a clean CLI, input validation, logging, and error handling.

## 🎥 Demo video

**[▶️ Watch the demo](https://drive.google.com/file/d/1D3NPLXUygwf0xfqNBbD1STVEby8XNILi/view?usp=sharing)**

## Features

- MARKET & LIMIT orders, BUY & SELL, with validated CLI input
- Clear output: request summary + response (`orderId`, `status`, `executedQty`, `avgPrice`)
- Separated layers (REST client / order domain / CLI) and file logging
- Exception handling for invalid input, API errors, and network failures
- **Bonus:** TWAP strategy, `--dry-run` mode, `balance` command, and 30 unit tests

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then paste your testnet API key/secret
```

Get keys at <https://testnet.binancefuture.com> → **API Management** →
**System generated** (HMAC).

## Usage

```bash
# Check connectivity + balance
python -m bot.healthcheck

# MARKET buy
python -m bot.cli order -s BTCUSDT --side BUY -t MARKET -q 0.002

# LIMIT sell
python -m bot.cli order -s BTCUSDT --side SELL -t LIMIT -q 0.002 -p 70000

# Validate only, place nothing (no keys needed)
python -m bot.cli order -s BTCUSDT --side BUY -t LIMIT -q 0.002 -p 55000 --dry-run

# TWAP (bonus): split 0.006 into 3 MARKET slices, 1s apart
python -m bot.cli twap -s BTCUSDT --side BUY -q 0.006 -n 3 -i 1
```

Flags: `-s` symbol · `-t` type · `-q` quantity · `-p` price. Run
`python -m bot.cli order --help` for all options.

## Tests

```bash
python -m pytest -q
```

## Logging

All requests, responses, and errors are logged to `logs/trading_bot.log`
(secret/signature never included). Example logs are in
[`sample_logs/`](sample_logs/).

## Notes

- Direct REST calls (`requests`); secrets loaded from `.env` (gitignored).
- `Decimal` used for price/quantity math; orders validated against live symbol
  filters (tick size, step size, min notional).
- Assumes one-way position mode.
- **TWAP** is the bonus (the testnet rejects STOP orders with `-4120`, so a
  client-side TWAP is used instead).
