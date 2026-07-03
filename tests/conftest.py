
from __future__ import annotations

from decimal import Decimal

import pytest

from bot.exceptions import ValidationError
from bot.exchange import SymbolFilters


def make_filters(**overrides) -> SymbolFilters:
    defaults = dict(
        symbol="BTCUSDT",
        status="TRADING",
        base_asset="BTC",
        quote_asset="USDT",
        price_precision=2,
        quantity_precision=3,
        tick_size=Decimal("0.10"),
        min_price=Decimal("0.10"),
        max_price=Decimal("1000000"),
        step_size=Decimal("0.001"),
        min_qty=Decimal("0.001"),
        max_qty=Decimal("1000"),
        market_step_size=Decimal("0.001"),
        market_min_qty=Decimal("0.001"),
        market_max_qty=Decimal("100"),
        min_notional=Decimal("5"),
    )
    defaults.update(overrides)
    return SymbolFilters(**defaults)


class FakeExchange:
    def __init__(self, filters: SymbolFilters) -> None:
        self._by_symbol = {filters.symbol: filters}

    def filters_for(self, symbol: str) -> SymbolFilters:
        try:
            return self._by_symbol[symbol]
        except KeyError:
            raise ValidationError(f"Unknown symbol '{symbol}'.") from None


class FakeClient:
    def __init__(self, price: str = "60000") -> None:
        self.price = Decimal(price)
        self.placed: list[tuple[int, dict]] = []
        self._next_id = 1000

    def ticker_price(self, symbol: str) -> Decimal:
        return self.price

    def place_order(self, params: dict) -> dict:
        order_id = self._next_id
        self._next_id += 1
        self.placed.append((order_id, dict(params)))
        return {
            "orderId": order_id,
            "symbol": params["symbol"],
            "side": params["side"],
            "type": params["type"],
            "status": "NEW",
            "origQty": params["quantity"],
            "executedQty": "0",
            "avgPrice": "0",
            "price": params.get("price", "0"),
            "cumQuote": "0",
        }

    def query_order(self, symbol: str, order_id: int) -> dict:
        for placed_id, params in self.placed:
            if placed_id == order_id:
                qty = Decimal(params["quantity"])
                return {
                    "orderId": order_id,
                    "symbol": symbol,
                    "side": params["side"],
                    "type": params["type"],
                    "status": "FILLED",
                    "origQty": params["quantity"],
                    "executedQty": params["quantity"],
                    "avgPrice": format(self.price, "f"),
                    "price": params.get("price", "0"),
                    "cumQuote": format(qty * self.price, "f"),
                }
        raise ValidationError(f"order {order_id} not found")


@pytest.fixture
def filters() -> SymbolFilters:
    return make_filters()


@pytest.fixture
def exchange(filters: SymbolFilters) -> FakeExchange:
    return FakeExchange(filters)


@pytest.fixture
def fake_client() -> FakeClient:
    return FakeClient()
