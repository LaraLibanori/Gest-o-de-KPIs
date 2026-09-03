import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
ISSUER = f"{SUPABASE_URL}/auth/v1"
AUDIENCE = "authenticated"
