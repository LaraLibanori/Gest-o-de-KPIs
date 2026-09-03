import os
from datetime import datetime, timezone

from fastapi import FastAPI

from .routers import dashboards, indicadores

app = FastAPI(title="KPI Builder API", version="0.1.0")

# Na Vercel os dois ficam no mesmo domínio. CORS só é preciso no local.
frontend_origin = os.environ.get("FRONTEND_ORIGIN")
if frontend_origin:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[frontend_origin],
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(dashboards.router)
app.include_router(indicadores.router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "kpi-builder-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
