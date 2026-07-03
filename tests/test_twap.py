from __future__ import annotations

from decimal import Decimal

import pytest

from bot.exceptions import ValidationError
from bot.orders import OrderService
from bot.twap import TwapExecutor
from tests.conftest import FakeClient, FakeExchange, make_filters


def _executor(price="60000", **filter_overrides):
    client = FakeClient(price=price)
    exchange = FakeExchange(make_filters(**filter_overrides))
    service = OrderService(client, exchange)
    return client, TwapExecutor(client, service, exchange, sleep=lambda _s: None)


def test_plan_splits_evenly():
    _client, ex = _executor()
    plan = ex.plan("BTCUSDT", "buy", "0.006", slices=3, interval_seconds=0)
    assert plan.slice_quantities == [Decimal("0.002")] * 3
    assert sum(plan.slice_quantities) == Decimal("0.006")


def test_plan_distributes_remainder_on_grid():
    _client, ex = _executor()
    plan = ex.plan("BTCUSDT", "buy", "0.007", slices=3, interval_seconds=0)
    assert plan.slice_quantities == [Decimal("0.003"), Decimal("0.002"), Decimal("0.002")]
    assert sum(plan.slice_quantities) == Decimal("0.007")


def test_plan_rejects_too_many_slices():
    _client, ex = _executor()
    with pytest.raises(ValidationError, match="too many"):
        ex.plan("BTCUSDT", "buy", "0.002", slices=5, interval_seconds=0)


def test_plan_rejects_total_off_step():
    _client, ex = _executor()
    with pytest.raises(ValidationError, match="multiple of the step"):
        ex.plan("BTCUSDT", "buy", "0.0025", slices=2, interval_seconds=0)


def test_plan_rejects_slice_below_min_notional():
    _client, ex = _executor(min_notional=Decimal("200"))
    with pytest.raises(ValidationError, match="minimum notional"):
        ex.plan("BTCUSDT", "buy", "0.006", slices=6, interval_seconds=0)


def test_execute_places_all_slices_and_aggregates():
    client, ex = _executor()
    plan = ex.plan("BTCUSDT", "buy", "0.006", slices=3, interval_seconds=0)
    result = ex.execute(plan)
    assert len(result.orders) == 3
    assert len(client.placed) == 3
    assert result.total_executed == Decimal("0.006")
    assert result.total_quote == Decimal("360.000")
    assert result.avg_price == Decimal("60000")
