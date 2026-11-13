"""Teste de ponta a ponta de verdade: sobe a API real, fala com um Postgres
real por HTTP real, e confere o caminho feliz completo (criar organização →
cadastrar conexão → ler catálogo → criar indicador com meta → montar
dashboard). Não usa o `app.dependency_overrides` que os testes do pytest
usam para pular a verificação do token.

A única coisa fingida aqui é o provedor de identidade: em vez do Supabase
Auth real, este script levanta um servidor HTTP mínimo que serve só o JWKS
(a chave pública), para a API conseguir validar um token que o próprio
script assina. Isso prova que o código de verificação de JWT funciona de
verdade (é o mesmo `app/auth.py` da produção), sem precisar de um projeto
Supabase. Deixar isso explícito é o ponto: ninguém deve ler o resultado
deste script como "login real testado" — login real depende do Supabase
Auth, que só roda com um projeto de verdade.

Uso:
    cd backend && python scripts/smoke_test.py

Precisa de um Postgres local, vazio, só para teste (mesma regra do
tests/conftest.py: só roda contra localhost/127.0.0.1). Variáveis opcionais:
    SMOKE_ADMIN_URL   (padrão postgresql://postgres:postgres@localhost:55432/postgres)
    SMOKE_APP_PORT    (padrão 8010, porta onde a API sobe para o teste)
"""

from __future__ import annotations

import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
import uuid
from contextlib import closing
from pathlib import Path

import asyncpg
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from jwt.algorithms import ECAlgorithm

RAIZ = Path(__file__).resolve().parent.parent

ADMIN_URL = os.environ.get(
    "SMOKE_ADMIN_URL", "postgresql://postgres:postgres@localhost:55432/postgres"
)
if not any(h in ADMIN_URL for h in ("@localhost:", "@127.0.0.1:")):
    raise SystemExit("este script só roda contra um Postgres local")

APP_PORT = int(os.environ.get("SMOKE_APP_PORT", "8010"))
APP_PASSWORD = "senha-smoke-" + uuid.uuid4().hex[:8]
APP_URL = ADMIN_URL.replace("postgres:postgres@", f"kpi_api:{APP_PASSWORD}@")

PASSOS: list[str] = []


def passo(texto: str) -> None:
    PASSOS.append(texto)
    print(f"  ✓ {texto}")


def falhar(texto: str) -> None:
    print(f"\n✗ FALHOU: {texto}", file=sys.stderr)
    sys.exit(1)


# --------------------------------------------------------------------------
# 1. Chave e "provedor de identidade" fake, só para assinar/validar o token
# --------------------------------------------------------------------------


def gerar_chave_e_jwks() -> tuple[bytes, dict]:
    priv = ec.generate_private_key(ec.SECP256R1())
    pem = priv.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    jwk = json.loads(ECAlgorithm(ECAlgorithm.SHA256).to_jwk(priv.public_key()))
    jwk.update(kid="smoke-1", use="sig", alg="ES256")
    return pem, {"keys": [jwk]}


def porta_livre() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def subir_jwks_fake(jwks: dict) -> tuple[http.server.HTTPServer, int]:
    corpo = json.dumps(jwks).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *a):  # silencio
            pass

    porta = porta_livre()
    servidor = http.server.HTTPServer(("127.0.0.1", porta), Handler)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return servidor, porta


def assinar_token(pem: bytes, sub: str, email: str, issuer: str) -> str:
    agora = int(time.time())
    return jwt.encode(
        {
            "sub": sub,
            "email": email,
            "role": "authenticated",
            "aud": "authenticated",
            "iss": issuer,
            "iat": agora,
            "exp": agora + 600,
        },
        pem,
        algorithm="ES256",
        headers={"kid": "smoke-1"},
    )


# --------------------------------------------------------------------------
# 2. Banco: schema auth mínimo + usuário de teste + "banco do cliente"
# --------------------------------------------------------------------------

STUB_AUTH = """
create schema if not exists auth;
create table if not exists auth.users (id uuid primary key, email text);
create or replace function auth.uid() returns uuid language sql stable as $$
  select (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')::uuid
$$;
"""


def aplicar_migrations() -> None:
    env = {
        **os.environ,
        "MIGRATIONS_DATABASE_URL": ADMIN_URL,
        "KPI_APP_PASSWORD": APP_PASSWORD,
    }
    resultado = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=RAIZ,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode != 0:
        falhar(f"alembic upgrade head falhou:\n{resultado.stdout}\n{resultado.stderr}")


async def preparar_banco(usuario_id: str, email: str) -> None:
    con = await asyncpg.connect(ADMIN_URL)
    try:
        await con.execute(STUB_AUTH)
    finally:
        await con.close()

    aplicar_migrations()

    con = await asyncpg.connect(ADMIN_URL)
    try:
        # A migration 0004 cria o role só na primeira vez; se o banco já
        # existia (outra rodada deste script, ou do pytest), a senha dele
        # pode ser outra. Garante que fica com a senha desta rodada.
        await con.execute(f"alter role kpi_api with password '{APP_PASSWORD}'")
        # Limpa sobra de uma rodada anterior deste mesmo script (o perfil
        # criado por trigger trava o e-mail como único).
        await con.execute("delete from auth.users where email = $1", email)
        await con.execute(
            "insert into auth.users (id, email) values ($1, $2)",
            uuid.UUID(usuario_id),
            email,
        )
        await con.execute("drop table if exists public.smoke_vendas")
        await con.execute(
            "create table public.smoke_vendas (id bigserial primary key, "
            "categoria text, valor_total numeric, vendida_em date)"
        )
        await con.execute(
            "insert into public.smoke_vendas (categoria, valor_total, vendida_em) "
            "select (array['bebidas','comida'])[1 + (n % 2)], "
            "(50 + n)::numeric, current_date - (n || ' days')::interval "
            "from generate_series(1, 30) n"
        )
    finally:
        await con.close()


def limpar_banco_sync() -> None:
    import asyncio

    async def _limpar():
        con = await asyncpg.connect(ADMIN_URL)
        try:
            await con.execute("drop table if exists public.smoke_vendas")
        finally:
            await con.close()

    asyncio.run(_limpar())


# --------------------------------------------------------------------------
# 3. Sobe a API real como subprocesso
# --------------------------------------------------------------------------


def subir_api(supabase_url: str) -> subprocess.Popen:
    env = {
        **os.environ,
        "DATABASE_URL": APP_URL,
        "MIGRATIONS_DATABASE_URL": ADMIN_URL,
        "KPI_APP_PASSWORD": APP_PASSWORD,
        "APP_SECRET_KEY": "4Gn3fF3bYQbQ8s0E7ZB2y9b6m8y0r9nE2p5u8v1w4x7=",
        "SUPABASE_URL": supabase_url,
        "PERMITIR_REDE_INTERNA": "1",
        "SEGREDO_SERVIDOR": "",
    }
    processo = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--port",
            str(APP_PORT),
            "--log-level",
            "warning",
        ],
        cwd=RAIZ,
        env=env,
    )
    base = f"http://127.0.0.1:{APP_PORT}"
    for _ in range(60):
        try:
            if httpx.get(f"{base}/health", timeout=1).status_code == 200:
                return processo
        except httpx.HTTPError:
            pass
        if processo.poll() is not None:
            falhar(
                "a API caiu ao subir — rode `uvicorn app.main:app` à mão para ver o erro"
            )
        time.sleep(0.5)
    processo.terminate()
    falhar("a API não respondeu em /health a tempo")
    raise SystemExit(1)  # inalcançável, só para o type checker


# --------------------------------------------------------------------------
# 4. O caminho feliz
# --------------------------------------------------------------------------


def rodar_caminho_feliz(token: str) -> None:
    base = f"http://127.0.0.1:{APP_PORT}"
    c = httpx.Client(
        base_url=base, headers={"Authorization": f"Bearer {token}"}, timeout=10
    )

    org = c.post("/organizacoes", json={"nome": "Acme Smoke"})
    if org.status_code != 201:
        falhar(f"criar organização: {org.status_code} {org.text}")
    org_id = org.json()["id"]
    passo("organização criada")

    base_conexoes = f"/organizacoes/{org_id}/conexoes"
    admin_host, admin_porta = _host_porta(ADMIN_URL)
    conexao = c.post(
        base_conexoes,
        json={
            "nome": "Banco de demonstração",
            "host": admin_host,
            "porta": admin_porta,
            "banco": "postgres",
            "usuario": "postgres",
            "senha": "postgres",
        },
    )
    if conexao.status_code != 201:
        falhar(f"criar conexão: {conexao.status_code} {conexao.text}")
    conexao_id = conexao.json()["id"]
    passo("conexão cadastrada")

    patch = c.patch(
        f"{base_conexoes}/{conexao_id}", json={"tabela_fato": "public.smoke_vendas"}
    )
    if patch.status_code != 200:
        falhar(f"definir tabela fato: {patch.status_code} {patch.text}")
    passo("tabela fato definida")

    catalogo = c.post(f"{base_conexoes}/{conexao_id}/catalogo")
    if catalogo.status_code != 201:
        falhar(f"ler catálogo: {catalogo.status_code} {catalogo.text}")
    campos = {campo["coluna"]: campo for campo in catalogo.json()}
    if "valor_total" not in campos:
        falhar("a coluna valor_total não apareceu no catálogo")
    passo(f"catálogo lido ({len(campos)} colunas classificadas)")

    base_ind = f"{base_conexoes}/{conexao_id}/indicadores"
    indicador = c.post(
        base_ind,
        json={"nome": "Receita total", "agregacao": "soma", "coluna": "valor_total"},
    )
    if indicador.status_code != 201:
        falhar(f"criar indicador: {indicador.status_code} {indicador.text}")
    indicador_id = indicador.json()["id"]
    passo("indicador criado")

    meta = c.patch(f"{base_ind}/{indicador_id}", json={"meta": 100})
    if meta.status_code != 200 or meta.json().get("meta") != 100.0:
        falhar(f"definir meta: {meta.status_code} {meta.text}")
    passo("meta do indicador definida")

    painel = c.get(f"{base_conexoes}/{conexao_id}/painel")
    if painel.status_code != 200:
        falhar(f"ler painel: {painel.status_code} {painel.text}")
    indicadores_no_painel = painel.json().get("indicadores", [])
    if not any(
        i["id"] == indicador_id and i.get("valor") is not None
        for i in indicadores_no_painel
    ):
        falhar("o indicador não apareceu calculado no painel")
    passo("painel calculou o indicador com valor real do banco")

    dashboard = c.post(f"/organizacoes/{org_id}/dashboards", json={"nome": "Vendas"})
    if dashboard.status_code != 201:
        falhar(f"criar dashboard: {dashboard.status_code} {dashboard.text}")
    dashboard_id = dashboard.json()["id"]
    passo("dashboard criado")

    vinculo = c.put(
        f"/organizacoes/{org_id}/dashboards/{dashboard_id}/indicadores",
        json={"indicadores": [indicador_id]},
    )
    if vinculo.status_code != 204:
        falhar(f"vincular indicador ao dashboard: {vinculo.status_code} {vinculo.text}")
    passo("indicador vinculado ao dashboard")

    detalhe = c.get(f"/organizacoes/{org_id}/dashboards/{dashboard_id}")
    if detalhe.status_code != 200:
        falhar(f"ler dashboard: {detalhe.status_code} {detalhe.text}")
    ids_no_dashboard = {i["id"] for i in detalhe.json().get("indicadores", [])}
    if indicador_id not in ids_no_dashboard:
        falhar("o dashboard não mostra o indicador vinculado")
    passo("dashboard confirmado com o indicador dentro")

    c.delete(f"/organizacoes/{org_id}")
    passo("organização de teste removida")


def _host_porta(url: str) -> tuple[str, int]:
    # postgresql://usuario:senha@host:porta/banco
    resto = url.split("@", 1)[1]
    host_porta = resto.split("/", 1)[0]
    host, porta = host_porta.split(":")
    return host, int(porta)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------


def main() -> None:
    import asyncio

    print("Smoke test de ponta a ponta (API real + Postgres real)\n")

    usuario_id = str(uuid.uuid4())
    email = "smoke@exemplo.com"
    pem, jwks = gerar_chave_e_jwks()
    servidor_jwks, porta_jwks = subir_jwks_fake(jwks)
    supabase_url = f"http://127.0.0.1:{porta_jwks}"
    issuer = f"{supabase_url}/auth/v1"
    token = assinar_token(pem, usuario_id, email, issuer)

    asyncio.run(preparar_banco(usuario_id, email))
    passo("banco de teste preparado (usuário + tabela de exemplo)")

    processo = subir_api(supabase_url)
    passo("API no ar")
    try:
        rodar_caminho_feliz(token)
    finally:
        processo.terminate()
        processo.wait(timeout=10)
        servidor_jwks.shutdown()
        limpar_banco_sync()

    print(
        f"\n✓ TUDO PASSOU ({len(PASSOS)} passos) — caminho feliz completo, de ponta a ponta."
    )


if __name__ == "__main__":
    main()
