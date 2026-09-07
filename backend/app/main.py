import os
from datetime import datetime, timezone

from fastapi import FastAPI, Response
from sqlalchemy import text

from .db import abrir_conexao
from .routers import conexoes, organizacoes, perfil

app = FastAPI(title="KPI Builder API", version="0.1.0")

# Na Vercel os dois ficam no mesmo domínio. CORS só é preciso no local.
frontend_origin = os.environ.get("FRONTEND_ORIGIN")
if frontend_origin:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

app.include_router(perfil.router)
app.include_router(organizacoes.router)
app.include_router(conexoes.router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "kpi-builder-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# health diz que subiu, ready diz que o banco responde.
@app.get("/ready")
async def ready(response: Response) -> dict:
    try:
        async with abrir_conexao() as conexao:
            role = await conexao.scalar(text("select current_user"))
    except Exception:  # noqa: BLE001 - qualquer falha aqui vira 503, nunca 500
        response.status_code = 503
        return {"status": "sem banco"}
    return {"status": "ok", "role": role}
