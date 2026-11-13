# E2E (Playwright)

`acesso.spec.ts` sobe o build de produção do Next (`npm run start`) e testa,
pelo navegador de verdade, sem nenhuma chamada mocada:

- a tela de login mostra os dois modos (entrar/criar conta) e os campos
  certos;
- uma rota protegida (`/conexoes`, `/dashboards`) redireciona para `/login`
  quando não há sessão — é o `AppLayout` chamando `supabase.auth.getUser()`
  de verdade;
- uma tentativa de login sem um Supabase real por trás falha de um jeito
  tratado na tela (alerta visível), não com página em branco ou erro não
  capturado.

Roda com `npm run test:e2e` (precisa de `npx playwright install --with-deps
chromium` antes, uma vez).

## O que não está aqui: login → conexão → indicador → dashboard pelo navegador

O login deste projeto passa inteiro pelo servidor do Next
(`src/app/auth/entrar/route.ts` chama `supabase.auth.signInWithPassword` do
lado do servidor, nunca do navegador) e guarda a sessão num cookie
`httpOnly` — desenho pensado para o token nunca aparecer no navegador. Isso
é ótimo para segurança e péssimo para testar sem depender de um Supabase
real: não existe chamada de rede do *browser* para interceptar com
`page.route()`, porque a chamada é feita pelo processo do Next, não pelo
Chromium.

Para fazer esse teste de verdade sem gastar as credenciais reais (que são
do Supabase do Ivan, fora deste repositório), o caminho é o mesmo princípio
já usado em `backend/scripts/smoke_test.py`: trocar só o provedor de
identidade por um fake local, e deixar todo o resto — Next, FastAPI,
Postgres — de verdade. Concretamente, faltam:

1. Um servidor HTTP mínimo que imite o Supabase Auth (GoTrue) nos quatro
   endpoints que o `@supabase/auth-js` usado aqui chama: `POST
   /auth/v1/token?grant_type=password` (login), `POST /auth/v1/signup`,
   `GET /auth/v1/user` e `GET /auth/v1/.well-known/jwks.json`. As duas
   primeiras precisam devolver `{access_token, refresh_token, expires_in,
   token_type, user}` no formato que o `@supabase/auth-js` espera (função
   `hasSession` em `node_modules/@supabase/auth-js/dist/main/lib/fetch.js`
   — vale ler antes de implementar, para não montar algo incompatível).
2. O `access_token` emitido precisa ser um JWT ES256 de verdade, verificável
   pelo `/auth/v1/.well-known/jwks.json` do mesmo servidor fake — exatamente
   a chave que `backend/scripts/smoke_test.py` já gera e assina. Isso é o
   que permite o teste ir além do login: com esse token, as chamadas reais
   que o navegador faz via `/servidor/*` continuam até o FastAPI de
   verdade, que valida o JWT do mesmo jeito que validaria um token real do
   Supabase.
3. Apontar `SUPABASE_URL` do Next **e** do backend (`uvicorn`) para esse
   mesmo servidor fake, e subir os três processos juntos no
   `playwright.config.ts` (`webServer` aceita uma lista).

Vale a pena fazer — é o que prova de ponta a ponta que o assistente de
cadastro, a classificação de colunas e o painel funcionam também pela tela,
não só pela API. Não entrou nesta rodada porque monta três processos
coordenados (servidor fake + API + Next) e eu preferi entregar algo que
já corro e confio, em vez de um teste de três camadas que eu não conseguia
validar de verdade neste ambiente (aqui o sandbox bloqueia o download do
Chromium do Playwright — os testes acima foram só conferidos com `playwright
test --list`, a execução real depende do CI). Enquanto isso não existe, a
evidência de que o caminho completo funciona pela tela vem de duas fontes
reais: `make e2e` (prova a lógica de ponta a ponta pela API) e a aplicação
do roteiro em `docs/avaliacao-de-usabilidade.md` com participantes de
verdade (prova a UI).
