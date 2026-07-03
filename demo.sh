#!/usr/bin/env bash
#
# demo.sh — a guided, presenter-paced walkthrough of the trading bot.
# Perfect for screen-recording a demo video.
#
#   ./demo.sh              # press Enter to advance between steps (recommended)
#   DEMO_AUTO=1 ./demo.sh  # hands-free: auto-advances every few seconds
#
# Normal commands run with logs hidden for a clean screen; the log FILE is
# revealed near the end to prove the full audit trail is captured.

set -uo pipefail
cd "$(dirname "$0")"

# Activate the venv if it isn't already.
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

CYAN=$'\033[1;36m'; GREEN=$'\033[1;32m'; YELLOW=$'\033[1;33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

banner() {
  printf "\n${CYAN}════════════════════════════════════════════════════════════${RESET}\n"
  printf "${CYAN}${BOLD}  %s${RESET}\n" "$1"
  printf "${CYAN}════════════════════════════════════════════════════════════${RESET}\n"
}

# Echo a command, then run it with logs (stderr) hidden.
run() { printf "\n${DIM}\$ %s${RESET}\n\n" "$*"; eval "$* 2>/dev/null" || true; }

# Like run(), but keeps stderr so intentional failure messages are visible.
run_fail() { printf "\n${DIM}\$ %s${RESET}\n\n" "$*"; eval "$* 2>&1" || true; }

pause() {
  if [ "${DEMO_AUTO:-0}" = "1" ]; then
    sleep "${DEMO_DELAY:-4}"
  else
    printf "\n${YELLOW}  ▶ Press Enter to continue…${RESET}"; read -r
  fi
}

clear
banner "Binance Futures Testnet Trading Bot — Live Demo"
printf "\n  A Python bot that places MARKET / LIMIT / TWAP orders on the\n"
printf "  Binance USDT-M Futures testnet, with validation, logging, and a\n"
printf "  clean CLI. Everything below runs against the REAL testnet.\n"
pause

banner "1) Connectivity + account (signed request)"
run "python -m bot.healthcheck"
run "python -m bot.cli balance"
pause

banner "2) Dry-run — validate + preview, place NOTHING (no keys needed)"
run "python -m bot.cli order -s BTCUSDT --side BUY -t MARKET -q 0.002 --dry-run"
run "python -m bot.cli order -s BTCUSDT --side BUY -t LIMIT -q 0.002 -p 50000 --dry-run"
pause

banner "3) MARKET order — fills immediately"
run "python -m bot.cli order -s BTCUSDT --side BUY -t MARKET -q 0.002"
pause

banner "4) LIMIT order — rests on the book as NEW"
printf "\n  ${DIM}(computing a resting price ~3%% below market)${RESET}\n"
LIMIT=$(python - <<'PY' 2>/dev/null
from decimal import Decimal
from bot.config import load_settings
from bot.client import BinanceFuturesClient
from bot.exchange import ExchangeInfo
s = load_settings(); c = BinanceFuturesClient(s)
f = ExchangeInfo(c).filters_for('BTCUSDT'); px = c.ticker_price('BTCUSDT')
print(format((px * Decimal('0.97') // f.tick_size) * f.tick_size, 'f')); c.close()
PY
)
run "python -m bot.cli order -s BTCUSDT --side BUY -t LIMIT -q 0.002 -p ${LIMIT}"
pause

banner "5) TWAP (bonus) — split 0.006 into 3 timed MARKET slices"
run "python -m bot.cli twap -s BTCUSDT --side BUY -q 0.006 -n 3 -i 2"
pause

banner "6) Validation & error handling — each is rejected cleanly"
run_fail "python -m bot.cli order -s BTCUSDT --side BUY -t LIMIT -q 0.002"
run_fail "python -m bot.cli order -s BTCUSDT --side HODL -t MARKET -q 0.002"
run_fail "python -m bot.cli order -s FAKEUSDT --side BUY -t MARKET -q 0.002"
pause

banner "7) Everything is logged (secret & signature never appear)"
run "tail -n 12 logs/trading_bot.log"
pause

banner "8) Automated tests — 30, fully mocked (no network)"
run "python -m pytest -q"
pause

banner "Demo complete ✅  —  MARKET · LIMIT · TWAP · validation · logging · tests"
printf "\n"
