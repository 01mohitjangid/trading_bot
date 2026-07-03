"""Input validation for order parameters.

Every numeric check uses `Decimal` so tick-size / step-size multiples are exact
(binary floats would make e.g. `0.3 % 0.1 != 0`). Each validator either returns
a normalized value or raises `ValidationError` with an actionable message.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from .exceptions import ValidationError
from .exchange import SymbolFilters

VALID_SIDES = ("BUY", "SELL")
VALID_ORDER_TYPES = ("MARKET", "LIMIT")
VALID_TIME_IN_FORCE = ("GTC", "IOC", "FOK", "GTX")


def plain(value: Decimal) -> str:
    """Format a Decimal without scientific notation (Binance wants plain strings)."""
    return format(value, "f")


def validate_side(side: str) -> str:
    normalized = str(side).strip().upper()
    if normalized not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Expected one of {', '.join(VALID_SIDES)}."
        )
    return normalized


def validate_order_type(order_type: str) -> str:
    normalized = str(order_type).strip().upper()
    if normalized not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Expected one of "
            f"{', '.join(VALID_ORDER_TYPES)}."
        )
    return normalized


def validate_time_in_force(tif: str) -> str:
    normalized = str(tif).strip().upper()
    if normalized not in VALID_TIME_IN_FORCE:
        raise ValidationError(
            f"Invalid timeInForce '{tif}'. Expected one of "
            f"{', '.join(VALID_TIME_IN_FORCE)}."
        )
    return normalized


def _to_decimal(value: Any, field: str) -> Decimal:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise ValidationError(f"{field} '{value}' is not a valid number.") from None
    if not number.is_finite():
        raise ValidationError(f"{field} '{value}' is not a finite number.")
    return number


def _check_multiple(value: Decimal, step: Decimal, field: str) -> None:
    if step > 0 and (value % step) != 0:
        raise ValidationError(
            f"{field} {plain(value)} is not a multiple of the required step "
            f"{plain(step)}."
        )


def validate_quantity(
    quantity: Any,
    filters: SymbolFilters,
    *,
    is_market: bool,
) -> Decimal:
    """Validate quantity against the (market or limit) lot-size filter."""
    qty = _to_decimal(quantity, "Quantity")
    if qty <= 0:
        raise ValidationError("Quantity must be greater than zero.")

    step = filters.market_step_size if is_market else filters.step_size
    min_qty = filters.market_min_qty if is_market else filters.min_qty
    max_qty = filters.market_max_qty if is_market else filters.max_qty

    if min_qty > 0 and qty < min_qty:
        raise ValidationError(
            f"Quantity {plain(qty)} is below the minimum {plain(min_qty)}."
        )
    if max_qty > 0 and qty > max_qty:
        raise ValidationError(
            f"Quantity {plain(qty)} exceeds the maximum {plain(max_qty)}."
        )
    _check_multiple(qty, step, "Quantity")
    return qty


def validate_price(price: Any, filters: SymbolFilters) -> Decimal:
    """Validate a limit price against the price filter."""
    value = _to_decimal(price, "Price")
    if value <= 0:
        raise ValidationError("Price must be greater than zero.")
    if filters.min_price > 0 and value < filters.min_price:
        raise ValidationError(
            f"Price {plain(value)} is below the minimum {plain(filters.min_price)}."
        )
    if filters.max_price > 0 and value > filters.max_price:
        raise ValidationError(
            f"Price {plain(value)} exceeds the maximum {plain(filters.max_price)}."
        )
    _check_multiple(value, filters.tick_size, "Price")
    return value


def validate_notional(
    quantity: Decimal,
    price: Decimal,
    filters: SymbolFilters,
) -> None:
    """Ensure quantity x price meets the symbol's minimum notional."""
    if filters.min_notional <= 0:
        return
    notional = quantity * price
    if notional < filters.min_notional:
        raise ValidationError(
            f"Notional {plain(notional)} (qty x price) is below the minimum "
            f"{plain(filters.min_notional)} for {filters.symbol}."
        )
