import asyncpg

from .config import DATABASE_URL

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        # O pooler em modo transaction não guarda prepared statements.
        _pool = await asyncpg.create_pool(
            DATABASE_URL, min_size=0, max_size=2, statement_cache_size=0
        )
    return _pool
