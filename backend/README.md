# Backend — KPI Builder API

FastAPI + uvicorn. Precisa de Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Sobe em http://localhost:8000. Documentação automática em `/docs`.

Rotas: `GET /health`, `GET /`.

## Variáveis de ambiente

`FRONTEND_ORIGIN` — origem liberada no CORS. Sem ela, assume `http://localhost:3000`.
