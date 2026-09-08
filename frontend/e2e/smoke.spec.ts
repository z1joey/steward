import { test, expect } from "@playwright/test";

// 骨架占位（T0-12）：验证前端可达；完整 e2e 见 Phase F（TF-03~05）。
test("smoke · app loads", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toBeVisible();
});
