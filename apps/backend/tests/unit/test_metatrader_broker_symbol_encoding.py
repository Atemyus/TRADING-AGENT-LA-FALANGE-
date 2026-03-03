import pytest

from src.engines.trading.metatrader_broker import MetaTraderBroker


@pytest.mark.asyncio
async def test_symbol_specification_path_encodes_hash_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = MetaTraderBroker(access_token="test-token", account_id="test-account")
    broker._connected = True

    captured: dict[str, str] = {}

    async def fake_request(method: str, endpoint: str, **kwargs):
        captured["endpoint"] = endpoint
        return {"tradeMode": "SYMBOL_TRADE_MODE_FULL"}

    monkeypatch.setattr(broker, "_request", fake_request)

    await broker._get_symbol_specification_for_broker_symbol("GOLD#")

    endpoint = captured["endpoint"]
    assert "GOLD%23" in endpoint
    assert "GOLD#/specification" not in endpoint


@pytest.mark.asyncio
async def test_current_price_path_encodes_hash_symbol_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = MetaTraderBroker(access_token="test-token", account_id="test-account")
    broker._connected = True
    broker._broker_symbols = ["GOLD#"]

    captured: list[str] = []

    async def fake_request(method: str, endpoint: str, **kwargs):
        captured.append(endpoint)
        return {"bid": 3000.0, "ask": 3000.2}

    monkeypatch.setattr(broker, "_request", fake_request)

    await broker.get_current_price("XAU_USD")

    assert any("/symbols/GOLD%23/current-price" in endpoint for endpoint in captured)
    assert not any("/symbols/GOLD#/current-price" in endpoint for endpoint in captured)


@pytest.mark.asyncio
async def test_candles_path_encodes_hash_symbol(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = MetaTraderBroker(access_token="test-token", account_id="test-account")
    broker._connected = True
    broker._symbol_map["XAU_USD"] = "GOLD#"

    captured: dict[str, str] = {}

    async def fake_request(method: str, endpoint: str, **kwargs):
        captured["endpoint"] = endpoint
        return []

    monkeypatch.setattr(broker, "_request", fake_request)

    await broker.get_candles("XAU_USD", timeframe="1h", count=10)

    endpoint = captured["endpoint"]
    assert "/historical-market-data/symbols/GOLD%23/timeframes/1h/candles" in endpoint
    assert "/historical-market-data/symbols/GOLD#/timeframes/1h/candles" not in endpoint
