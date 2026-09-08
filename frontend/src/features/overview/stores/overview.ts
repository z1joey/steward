import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";

/** 切店重置注册（Pinia 激活后调用一次）。 */
let resetRegistered = false;

export function ensureOverviewResetRegistered(): void {
  if (resetRegistered) return;
  resetRegistered = true;
  registerStoreReset(() => useOverviewStore().$reset());
}

export interface OverviewData {
  store: { id: number; name: string };
  month: string;
  income: string;
  expense: string;
  public_balance: string;
  pending_claims: { count: number; amount: string };
}

/** TE-02 · overviewStore：当前店四 KPI（AC-OV-01/02 / US-D1）。 */
export const useOverviewStore = defineStore("overview", {
  state: () => ({
    month: "" as string,
    data: null as OverviewData | null,
    loading: false,
  }),
  actions: {
    async refresh(month?: string): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<OverviewData>("/overview", {
          params: month ? { month } : {},
        });
        this.data = data;
        this.month = data.month;
      } finally {
        this.loading = false;
      }
    },
    $reset() {
      this.month = "";
      this.data = null;
      this.loading = false;
    },
  },
});
