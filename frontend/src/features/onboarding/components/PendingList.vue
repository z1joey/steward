<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

import { api, registerRefreshHook } from "@/app/http";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";
import type { PendingList } from "@/shared/types";

/**
 * TA-10 · 待处理邀请 / 转让列表（/onboarding 与 /invites 复用同一组件）。
 * 接受 / 拒绝：ConfirmButton 防连点；invites 未含 version，初始恒为 1。
 */
const emit = defineEmits<{ changed: [] }>();

const pending = ref<PendingList>({ invites: [], transfers: [] });
const loading = ref(false);

async function refresh(): Promise<void> {
  loading.value = true;
  try {
    const { data } = await api.get<PendingList>("/invites");
    pending.value = data;
  } finally {
    loading.value = false;
  }
}

async function accept(kind: "invite" | "transfer", id: number): Promise<void> {
  const path = kind === "invite" ? `/invites/${id}/accept` : `/transfers/${id}/accept`;
  await api.post(path, { version: 1 });
  await refresh();
  emit("changed");
}

async function reject(id: number): Promise<void> {
  await api.post(`/invites/${id}/reject`, { version: 1 });
  await refresh();
  emit("changed");
}

onMounted(refresh);
const unregisterRefresh = registerRefreshHook(refresh);
onBeforeUnmount(unregisterRefresh);
</script>

<template>
  <section class="pending">
    <h3 class="section-title">{{ COPY.pendingInvites }}</h3>
    <p v-if="!loading && pending.invites.length === 0 && pending.transfers.length === 0" class="empty">
      暂无待处理事项
    </p>

    <template v-if="pending.invites.length">
      <h4 class="sub-title">{{ COPY.invitesSection }}</h4>
      <ul class="list">
        <li v-for="i in pending.invites" :key="`i-${i.id}`" class="row">
          <span class="desc">
            {{ i.store.name }} · {{ COPY.roleStoreManager }} {{ COPY.invitesSection }} ·
            来自 {{ i.inviter_phone }}
          </span>
          <span class="actions">
            <ConfirmButton :action="() => accept('invite', i.id)">{{ COPY.accept }}</ConfirmButton>
            <ConfirmButton :action="() => reject(i.id)" danger>{{ COPY.reject }}</ConfirmButton>
          </span>
        </li>
      </ul>
    </template>

    <template v-if="pending.transfers.length">
      <h4 class="sub-title">{{ COPY.transfersSection }}</h4>
      <ul class="list">
        <li v-for="t in pending.transfers" :key="`t-${t.id}`" class="row">
          <span class="desc">
            {{ t.store.name }} · {{ COPY.roleManager }} {{ COPY.transfersSection }} ·
            来自 {{ t.from_phone }}
          </span>
          <span class="actions">
            <ConfirmButton :action="() => accept('transfer', t.id)">
              {{ COPY.accept }}
            </ConfirmButton>
          </span>
        </li>
      </ul>
    </template>
  </section>
</template>

<style scoped>
.pending {
  display: grid;
  gap: var(--space-sm);
}
.section-title {
  margin: 0 0 var(--space-xs);
  font-size: var(--text-lg);
}
.sub-title {
  margin: var(--space-sm) 0 0;
  font-size: var(--text-md);
  color: var(--color-text-muted);
}
.empty {
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--space-sm);
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  background: var(--color-surface);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}
.actions {
  display: flex;
  gap: var(--space-sm);
}
</style>
