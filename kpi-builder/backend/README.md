# Backend &mdash; KPI Builder API

API em **FastAPI + uvicorn** (Python).

## Rodar localmente

Precisa de Python 3.10+.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # sobe em http://localhost:8000
```

Rotas:

- `GET /health` &mdash; health check, retorna `{ "status": "ok", ... }`
- `GET /` &mdash; mensagem raiz
- `GET /docs` &mdash; documentacao interativa (Swagger UI, gerada automaticamente)

Teste rapido:

```bash
curl http://localhost:8000/health
```

## Variaveis de ambiente

- `FRONTEND_ORIGIN` &mdash; URL do front pra liberar no CORS (ex: `https://kpi-builder.vercel.app`). Se nao definir, libera geral (`*`) &mdash; ok em dev, mas em producao coloque a URL certa.

Quando for conectar no banco, as credenciais entram aqui via `.env` (ja no `.gitignore`), nunca no codigo.

## Deploy

O uvicorn e um servidor que fica rodando, entao o backend nao vai no Vercel junto com o front. Opcoes gratuitas boas pra TCC:

- **Render** (https://render.com) &mdash; cria um "Web Service" apontando pra pasta `backend/`, com start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Railway** (https://railway.app) &mdash; parecido.

Depois do deploy, pegue a URL da API e coloque no front (variavel `NEXT_PUBLIC_API_URL` no Vercel).
