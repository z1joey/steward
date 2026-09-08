/**
 * TF-04 · 店长会话 e2e（testing.md §3 / AC-LED-06 · AC-PAY-02/03 · AC-DIV-03 · AC-INV-05 · ui-spec §6）：
 * 报销/驳回/冲正/结算/确认发放/设置入口全部不可见；直接访问 /settings/members 被重定向。
 */
import { expect, test } from "@playwright/test";

import { COPY } from "../src/shared/copy";
import {
  addStoreManager,
  createEntry,
  seedStore,
  uiLogin,
} from "./helpers";

test("店长会话：所有管理者操作不可见（AC-LED-06 · AC-PAY-03 · AC-DIV-03 · AC-INV-05）", async ({
  page,
  request,
}) => {
  const { manager, storeId } = await seedStore(request, "tf04");
  const sm = await addStoreManager(request, manager, storeId, "tf04");

  // 造一条待审报销，验证待审行对店长可见但无操作按钮
  await createEntry(request, sm, storeId, {
    amount: "30",
    memo: "店长报销单",
    needs_reimbursement: true,
  });
  await uiLogin(page, sm.phone);
  await expect(page).toHaveURL(/\/ledger\/entries$/);
  await expect(page.getByText(COPY.pendingReview, { exact: true })).toBeVisible();

  // 报销 / 驳回按钮不渲染（筛选 chip「报销」在 nav 中，限定表格作用域）
  const tableBody = page.locator("table tbody");
  await expect(tableBody.getByRole("button", { name: COPY.claimApprove })).toHaveCount(0);
  await expect(tableBody.getByRole("button", { name: COPY.claimReject })).toHaveCount(0);
  // 冲正入口不渲染
  await expect(page.locator('button[aria-label="更多操作"]')).toHaveCount(0);

  // 薪资 Tab：结算按钮不渲染；无「计算」按钮（AC-PAY-01 双保险）
  await page.goto("/employees?tab=payroll");
  await expect(page.getByRole("button", { name: COPY.payrollSettle })).toHaveCount(0);
  await expect(page.getByText("计算")).toHaveCount(0);

  // 统计页：确认发放按钮不渲染；分红输入只读
  await page.goto("/ledger/stats");
  await expect(page.getByRole("button", { name: COPY.dividendConfirm })).toHaveCount(0);
  await expect(page.locator(".dividend-form input").first()).toBeDisabled();

  // 侧栏设置入口隐藏（ui-spec §6 / AC-INV-05）
  await expect(page.getByRole("link", { name: COPY.navSettings })).toHaveCount(0);
});

test("店长直接访问 /settings/members 被重定向（requiresManager 兜底）", async ({
  page,
  request,
}) => {
  const { manager, storeId } = await seedStore(request, "tf04b");
  const sm = await addStoreManager(request, manager, storeId, "tf04b");
  await uiLogin(page, sm.phone);

  await page.goto("/settings/members");
  await expect(page).toHaveURL(/\/ledger\/entries$/);
});
