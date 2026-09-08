import axios from "axios";

import { COPY } from "@/shared/copy";

import { resetStoreScopedStores } from "./reset";
import { useSessionStore } from "./stores/session";
import { useStoreContextStore } from "./stores/storeContext";
import { useToastStore } from "./stores/toasts";

/**
 * T0-08 · http 客户端（B-specs §0.5）：
 * - 请求注入 Authorization / X-Store-Id
 * - 401 → 清 session 跳 /login
 * - 409 → 全局 toast「已被别人更新，已刷新」+ 当前页 refresh()（seat_conflict 分支钩子）
 */
export const api = axios.create({ baseURL: "/api" });

api.interceptors.request.use((config) => {
  const session = useSessionStore();
  if (session.token) {
    config.headers.Authorization = `Bearer ${session.token}`;
  }
  const ctx = useStoreContextStore();
  if (ctx.selectedStoreId != null) {
    config.headers["X-Store-Id"] = String(ctx.selectedStoreId);
  }
  return config;
});

// 当前页刷新钩子：409 后重拉当前页数据（页面/feature store 注册）
const refreshHooks = new Set<() => void>();

export function registerRefreshHook(fn: () => void): () => void {
  refreshHooks.add(fn);
  return () => refreshHooks.delete(fn);
}

function runRefreshHooks(): void {
  refreshHooks.forEach((fn) => fn());
}

// seat_conflict 分支钩子：页面可替换席位冲突文案（默认同全局 409 文案）
let seatConflictHandler: (() => void) | null = null;

export function setSeatConflictHandler(fn: (() => void) | null): void {
  seatConflictHandler = fn;
}

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status: number | undefined = error.response?.status;
    const detail: string | undefined = error.response?.data?.detail;

    if (status === 401) {
      const session = useSessionStore();
      session.logout();
      resetStoreScopedStores();
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    } else if (status === 409) {
      const toasts = useToastStore();
      if (detail === "seat_conflict" && seatConflictHandler) {
        seatConflictHandler();
      } else {
        toasts.show(COPY.conflictToast, "info");
      }
      runRefreshHooks();
    }
    return Promise.reject(error);
  },
);
