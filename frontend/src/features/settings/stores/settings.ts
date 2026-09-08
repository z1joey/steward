import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";
import { useStoreContextStore } from "@/app/stores/storeContext";
import { COPY } from "@/shared/copy";
import type { MembersSettings } from "@/shared/types";

/** 切店重置注册（Pinia 激活后调用一次）。 */
let resetRegistered = false;

export function ensureSettingsResetRegistered(): void {
  if (resetRegistered) return;
  resetRegistered = true;
  registerStoreReset(() => useSettingsStore().$reset());
}

function currentStoreId(): number {
  const ctx = useStoreContextStore();
  if (ctx.selectedStoreId == null) throw new Error("no store selected");
  return ctx.selectedStoreId;
}

/**
 * TE-03 · settingsStore：本店成员 + 待接受区（US-F1 / AC-INV-01/04 / AC-TR-01~03）。
 * 409 already_member / pending_exists → 页面文案映射（AC-INV-04）；
 * 转让 409 seat_conflict → 全局 toast + refresh 兜底。
 */
export const useSettingsStore = defineStore("settings", {
  state: () => ({
    data: null as MembersSettings | null,
    loading: false,
    inviteError: "" as string,
    transferError: "" as string,
  }),
  getters: {
    hasPendingTransfer(state): boolean {
      return (state.data?.pending_transfers.length ?? 0) > 0;
    },
  },
  actions: {
    async refresh(): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<MembersSettings>("/settings/members");
        this.data = data;
      } finally {
        this.loading = false;
      }
    },
    async invite(phone: string): Promise<void> {
      this.inviteError = "";
      try {
        await api.post(`/stores/${currentStoreId()}/invites`, { phone });
        await this.refresh();
      } catch (e) {
        const detail = (e as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail;
        if (detail === "already_member") {
          this.inviteError = COPY.alreadyMemberMsg;
        } else if (detail === "pending_exists") {
          this.inviteError = COPY.pendingExistsMsg;
        } else if (detail === "phone_not_registered") {
          this.inviteError = "该手机号尚未注册";
        } else {
          throw e;
        }
      }
    },
    async transfer(phone: string): Promise<void> {
      this.transferError = "";
      try {
        await api.post(`/stores/${currentStoreId()}/transfers`, { phone });
        await this.refresh();
      } catch (e) {
        const detail = (e as { response?: { data?: { detail?: string } } }).response?.data
          ?.detail;
        if (detail === "phone_not_registered") {
          this.transferError = "该手机号尚未注册";
        } else if (detail === "self_transfer") {
          this.transferError = "不能转让给自己";
        } else {
          throw e;   // 409 seat_conflict → 全局 toast + refresh 兜底
        }
      }
    },
    $reset() {
      this.data = null;
      this.loading = false;
      this.inviteError = "";
      this.transferError = "";
    },
  },
});
