"""Configuration loading.

Settings come from environment variables (optionally via a local `.env` file)
so that secrets never live in source control. `load_settings()` is the single
entry point; everything downstream receives an immutable `Settings` object.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .exceptions import ConfigError

# Default Binance USDT-M Futures testnet base URL (per the task brief).
DEFAULT_BASE_URL = "https://testnet.binancefuture.com"


@dataclass(frozen=True)
class Settings:
    """Immutable application settings."""

    api_key: str
    api_secret: str
    base_url: str = DEFAULT_BASE_URL
    recv_window: int = 5000
    timeout: float = 10.0
    log_dir: Path = Path("logs")
    log_level: str = "INFO"

    @property
    def has_credentials(self) -> bool:
        """True when both API key and secret are present."""
        return bool(self.api_key and self.api_secret)

    def require_credentials(self) -> None:
        """Raise if credentials are needed but missing (called before signing)."""
        if not self.has_credentials:
            raise ConfigError(
                "Missing API credentials. Set BINANCE_API_KEY and "
                "BINANCE_API_SECRET (copy .env.example to .env)."
            )


def load_settings(dotenv_path: str | os.PathLike[str] | None = None) -> Settings:
    """Load settings from the environment (and a `.env` file if present)."""
    # No-op if the file does not exist; existing env vars take precedence.
    load_dotenv(dotenv_path)

    base_url = os.getenv("BINANCE_BASE_URL", DEFAULT_BASE_URL).strip()
    if not base_url:
        raise ConfigError("BINANCE_BASE_URL must not be empty.")

    try:
        recv_window = int(os.getenv("BINANCE_RECV_WINDOW", "5000"))
        timeout = float(os.getenv("HTTP_TIMEOUT", "10"))
    except ValueError as exc:
        raise ConfigError(f"Invalid numeric configuration value: {exc}") from exc

    return Settings(
        api_key=os.getenv("BINANCE_API_KEY", "").strip(),
        api_secret=os.getenv("BINANCE_API_SECRET", "").strip(),
        base_url=base_url,
        recv_window=recv_window,
        timeout=timeout,
        log_dir=Path(os.getenv("LOG_DIR", "logs")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )
