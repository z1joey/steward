/**
 * TA-T3 · T-INV / T-TR / T-CON-02 UI 层（testing.md §3 / AC-INV / AC-TR / AC-CON-02）。
 * 邀请/转让发起无 UI（TA-12 后补），种子经 API（request 夹具）造数；断言引用 COPY 常量。
 */
import { expect, test, type APIRequestContext } from "@playwright/test";

import { COPY } from "../src/shared/copy";
import {
  acceptInvite,
  Actor,
  createInvite,
  createStore,
  createTransfer,
  registerAndLogin,
  uniquePhone,
  uiLogin,
} from "./helpers";

async function seedStoreWithManager(
  request: APIRequestContext,
): Promise<{ manager: Actor; storeName: string; storeId: number }> {
  const manager = await registerAndLogin(request, uniquePhone("e2e-m-"));
  const storeName = `受让店-${uniquePhone("").slice(-8)}`;
  const storeId = await createStore(request, manager, storeName);
  return { manager, storeName, storeId };
}

test("T-INV-01/02 · 待接受邀请出现于引导页，接受后门店生效（AC-INV-02/03）", async ({
  page,
  request,
}) => {
  const { manager, storeName, storeId } = await seedStoreWithManager(request);
  const sm = await registerAndLogin(request, uniquePhone("e2e-sm-"));
  await createInvite(request, manager, storeId, sm.phone);

  // 未接受前：门店列表无本店（AC-INV-02，UI 经引导页落点验证）
  await uiLogin(page, sm.phone);
  await expect(page).toHaveURL(/\/onboarding$/);
  const row = page.locator(".row").filter({ hasText: storeName });
  await expect(row).toContainText(COPY.roleStoreManager);
  await expect(page.locator(".store-name")).toHaveCount(0);   // 顶栏尚无店名

  // 接受 → 角色店长生效，门店进入上下文（AC-INV-03）
  await row.getByRole("button", { name: COPY.accept }).click();
  await expect(page).toHaveURL(/\/ledger\/entries$/);
  await expect(page.locator(".store-name")).toHaveText(storeName);
  await expect(page.locator("select.store-select")).toHaveCount(0);   // 单店隐藏选择器
});

test("T-INV · 拒绝邀请后列表清空", async ({ page, request }) => {
  const { manager, storeName, storeId } = await seedStoreWithManager(request);
  const sm = await registerAndLogin(request, uniquePhone("e2e-rj-"));
  await createInvite(request, manager, storeId, sm.phone);

  await uiLogin(page, sm.phone);
  const row = page.locator(".row").filter({ hasText: storeName });
  await row.getByRole("button", { name: COPY.reject }).click();
  await expect(page.getByText("暂无待处理事项")).toBeVisible();
  await expect(page).toHaveURL(/\/onboarding$/);   // 拒绝不产生 membership，仍无店
});

test("T-CON-02 · 接受已被处理的事项 → toast「已被别人更新，已刷新」（AC-CON-02）", async ({
  page,
  request,
}) => {
  const { manager, storeName, storeId } = await seedStoreWithManager(request);
  const sm = await registerAndLogin(request, uniquePhone("e2e-con-"));
  const inviteId = await createInvite(request, manager, storeId, sm.phone);

  await uiLogin(page, sm.phone);   // UI 会话停在引导页看到待接受行
  const row = page.locator(".row").filter({ hasText: storeName });
  await expect(row).toBeVisible();

  await acceptInvite(request, sm, inviteId);   // 另一会话抢先接受

  await row.getByRole("button", { name: COPY.accept }).click();   // 本会话再点 → 409
  await expect(page.locator(".toast")).toHaveText(COPY.conflictToast);
  // 刷新钩子已重拉列表 → 行消失，仍留在引导页（无导航副作用）
  await expect(page.getByText("暂无待处理事项")).toBeVisible();
  await expect(page).toHaveURL(/\/onboarding$/);
});

test("T-TR · 接受转让成为管理者，设置入口可见（AC-TR-01）", async ({ page, request }) => {
  const { manager, storeName, storeId } = await seedStoreWithManager(request);
  const target = await registerAndLogin(request, uniquePhone("e2e-tr-"));
  await createTransfer(request, manager, storeId, target.phone);

  await uiLogin(page, target.phone);
  await expect(page).toHaveURL(/\/onboarding$/);
  const row = page.locator(".row").filter({ hasText: storeName });
  await expect(row).toContainText(COPY.roleManager);
  await expect(row).toContainText(COPY.transfersSection);

  await row.getByRole("button", { name: COPY.accept }).click();
  await expect(page).toHaveURL(/\/ledger\/entries$/);
  await expect(page.locator(".store-name")).toHaveText(storeName);
  // 新管理者：设置（本店成员）入口可见（AC-INV-05 的管理者侧）
  await expect(page.locator('a[href="/settings/members"]')).toBeVisible();
});

test("AC-INV-05 · 店长无设置/邀请管理入口，直冲被守卫拦截", async ({ page, request }) => {
  const { manager, storeName, storeId } = await seedStoreWithManager(request);
  const sm = await registerAndLogin(request, uniquePhone("e2e-noentry-"));
  const inviteId = await createInvite(request, manager, storeId, sm.phone);
  await acceptInvite(request, sm, inviteId);   // 经 API 成为店长

  await uiLogin(page, sm.phone);
  await expect(page).toHaveURL(/\/ledger\/entries$/);
  await expect(page.locator('a[href="/settings/members"]')).toHaveCount(0);   // 无设置入口
  await expect(page.locator(".invites-link")).toHaveCount(0);                 // 无待处理角标

  await page.goto("/settings/members");   // 直冲 → requiresManager 兜底
  await expect(page).toHaveURL(/\/ledger\/entries$/);
  await expect(page.locator(".store-name")).toHaveText(storeName);
});
