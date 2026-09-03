"""
API do KPI Builder (FastAPI).

Rodar em desenvolvimento:
    uvicorn app.main:app --reload

Docs interativas (Swagger): http://localhost:8000/docs
"""
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="KPI Builder API",
    description="Backend do TCC: conectar banco de dados e montar dashboards de KPI sem programar.",
    version="0.1.0",
)

# CORS: libera o front (Next.js) a chamar a API.
# Em producao, troque "*" pela URL do front no Vercel via env FRONTEND_ORIGIN.
frontend_origin = os.getenv("FRONTEND_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin] if frontend_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["infra"])
def health() -> dict:
    """Health check da API. Usado por monitoramento / deploy pra ver se esta no ar."""
    return {
        "status": "ok",
        "service": "kpi-builder-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/", tags=["infra"])
def root() -> dict:
    return {"message": "KPI Builder API. Veja /docs para a documentacao."}
