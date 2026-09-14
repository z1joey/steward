<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { registerRefreshHook } from "@/app/http";
import {
  ensureRecurringResetRegistered,
  useRecurringStore,
} from "@/features/recurring/stores/recurring";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";
import { RECURRING_KIND_LABELS, RECURRING_PERIOD_LABELS } from "@/shared/enums";
import type { RecurringItem, RecurringKind } from "@/shared/types";

/**
 * TC-05 · /ledger/recurring（AC-REC-01~03 / US-C1 / ui-spec §3.2）：
 * 列表（周期固定「每月」；工资项金额列「来自结算」无输入框）；
 * 新建/编辑抽屉（wages 禁用金额并提示）；浮动项「记本月」小窗 [C · O-10]。
 */
const recurring = useRecurringStore();

let unregisterRefresh: (() => void) | null = null;

onMounted(() => {
  ensureRecurringResetRegistered();
  recurring.refresh();
  unregisterRefresh = registerRefreshHook(() => void recurring.refresh());
});
onBeforeUnmount(() => {
  unregisterRefresh?.();
  unregisterRefresh = null;
});

// —— 新建 / 编辑抽屉 ——
const drawerOpen = ref(false);
const editing = ref<RecurringItem | null>(null);
const formName = ref("");
const formKind = ref<RecurringKind>("rent");
const formFixed = ref(true);
const formAmount = ref("");

const KIND_OPTIONS: RecurringKind[] = ["rent", "utilities", "wages"];

function openCreate(): void {
  editing.value = null;
  formName.value = "";
  formKind.value = "rent";
  formFixed.value = true;
  formAmount.value = "";
  drawerOpen.value = true;
}

function openEdit(item: RecurringItem): void {
  editing.value = item;
  formName.value = item.name;
  formKind.value = item.kind;
  formFixed.value = item.is_fixed;
  formAmount.value = item.fixed_amount ?? "";
  drawerOpen.value = true;
}

async function submitDrawer(): Promise<void> {
  if (editing.value == null) {
    await recurring.createItem({
      name: formName.value.trim(),
      kind: formKind.value,
      is_fixed: formFixed.value,
      fixed_amount: formFixed.value && formKind.value !== "wages" ? formAmount.value : undefined,
    });
  } else {
    await recurring.updateItem(editing.value.id, editing.value.version, {
      name: formName.value.trim(),
      is_fixed: formKind.value === "wages" ? false : formFixed.value,
      fixed_amount:
        formKind.value !== "wages" && formFixed.value ? formAmount.value : null,
      active: editing.value.active,
    });
  }
  drawerOpen.value = false;
}

// —— 记本月（浮动项）——
const recordTarget = ref<RecurringItem | null>(null);
const recordAmount = ref("");

function openRecord(item: RecurringItem): void {
  recordTarget.value = item;
  recordAmount.value = "";
}

async function submitRecord(): Promise<void> {
  const t = recordTarget.value;
  if (t == null) return;
  await recurring.recordThisMonth(t.id, t.version, recordAmount.value.trim());
  recordTarget.value = null;
}

const wagesHint = computed(() => formKind.value === "wages");
</script>

<template>
  <div class="page">
    <header class="head">
      <h1 class="title">{{ COPY.navRecurring }}</h1>
      <button type="button" class="primary-btn" @click="openCreate">
        {{ COPY.newRecurring }}
      </button>
    </header>

    <table class="table">
      <thead>
        <tr>
          <th>{{ COPY.recurringName }}</th>
          <th>{{ COPY.recurringKind }}</th>
          <th>周期</th>
          <th class="right">{{ COPY.amount }}</th>
          <th class="right">{{ COPY.operations }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in recurring.items" :key="item.id">
          <td>{{ item.name }}</td>
          <td>{{ RECURRING_KIND_LABELS[item.kind] }}</td>
          <td>{{ RECURRING_PERIOD_LABELS[item.period] }}</td>
          <td class="right tabular">
            <template v-if="item.kind === 'wages'">{{ COPY.fromSettlement }}</template>
            <template v-else-if="item.is_fixed">{{ item.fixed_amount }}</template>
            <template v-else>
              {{ item.current_month_occurrence?.amount ?? COPY.thisMonthNotRecorded }}
            </template>
          </td>
          <td class="right actions-cell">
            <button
              v-if="item.kind !== 'wages' && !item.is_fixed"
              type="button"
              class="text-btn"
              @click="openRecord(item)"
            >
              {{ COPY.recordThisMonth }}
            </button>
            <button type="button" class="text-btn" @click="openEdit(item)">
              {{ COPY.edit }}
            </button>
          </td>
        </tr>
        <tr v-if="recurring.items.length === 0 && !recurring.loading">
          <td class="empty" colspan="5">暂无周期项</td>
        </tr>
      </tbody>
    </table>

    <!-- 新建 / 编辑抽屉 -->
    <Teleport to="body">
      <div v-if="drawerOpen" class="drawer-overlay" @click.self="drawerOpen = false">
        <div class="drawer" role="dialog" :aria-label="COPY.newRecurring">
          <h2 class="drawer-title">
            {{ editing ? COPY.editRecurring : COPY.newRecurring }}
          </h2>
          <label class="field">
            <span>{{ COPY.recurringName }}</span>
            <input v-model="formName" maxlength="100" />
          </label>
          <label class="field">
            <span>{{ COPY.recurringKind }}</span>
            <select v-model="formKind">
              <option v-for="k in KIND_OPTIONS" :key="k" :value="k">
                {{ RECURRING_KIND_LABELS[k] }}
              </option>
            </select>
          </label>
          <label class="field">
            <span>金额方式</span>
            <select v-model="formFixed" :disabled="wagesHint">
              <option :value="true">{{ COPY.recurringFixed }}</option>
              <option :value="false">{{ COPY.recurringFloating }}</option>
            </select>
          </label>
          <label class="field">
            <span>{{ COPY.amount }}</span>
            <input
              v-model="formAmount"
              type="number"
              min="0.01"
              step="0.01"
              :disabled="wagesHint || !formFixed"
            />
          </label>
          <p v-if="wagesHint" class="hint">{{ COPY.wagesNoHandFill }}</p>
          <div class="actions">
            <ConfirmButton :action="submitDrawer">
              {{ editing ? COPY.edit : COPY.newRecurring }}
            </ConfirmButton>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 记本月小窗 -->
    <AppModal :open="recordTarget != null" :title="COPY.recordThisMonth" @close="recordTarget = null">
      <label class="field">
        <span>{{ COPY.amount }}</span>
        <input v-model="recordAmount" type="number" min="0.01" step="0.01" />
      </label>
      <div class="actions">
        <ConfirmButton :action="submitRecord">{{ COPY.recordThisMonth }}</ConfirmButton>
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
/* .table th 的 text-align:left 优先级(0,1,1)高于单类 .right(0,1,0)，
   会盖掉表头右对齐——用 .table .right(0,2,0) 压回 */
.table .right {
  text-align: right;
}
.actions-cell {
  white-space: nowrap;
}
.tabular {
  font-variant-numeric: tabular-nums;
}
.text-btn {
  border: none;
  background: transparent;
  color: var(--color-primary);
  font-size: var(--text-sm);
  margin-left: var(--space-md);
}
.text-btn:hover {
  text-decoration: underline;
}
.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-xl);
}
.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 50;
  display: flex;
  justify-content: flex-end;
}
.drawer {
  width: 400px;
  max-width: 100vw;
  height: 100%;
  background: var(--color-surface);
  box-shadow: var(--shadow-md);
  padding: var(--space-lg);
  display: grid;
  gap: var(--space-md);
  align-content: start;
  overflow: auto;
}
.drawer-title {
  margin: 0;
  font-size: var(--text-lg);
}
.field {
  display: grid;
  gap: var(--space-xs);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.field input,
.field select {
  padding: var(--space-sm);
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
  font-size: var(--text-md);
}
.hint {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-warning);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
