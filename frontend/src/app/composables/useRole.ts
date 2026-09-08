import { computed } from "vue";

import { useStoreContextStore } from "@/app/stores/storeContext";

/**
 * useRole（B-specs §0.5）：只控显隐；失败仍由 http 403 兜底。
 * can(action) 的 action 取 Deny 清单键（api.md §5）。
 */
export const MANAGER_ONLY_ACTIONS = [
  "claims.approve",
  "claims.reject",
  "payroll.settle",
  "dividend.confirm",
  "ledger.reverse",
  "invites.create",
  "transfers.create",
] as const;

export type ManagerOnlyAction = (typeof MANAGER_ONLY_ACTIONS)[number];

export function useRole() {
  const ctx = useStoreContextStore();
  const isManager = computed(() => ctx.isManager);
  function can(_action: ManagerOnlyAction): boolean {
    return ctx.isManager;
  }
  return { isManager, can };
}
