import { defineConfig, devices } from "@playwright/test";

/**
 * Smoke tests reais (sem mock de login — ver e2e/README.md para o porquê).
 * Sobe o build de produção do Next e roda contra ele.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
    trace: "on-first-retry",
  },
  webServer: {
    command: "npm run start -- --port 3100",
    url: "http://127.0.0.1:3100/login",
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
    env: {
      SUPABASE_URL: "https://smoke-test.invalid",
      SUPABASE_ANON_KEY: "chave-de-smoke-test-nao-real",
      SEGREDO_SERVIDOR: "",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
