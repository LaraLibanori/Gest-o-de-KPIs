# KPI Builder

Plataforma web onde a pessoa **conecta um banco de dados e monta seus proprios dashboards de indicadores (KPIs), sem precisar programar**.

Projeto de TCC &mdash; Parte 5 (Desenvolvimento da aplicacao).

## Arquitetura

Monorepo com duas partes separadas:

```
kpi-builder/
├─ frontend/   → Next.js 15 (App Router) + React 19 + TypeScript   (deploy no Vercel)
└─ backend/    → FastAPI + uvicorn (Python)                        (deploy no Render/Railway)
```

O front conversa com o backend por HTTP. O health check da API mora no backend, em `GET /health`.

---

## Rodar tudo localmente

Abra **dois terminais**.

### 1) Backend (FastAPI) &mdash; porta 8000

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Testa: `curl http://localhost:8000/health` &rarr; `{ "status": "ok", ... }`
Docs automaticas: http://localhost:8000/docs

### 2) Frontend (Next.js) &mdash; porta 3000

```bash
cd frontend
npm install
cp .env.local.example .env.local   # aponta pro backend em localhost:8000
npm run dev
```

Abre http://localhost:3000 &mdash; a home mostra se a API esta online.

---

## Subir pro GitHub

O primeiro commit ja esta feito (o `.git` vem junto). Falta so criar o repo remoto e dar push. Troque `SEU-USUARIO` pelo dono do repo (ex: `LaraLibanori`):

1. Cria em https://github.com/new com nome `kpi-builder`, **sem** README/gitignore/license.
2. Na pasta do projeto:

```bash
git remote add origin https://github.com/SEU-USUARIO/kpi-builder.git
git branch -M main
git push -u origin main
```

---

## Deploy

### Frontend &rarr; Vercel

1. Conta em https://vercel.com (loga com o GitHub).
2. **Add New... > Project** e escolhe o repo `kpi-builder`.
3. Em **Root Directory**, seleciona a pasta **`frontend`** (importante, porque o repo tem duas pastas).
4. O Vercel reconhece Next.js sozinho. Em **Environment Variables**, adiciona:
   - `NEXT_PUBLIC_API_URL` = a URL publica do backend (depois de fazer o deploy dele).
5. **Deploy**. Cada `git push` na `main` vira deploy automatico.

### Backend &rarr; Render (ou Railway)

O uvicorn e um servidor que fica rodando, entao **nao** vai no Vercel junto com o front.

1. Em https://render.com, **New > Web Service** apontando pro mesmo repo.
2. **Root Directory:** `backend`
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Em variaveis de ambiente, adiciona `FRONTEND_ORIGIN` = a URL do front no Vercel (pro CORS).
6. Depois do deploy, copia a URL da API e coloca no `NEXT_PUBLIC_API_URL` do Vercel.

---

## Variaveis de ambiente (resumo)

| Onde     | Variavel             | Pra que                                  |
|----------|----------------------|------------------------------------------|
| frontend | `NEXT_PUBLIC_API_URL`| URL do backend que o front vai chamar    |
| backend  | `FRONTEND_ORIGIN`    | URL do front liberada no CORS            |

Credenciais de banco de dados **nunca** vao no codigo &mdash; entram em `.env` (local) ou nas Environment Variables do provedor.

---

## Proximos passos (rascunho)

- [ ] Endpoint no backend pra testar conexao com um banco (host, porta, usuario, senha)
- [ ] Leitura do schema (tabelas e colunas disponiveis)
- [ ] Editor de indicadores (metrica, agrupamento, filtro)
- [ ] Renderizacao dos graficos no dashboard (front)
- [ ] Autenticacao de usuarios
