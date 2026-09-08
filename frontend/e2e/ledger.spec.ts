/**
 * TF-03 · 管理者会话 e2e（testing.md §3 / AC-LED-01/04/07/08 · AC-DIV-02）：
 * 记一笔为独立弹窗；勾报销 → 待审行；报销 → 划线 +「已报销 · 公账已扣」；
 * 六类筛选；冲正入口可达；分红超额红字。
 * 断言文案引用 src/shared/copy.ts 的 COPY 常量。
 */
import { expect, test } from "@playwright/test";

import { COPY } from "../src/shared/copy";
import { createEntry, seedStore, uiLogin } from "./helpers";

test("记一笔为独立弹窗；提交后关闭并刷新列表（AC-LED-01/02）", async ({ page, request }) => {
  const { manager } = await seedStore(request, "tf03a");
  await uiLogin(page, manager.phone);

  await expect(page.locator(".modal")).toHaveCount(0);
  await page.getByRole("button", { name: COPY.recordEntry }).click();
  const modal = page.locator(".modal");
  await expect(modal).toBeVisible();                        // 独立弹窗（非页内表单）

  await modal.locator('input[type="number"]').fill("12.5");
  await modal.locator('input[maxlength="500"]').fill("买耗材");
  await modal.getByRole("button", { name: COPY.recordEntry }).click();

  await expect(page.locator(".modal")).toHaveCount(0);      // 成功关闭
  await expect(page.getByText("买耗材")).toBeVisible();     // 列表已刷新
});

test("勾报销 → 待审行；管理者报销 → 划线 +「已报销 · 公账已扣」（AC-LED-03/04）", async ({
  page,
  request,
}) => {
  const { manager, storeId } = await seedStore(request, "tf03b");
  await createEntry(request, manager, storeId, {
    amount: "30",
    memo: "打车",
    needs_reimbursement: true,
  });
  await uiLogin(page, manager.phone);

  const pending = page.getByText(COPY.pendingReview, { exact: true });
  await expect(pending).toBeVisible();                      // 待审行
  // 行内报销按钮（与筛选 chip「报销」同名 → 限定行作用域）
  await page
    .locator("tr", { hasText: COPY.pendingReview })
    .getByRole("button", { name: COPY.claimApprove })
    .click();

  // 划线 + 成功文案
  await expect(page.locator("tr.posted")).toBeVisible();
  await expect(page.getByText(COPY.claimedDone)).toBeVisible();
});

test("六类筛选（AC-LED-07）", async ({ page, request }) => {
  const { manager, storeId } = await seedStore(request, "tf03c");
  await createEntry(request, manager, storeId, {
    amount: "10",
    memo: "手工分录",
    needs_reimbursement: false,
  });
  await createEntry(request, manager, storeId, {
    amount: "20",
    memo: "待审报销单",
    needs_reimbursement: true,
  });
  await uiLogin(page, manager.phone);

  const chips = ["全部", "手工", "报销", "工资", "分红", "周期"] as const;
  const chipLabels: Record<(typeof chips)[number], string> = {
    全部: COPY.filterAll,
    手工: "手工",
    报销: "报销",
    工资: "工资",
    分红: "分红",
    周期: "周期",
  };
  for (const c of chips) {
    await page.locator(".chips").getByRole("button", { name: chipLabels[c] }).click();
  }

  // 手工 → 仅手工分录
  await page.locator(".chips").getByRole("button", { name: "手工" }).click();
  await expect(page.getByText("手工分录")).toBeVisible();
  await expect(page.getByText("待审报销单")).toHaveCount(0);
  // 报销 → 仅待审行
  await page.locator(".chips").getByRole("button", { name: "报销" }).click();
  await expect(page.getByText("待审报销单")).toBeVisible();
  await expect(page.getByText("手工分录")).toHaveCount(0);
  // 工资/分红/周期 → 空
  for (const c of ["工资", "分红", "周期"] as const) {
    await page.locator(".chips").getByRole("button", { name: chipLabels[c] }).click();
    await expect(page.getByText("暂无流水")).toBeVisible();
  }
  // 全部 → 两者合并（待审置顶）
  await page.locator(".chips").getByRole("button", { name: COPY.filterAll }).click();
  await expect(page.getByText("待审报销单")).toBeVisible();
  await expect(page.getByText("手工分录")).toBeVisible();
});

test("冲正入口可达：行内溢出菜单 → 确认弹窗（AC-LED-08）", async ({ page, request }) => {
  const { manager, storeId } = await seedStore(request, "tf03d");
  await createEntry(request, manager, storeId, {
    amount: "10",
    memo: "可冲正分录",
    needs_reimbursement: false,
  });
  await uiLogin(page, manager.phone);

  await page.locator('button[aria-label="更多操作"]').first().click();
  await page.getByRole("button", { name: COPY.reverse }).click();
  const modal = page.locator(".modal");
  await expect(modal).toBeVisible();                        // 确认弹窗（可选原因）
  await expect(modal.getByText(COPY.reverseReason)).toBeVisible();
});

test("分红超额：即时红字 + 按钮禁用（AC-DIV-02）", async ({ page, request }) => {
  const { manager } = await seedStore(request, "tf03e");
  await uiLogin(page, manager.phone);
  await page.getByRole("link", { name: COPY.navStats }).click();
  await expect(page).toHaveURL(/\/ledger\/stats$/);

  const dividendInput = page.locator('input[type="number"]').first();
  const confirmBtn = page.getByRole("button", { name: COPY.dividendConfirm });

  await dividendInput.fill("100");                          // 余额 0 → 超额
  await expect(page.getByText(COPY.overBalance)).toBeVisible();
  await expect(confirmBtn).toBeDisabled();
});
