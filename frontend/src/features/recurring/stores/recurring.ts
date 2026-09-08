import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";
import type { RecurringItem } from "@/shared/types";

/** 切店重置注册（TB-09 同款；Pinia 激活后调用一次）。 */
let resetRegistered = false;

export function ensureRecurringResetRegistered(): void {
  if (resetRegistered) return;
  resetRegistered = true;
  registerStoreReset(() => useRecurringStore().$reset());
}

/**
 * TC-05 · recurringStore：周期项列表 + 记本月（[C · O-10]）。
 */
export const useRecurringStore = defineStore("recurring", {
  state: () => ({
    items: [] as RecurringItem[],
    loading: false,
  }),
  actions: {
    async refresh(): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<{ items: RecurringItem[] }>("/ledger/recurring");
        this.items = data.items;
      } finally {
        this.loading = false;
      }
    },
    async recordThisMonth(id: number, version: number, amount: string): Promise<void> {
      const month = new Date();
      const period = `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, "0")}`;
      await api.post(`/ledger/recurring/${id}/occurrences`, {
        period_month: period,
        amount: amount || undefined,
        version,
      });
      await this.refresh();
    },
    async updateItem(
      id: number,
      version: number,
      fields: { name?: string; is_fixed?: boolean; fixed_amount?: string | null; active?: boolean },
    ): Promise<void> {
      await api.put(`/ledger/recurring/${id}`, { version, ...fields });
      await this.refresh();
    },
    async createItem(payload: {
      name: string;
      kind: string;
      is_fixed: boolean;
      fixed_amount?: string;
    }): Promise<void> {
      await api.post("/ledger/recurring", payload);
      await this.refresh();
    },
    $reset() {
      this.items = [];
      this.loading = false;
    },
  },
});
