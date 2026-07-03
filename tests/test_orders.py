from __future__ import annotations

from decimal import Decimal

import pytest

from bot.exceptions import ValidationError
from bot.orders import OrderRequest, OrderResult, OrderService
from tests.conftest import FakeClient, FakeExchange, make_filters


def _service(price="60000"):
    client = FakeClient(price=price)
    service = OrderService(client, FakeExchange(make_filters()))
    return client, service


def test_build_market_request():
    _client, service = _service()
    req = service.build_request("btcusdt", "buy", "market", "0.002")
    assert req.symbol == "BTCUSDT"
    assert req.side == "BUY"
    assert req.type == "MARKET"
    assert req.quantity == Decimal("0.002")
    assert req.price is None


def test_build_limit_request_serializes():
    _client, service = _service()
    req = service.build_request("BTCUSDT", "sell", "limit", "0.002", price="60000.10")
    params = req.to_params()
    assert params == {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "type": "LIMIT",
        "quantity": "0.002",
        "price": "60000.10",
        "timeInForce": "GTC",
    }


def test_limit_requires_price():
    _client, service = _service()
    with pytest.raises(ValidationError, match="Price is required"):
        service.build_request("BTCUSDT", "buy", "limit", "0.002")


def test_unknown_symbol_rejected():
    _client, service = _service()
    with pytest.raises(ValidationError, match="Unknown symbol"):
        service.build_request("DOGEUSDT", "buy", "market", "0.002")


def test_market_notional_enforced():
    client = FakeClient(price="100")
    service = OrderService(client, FakeExchange(make_filters(min_notional=Decimal("50"))))
    with pytest.raises(ValidationError, match="below the minimum"):
        service.build_request("BTCUSDT", "buy", "market", "0.002")


def test_order_result_from_response_maps_fields():
    data = {
        "orderId": 42,
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "status": "FILLED",
        "origQty": "0.002",
        "executedQty": "0.002",
        "avgPrice": "60000",
        "price": "0",
        "cumQuote": "120",
    }
    result = OrderResult.from_response(data)
    assert result.order_id == 42
    assert result.status == "FILLED"
    assert result.executed_qty == "0.002"
    assert result.avg_price == "60000"
    assert result.raw is data


def test_place_resettles_market_order_to_filled():
    client, service = _service()
    result = service.place_order("BTCUSDT", "buy", "market", "0.002")
    assert result.status == "FILLED"
    assert result.executed_qty == "0.002"
    assert result.avg_price == "60000"
    assert len(client.placed) == 1


def test_market_request_summary_omits_price():
    req = OrderRequest(
        symbol="BTCUSDT", side="BUY", type="MARKET", quantity=Decimal("0.002")
    )
    assert "price" not in req.summary()
    assert req.to_params() == {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "type": "MARKET",
        "quantity": "0.002",
    }
