import os
from typing import Any

import httpx
from fastapi import HTTPException

BASE_URL = "https://api.twelvedata.com"


def _api_key() -> str:
    key = os.getenv("TWELVE_DATA_API_KEY", "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Brak TWELVE_DATA_API_KEY. Dodaj klucz w lokalnym pliku .env i uruchom ponownie Docker Compose.",
        )
    return key


async def _get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    request_params = {**params, "apikey": _api_key()}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(f"{BASE_URL}/{path}", params=request_params)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Twelve Data nie odpowiedziało na czas.") from exc
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        if status == 429:
            raise HTTPException(status_code=429, detail="Limit zapytań Twelve Data został osiągnięty.") from exc
        raise HTTPException(status_code=502, detail=f"Twelve Data zwróciło HTTP {status}.") from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="Nie udało się odczytać odpowiedzi Twelve Data.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=502, detail="Twelve Data zwróciło nieoczekiwany format.")
    if payload.get("status") == "error" or payload.get("code"):
        message = str(payload.get("message") or "Błąd dostawcy danych.")
        code = payload.get("code")
        if str(code) == "429":
            raise HTTPException(status_code=429, detail="Limit lub uprawnienia planu Twelve Data blokują to zapytanie.")
        raise HTTPException(status_code=502, detail=f"Twelve Data: {message[:220]}")
    return payload


async def search_symbols(query: str, limit: int = 20) -> list[dict[str, Any]]:
    payload = await _get("symbol_search", {"symbol": query.strip(), "outputsize": limit})
    results = payload.get("data", [])
    if not isinstance(results, list):
        return []
    return [
        {
            "symbol": item.get("symbol"),
            "name": item.get("instrument_name") or item.get("name") or item.get("symbol"),
            "exchange": item.get("exchange"),
            "mic_code": item.get("mic_code"),
            "country": item.get("country"),
            "currency": item.get("currency"),
            "instrument_type": item.get("instrument_type") or item.get("type"),
            "isin": item.get("isin"),
        }
        for item in results
        if isinstance(item, dict) and item.get("symbol") and item.get("mic_code")
    ]


async def fetch_time_series(
    symbol: str,
    exchange: str | None,
    mic_code: str | None,
    interval: str,
    outputsize: int,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "order": "ASC",
    }
    if mic_code:
        params["mic_code"] = mic_code
    elif exchange:
        params["exchange"] = exchange
    payload = await _get("time_series", params)
    values = payload.get("values", [])
    if not isinstance(values, list):
        raise HTTPException(status_code=502, detail="Twelve Data nie zwróciło szeregu cen.")
    return {"meta": payload.get("meta", {}), "values": values}
