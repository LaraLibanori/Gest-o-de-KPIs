import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Chave Fernet que cifra a senha do banco de cada conexao.
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "")

# O alembic precisa de conexao de sessao, na porta 5432.
MIGRATIONS_DATABASE_URL = os.environ.get("MIGRATIONS_DATABASE_URL", "") or DATABASE_URL

JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
ISSUER = f"{SUPABASE_URL}/auth/v1"
AUDIENCE = "authenticated"


def url_asyncpg(url: str) -> str:
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)
