"""Connectivity smoke test for the Binance Futures testnet.

Run this after configuring your `.env` to confirm the Step 1 foundation works:

    python -m bot.healthcheck

Public checks (ping, server time) work without credentials. The balance check
runs only when API keys are configured.
"""
from __future__ import annotations

import sys

from .client import BinanceFuturesClient
from .config import load_settings
from .exceptions import TradingBotError
from .logging_config import setup_logging


def main() -> int:
    settings = load_settings()
    logger = setup_logging(settings.log_dir, settings.log_level)

    logger.info("Base URL: %s", settings.base_url)
    logger.info("Credentials configured: %s", settings.has_credentials)

    try:
        with BinanceFuturesClient(settings, logger) as client:
            client.ping()
            print("✓ Ping OK")

            server_time = client.server_time()
            print(f"✓ Server time: {server_time}")

            if settings.has_credentials:
                usdt = client.get_usdt_balance()
                if usdt:
                    print(
                        f"✓ USDT balance: {usdt.get('balance')} "
                        f"(available: {usdt.get('availableBalance')})"
                    )
                else:
                    print("✓ Authenticated, but no USDT balance entry found.")
            else:
                print(
                    "• Skipping balance check — no API credentials set. "
                    "Add them to .env to enable signed requests."
                )
    except TradingBotError as exc:
        logger.error("Health check failed: %s", exc)
        print(f"✗ Health check failed: {exc}", file=sys.stderr)
        return 1

    print("\nStep 1 foundation is working. ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
