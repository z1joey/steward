<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

import { registerRefreshHook } from "@/app/http";
import {
  ensureSettingsResetRegistered,
  useSettingsStore,
} from "@/features/settings/stores/settings";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";
import { ROLE_LABELS } from "@/shared/enums";

/**
 * TE-03 · /settings/members（US-F1 · AC-INV-01/04 · AC-TR-01~03 / ui-spec §5.2）：
 * 成员表（手机号/角色/加入时间）；待接受区（邀请 · 转让）；
 * 「邀请店长」弹窗（始终可用；409 → 页面文案）；
 * 「转让管理者」弹窗 + 二次确认（已有待接受转让时禁用 [C]）。
 */
const settings = useSettingsStore();

let unregisterRefresh: (() => void) | null = null;

onMounted(() => {
  ensureSettingsResetRegistered();
  settings.refresh();
  unregisterRefresh = registerRefreshHook(() => void settings.refresh());
});
onBeforeUnmount(() => {
  unregisterRefresh?.();
  unregisterRefresh = null;
});

// —— 邀请店长 ——
const inviteOpen = ref(false);
const invitePhone = ref("");

function openInvite(): void {
  invitePhone.value = "";
  settings.inviteError = "";
  inviteOpen.value = true;
}

async function submitInvite(): Promise<void> {
  if (!invitePhone.value.trim()) return;
  await settings.invite(invitePhone.value.trim());
  if (!settings.inviteError) inviteOpen.value = false;
}

// —— 转让管理者（二次确认）——
const transferOpen = ref(false);
const confirmOpen = ref(false);
const transferPhone = ref("");

function openTransfer(): void {
  transferPhone.value = "";
  settings.transferError = "";
  transferOpen.value = true;
}

function goConfirm(): Promise<void> {
  if (!transferPhone.value.trim()) return Promise.resolve();
  transferOpen.value = false;
  confirmOpen.value = true;
  return Promise.resolve();
}

async function submitTransfer(): Promise<void> {
  await settings.transfer(transferPhone.value.trim());
  confirmOpen.value = false;
}

function fmtTime(iso: string): string {
  return iso.slice(0, 10);
}
</script>

<template>
  <div class="page">
    <header class="head">
      <h1 class="title">{{ COPY.navSettings }}</h1>
      <div class="head-actions">
        <button type="button" class="primary-btn" @click="openInvite">
          {{ COPY.inviteManager }}
        </button>
        <button
          type="button"
          class="ghost-btn"
          :disabled="settings.hasPendingTransfer"
          @click="openTransfer"
        >
          {{ COPY.transferManager }}
        </button>
      </div>
    </header>
    <p v-if="settings.hasPendingTransfer" class="hint">
      已有待接受转让，完成后方可再次发起
    </p>

    <!-- 成员表 -->
    <table class="table">
      <thead>
        <tr>
          <th>{{ COPY.memberPhone }}</th>
          <th>{{ COPY.memberRole }}</th>
          <th>{{ COPY.memberSince }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in settings.data?.members ?? []" :key="m.user.id">
          <td>{{ m.user.phone }}</td>
          <td>{{ ROLE_LABELS[m.role as keyof typeof ROLE_LABELS] }}</td>
          <td>{{ fmtTime(m.since) }}</td>
        </tr>
      </tbody>
    </table>

    <!-- 待接受区 -->
    <section class="card">
      <h2 class="section-title">{{ COPY.pendingSection }}</h2>
      <div class="pending-grid">
        <div>
          <div class="pending-label">{{ COPY.invitesSection }}</div>
          <div v-for="i in settings.data?.pending_invites ?? []" :key="i.id" class="pending-row">
            <span>{{ i.user.phone }}</span>
            <span class="muted">{{ fmtTime(i.created_at) }}</span>
          </div>
          <p v-if="(settings.data?.pending_invites.length ?? 0) === 0" class="muted">无</p>
        </div>
        <div>
          <div class="pending-label">{{ COPY.transfersSection }}</div>
          <div v-for="t in settings.data?.pending_transfers ?? []" :key="t.id" class="pending-row">
            <span>{{ t.user.phone }}</span>
            <span class="muted">{{ fmtTime(t.created_at) }}</span>
          </div>
          <p v-if="(settings.data?.pending_transfers.length ?? 0) === 0" class="muted">无</p>
        </div>
      </div>
    </section>

    <!-- 邀请店长弹窗 -->
    <AppModal :open="inviteOpen" :title="COPY.inviteManager" @close="inviteOpen = false">
      <label class="field">
        <span>{{ COPY.phone }}</span>
        <input v-model="invitePhone" maxlength="32" @keyup.enter="submitInvite" />
      </label>
      <p v-if="settings.inviteError" class="error">{{ settings.inviteError }}</p>
      <div class="actions">
        <ConfirmButton :action="submitInvite">{{ COPY.inviteManager }}</ConfirmButton>
      </div>
    </AppModal>

    <!-- 转让管理者：填写弹窗 -->
    <AppModal :open="transferOpen" :title="COPY.transferManager" @close="transferOpen = false">
      <label class="field">
        <span>{{ COPY.transferTo }}</span>
        <input v-model="transferPhone" maxlength="32" @keyup.enter="goConfirm" />
      </label>
      <p v-if="settings.transferError" class="error">{{ settings.transferError }}</p>
      <div class="actions">
        <ConfirmButton :action="goConfirm">{{ COPY.transferManager }}</ConfirmButton>
      </div>
    </AppModal>

    <!-- 转让管理者：二次确认弹窗 -->
    <AppModal :open="confirmOpen" :title="COPY.transferConfirmTitle" @close="confirmOpen = false">
      <p class="hint">{{ COPY.transferConfirmHint }}（{{ transferPhone }}）</p>
      <div class="actions">
        <ConfirmButton danger :action="submitTransfer">
          {{ COPY.transferManager }}
        </ConfirmButton>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-md);
  max-width: var(--size-content-max);
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
.head-actions {
  display: flex;
  gap: var(--space-md);
}
.primary-btn {
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}
.primary-btn:hover {
  background: var(--color-primary-hover);
}
.ghost-btn {
  background: transparent;
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}
.ghost-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.table th {
  text-align: left;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--color-line);
}
.table td {
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--color-line);
  font-size: var(--text-md);
}
.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  display: grid;
  gap: var(--space-md);
}
.section-title {
  margin: 0;
  font-size: var(--text-md);
  font-weight: 600;
}
.pending-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-lg);
}
.pending-label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin-bottom: var(--space-sm);
}
.pending-row {
  display: flex;
  justify-content: space-between;
  padding: var(--space-xs) 0;
  font-size: var(--text-md);
}
.muted {
  color: var(--color-text-muted);
}
.hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.field {
  display: grid;
  gap: var(--space-xs);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.field input {
  padding: var(--space-sm);
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
  font-size: var(--text-md);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
.error {
  margin: 0;
  color: var(--color-error);
  font-size: var(--text-sm);
}
</style>
