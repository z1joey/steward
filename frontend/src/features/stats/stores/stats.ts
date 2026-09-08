import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";
import { COPY } from "@/shared/copy";
import type { DividendConfirmResponse, LedgerStats } from "@/shared/types";

/** 切店重置注册（Pinia 激活后调用一次）。 */
let resetRegistered = false;

export function ensureStatsResetRegistered(): void {
  if (resetRegistered) return;
  resetRegistered = true;
  registerStoreReset(() => useStatsStore().$reset());
}

/**
 * TC-06 · statsStore：统计页数据 + 确认发放（AC-STAT-01 / AC-DIV-01~03）。
 */
export const useStatsStore = defineStore("stats", {
  state: () => ({
    month: "" as string,
    stats: null as LedgerStats | null,
    loading: false,
    dividendError: "" as string,
  }),
  actions: {
    async refresh(month?: string): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<LedgerStats>("/ledger/stats", {
          params: month ? { month } : {},
        });
        this.stats = data;
        this.month = data.month;
      } finally {
        this.loading = false;
      }
    },
    async confirmDividend(amount: string, memo: string): Promise<void> {
      if (this.stats == null) return;
      this.dividendError = "";
      try {
        await api.post<DividendConfirmResponse>("/dividends/confirm", {
          amount,
          memo,
          public_account_version: this.stats.public.version,
        });
        await this.refresh(this.month);
      } catch (e) {
        const status = (e as { response?: { status?: number } }).response?.status;
        if (status === 422) {
          this.dividendError = COPY.insufficientBalance;
        }
        throw e;
      }
    },
    $reset() {
      this.month = "";
      this.stats = null;
      this.loading = false;
      this.dividendError = "";
    },
  },
});
