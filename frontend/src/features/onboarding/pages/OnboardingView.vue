<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { homePath } from "@/app/router";
import { resetStoreScopedStores } from "@/app/reset";
import { useSessionStore } from "@/app/stores/session";
import { useStoreContextStore } from "@/app/stores/storeContext";
import CreateStoreModal from "@/features/onboarding/components/CreateStoreModal.vue";
import PendingList from "@/features/onboarding/components/PendingList.vue";
import { COPY } from "@/shared/copy";

/**
 * TA-10 · 无店空态（AC-AUTH-03 / US-A3）：
 * 仅「创建门店」+ 待处理邀请 / 转让；不渲染侧栏主模块（bare 布局）。
 */
const router = useRouter();
const session = useSessionStore();
const ctx = useStoreContextStore();

const showCreate = ref(false);

async function afterChanged(): Promise<void> {
  // 接受邀请 / 转让后可能已有门店 → 重新决策落点
  await ctx.refresh();
  if (ctx.stores.length > 0) {
    resetStoreScopedStores();
    await router.push(await homePath());
  }
}

async function afterCreated(): Promise<void> {
  await router.push("/ledger/entries");
}

async function logout(): Promise<void> {
  session.logout();
  resetStoreScopedStores();
  await router.push("/login");
}
</script>

<template>
  <div class="onboarding">
    <div class="card">
      <header class="head">
        <h1 class="title">{{ COPY.appName }}</h1>
        <button type="button" class="logout" @click="logout">{{ COPY.logout }}</button>
      </header>

      <p class="hint">创建你的门店，或处理下面的待接受邀请 / 转让。</p>

      <button type="button" class="primary" @click="showCreate = true">
        {{ COPY.createStore }}
      </button>

      <PendingList @changed="afterChanged" />
    </div>

    <CreateStoreModal v-model="showCreate" @created="afterCreated" />
  </div>
</template>

<style scoped>
.onboarding {
  min-height: 100vh;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: var(--space-2xl) var(--space-md);
}
.card {
  width: var(--size-modal-sm);
  max-width: 100%;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-xl);
  display: grid;
  gap: var(--space-md);
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.title {
  margin: 0;
  font-size: var(--text-xl);
}
.logout {
  border: none;
  background: transparent;
  color: var(--color-text-muted);
}
.hint {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
.primary {
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  justify-self: start;
}
.primary:hover {
  background: var(--color-primary-hover);
}
</style>
