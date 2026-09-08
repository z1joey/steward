import { createRouter, createWebHistory } from "vue-router";

import { useSessionStore } from "@/app/stores/session";
import { useStoreContextStore } from "@/app/stores/storeContext";

/**
 * T0-10 · 路由表（ui-spec §2 全部 path + /onboarding /invites [C · O-12]）
 * 守卫：requiresAuth / requiresStore / requiresManager（B-specs §0.5）。
 */

/** TA-12 · 登录后落点决策：有店 → /ledger/entries；无店 → /onboarding。 */
export async function homePath(): Promise<string> {
  const ctx = useStoreContextStore();
  try {
    await ctx.ensureLoaded();
  } catch {
    return "/login";
  }
  return ctx.stores.length > 0 ? "/ledger/entries" : "/onboarding";
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: () => "/ledger/entries" },
    {
      path: "/login",
      component: () => import("@/features/auth/pages/LoginView.vue"),
      meta: { bare: true, guestOnly: true },
    },
    {
      path: "/register",
      component: () => import("@/features/auth/pages/RegisterView.vue"),
      meta: { bare: true, guestOnly: true },
    },
    {
      path: "/onboarding",
      component: () => import("@/features/onboarding/pages/OnboardingView.vue"),
      meta: { bare: true, requiresAuth: true, title: "创建门店" },
    },
    {
      path: "/invites",
      component: () => import("@/features/onboarding/pages/InvitesView.vue"),
      meta: { requiresAuth: true, title: "待处理邀请" },
    },
    {
      path: "/ledger/entries",
      component: () => import("@/features/placeholder/pages/PlaceholderView.vue"),
      meta: { requiresAuth: true, requiresStore: true, title: "流水" },
    },
    {
      path: "/ledger/recurring",
      component: () => import("@/features/placeholder/pages/PlaceholderView.vue"),
      meta: { requiresAuth: true, requiresStore: true, title: "周期" },
    },
    {
      path: "/ledger/stats",
      component: () => import("@/features/placeholder/pages/PlaceholderView.vue"),
      meta: { requiresAuth: true, requiresStore: true, title: "统计" },
    },
    {
      path: "/overview",
      component: () => import("@/features/placeholder/pages/PlaceholderView.vue"),
      meta: { requiresAuth: true, requiresStore: true, title: "概览" },
    },
    {
      path: "/employees",
      component: () => import("@/features/placeholder/pages/PlaceholderView.vue"),
      meta: { requiresAuth: true, requiresStore: true, title: "员工" },
    },
    {
      path: "/employees/:id",
      component: () => import("@/features/placeholder/pages/PlaceholderView.vue"),
      meta: { requiresAuth: true, requiresStore: true, title: "员工详情" },
    },
    {
      path: "/settings/members",
      component: () => import("@/features/placeholder/pages/PlaceholderView.vue"),
      meta: { requiresAuth: true, requiresStore: true, requiresManager: true, title: "本店成员" },
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  const session = useSessionStore();
  const ctx = useStoreContextStore();

  if (to.meta.requiresAuth && !session.token) {
    return { path: "/login", query: { redirect: to.fullPath } };
  }
  // 已登录访问 /login /register → 落点决策
  if (to.meta.guestOnly && session.token) {
    return await homePath();
  }
  if (to.meta.requiresAuth && session.token) {
    try {
      await ctx.ensureLoaded();
    } catch {
      session.logout();
      return { path: "/login" };
    }
  }
  // requiresStore：无已接受 membership → /onboarding（AC-AUTH-03）
  if (to.meta.requiresStore && ctx.stores.length === 0) {
    return "/onboarding";
  }
  // requiresManager：非管理者 → /ledger/entries 兜底（AC-INV-05 / ui-spec §6）
  if (to.meta.requiresManager && !ctx.isManager) {
    return "/ledger/entries";
  }
});
