# KPI Builder

Plataforma web onde a pessoa conecta um banco de dados e monta seus próprios
dashboards de indicadores, sem precisar programar.

Projeto de TCC — Parte 5 (Desenvolvimento da aplicação).

No ar: <https://kpi-builder-ivanabreuelementardis-projects.vercel.app>

Conta para testar:

```
e-mail   admin@kpibuilder.app
senha    admin123
```

Também dá para criar a sua na própria tela de login: a conta já entra ativa,
sem confirmar e-mail.

Por enquanto estão prontos o login, as organizações e o cadastro das conexões.
A leitura da tabela fato e os indicadores vêm depois.

## Como funciona

O login é feito pelo Supabase Auth, direto no navegador. O front guarda a
sessão em cookie e manda o token em toda chamada para a API. O FastAPI confere
esse token e só então consulta o banco.

```
Next.js  ──login──>  Supabase Auth
   │
   └──/api + token──>  FastAPI  ──SQL──>  Postgres (Supabase)
```

Os dois sobem juntos na Vercel, no mesmo domínio: `/api/*` vai para o backend
e o resto para o front, conforme o `vercel.json`.

```
frontend/   Next.js 15 (App Router) + React 19 + TypeScript + shadcn/ui
backend/    FastAPI + SQLAlchemy + Alembic
supabase/   seed.sql, para rodar no SQL Editor
```

Tabelas:

```
perfis                 dados do usuário na aplicação
organizacoes           o espaço compartilhado
organizacao_membros    quem participa de qual organização
convites               quem foi convidado e ainda não tem conta
conexoes               bancos da empresa, com a senha cifrada
catalogo_campos        colunas da tabela fato e o papel de cada uma
```

O schema `exemplo` tem uma base fictícia que faz o papel de banco do cliente,
com um usuário de leitura à parte. `make exemplo` cria.

Tudo pendura na organização, não no usuário. É assim que duas pessoas veem os
mesmos dados.

## Rodar local

Os comandos estão no `Makefile`. No Windows, use o Git Bash.

```bash
make env-init   # cria frontend/.env.local e backend/.env
make instalar   # dependências do front e do back
make migrar     # cria as tabelas no Supabase
make dev        # front em :3000 e back em :8000
```

Preencha os dois arquivos de ambiente antes do `make dev`. Use a string do
**pooler** do Supabase, não a conexão direta. `make ajuda` lista o resto.

Para conferir se compila, o mesmo que roda no CI:

```bash
make checar
```

Os testes cobrem o que mais importa: que uma pessoa não veja os dados da outra.
Precisam de um Postgres vazio à parte.

```bash
docker run -d -e POSTGRES_PASSWORD=postgres -p 55432:5432 postgres:16
make testes
```

## Migrations

O banco é descrito em `backend/app/models.py` e versionado pelo Alembic.

```bash
make migrar                      # aplica o que estiver pendente
make migracao m="cria conexoes"  # gera a migration a partir do models.py
make migracoes                   # migration atual e histórico
```

## Deploy

Sai da máquina, pela CLI da Vercel.

```bash
make env        # manda as variáveis do .env para a Vercel
make preview    # publica um preview
make producao   # publica em produção
```

Os dois últimos terminam conferindo as rotas principais.

## Variáveis de ambiente

| Onde     | Variável                        | Para quê                            |
|----------|---------------------------------|-------------------------------------|
| frontend | `NEXT_PUBLIC_SUPABASE_URL`      | URL do projeto no Supabase          |
| frontend | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | chave pública, usada no login       |
| backend  | `SUPABASE_URL`                  | usada para validar o token          |
| backend  | `DATABASE_URL`                  | conexão da API                      |
| backend  | `APP_SECRET_KEY`                | cifra a senha de cada conexão       |
| backend  | `MIGRATIONS_DATABASE_URL`       | só para o Alembic, fica na máquina  |
| backend  | `KPI_APP_PASSWORD`              | só para a migration que cria o usuário do banco |
| backend  | `DEMO_LEITOR_PASSWORD`          | só para criar a base de exemplo |

As duas últimas não vão para a Vercel.

## Acesso

São duas camadas. Na aplicação, cada rota confere se você participa da
organização. No banco, a API conecta com um usuário sem privilégio de
administrador, e as políticas de RLS filtram as linhas pelo usuário da sessão.

## Endpoints

| Método | Rota                                              |
|--------|---------------------------------------------------|
| GET    | `/api/health`                                     |
| GET    | `/api/ready`                                      |
| GET    | `/api/perfil`                                     |
| GET    | `/api/organizacoes`                               |
| POST   | `/api/organizacoes`                               |
| DELETE | `/api/organizacoes/{id}`                          |
| GET    | `/api/organizacoes/{id}/membros`                  |
| DELETE | `/api/organizacoes/{id}/membros/{usuario_id}`     |
| GET    | `/api/organizacoes/{id}/convites`                 |
| POST   | `/api/organizacoes/{id}/convites`                 |
| DELETE | `/api/organizacoes/{id}/convites/{convite_id}`    |
| GET    | `/api/organizacoes/{id}/conexoes`                 |
| POST   | `/api/organizacoes/{id}/conexoes`                 |
| PATCH  | `/api/organizacoes/{id}/conexoes/{cid}`           |
| POST   | `/api/organizacoes/{id}/conexoes/{cid}/verificar` |
| GET    | `/api/organizacoes/{id}/conexoes/{cid}/catalogo`  |
| POST   | `/api/organizacoes/{id}/conexoes/{cid}/catalogo`  |
| PATCH  | `/api/.../catalogo/{campo}`                       |
| DELETE | `/api/organizacoes/{id}/conexoes/{cid}`           |

Menos `/health` e `/ready`, todas pedem `Authorization: Bearer <token>`.

Dá para convidar quem ainda não tem conta: o convite fica guardado e a pessoa
entra na organização quando se cadastrar.

## O que falta

- [x] Ler os metadados da tabela fato e sugerir métricas e dimensões
- [ ] Assistente em etapas para cadastrar a conexão
- [ ] Sugestão de rótulo e papel por LLM
- [ ] Definição de KPIs e de campos calculados
- [ ] Dashboards com os indicadores da organização
