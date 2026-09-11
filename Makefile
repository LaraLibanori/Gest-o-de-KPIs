# Comandos do projeto. Rode da raiz, e no Windows pelo Git Bash.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := ajuda

# O venv guarda os executaveis em Scripts no Windows e em bin no resto.
ifeq ($(OS),Windows_NT)
  PY := $(CURDIR)/backend/.venv/Scripts/python.exe
  PYTHON := python
else
  PY := $(CURDIR)/backend/.venv/bin/python
  PYTHON := python3
endif

# Cada projeto tem o seu arquivo de ambiente e nenhum dos dois vai para o git.
ENV_FRONT := frontend/.env.local
ENV_BACK := backend/.env

# Portas do local. Da para trocar: make dev PORTA_FRONT=3001
PORTA_FRONT ?= 3000
PORTA_BACK ?= 8000
URL_FRONT := http://localhost:$(PORTA_FRONT)
URL_BACK := http://localhost:$(PORTA_BACK)

ESCOPO := ivanabreuelementardis-projects
VERCEL := vercel --scope $(ESCOPO)

# O que precisa estar cadastrado na Vercel para o deploy funcionar.
VARS_FRONT := NEXT_PUBLIC_SUPABASE_URL NEXT_PUBLIC_SUPABASE_ANON_KEY
VARS_BACK := SUPABASE_URL DATABASE_URL APP_SECRET_KEY CEREBRAS_API_KEY GROQ_API_KEY

# Le o arquivo de ambiente ignorando o \r que o Windows deixa no fim da linha.
CARREGAR = set -a; . <(tr -d '\r' < $(1)); set +a

.PHONY: ajuda env-init instalar dev dev-front dev-back checar checar-front checar-back \
	env env-front env-back migrar migracao migracoes exemplo testes lint preview producao testar portas limpar

ajuda:
	@echo "make env-init   cria os .env a partir dos exemplos"
	@echo "make instalar   instala as dependencias do front e do back"
	@echo "make dev        sobe os dois locais (front :$(PORTA_FRONT), back :$(PORTA_BACK))"
	@echo "make checar     lint, typecheck e build, igual ao CI"
	@echo "make testes     roda os testes do backend (precisa de um Postgres vazio)"
	@echo "make migrar     aplica as migrations pendentes no banco"
	@echo "make migracao m=\"texto\"   cria uma migration a partir do models.py"
	@echo "make migracoes  mostra a migration atual e o historico"
	@echo "make exemplo    cria a base de exemplo, no papel de banco do cliente"
	@echo "make env        manda as variaveis dos .env para a Vercel"
	@echo "make preview    publica um preview e testa as rotas"
	@echo "make producao   publica em producao e testa as rotas"
	@echo "make testar URL=https://...   confere as rotas de uma URL qualquer"
	@echo "make limpar     apaga build, cache e venv"

env-init:
	@test -f $(ENV_FRONT) || { cp frontend/.env.local.example $(ENV_FRONT); echo "criado $(ENV_FRONT)"; }
	@test -f $(ENV_BACK) || { cp backend/.env.example $(ENV_BACK); echo "criado $(ENV_BACK)"; }
	@echo "preencha os dois com os dados do Supabase"

instalar:
	cd frontend && npm install
	@if command -v uv >/dev/null 2>&1; then \
	  uv venv backend/.venv; \
	  uv pip install --python "$(PY)" -r backend/requirements.txt -r backend/requirements-dev.txt; \
	else \
	  $(PYTHON) -m venv backend/.venv; \
	  "$(PY)" -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt; \
	fi

# O Next le o frontend/.env.local sozinho; o uvicorn precisa carregar.
dev: portas
	@echo "front $(URL_FRONT)  back $(URL_BACK)"
	@trap 'kill 0' EXIT; \
	$(MAKE) --no-print-directory dev-back & \
	$(MAKE) --no-print-directory dev-front & \
	wait

# Sem o --port o Next pula de porta e o CORS do backend erra o alvo.
dev-front:
	cd frontend && NEXT_PUBLIC_API_URL=$(URL_BACK) npm run dev -- --port $(PORTA_FRONT)

dev-back:
	$(call CARREGAR,$(ENV_BACK)); \
	export FRONTEND_ORIGIN=$(URL_FRONT); \
	cd backend && "$(PY)" -m uvicorn app.main:app --reload --port $(PORTA_BACK)

portas:
	@for porta in $(PORTA_BACK) $(PORTA_FRONT); do \
	  if (exec 3<>/dev/tcp/127.0.0.1/$$porta) 2>/dev/null; then \
	    echo "a porta $$porta ja esta em uso, feche o processo antes"; exit 1; \
	  fi; \
	done

# O alembic usa o MIGRATIONS_DATABASE_URL, que aponta para o session pooler.
migrar:
	$(call CARREGAR,$(ENV_BACK)); \
	cd backend && "$(PY)" -m alembic upgrade head

migracao:
	@test -n "$(m)" || { echo 'uso: make migracao m="o que mudou"'; exit 1; }
	@$(call CARREGAR,$(ENV_BACK)); \
	cd backend && "$(PY)" -m alembic revision --autogenerate -m "$(m)"

migracoes:
	@$(call CARREGAR,$(ENV_BACK)); \
	cd backend && "$(PY)" -m alembic current && "$(PY)" -m alembic history

exemplo:
	@$(call CARREGAR,$(ENV_BACK)); \
	[ -n "$${DEMO_LEITOR_PASSWORD:-}" ] || { echo "falta DEMO_LEITOR_PASSWORD em $(ENV_BACK)"; exit 1; }; \
	psql "$$MIGRATIONS_DATABASE_URL" -q -v ON_ERROR_STOP=1 \
	  -v senha="$$DEMO_LEITOR_PASSWORD" -f supabase/exemplo.sql
	@echo "base de exemplo criada em exemplo.vendas"

# Precisa de um Postgres vazio na 55432, veja o README.
testes:
	cd backend && "$(PY)" -m pytest -q

checar: lint checar-front checar-back

lint:
	cd backend && "$(PY)" -m ruff check app alembic tests
	cd backend && "$(PY)" -m ruff format --check app alembic tests

# Build antes do tsc: e ele que regenera o .next/types.
checar-front:
	cd frontend && npm run build
	cd frontend && npx tsc --noEmit

checar-back:
	cd backend && "$(PY)" -c "import app.main"

# Cadastra em producao e em preview, sobrescrevendo o que ja existir.
env: env-front env-back

env-front:
	@$(call CARREGAR,$(ENV_FRONT)); \
	for nome in $(VARS_FRONT); do \
	  valor="$${!nome:-}"; \
	  [ -n "$$valor" ] || { echo "falta $$nome em $(ENV_FRONT)"; exit 1; }; \
	  case "$$valor" in *xxxxxxxx*|*SENHA*|"eyJ...") echo "$$nome ainda esta com o valor de exemplo em $(ENV_FRONT)"; exit 1;; esac; \
	  for alvo in production preview; do \
	    printf '%s' "$$valor" | $(VERCEL) env add "$$nome" "$$alvo" --force --yes >/dev/null; \
	  done; \
	  echo "ok  $$nome"; \
	done

env-back:
	@$(call CARREGAR,$(ENV_BACK)); \
	for nome in $(VARS_BACK); do \
	  valor="$${!nome:-}"; \
	  [ -n "$$valor" ] || { echo "falta $$nome em $(ENV_BACK)"; exit 1; }; \
	  case "$$valor" in *xxxxxxxx*|*SENHA*|"eyJ...") echo "$$nome ainda esta com o valor de exemplo em $(ENV_BACK)"; exit 1;; esac; \
	  for alvo in production preview; do \
	    printf '%s' "$$valor" | $(VERCEL) env add "$$nome" "$$alvo" --force --yes >/dev/null; \
	  done; \
	  echo "ok  $$nome"; \
	done

preview:
	@url=$$($(VERCEL) deploy --yes 2>&1 | grep -oE 'https://[a-z0-9.-]+\.vercel\.app' | tail -1); \
	echo "preview: $$url"; \
	$(MAKE) --no-print-directory testar URL=$$url

producao:
	@url=$$($(VERCEL) deploy --prod --yes 2>&1 | grep -oE 'https://[a-z0-9.-]+\.vercel\.app' | tail -1); \
	echo "producao: $$url"; \
	$(MAKE) --no-print-directory testar URL=$$url

# vercel curl porque o preview fica atras da protecao da Vercel.
testar:
	@test -n "$(URL)" || { echo "uso: make testar URL=https://exemplo.vercel.app"; exit 1; }
	@falhou=; \
	for par in /api/health=200 /api/ready=200 /login=200 /=307; do \
	  rota=$${par%%=*}; esperado=$${par##*=}; \
	  codigo=$$(vercel curl "$(URL)$$rota" -s -o /dev/null -w '%{http_code}' 2>/dev/null); \
	  if [ "$$codigo" = "$$esperado" ]; then echo "ok   $$rota -> $$codigo"; \
	  else echo "erro $$rota -> $$codigo (esperado $$esperado)"; falhou=1; fi; \
	done; \
	[ -z "$$falhou" ] || exit 1

limpar:
	rm -rf frontend/.next frontend/node_modules frontend/tsconfig.tsbuildinfo
	rm -rf backend/.venv
	find backend -name __pycache__ -type d -exec rm -rf {} +
