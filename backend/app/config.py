import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Chave Fernet que cifra a senha do banco de cada conexao.
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY", "")

# So para desenvolvimento, quando o banco de teste roda na propria maquina.
PERMITIR_REDE_INTERNA = os.environ.get("PERMITIR_REDE_INTERNA") == "1"

# O alembic precisa de conexao de sessao, na porta 5432.
MIGRATIONS_DATABASE_URL = os.environ.get("MIGRATIONS_DATABASE_URL", "") or DATABASE_URL

JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
ISSUER = f"{SUPABASE_URL}/auth/v1"
AUDIENCE = "authenticated"


OBRIGATORIAS = ("SUPABASE_URL", "DATABASE_URL", "APP_SECRET_KEY")


# Falta de variavel derruba o processo no boot, e nao na primeira requisicao.
def conferir_ambiente() -> None:
    faltando = [nome for nome in OBRIGATORIAS if not os.environ.get(nome)]
    if faltando:
        raise RuntimeError(f"faltam variáveis de ambiente: {', '.join(faltando)}")
    if PERMITIR_REDE_INTERNA and os.environ.get("VERCEL_ENV") == "production":
        raise RuntimeError("PERMITIR_REDE_INTERNA não pode ficar ligado em produção")


def url_asyncpg(url: str) -> str:
    return url.replace("postgresql://", "postgresql+asyncpg://", 1)
