import os
from pathlib import Path

import asyncpg

MIGRATIONS_DIR = Path(os.getenv("MIGRATIONS_DIR", "/app/migrations"))


async def apply_migrations() -> None:
    connection = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await connection.execute("SELECT pg_advisory_lock(716284019)")
        await connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        applied = {row["version"] for row in await connection.fetch("SELECT version FROM schema_migrations")}
        for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if migration_path.name in applied:
                continue
            sql = migration_path.read_text(encoding="utf-8")
            async with connection.transaction():
                await connection.execute(sql)
                await connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES ($1)",
                    migration_path.name,
                )
    finally:
        await connection.execute("SELECT pg_advisory_unlock(716284019)")
        await connection.close()
