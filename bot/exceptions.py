"""Custom exception hierarchy for the trading bot.

A single base class (`TradingBotError`) lets callers catch every domain error
with one `except`, while the subclasses let them distinguish *why* something
failed (bad config, bad input, network, or a Binance-side rejection).
"""
from __future__ import annotations


class TradingBotError(Exception):
    """Base class for all trading-bot errors."""


class ConfigError(TradingBotError):
    """Configuration is missing or invalid (e.g. absent API credentials)."""


class ValidationError(TradingBotError):
    """User input failed validation (used from Step 2 onward)."""


class BinanceRequestError(TradingBotError):
    """A network-level failure (timeout, DNS, connection reset)."""


class BinanceAPIError(TradingBotError):
    """Binance returned an error response.

    Attributes:
        code: Binance business error code (e.g. -2019 "Margin is insufficient").
        message: Human-readable message returned by Binance.
        status_code: The HTTP status code of the response.
    """

    def __init__(
        self,
        code: int | None,
        message: str,
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self._render())

    def _render(self) -> str:
        parts: list[str] = []
        if self.status_code is not None:
            parts.append(f"HTTP {self.status_code}")
        if self.code is not None:
            parts.append(f"code={self.code}")
        parts.append(self.message)
        return " | ".join(parts)
