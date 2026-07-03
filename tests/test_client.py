from __future__ import annotations

import hashlib
import hmac

from bot.client import BinanceFuturesClient
from bot.config import Settings


def _client(secret="topsecret", key="apikey"):
    settings = Settings(api_key=key, api_secret=secret, base_url="https://testnet.example")
    return BinanceFuturesClient(settings)


class _FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._payload = payload if payload is not None else {}
        self.text = str(self._payload)

    def json(self):
        return self._payload


class _RecordingSession:
    def __init__(self):
        self.headers = {}
        self.last_url = None

    def request(self, method, url, timeout=None):
        self.last_url = url
        return _FakeResponse(200, {"ok": True})

    def close(self):
        pass


def test_sign_is_hmac_sha256_over_query():
    client = _client(secret="topsecret")
    query = "symbol=BTCUSDT&side=BUY&timestamp=123"
    expected = hmac.new(b"topsecret", query.encode(), hashlib.sha256).hexdigest()
    assert client._sign(query) == expected
    assert len(client._sign(query)) == 64


def test_signed_request_signs_exactly_what_it_sends():
    client = _client(secret="topsecret")
    client._session = _RecordingSession()

    client.get_balances()

    url = client._session.last_url
    assert url is not None
    assert "/fapi/v2/balance?" in url
    assert "timestamp=" in url and "recvWindow=" in url

    query = url.split("?", 1)[1]
    signed_part, signature = query.rsplit("&signature=", 1)
    expected = hmac.new(b"topsecret", signed_part.encode(), hashlib.sha256).hexdigest()
    assert signature == expected


def test_unsigned_request_has_no_signature():
    client = _client()
    client._session = _RecordingSession()
    client.ping()
    assert "signature=" not in (client._session.last_url or "")
