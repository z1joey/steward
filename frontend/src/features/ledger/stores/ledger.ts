import { defineStore } from "pinia";

import { api } from "@/app/http";
import type { LedgerList, LedgerRow } from "@/shared/types";

export type LedgerFilter = "all" | "manual" | "claim" | "payroll" | "dividend" | "recurring";

/**
 * TB-07/TB-09 · ledgerStore：流水列表状态。
 * refresh() 供 409 全局钩子与切店重拉（TB-09 挂接 resetStoreScopedStores）。
 */
export const useLedgerStore = defineStore("ledger", {
  state: () => ({
    items: [] as LedgerRow[],
    total: 0,
    filter: "all" as LedgerFilter,
    loading: false,
  }),
  actions: {
    async refresh(): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<LedgerList>("/ledger/entries", {
          params: this.filter === "all" ? {} : { filter: this.filter },
        });
        this.items = data.items;
        this.total = data.total;
      } finally {
        this.loading = false;
      }
    },
    async setFilter(filter: LedgerFilter): Promise<void> {
      this.filter = filter;
      await this.refresh();
    },
    async approveClaim(claimId: number, version: number): Promise<void> {
      await api.post(`/claims/${claimId}/approve`, { version });
      await this.refresh();
    },
    async rejectClaim(claimId: number, version: number): Promise<void> {
      await api.post(`/claims/${claimId}/reject`, { version });
      await this.refresh();
    },
    async reverseEntry(entryId: number, version: number, reason: string): Promise<void> {
      await api.post(`/ledger/entries/${entryId}/reverse`, { version, reason });
      await this.refresh();
    },
    /** 冲正入口可达性：普通分录、未被冲正过（TB-08）。 */
    canReverse(row: LedgerRow): boolean {
      return row.row_type === "entry" && !row.is_reversal && row.reversed_by_id == null;
    },
    $reset() {
      this.items = [];
      this.total = 0;
      this.filter = "all";
      this.loading = false;
    },
  },
});
