from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Callable

from .client import BinanceFuturesClient
from .exceptions import ValidationError
from .exchange import ExchangeInfo
from .logging_config import get_logger
from .orders import OrderResult, OrderService
from .validators import plain, validate_quantity, validate_side


@dataclass(frozen=True)
class TwapPlan:
    symbol: str
    side: str
    total_quantity: Decimal
    slice_quantities: list[Decimal]
    interval_seconds: float

    @property
    def slices(self) -> int:
        return len(self.slice_quantities)


@dataclass
class TwapResult:
    plan: TwapPlan
    orders: list[OrderResult] = field(default_factory=list)

    @property
    def total_executed(self) -> Decimal:
        return sum((Decimal(o.executed_qty or "0") for o in self.orders), Decimal("0"))

    @property
    def total_quote(self) -> Decimal:
        return sum((Decimal(o.cum_quote or "0") for o in self.orders), Decimal("0"))

    @property
    def avg_price(self) -> Decimal | None:
        executed = self.total_executed
        if executed <= 0:
            return None
        return self.total_quote / executed


class TwapExecutor:
    def __init__(
        self,
        client: BinanceFuturesClient,
        service: OrderService,
        exchange_info: ExchangeInfo,
        logger: object | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._client = client
        self._service = service
        self._exchange = exchange_info
        self._log = logger or get_logger()
        self._sleep = sleep

    def plan(
        self,
        symbol: str,
        side: str,
        total_quantity: object,
        slices: int,
        interval_seconds: float,
    ) -> TwapPlan:
        side = validate_side(side)
        symbol = str(symbol).strip().upper()
        if slices < 1:
            raise ValidationError("Number of slices must be at least 1.")
        if interval_seconds < 0:
            raise ValidationError("Interval must be zero or positive.")

        filters = self._exchange.filters_for(symbol)
        step = filters.market_step_size

        try:
            total = Decimal(str(total_quantity).strip())
        except (InvalidOperation, ValueError):
            raise ValidationError(
                f"Quantity '{total_quantity}' is not a valid number."
            ) from None
        if total <= 0:
            raise ValidationError("Total quantity must be greater than zero.")
        if step > 0 and total % step != 0:
            raise ValidationError(
                f"Total quantity {plain(total)} must be a multiple of the step "
                f"size {plain(step)}."
            )

        quantities = self._split(total, slices, step, filters.market_min_qty)

        self._check_slice_notional(symbol, min(quantities), filters.min_notional)

        for qty in quantities:
            validate_quantity(qty, filters, is_market=True)

        return TwapPlan(symbol, side, total, quantities, float(interval_seconds))

    def _split(
        self,
        total: Decimal,
        slices: int,
        step: Decimal,
        min_qty: Decimal,
    ) -> list[Decimal]:
        base = (total / slices)
        if step > 0:
            base = (base // step) * step
        if base <= 0 or (min_qty > 0 and base < min_qty):
            raise ValidationError(
                f"{slices} slices is too many for total {plain(total)} — each "
                f"slice would fall below the minimum {plain(min_qty)}."
            )
        quantities = [base] * slices
        remainder = total - base * slices
        extra = int(remainder // step) if step > 0 else 0
        for i in range(extra):
            quantities[i % slices] += step
        return quantities

    def _check_slice_notional(
        self,
        symbol: str,
        smallest_slice: Decimal,
        min_notional: Decimal,
    ) -> None:
        if min_notional <= 0:
            return
        ref_price = self._client.ticker_price(symbol)
        if smallest_slice * ref_price < min_notional:
            raise ValidationError(
                f"Each slice (~{plain(smallest_slice)}) would be below the "
                f"minimum notional {plain(min_notional)} at price "
                f"{plain(ref_price)}. Use fewer slices or a larger quantity."
            )

    def execute(self, plan: TwapPlan) -> TwapResult:
        result = TwapResult(plan=plan)
        total = plan.slices
        for index, qty in enumerate(plan.slice_quantities, start=1):
            self._log.info(
                "TWAP slice %d/%d: %s %s %s",
                index,
                total,
                plan.side,
                plain(qty),
                plan.symbol,
            )
            order = self._service.place_order(plan.symbol, plan.side, "MARKET", qty)
            result.orders.append(order)
            if index < total and plan.interval_seconds > 0:
                self._sleep(plan.interval_seconds)
        return result
