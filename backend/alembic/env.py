import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.config import MIGRATIONS_DATABASE_URL, url_asyncpg
from app.models import Base

config = context.config
config.set_main_option("sqlalchemy.url", url_asyncpg(MIGRATIONS_DATABASE_URL))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# O schema auth e do Supabase: as migrations nao mexem nele.
def incluir(objeto, nome, tipo, reflexo, comparado):
    if tipo == "table":
        return objeto.schema in (None, "public")
    return True


def rodar_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        include_object=incluir,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def aplicar(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=incluir,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def rodar_online() -> None:
    motor = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )
    async with motor.connect() as conexao:
        await conexao.run_sync(aplicar)
    await motor.dispose()


if context.is_offline_mode():
    rodar_offline()
else:
    asyncio.run(rodar_online())
