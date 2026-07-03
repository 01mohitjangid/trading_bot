"""Exchange-info parsing and caching.

Binance returns a symbol's trading rules as a list of loosely-typed "filters".
This module turns that into a typed, cached `SymbolFilters` object so the
validators can work with real numbers instead of dict digging.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from .client import BinanceFuturesClient
from .exceptions import ValidationError


@dataclass(frozen=True)
class SymbolFilters:
    """The trading rules we care about for a single symbol."""

    symbol: str
    status: str
    base_asset: str
    quote_asset: str
    price_precision: int
    quantity_precision: int
    # PRICE_FILTER
    tick_size: Decimal
    min_price: Decimal
    max_price: Decimal
    # LOT_SIZE (LIMIT orders)
    step_size: Decimal
    min_qty: Decimal
    max_qty: Decimal
    # MARKET_LOT_SIZE (MARKET orders)
    market_step_size: Decimal
    market_min_qty: Decimal
    market_max_qty: Decimal
    # MIN_NOTIONAL
    min_notional: Decimal

    @property
    def is_trading(self) -> bool:
        return self.status == "TRADING"


def _find_filter(filters: list[dict[str, Any]], filter_type: str) -> dict[str, Any]:
    for entry in filters:
        if entry.get("filterType") == filter_type:
            return entry
    return {}


def _dec(mapping: dict[str, Any], key: str, default: str = "0") -> Decimal:
    return Decimal(str(mapping.get(key, default)))


def parse_symbol_filters(entry: dict[str, Any]) -> SymbolFilters:
    """Build a `SymbolFilters` from one entry of exchangeInfo["symbols"]."""
    filters = entry.get("filters", [])
    price_f = _find_filter(filters, "PRICE_FILTER")
    lot_f = _find_filter(filters, "LOT_SIZE")
    market_lot_f = _find_filter(filters, "MARKET_LOT_SIZE")
    notional_f = _find_filter(filters, "MIN_NOTIONAL")

    return SymbolFilters(
        symbol=entry["symbol"],
        status=entry.get("status", "UNKNOWN"),
        base_asset=entry.get("baseAsset", ""),
        quote_asset=entry.get("quoteAsset", ""),
        price_precision=int(entry.get("pricePrecision", 8)),
        quantity_precision=int(entry.get("quantityPrecision", 8)),
        tick_size=_dec(price_f, "tickSize"),
        min_price=_dec(price_f, "minPrice"),
        max_price=_dec(price_f, "maxPrice"),
        step_size=_dec(lot_f, "stepSize"),
        min_qty=_dec(lot_f, "minQty"),
        max_qty=_dec(lot_f, "maxQty"),
        # Fall back to LOT_SIZE if MARKET_LOT_SIZE is absent.
        market_step_size=_dec(market_lot_f, "stepSize", str(_dec(lot_f, "stepSize"))),
        market_min_qty=_dec(market_lot_f, "minQty", str(_dec(lot_f, "minQty"))),
        market_max_qty=_dec(market_lot_f, "maxQty", str(_dec(lot_f, "maxQty"))),
        min_notional=_dec(notional_f, "notional"),
    )


class ExchangeInfo:
    """Fetches exchange info once, caches it, and resolves per-symbol filters."""

    def __init__(self, client: BinanceFuturesClient) -> None:
        self._client = client
        self._symbols: dict[str, SymbolFilters] | None = None

    def load(self, force: bool = False) -> None:
        if self._symbols is not None and not force:
            return
        data = self._client.exchange_info()
        self._symbols = {
            s["symbol"]: parse_symbol_filters(s) for s in data.get("symbols", [])
        }

    def filters_for(self, symbol: str) -> SymbolFilters:
        self.load()
        assert self._symbols is not None  # populated by load()
        try:
            return self._symbols[symbol]
        except KeyError:
            raise ValidationError(
                f"Unknown symbol '{symbol}'. It is not listed on the exchange."
            ) from None

    @property
    def symbols(self) -> list[str]:
        self.load()
        assert self._symbols is not None
        return sorted(self._symbols)
