import { defineStore } from "pinia";

import { api } from "@/app/http";
import type { StoreItem } from "@/shared/types";

const STORE_KEY = "steward.selectedStoreId";

function readInitialStoreId(): number | null {
  const raw = localStorage.getItem(STORE_KEY);
  return raw != null && raw !== "" ? Number(raw) : null;
}

/**
 * useStoreContext（B-specs §0.5）：
 * stores[]（含 role，仅已接受）· selectedStoreId（持久化）· role getter。
 * watch(selectedStoreId) → resetStoreScopedStores() 在 AppShell 中挂接。
 */
export const useStoreContextStore = defineStore("storeContext", {
  state: () => ({
    stores: [] as StoreItem[],
    selectedStoreId: readInitialStoreId(),
    loaded: false,
    pendingCount: 0,
  }),
  getters: {
    /** 当前店角色（无店 / 未选中 → null）。 */
    role(state): "manager" | "store_manager" | null {
      return state.stores.find((s) => s.id === state.selectedStoreId)?.role ?? null;
    },
    isManager(): boolean {
      return this.role === "manager";
    },
  },
  actions: {
    async refresh(): Promise<void> {
      const { data } = await api.get<{ items: StoreItem[] }>("/stores");
      this.stores = data.items;
      if (!this.stores.some((s) => s.id === this.selectedStoreId)) {
        this.selectedStoreId = this.stores[0]?.id ?? null;
      }
      this.loaded = true;
      // 待处理角标（邀请 + 转让；无店时同样可见）
      try {
        const res = await api.get<PendingPayload>("/invites");
        this.pendingCount = res.data.invites.length + res.data.transfers.length;
      } catch {
        this.pendingCount = 0;
      }
    },
    async ensureLoaded(): Promise<void> {
      if (!this.loaded) await this.refresh();
    },
    select(storeId: number): void {
      this.selectedStoreId = storeId;
      localStorage.setItem(STORE_KEY, String(storeId));
    },
    persistSelection(): void {
      if (this.selectedStoreId == null) localStorage.removeItem(STORE_KEY);
      else localStorage.setItem(STORE_KEY, String(this.selectedStoreId));
    },
  },
});

interface PendingPayload {
  invites: unknown[];
  transfers: unknown[];
}
