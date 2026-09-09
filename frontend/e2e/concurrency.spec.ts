/**
 * TF-05 · 并发 / 隔离 e2e（testing.md §3 / AC-CON-02 · AC-ISO-03 · AC-PAY-01）：
 * 双标签页旧 version 保存 → toast「已被别人更新，已刷新」；切店后列表/表单/弹窗清空；
 * 薪资 Tab 无「计算」按钮且改班次后应发金额即时变（[O-07 拍板 2026-09-09] 真实费率）。
 */
import { expect, test, type Page } from "@playwright/test";

import { COPY } from "../src/shared/copy";
import { createEntry, seedStore, uiLogin } from "./helpers";

test("双标签页旧 version 报销 → 一方成功，另一方 toast + 刷新（AC-CON-02/03）", async ({
  browser,
  request,
}) => {
  const { manager, storeId } = await seedStore(request, "tf05a");
  const claim = await createEntry(request, manager, storeId, {
    amount: "30",
    memo: "并发报销单",
    needs_reimbursement: true,
  });
  void claim;

  const context = await browser.newContext({ locale: "zh-CN" });
  const pageA = await context.newPage();
  await uiLogin(pageA, manager.phone);
  // 双标签页共享同一会话（localStorage）：B 直接进入流水页，不重复登录
  const pageB = await context.newPage();
  await pageB.goto("/ledger/entries");

  // 两个标签页都渲染出同一条待审行（B 持旧列表 = 旧 version 快照）
  const approveIn = (p: Page) =>
    p
      .locator("tr", { hasText: COPY.pendingReview })
      .getByRole("button", { name: COPY.claimApprove });
  await expect(approveIn(pageA)).toBeVisible();
  await expect(approveIn(pageB)).toBeVisible();

  await approveIn(pageA).click();
  await expect(pageA.locator("tr.posted")).toBeVisible();   // A 成功

  await approveIn(pageB).click();                            // B 持旧数据 → 409
  await expect(pageB.getByText(COPY.conflictToast)).toBeVisible();
  // 刷新钩子生效：B 的列表同步为已报销
  await expect(pageB.locator("tr.posted")).toBeVisible();
  await expect(approveIn(pageB)).toHaveCount(0);

  await context.close();
});

test("切店后列表清空（AC-ISO-03）", async ({ page, request }) => {
  const { manager, storeId } = await seedStore(request, "tf05b");
  await createEntry(request, manager, storeId, {
    amount: "10",
    memo: "S1专属分录",
    needs_reimbursement: false,
  });
  // 第二家店（同管理者，选择器可见）
  const r = await request.post("/api/stores", {
    data: { name: `S2-${Date.now().toString(36)}` },
    headers: { Authorization: `Bearer ${manager.token}` },
  });
  if (!r.ok()) throw new Error("create second store failed");
  const second = (await r.json()).id as number;
  void second;

  await uiLogin(page, manager.phone);
  await expect(page.getByText("S1专属分录")).toBeVisible();

  await page.selectOption('select[aria-label="门店名称"]', { index: 1 });
  await expect(page.getByText("S1专属分录")).toHaveCount(0);   // 残影清空
});

test("薪资 Tab：无「计算」按钮；改班次后应发即时变（AC-PAY-01 · O-07）", async ({
  page,
  request,
}) => {
  const { manager, storeId } = await seedStore(request, "tf05c");

  // 直接造员工（时薪 50，[O-07] 单价存员工档案）+ 后续经 UI 排班
  const emp = await request.post("/api/employees", {
    data: { name: "张三", job_type: "long_term", pay_type: "hourly", unit_price: "50" },
    headers: { Authorization: `Bearer ${manager.token}`, "X-Store-Id": String(storeId) },
  });
  if (!emp.ok()) throw new Error("create employee failed");
  const empId = (await emp.json()).id as number;
  void empId;

  await uiLogin(page, manager.phone);
  await page.goto("/employees?tab=payroll");

  // 无任何「计算」按钮（Locked）；无班次 → 预览为空
  await expect(page.getByText("计算", { exact: true })).toHaveCount(0);
  await expect(page.getByText("计算", { exact: false })).toHaveCount(0);
  await expect(page.getByText("本月暂无排班")).toBeVisible();

  // 排班 Tab 保存班次 → 切回薪资 → 汇总自动更新（compute-on-read）
  await page.getByRole("button", { name: COPY.tabShifts }).click();
  await page.locator(".day-cell").first().click();
  const modal = page.locator(".modal");
  await expect(modal).toBeVisible();
  await modal.locator('input[type="time"]').first().fill("10:00");
  await modal.locator('input[type="time"]').nth(1).fill("14:00");
  await modal.getByRole("button", { name: "新增" }).click();
  await expect(page.locator(".seg").first()).toBeVisible();

  await page.getByRole("button", { name: COPY.tabPayroll }).click();
  await expect(page.getByText("张三")).toBeVisible();
  // 应发 200.00 = 4h × 时薪 50（真实费率规则，随班次即时变化 AC-PAY-01）
  await expect(page.getByText("200.00").first()).toBeVisible();
});
