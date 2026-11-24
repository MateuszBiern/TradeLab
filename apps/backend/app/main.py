import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.market import router as market_router
from app.api.instruments import router as instruments_router
from app.api.research import router as research_router
from app.core.migrations import apply_migrations


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await apply_migrations()
    yield


app = FastAPI(title="TradeLab AI API", version="0.4.0", lifespan=lifespan)

origins = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(market_router)
app.include_router(instruments_router)
app.include_router(research_router)


@app.get("/api/v1/health")
async def health():
    database_ok = False
    redis_ok = False

    try:
        connection = await asyncpg.connect(os.environ["DATABASE_URL"])
        await connection.close()
        database_ok = True
    except Exception:
        pass

    try:
        client = Redis.from_url(os.environ["REDIS_URL"])
        redis_ok = bool(await client.ping())
        await client.aclose()
    except Exception:
        pass

    result = {"status": "ok" if database_ok and redis_ok else "degraded", "database": database_ok, "redis": redis_ok}
    if not database_ok or not redis_ok:
        raise HTTPException(status_code=503, detail=result)
    return result


@app.get("/api/v1/overview")
async def overview():
    return {
        "product": "TradeLab AI",
        "mode": "global_research",
        "trading_enabled": False,
        "agents": [],
        "opportunities": [],
    }
