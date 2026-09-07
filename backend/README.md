# Backend — KPI Builder API

FastAPI + uvicorn. Precisa de Python 3.10+.

Da raiz do projeto, `make dev` sobe este serviço junto com o front. Para subir
só ele, `make dev-back`. Na mão:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Sobe em http://localhost:8000. Documentação automática em `/docs`.

As tabelas vêm das migrations do Alembic (`make migrar` na raiz), não de SQL
rodado à mão.

## Variáveis de ambiente

`SUPABASE_URL` e `DATABASE_URL` ficam no `backend/.env`.

`FRONTEND_ORIGIN` — origem liberada no CORS. Sem ela o CORS nem é ligado, o que
serve para a Vercel, onde os dois ficam no mesmo domínio.
