import { defineConfig } from "@playwright/test";

/**
 * Playwright 骨架（T0-12）。e2e 用例在 Phase F（TF-03~05）落全；
 * 本文件仅锁定基址，供 `npm run e2e` 手动运行。
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:8080",
    locale: "zh-CN",
  },
});
