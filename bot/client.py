from __future__ import annotations

import hashlib
import hmac
import logging
import time
from decimal import Decimal
from typing import Any, Mapping
from urllib.parse import urlencode

import requests

from .config import Settings
from .exceptions import BinanceAPIError, BinanceRequestError
from .logging_config import get_logger

PING_PATH = "/fapi/v1/ping"
TIME_PATH = "/fapi/v1/time"
BALANCE_PATH = "/fapi/v2/balance"
EXCHANGE_INFO_PATH = "/fapi/v1/exchangeInfo"
TICKER_PRICE_PATH = "/fapi/v1/ticker/price"
ORDER_PATH = "/fapi/v1/order"


class BinanceFuturesClient:
    def __init__(
        self,
        settings: Settings,
        logger: logging.Logger | None = None,
    ) -> None:
        self._settings = settings
        self._log = logger or get_logger()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "trading-bot/0.1"})
        if settings.api_key:
            self._session.headers.update({"X-MBX-APIKEY": settings.api_key})

    def _sign(self, query_string: str) -> str:
        return hmac.new(
            self._settings.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _request(
        self,
        method: str,
        path: str,
        params: Mapping[str, Any] | None = None,
        *,
        signed: bool = False,
    ) -> Any:
        params = dict(params or {})

        if signed:
            self._settings.require_credentials()
            params["timestamp"] = int(time.time() * 1000)
            params["recvWindow"] = self._settings.recv_window

        query = urlencode(params)
        if signed:
            query = f"{query}&signature={self._sign(query)}"

        url = f"{self._settings.base_url}{path}"
        if query:
            url = f"{url}?{query}"

        self._log.info("--> %s %s params=%s signed=%s", method, path, params, signed)

        try:
            response = self._session.request(
                method, url, timeout=self._settings.timeout
            )
        except requests.exceptions.RequestException as exc:
            self._log.error("Network error on %s %s: %s", method, path, exc)
            raise BinanceRequestError(f"Network error calling {path}: {exc}") from exc

        return self._handle_response(method, path, response)

    def _handle_response(
        self,
        method: str,
        path: str,
        response: requests.Response,
    ) -> Any:
        try:
            payload: Any = response.json()
        except ValueError:
            payload = response.text

        if not response.ok:
            code: int | None = None
            message = str(payload)
            if isinstance(payload, dict):
                code = payload.get("code")
                message = payload.get("msg", message)
            self._log.error(
                "<-- %s %s HTTP %s code=%s msg=%s",
                method,
                path,
                response.status_code,
                code,
                message,
            )
            raise BinanceAPIError(code, message, response.status_code)

        self._log.info("<-- %s %s HTTP %s OK", method, path, response.status_code)
        self._log.debug("Response body: %s", payload)
        return payload

    def ping(self) -> bool:
        self._request("GET", PING_PATH)
        return True

    def server_time(self) -> int:
        data = self._request("GET", TIME_PATH)
        return int(data["serverTime"])

    def exchange_info(self) -> dict[str, Any]:
        return self._request("GET", EXCHANGE_INFO_PATH)

    def ticker_price(self, symbol: str) -> Decimal:
        data = self._request("GET", TICKER_PRICE_PATH, {"symbol": symbol})
        return Decimal(str(data["price"]))

    def get_balances(self) -> list[dict[str, Any]]:
        return self._request("GET", BALANCE_PATH, signed=True)

    def place_order(self, params: Mapping[str, Any]) -> dict[str, Any]:
        return self._request("POST", ORDER_PATH, params, signed=True)

    def query_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        return self._request(
            "GET", ORDER_PATH, {"symbol": symbol, "orderId": order_id}, signed=True
        )

    def get_usdt_balance(self) -> dict[str, Any] | None:
        for entry in self.get_balances():
            if entry.get("asset") == "USDT":
                return entry
        return None

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "BinanceFuturesClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()
