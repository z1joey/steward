<script setup lang="ts">
import { onMounted, ref } from "vue";

import { useLedgerStore } from "@/features/ledger/stores/ledger";
import type { LedgerFilter } from "@/features/ledger/stores/ledger";
import RecordEntryModal from "@/features/ledger/components/RecordEntryModal.vue";
import { useRole } from "@/app/composables/useRole";
import { COPY } from "@/shared/copy";
import { SOURCE_TYPE_LABELS } from "@/shared/enums";
import type { LedgerRow } from "@/shared/types";

/**
 * TB-07 · 流水页（ui-spec §3.1 / AC-LED-04/06/07）：
 * 记一笔弹窗 · 六类筛选 chips · 待审行（管理者报销/驳回）· 已报销划线 ·
 * 工资行「来自结算」。
 */
const ledger = useLedgerStore();
const { can } = useRole();

const showRecord = ref(false);

const FILTERS: { value: LedgerFilter; label: string }[] = [
  { value: "all", label: COPY.filterAll },
  { value: "manual", label: SOURCE_TYPE_LABELS.manual },
  { value: "claim", label: SOURCE_TYPE_LABELS.claim },
  { value: "payroll", label: SOURCE_TYPE_LABELS.payroll },
  { value: "dividend", label: SOURCE_TYPE_LABELS.dividend },
  { value: "recurring", label: SOURCE_TYPE_LABELS.recurring },
];

onMounted(() => {
  ledger.refresh();
});

async function onCreated(): Promise<void> {
  await ledger.refresh();
}

function isPostedClaim(row: LedgerRow): boolean {
  return row.row_type === "entry" && row.source_type === "claim" && row.claim_status === "posted";
}
</script>

<template>
  <div class="page">
    <header class="head">
      <h1 class="title">{{ COPY.navEntries }}</h1>
      <button type="button" class="record-btn" @click="showRecord = true">
        {{ COPY.recordEntry }}
      </button>
    </header>

    <nav class="chips">
      <button
        v-for="f in FILTERS"
        :key="f.value"
        type="button"
        class="chip"
        :class="{ active: ledger.filter === f.value }"
        @click="ledger.setFilter(f.value)"
      >
        {{ f.label }}
      </button>
    </nav>

    <table class="entries">
      <thead>
        <tr>
          <th class="col-date">{{ COPY.date }}</th>
          <th>{{ COPY.memo }}</th>
          <th class="col-source">来源</th>
          <th class="col-amount">{{ COPY.amount }}</th>
          <th class="col-status">状态</th>
          <th class="col-actions"></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in ledger.items"
          :key="`${row.row_type}-${row.id}`"
          :class="{ posted: isPostedClaim(row) }"
        >
          <td class="col-date tabular">{{ row.date }}</td>
          <td>
            <span class="memo">{{ row.memo || "—" }}</span>
            <span v-if="row.source_type === 'payroll'" class="sub">{{ COPY.fromSettlement }}</span>
          </td>
          <td class="col-source">
            {{ row.source_type ? SOURCE_TYPE_LABELS[row.source_type] : "—" }}
          </td>
          <td class="col-amount tabular">
            {{ row.amount }}
          </td>
          <td class="col-status">
            <template v-if="row.row_type === 'claim_pending'">
              <span class="pill warning">{{ COPY.pendingReview }}</span>
            </template>
            <template v-else-if="isPostedClaim(row)">
              <span class="pill success">{{ COPY.claimedDone }}</span>
            </template>
            <template v-else-if="row.is_reversal">
              <span class="pill muted">{{ COPY.reversed }}</span>
            </template>
          </td>
          <td class="col-actions">
            <template v-if="row.row_type === 'claim_pending' && can('claims.approve')">
              <ConfirmButton
                class="mini"
                :action="() => ledger.approveClaim(row.id, row.version)"
              >
                {{ COPY.claimApprove }}
              </ConfirmButton>
              <ConfirmButton
                class="mini danger-text"
                :action="() => ledger.rejectClaim(row.id, row.version)"
              >
                {{ COPY.claimReject }}
              </ConfirmButton>
            </template>
          </td>
        </tr>
        <tr v-if="ledger.items.length === 0 && !ledger.loading">
          <td class="empty" colspan="6">暂无流水</td>
        </tr>
      </tbody>
    </table>

    <RecordEntryModal v-model="showRecord" @created="onCreated" />
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
.record-btn {
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}
.record-btn:hover {
  background: var(--color-primary-hover);
}
.chips {
  display: flex;
  gap: var(--space-sm);
  flex-wrap: wrap;
}
.chip {
  border: 1px solid var(--color-line-strong);
  background: var(--color-surface);
  border-radius: var(--radius-pill);
  padding: var(--space-xs) var(--space-md);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.chip.active {
  background: var(--color-primary-soft);
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.entries {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  overflow: hidden;
}
.entries th {
  text-align: left;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  font-weight: 500;
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--color-line);
}
.entries td {
  padding: var(--space-sm) var(--space-md);
  border-bottom: 1px solid var(--color-line);
  font-size: var(--text-md);
}
.col-date,
.col-source {
  white-space: nowrap;
}
.col-amount {
  text-align: right;
  white-space: nowrap;
}
.col-actions {
  text-align: right;
  white-space: nowrap;
}
.tabular {
  font-variant-numeric: tabular-nums;
}
.memo {
  display: block;
}
.sub {
  display: block;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
tr.posted td {
  text-decoration: line-through;
  color: var(--color-text-muted);
}
tr.posted td .pill {
  text-decoration: none;
}
.pill {
  display: inline-block;
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  padding: 2px var(--space-sm);
}
.pill.warning {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.pill.success {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.pill.muted {
  background: var(--color-surface-sunken);
  color: var(--color-text-muted);
}
.mini {
  padding: 2px var(--space-sm);
  font-size: var(--text-sm);
}
.danger-text {
  background: transparent;
  color: var(--color-error);
  border: 1px solid var(--color-error);
}
.danger-text:hover:not(:disabled) {
  background: var(--color-error-soft);
}
.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-xl);
}
</style>
