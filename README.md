# KPI Builder

Plataforma web onde a pessoa conecta um banco de dados e monta seus próprios
dashboards de indicadores, sem precisar programar.

Projeto de TCC — Parte 5 (Desenvolvimento da aplicação).

## Como funciona

O login é feito pelo Supabase Auth, direto no navegador. O front guarda a
sessão em cookie e manda o token do Supabase em toda chamada para a API. O
FastAPI confere esse token, descobre quem é o usuário e só então roda as
queries no Postgres do Supabase.

```
Next.js  ──login──>  Supabase Auth
   │
   └──/api + token──>  FastAPI  ──SQL──>  Postgres (Supabase)
```

```
frontend/   Next.js 15 (App Router) + React 19 + TypeScript
backend/    FastAPI + asyncpg
supabase/   schema.sql e seed.sql, para rodar no SQL Editor
```

Os dois sobem juntos na Vercel, no mesmo domínio: `/api/*` vai para o backend
e o resto para o front. A configuração está no `vercel.json`.

## Configurar o Supabase

1. Crie um projeto em https://supabase.com.
2. No **SQL Editor**, rode `supabase/schema.sql`.
3. Crie sua conta pela tela de login do app.
4. Rode `supabase/seed.sql` (troque o e-mail pelo seu) para ter dados de teste.

## Rodar local

Copie os exemplos de variáveis e preencha com as chaves do seu projeto:

```bash
cp frontend/.env.local.example frontend/.env.local
cp backend/.env.example backend/.env
```

Com a CLI da Vercel os dois serviços sobem juntos em http://localhost:3000:

```bash
npm i -g vercel
vercel dev
```

Ou separado, em dois terminais:

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
FRONTEND_ORIGIN=http://localhost:3000 uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

Rodando separado, descomente `NEXT_PUBLIC_API_URL` no `.env.local`.

## Variáveis de ambiente

| Onde     | Variável                        | Para quê                          |
|----------|---------------------------------|-----------------------------------|
| frontend | `NEXT_PUBLIC_SUPABASE_URL`      | URL do projeto no Supabase        |
| frontend | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | chave pública, usada no login     |
| backend  | `SUPABASE_URL`                  | usada para validar o token        |
| backend  | `DATABASE_URL`                  | conexão com o Postgres (pooler)   |

A `service_role key` não é usada em lugar nenhum e não deve ir para o front.

## Endpoints

| Método | Rota                                     |
|--------|------------------------------------------|
| GET    | `/api/health`                            |
| GET    | `/api/dashboards`                        |
| POST   | `/api/dashboards`                        |
| DELETE | `/api/dashboards/{id}`                   |
| GET    | `/api/dashboards/{id}/indicadores`       |
| POST   | `/api/dashboards/{id}/indicadores`       |
| GET    | `/api/indicadores/{id}/valor`            |
| DELETE | `/api/indicadores/{id}`                  |

Menos o `/health`, todas exigem o header `Authorization: Bearer <token>`.

## O que falta

- [ ] Conectar um banco externo do usuário, além das tabelas do Supabase
- [ ] Filtros e agrupamento por período nos indicadores
- [ ] Gráficos, hoje o dashboard só mostra o número
