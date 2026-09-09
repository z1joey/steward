import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";
import { COPY } from "@/shared/copy";
import type {
  AdjustmentList,
  BalanceAdjustResponse,
  DividendConfirmResponse,
  LedgerStats,
} from "@/shared/types";

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
    adjustments: { items: [], total: 0 } as AdjustmentList,
    loading: false,
    dividendError: "" as string,
    adjustError: "" as string,
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
        // 调整记录公示（公账下方最近 3 条，两角色可见）
        const { data: adj } = await api.get<AdjustmentList>(
          "/public-account/adjustments",
          { params: { limit: 3 } },
        );
        this.adjustments = adj;
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
    /** 公账余额调整（管理者；原因必填，服务端生成「公账调整」分录 + 配对流水）。 */
    async adjustBalance(newBalance: string, reason: string): Promise<void> {
      if (this.stats == null) return;
      this.adjustError = "";
      try {
        await api.post<BalanceAdjustResponse>("/public-account/adjust", {
          new_balance: newBalance,
          reason,
          public_account_version: this.stats.public.version,
        });
        await this.refresh(this.month);
      } catch (e) {
        const status = (e as { response?: { status?: number; data?: { detail?: string } } })
          .response?.status;
        if (status === 422) {
          const detail = (
            e as { response?: { data?: { detail?: string } } }
          ).response?.data?.detail;
          this.adjustError =
            detail === "no_change" ? COPY.noChange : COPY.adjustFailed;
        }
        throw e;
      }
    },
    $reset() {
      this.month = "";
      this.stats = null;
      this.adjustments = { items: [], total: 0 };
      this.loading = false;
      this.dividendError = "";
      this.adjustError = "";
    },
  },
});
