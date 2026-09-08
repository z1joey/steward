import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";
import type { PayrollData } from "@/shared/types";

/** 切店重置注册（Pinia 激活后调用一次）。 */
let resetRegistered = false;

export function ensurePayrollResetRegistered(): void {
  if (resetRegistered) return;
  resetRegistered = true;
  registerStoreReset(() => usePayrollStore().$reset());
}

function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/**
 * TD-09 · payrollStore：薪资只读自动汇总 + 结算（AC-PAY-01/02 · US-E7/E8）。
 * 排班保存后由页面触发 refresh()（AC-PAY-01 自动更新）。
 */
export const usePayrollStore = defineStore("payroll", {
  state: () => ({
    month: currentMonth(),
    data: null as PayrollData | null,
    loading: false,
  }),
  actions: {
    async refresh(): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<PayrollData>("/payroll", {
          params: { month: this.month },
        });
        this.data = data;
      } finally {
        this.loading = false;
      }
    },
    async setMonth(month: string): Promise<void> {
      this.month = month;
      await this.refresh();
    },
    async settle(): Promise<void> {
      await api.post("/payroll/settle", { month: this.month });
      await this.refresh();
    },
    $reset() {
      this.month = currentMonth();
      this.data = null;
      this.loading = false;
    },
  },
});
