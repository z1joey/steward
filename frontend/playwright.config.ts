import { defineConfig } from "@playwright/test";

/**
 * Playwright e2e（TA-T3 起落用例）：webServer 自动拉起
 * - 前端 Vite :8080（/api 代理 → localhost:8000）
 * - 后端 uvicorn :8000，独立 e2e 库 steward_e2e（写真实数据，与 dev/test 库隔离）
 * E2E_BASE_URL 指向他处时跳过前端 server（后端仍需本机 :8000 可用）。
 */
const E2E_DB = "postgresql+psycopg://localhost/steward_e2e";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    locale: "zh-CN",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: [
    ...(process.env.E2E_BASE_URL
      ? []
      : [
          {
            command: "npm run dev -- --port 8080 --strictPort",
            url: "http://localhost:8080",
            reuseExistingServer: !process.env.CI,
            timeout: 60_000,
          },
        ]),
    {
      command:
        `cd ../backend` +
        ` && STEWARDS_DATABASE_URL=${E2E_DB} uv run alembic upgrade head` +
        ` && STEWARDS_DATABASE_URL=${E2E_DB} uv run uvicorn app.main:app --port 8000`,
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
