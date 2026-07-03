from __future__ import annotations


class TradingBotError(Exception):
    pass


class ConfigError(TradingBotError):
    pass


class ValidationError(TradingBotError):
    pass


class BinanceRequestError(TradingBotError):
    pass


class BinanceAPIError(TradingBotError):
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
