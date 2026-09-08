/**
 * TA-T3 · T-AUTH-01~03 UI 层（testing.md §3 / AC-AUTH-01~05）。
 * 断言文案引用 src/shared/copy.ts 的 COPY 常量（其头部契约要求）。
 */
import { expect, test } from "@playwright/test";

import { COPY } from "../src/shared/copy";
import { createStore, PASSWORD, registerAndLogin, uniquePhone, uiLogin } from "./helpers";

test("T-AUTH-01 · 注册 → 自动登录落引导；错误凭证提示（AC-AUTH-01/02）", async ({ page }) => {
  const phone = uniquePhone("e2e-a1-");

  await page.goto("/register");
  await page.fill('input[name="phone"]', phone);
  await page.fill('input[name="password"]', PASSWORD);
  await page.getByRole("button", { name: COPY.register, exact: true }).click();
  await expect(page).toHaveURL(/\/onboarding$/);   // 注册成功自动登录，无店 → 引导

  // 退出后错误密码登录 → 锁定文案
  await page.getByRole("button", { name: COPY.logout }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.fill('input[name="phone"]', phone);
  await page.fill('input[name="password"]', PASSWORD + "-wrong");
  await page.getByRole("button", { name: COPY.login, exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText(COPY.loginFailed);

  // 正确凭证 → 会话建立
  await page.fill('input[name="password"]', PASSWORD);
  await page.getByRole("button", { name: COPY.login, exact: true }).click();
  await expect(page).toHaveURL(/\/onboarding$/);
});

test("AC-AUTH-01 · 重复手机号注册拒绝（AC-AUTH-01）", async ({ page, request }) => {
  const phone = uniquePhone("e2e-dup-");
  await registerAndLogin(request, phone);   // 先占号

  await page.goto("/register");
  await page.fill('input[name="phone"]', phone);
  await page.fill('input[name="password"]', PASSWORD);
  await page.getByRole("button", { name: COPY.register, exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("该手机号已注册");
});

test("T-AUTH-02 · 无店仅「创建门店」与待处理邀请（AC-AUTH-03）", async ({ page, request }) => {
  const actor = await registerAndLogin(request, uniquePhone("e2e-a2-"));
  await uiLogin(page, actor.phone);

  // bare 布局：无侧栏主流程入口
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("button", { name: COPY.createStore })).toBeVisible();
  await expect(page.getByRole("heading", { name: COPY.pendingInvites })).toBeVisible();
  await expect(page.getByText("暂无待处理事项")).toBeVisible();
  await expect(page.locator('a[href="/ledger/entries"]')).toHaveCount(0);

  // 直冲主流程路由 → 守卫弹回引导
  await page.goto("/ledger/entries");
  await expect(page).toHaveURL(/\/onboarding$/);
});

test("T-AUTH-03 · 创建门店 → 进流水；单店隐藏选择器（AC-AUTH-04/05）", async ({ page }) => {
  const phone = uniquePhone("e2e-a3-");
  const storeName = `司舵e2e-${phone.slice(-6)}`;

  await page.goto("/register");
  await page.fill('input[name="phone"]', phone);
  await page.fill('input[name="password"]', PASSWORD);
  await page.getByRole("button", { name: COPY.register, exact: true }).click();
  await expect(page).toHaveURL(/\/onboarding$/);

  // 弹窗建店
  await page.getByRole("button", { name: COPY.createStore }).click();
  const dialog = page.getByRole("dialog", { name: COPY.createStore });
  await expect(dialog).toBeVisible();
  await dialog.getByLabel(COPY.storeName).fill(storeName);
  await dialog.getByRole("button", { name: COPY.createStore }).click();

  // 落点流水；顶栏为当前店；单店 → 无选择器（AC-AUTH-05）
  await expect(page).toHaveURL(/\/ledger\/entries$/);
  await expect(page.locator(".store-name")).toHaveText(storeName);
  await expect(page.locator("select.store-select")).toHaveCount(0);
});

test("AC-AUTH-05 · 多店显示选择器且仅列已接受门店", async ({ page, request }) => {
  const actor = await registerAndLogin(request, uniquePhone("e2e-a5-"));
  const nameA = `店A-${uniquePhone("")}`;
  const nameB = `店B-${uniquePhone("")}`;
  await createStore(request, actor, nameA);
  await createStore(request, actor, nameB);

  await uiLogin(page, actor.phone);
  await expect(page).toHaveURL(/\/ledger\/entries$/);

  const select = page.locator("select.store-select");
  await expect(select).toBeVisible();
  await expect(select.getByRole("option", { name: nameA })).toBeAttached();
  await expect(select.getByRole("option", { name: nameB })).toBeAttached();
  await expect(page.locator(".store-name")).toHaveText(nameA);   // 默认首店
});
