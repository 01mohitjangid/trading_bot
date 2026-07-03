from __future__ import annotations

from decimal import Decimal

import pytest

from bot.exceptions import ValidationError
from bot.validators import (
    plain,
    validate_notional,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_time_in_force,
)
from tests.conftest import make_filters


def test_validate_side_normalizes():
    assert validate_side("buy") == "BUY"
    assert validate_side("  Sell ") == "SELL"


def test_validate_side_rejects_unknown():
    with pytest.raises(ValidationError):
        validate_side("hodl")


def test_validate_order_type():
    assert validate_order_type("market") == "MARKET"
    with pytest.raises(ValidationError):
        validate_order_type("iceberg")


def test_validate_time_in_force():
    assert validate_time_in_force("gtc") == "GTC"
    with pytest.raises(ValidationError):
        validate_time_in_force("soon")


def test_plain_has_no_scientific_notation():
    assert plain(Decimal("0.0010")) == "0.0010"
    assert plain(Decimal("1E-3")) == "0.001"
    assert plain(Decimal("100")) == "100"


def test_validate_quantity_ok():
    filters = make_filters()
    assert validate_quantity("0.002", filters, is_market=False) == Decimal("0.002")


def test_validate_quantity_below_minimum():
    filters = make_filters(min_qty=Decimal("0.01"))
    with pytest.raises(ValidationError, match="below the minimum"):
        validate_quantity("0.005", filters, is_market=False)


def test_validate_quantity_off_step():
    filters = make_filters()
    with pytest.raises(ValidationError, match="multiple of the required step"):
        validate_quantity("0.0015", filters, is_market=False)


def test_validate_quantity_uses_market_lot_size():
    filters = make_filters(market_step_size=Decimal("0.01"), market_min_qty=Decimal("0.01"))
    with pytest.raises(ValidationError):
        validate_quantity("0.005", filters, is_market=True)


def test_validate_price_ok():
    filters = make_filters()
    assert validate_price("60000.10", filters) == Decimal("60000.10")


def test_validate_price_off_tick():
    filters = make_filters()
    with pytest.raises(ValidationError, match="multiple of the required step"):
        validate_price("60000.05", filters)


def test_validate_notional_below_minimum():
    filters = make_filters(min_notional=Decimal("50"))
    with pytest.raises(ValidationError, match="below the minimum"):
        validate_notional(Decimal("0.0001"), Decimal("60000"), filters)


def test_validate_notional_ok():
    filters = make_filters(min_notional=Decimal("50"))
    validate_notional(Decimal("0.002"), Decimal("60000"), filters)
