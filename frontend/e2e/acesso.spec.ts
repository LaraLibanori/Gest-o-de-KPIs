import { expect, test } from "@playwright/test";

/**
 * Smoke tests de verdade: nenhuma chamada ao Supabase é mocada. O que dá
 * para testar sem um projeto Supabase (de teste ou real) é exatamente isto
 * — a tela de login renderizar e a proteção de rota funcionar antes de
 * qualquer tentativa de autenticar. Ver e2e/README.md para o que falta e
 * por quê (um caminho completo de login → cadastrar conexão → dashboard
 * via browser).
 */

test("tela de login mostra os dois modos e os campos esperados", async ({
  page,
}) => {
  await page.goto("/login");

  await expect(page.getByRole("tab", { name: "Entrar" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Criar conta" })).toBeVisible();
  await expect(page.getByLabel("E-mail")).toBeVisible();
  await expect(page.getByLabel("Senha")).toBeVisible();

  await page.getByRole("tab", { name: "Criar conta" }).click();
  await expect(
    page.getByText("A conta já fica ativa, sem confirmar e-mail."),
  ).toBeVisible();
});

test("visitar uma rota protegida sem sessão redireciona para o login", async ({
  page,
}) => {
  await page.goto("/conexoes");
  await expect(page).toHaveURL(/\/login/);
});

test("o painel de dashboards também exige login", async ({ page }) => {
  await page.goto("/dashboards");
  await expect(page).toHaveURL(/\/login/);
});

test("tentar entrar com credencial inexistente mostra erro, não quebra a página", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill(`smoke-${Date.now()}@exemplo.com`);
  await page.getByLabel("Senha").fill("senha-que-nao-existe");
  await page.getByRole("button", { name: "Entrar" }).click();

  // Sem um Supabase real por trás, a chamada falha (rede/indisponível) ou
  // responde "credenciais inválidas" — qualquer um dos dois é uma falha
  // tratada na tela, nunca uma página em branco ou um erro não capturado.
  await expect(page.getByRole("alert")).toBeVisible({ timeout: 15_000 });
  await expect(page).toHaveURL(/\/login/);
});
