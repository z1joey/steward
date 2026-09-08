<script setup lang="ts">
import { useRouter } from "vue-router";

import { homePath } from "@/app/router";
import { resetStoreScopedStores } from "@/app/reset";
import { useSessionStore } from "@/app/stores/session";
import { useStoreContextStore } from "@/app/stores/storeContext";
import { useRole } from "@/app/composables/useRole";
import StoreSelect from "@/shared/components/StoreSelect.vue";
import { COPY } from "@/shared/copy";

/**
 * T0-06 · App Shell（design-system §6）：侧栏 188px（surface 底 / primary 激活）
 * · 顶栏 48px · 内容区。设置入口仅管理者（AC-INV-05 / ui-spec §6）。
 */
const router = useRouter();
const session = useSessionStore();
const ctx = useStoreContextStore();
const { isManager } = useRole();

async function onStoreSwitched(): Promise<void> {
  // TA-11 · 切店：resetStoreScopedStores()（清残影 + 关弹窗）→ 重拉
  resetStoreScopedStores();
  await ctx.refresh();
}

async function logout(): Promise<void> {
  session.logout();
  resetStoreScopedStores();
  await router.push("/login");
}

async function goHome(): Promise<void> {
  await router.push(await homePath());
}
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand" @click="goHome">{{ COPY.appName }}</div>

      <StoreSelect @changed="onStoreSwitched" />

      <nav class="nav">
        <div class="group-label">{{ COPY.navLedger }}</div>
        <RouterLink class="item" to="/ledger/entries">{{ COPY.navEntries }}</RouterLink>
        <RouterLink class="item sub" to="/ledger/recurring">{{ COPY.navRecurring }}</RouterLink>
        <RouterLink class="item sub" to="/ledger/stats">{{ COPY.navStats }}</RouterLink>
        <RouterLink class="item" to="/overview">{{ COPY.navOverview }}</RouterLink>
        <RouterLink class="item" to="/employees">{{ COPY.navEmployees }}</RouterLink>
        <RouterLink v-if="isManager" class="item" to="/settings/members">
          {{ COPY.navSettings }}
        </RouterLink>
      </nav>

      <div class="footer">
        <RouterLink v-if="ctx.pendingCount > 0" class="item invites-link" to="/invites">
          {{ COPY.pendingInvites }}
          <span class="badge">{{ ctx.pendingCount }}</span>
        </RouterLink>
        <button type="button" class="item logout" @click="logout">{{ COPY.logout }}</button>
      </div>
    </aside>

    <div class="main">
      <header class="topbar">
        <span class="store-name">
          {{ ctx.stores.find((s) => s.id === ctx.selectedStoreId)?.name ?? "" }}
        </span>
      </header>
      <main class="content">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
}
.sidebar {
  width: var(--size-sidebar);
  flex: 0 0 var(--size-sidebar);
  background: var(--color-surface);
  border-right: 1px solid var(--color-line);
  display: flex;
  flex-direction: column;
  padding: var(--space-md) var(--space-sm);
  gap: var(--space-md);
}
.brand {
  font-size: var(--text-lg);
  font-weight: 600;
  padding: 0 var(--space-sm);
  cursor: pointer;
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}
.group-label {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  padding: var(--space-sm);
}
.item {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm);
  border-radius: var(--radius-md);
  color: var(--color-text);
  text-decoration: none;
  border: none;
  background: transparent;
  text-align: left;
  font-size: var(--text-md);
  width: 100%;
}
.item.sub {
  padding-left: var(--space-lg);
}
.item:hover {
  background: var(--color-primary-soft);
}
.item.router-link-active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
  font-weight: 500;
}
.footer {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-top: 1px solid var(--color-line);
  padding-top: var(--space-sm);
}
.badge {
  background: var(--color-warning-soft);
  color: var(--color-warning);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  padding: 0 var(--space-sm);
}
.logout {
  color: var(--color-text-muted);
}
.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  height: var(--size-topbar);
  flex: 0 0 var(--size-topbar);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-line);
  display: flex;
  align-items: center;
  padding: 0 var(--space-lg);
}
.store-name {
  font-weight: 600;
}
.content {
  flex: 1;
  overflow: auto;
  padding: var(--space-lg);
}
</style>
