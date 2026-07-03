from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .client import BinanceFuturesClient
from .exceptions import TradingBotError, ValidationError
from .exchange import ExchangeInfo, SymbolFilters
from .logging_config import get_logger
from .validators import (
    plain,
    validate_notional,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_time_in_force,
)

MAX_SETTLE_POLLS = 5
SETTLE_POLL_SECONDS = 0.2
_PENDING_STATUSES = ("NEW", "PARTIALLY_FILLED")


@dataclass(frozen=True)
class OrderRequest:
    symbol: str
    side: str
    type: str
    quantity: Decimal
    price: Decimal | None = None
    time_in_force: str = "GTC"

    def to_params(self) -> dict[str, str]:
        params = {
            "symbol": self.symbol,
            "side": self.side,
            "type": self.type,
            "quantity": plain(self.quantity),
        }
        if self.type == "LIMIT":
            params["price"] = plain(self.price)
            params["timeInForce"] = self.time_in_force
        return params

    def summary(self) -> str:
        bits = [
            f"symbol={self.symbol}",
            f"side={self.side}",
            f"type={self.type}",
            f"quantity={plain(self.quantity)}",
        ]
        if self.type == "LIMIT":
            bits.append(f"price={plain(self.price)}")
            bits.append(f"timeInForce={self.time_in_force}")
        return ", ".join(bits)


@dataclass(frozen=True)
class OrderResult:
    order_id: int
    symbol: str
    side: str
    type: str
    status: str
    orig_qty: str
    executed_qty: str
    avg_price: str
    price: str
    cum_quote: str
    raw: dict[str, Any] = field(repr=False, default_factory=dict)

    @classmethod
    def from_response(cls, data: dict[str, Any]) -> "OrderResult":
        return cls(
            order_id=int(data.get("orderId", 0)),
            symbol=str(data.get("symbol", "")),
            side=str(data.get("side", "")),
            type=str(data.get("type", "")),
            status=str(data.get("status", "")),
            orig_qty=str(data.get("origQty", "")),
            executed_qty=str(data.get("executedQty", "")),
            avg_price=str(data.get("avgPrice", "")),
            price=str(data.get("price", "")),
            cum_quote=str(data.get("cumQuote", "")),
            raw=data,
        )


class OrderService:
    def __init__(
        self,
        client: BinanceFuturesClient,
        exchange_info: ExchangeInfo | None = None,
        logger: Any | None = None,
    ) -> None:
        self._client = client
        self._exchange = exchange_info or ExchangeInfo(client)
        self._log = logger or get_logger()

    def build_request(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Any,
        price: Any | None = None,
        time_in_force: str = "GTC",
    ) -> OrderRequest:
        side = validate_side(side)
        order_type = validate_order_type(order_type)
        symbol_norm = str(symbol).strip().upper()

        filters = self._exchange.filters_for(symbol_norm)
        if not filters.is_trading:
            raise ValidationError(
                f"Symbol {filters.symbol} is not currently trading "
                f"(status={filters.status})."
            )

        is_market = order_type == "MARKET"
        qty = validate_quantity(quantity, filters, is_market=is_market)

        price_dec: Decimal | None = None
        if order_type == "LIMIT":
            if price is None:
                raise ValidationError("Price is required for LIMIT orders.")
            time_in_force = validate_time_in_force(time_in_force)
            price_dec = validate_price(price, filters)
            validate_notional(qty, price_dec, filters)
        else:
            if price is not None:
                self._log.debug("Ignoring price for MARKET order on %s.", filters.symbol)
            self._check_market_notional(qty, filters)

        return OrderRequest(
            symbol=filters.symbol,
            side=side,
            type=order_type,
            quantity=qty,
            price=price_dec,
            time_in_force=time_in_force,
        )

    def _check_market_notional(self, qty: Decimal, filters: SymbolFilters) -> None:
        if filters.min_notional <= 0:
            return
        try:
            ref_price = self._client.ticker_price(filters.symbol)
        except TradingBotError as exc:
            self._log.warning(
                "Skipping notional check for %s — could not fetch price: %s",
                filters.symbol,
                exc,
            )
            return
        try:
            validate_notional(qty, ref_price, filters)
        except ValidationError as exc:
            raise ValidationError(
                f"{exc} (estimated with last price {plain(ref_price)})"
            ) from None

    def place(self, request: OrderRequest) -> OrderResult:
        self._log.info("Placing order: %s", request.summary())
        data = self._client.place_order(request.to_params())
        result = OrderResult.from_response(data)
        result = self._settle(result)
        self._log.info(
            "Order settled: id=%s status=%s executedQty=%s avgPrice=%s",
            result.order_id,
            result.status,
            result.executed_qty,
            result.avg_price,
        )
        return result

    def _settle(self, result: OrderResult) -> OrderResult:
        if not result.order_id:
            return result
        settled = result
        for attempt in range(MAX_SETTLE_POLLS):
            try:
                data = self._client.query_order(settled.symbol, settled.order_id)
            except TradingBotError as exc:
                self._log.warning(
                    "Could not re-query order %s: %s — using last known state.",
                    settled.order_id,
                    exc,
                )
                return settled
            settled = OrderResult.from_response(data)
            if settled.type != "MARKET" or settled.status not in _PENDING_STATUSES:
                break
            if attempt < MAX_SETTLE_POLLS - 1:
                time.sleep(SETTLE_POLL_SECONDS)
        return settled

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: Any,
        price: Any | None = None,
        time_in_force: str = "GTC",
    ) -> OrderResult:
        request = self.build_request(
            symbol,
            side,
            order_type,
            quantity,
            price=price,
            time_in_force=time_in_force,
        )
        return self.place(request)
