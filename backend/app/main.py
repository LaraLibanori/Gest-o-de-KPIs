import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .db import abrir_conexao
from .routers import conexoes, organizacoes, perfil

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
registro = logging.getLogger("kpi")

app = FastAPI(title="KPI Builder API", version="0.1.0")


# Um identificador por requisicao, para achar o erro no log depois.
@app.middleware("http")
async def identificar(request: Request, chamar):
    request.state.pedido = uuid.uuid4().hex[:8]
    resposta = await chamar(request)
    resposta.headers["X-Request-Id"] = request.state.pedido
    return resposta


@app.exception_handler(Exception)
async def falha(request: Request, erro: Exception):
    pedido = getattr(request.state, "pedido", "")
    registro.exception("%s %s %s", pedido, request.method, request.url.path)
    return JSONResponse(
        {"detail": "erro interno"},
        status_code=500,
        headers={"X-Request-Id": pedido},
    )


# Na Vercel os dois ficam no mesmo domínio. CORS só é preciso no local.
frontend_origin = os.environ.get("FRONTEND_ORIGIN")
if frontend_origin:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
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
