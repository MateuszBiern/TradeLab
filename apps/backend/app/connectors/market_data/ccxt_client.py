import os
from typing import Any

import ccxt.async_support as ccxt
from fastapi import HTTPException

EXCHANGES = {
    "binance": "Binance",
    "bybit": "Bybit",
    "kraken": "Kraken",
    "coinbase": "Coinbase Advanced",
}
DEFAULT_EXCHANGE = os.getenv("DEFAULT_EXCHANGE", "binance").lower()
DEFAULT_SYMBOL = os.getenv("DEFAULT_MARKET_SYMBOL", "BTC/USDT")


def normalize_exchange(exchange_id: str) -> str:
    normalized = exchange_id.lower()
    if normalized not in EXCHANGES:
        raise HTTPException(status_code=422, detail="Unsupported exchange")
    return normalized


def create_exchange(exchange_id: str):
    normalized = normalize_exchange(exchange_id)
    exchange_class = getattr(ccxt, normalized, None)
    if exchange_class is None:
        raise HTTPException(status_code=500, detail="Configured exchange is not supported by CCXT")
    return exchange_class({"enableRateLimit": True, "timeout": 15000})


async def _run_exchange(exchange_id: str, operation):
    exchange = create_exchange(exchange_id)
    try:
        await exchange.load_markets()
        return await operation(exchange)
    except HTTPException:
        raise
    except ccxt.NetworkError as exc:
        raise HTTPException(status_code=502, detail="Exchange market-data service is unavailable") from exc
    except ccxt.ExchangeError as exc:
        raise HTTPException(status_code=502, detail="Exchange rejected the market-data request") from exc
    finally:
        await exchange.close()


async def list_spot_markets(exchange_id: str) -> list[dict[str, Any]]:
    async def operation(exchange):
        markets = [
            {"symbol": market["symbol"], "base": market.get("base"), "quote": market.get("quote")}
            for market in exchange.markets.values()
            if market.get("spot") and market.get("active", True) and "/" in market.get("symbol", "")
        ]
        return sorted(markets, key=lambda item: item["symbol"])

    return await _run_exchange(exchange_id, operation)


async def fetch_ticker(exchange_id: str, symbol: str) -> dict[str, Any]:
    async def operation(exchange):
        market = exchange.markets.get(symbol)
        if market is None or not market.get("spot"):
            raise HTTPException(status_code=404, detail="Spot symbol was not found on the selected exchange")
        ticker = await exchange.fetch_ticker(symbol)
        return {
            "exchange": exchange.id,
            "exchange_name": EXCHANGES[exchange.id],
            "symbol": ticker.get("symbol", symbol),
            "timestamp": ticker.get("timestamp"),
            "last": ticker.get("last"),
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "change_percent_24h": ticker.get("percentage"),
            "quote_volume_24h": ticker.get("quoteVolume"),
        }

    return await _run_exchange(exchange_id, operation)


async def fetch_candles(exchange_id: str, symbol: str, timeframe: str, limit: int) -> list[list[float]]:
    allowed_timeframes = {"1m", "5m", "15m", "1h", "4h", "1d"}
    if timeframe not in allowed_timeframes:
        raise HTTPException(status_code=422, detail="Unsupported timeframe")

    async def operation(exchange):
        market = exchange.markets.get(symbol)
        if market is None or not market.get("spot"):
            raise HTTPException(status_code=404, detail="Spot symbol was not found on the selected exchange")
        if not exchange.has.get("fetchOHLCV"):
            raise HTTPException(status_code=502, detail="OHLCV candles are not available on the selected exchange")
        return await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)

    return await _run_exchange(exchange_id, operation)


async def fetch_base_ticker(exchange_id: str, base: str) -> dict[str, Any]:
    normalized = normalize_exchange(exchange_id)
    base_code = base.strip().upper()
    preferred_quotes = ("USDT", "USD", "USDC", "EUR")

    async def operation(exchange):
        candidates = [
            market for market in exchange.markets.values()
            if market.get("spot") and market.get("active", True) and market.get("base") == base_code
        ]
        candidates.sort(key=lambda market: preferred_quotes.index(market.get("quote")) if market.get("quote") in preferred_quotes else len(preferred_quotes))
        if not candidates:
            return {"exchange": normalized, "exchange_name": EXCHANGES[normalized], "base": base_code, "available": False, "reason": "No active spot pair found"}
        market = candidates[0]
        ticker = await exchange.fetch_ticker(market["symbol"])
        return {
            "exchange": normalized,
            "exchange_name": EXCHANGES[normalized],
            "base": base_code,
            "symbol": ticker.get("symbol", market["symbol"]),
            "quote": market.get("quote"),
            "available": ticker.get("last") is not None,
            "last": ticker.get("last"),
            "bid": ticker.get("bid"),
            "ask": ticker.get("ask"),
            "change_percent_24h": ticker.get("percentage"),
            "timestamp": ticker.get("timestamp"),
        }

    try:
        return await _run_exchange(normalized, operation)
    except HTTPException as exc:
        return {"exchange": normalized, "exchange_name": EXCHANGES[normalized], "base": base_code, "available": False, "reason": exc.detail}