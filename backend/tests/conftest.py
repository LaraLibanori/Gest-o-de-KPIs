import os
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
import pytest

RAIZ = Path(__file__).resolve().parent.parent

ADMIN = os.environ.get(
    "MIGRATIONS_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:55432/postgres",
)
SENHA_APP = os.environ.get("KPI_APP_PASSWORD", "senha-de-teste")
APP = ADMIN.replace("postgres:postgres@", f"kpi_api:{SENHA_APP}@")

os.environ["MIGRATIONS_DATABASE_URL"] = ADMIN
os.environ["KPI_APP_PASSWORD"] = SENHA_APP
os.environ["DATABASE_URL"] = APP
os.environ.setdefault("SUPABASE_URL", "https://exemplo.supabase.co")
os.environ.setdefault("APP_SECRET_KEY", "tNJCGQ4WbxI1PD7mQOiae-rz3HtcFeZR7NL9q5U8tTA=")

# No Supabase o schema auth ja existe; aqui ele e criado a mao.
STUB = """
drop schema if exists public cascade;
create schema public;
drop schema if exists auth cascade;
create schema auth;
create table auth.users (id uuid primary key, email text);
create function auth.uid() returns uuid language sql stable as $$
  select (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')::uuid
$$;
"""


@pytest.fixture(scope="session")
def banco():
    import asyncio

    async def preparar():
        con = await asyncpg.connect(ADMIN)
        await con.execute(STUB)
        await con.close()

    asyncio.run(preparar())
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ,
        check=True,
        capture_output=True,
    )
    return APP


@pytest.fixture
async def conexao(banco):
    con = await asyncpg.connect(banco)
    yield con
    await con.close()


@pytest.fixture
async def admin(banco):
    con = await asyncpg.connect(ADMIN)
    yield con
    await con.close()


@pytest.fixture
async def limpar(admin):
    await admin.execute("delete from organizacoes")
    await admin.execute("delete from auth.users")


async def criar_usuario(admin, email: str) -> uuid.UUID:
    # O trigger da migration cria o perfil e converte os convites pendentes.
    return await admin.fetchval(
        "insert into auth.users (id, email) values (gen_random_uuid(), $1) returning id",
        email.lower(),
    )


@pytest.fixture
def cliente(banco, limpar):
    from httpx import ASGITransport, AsyncClient

    from app.auth import User, get_user
    from app.main import app

    def fabricar(usuario_id: uuid.UUID | None, email: str = ""):
        if usuario_id is None:
            app.dependency_overrides.pop(get_user, None)
        else:
            app.dependency_overrides[get_user] = lambda: User(
                id=usuario_id, email=email
            )
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://teste")

    yield fabricar
    app.dependency_overrides.clear()
