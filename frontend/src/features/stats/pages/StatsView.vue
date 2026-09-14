<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { registerRefreshHook } from "@/app/http";
import { useRole } from "@/app/composables/useRole";
import { ensureStatsResetRegistered, useStatsStore } from "@/features/stats/stores/stats";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";
import { SOURCE_TYPE_LABELS, TXN_DIRECTION_LABELS } from "@/shared/enums";
import type { RecentTxn } from "@/shared/types";

/**
 * TC-06 · /ledger/stats（AC-STAT-01 / AC-DIV-01~03 / US-C2/C3/C4 / ui-spec §3.3）：
 * KPI 卡 ×3（利润率 null → 「—」）；公账卡（余额 + 最近变动 in 绿 / out 默认 +
 * 管理者「调整余额」——新余额 + 必填原因，生成公账调整分录）；
 * 分红区：管理者输入 + 确认发放（> 余额即时红字 + 禁用；422 红字不出现成功态）；
 * 店长金额只读、无按钮。
 */
const stats = useStatsStore();
const { isManager } = useRole();

const dividendAmount = ref("");
const dividendMemo = ref("");

// 公账余额调整（管理者）
const adjustOpen = ref(false);
const adjustNewBalance = ref("");
const adjustReason = ref("");
const adjustDisabled = computed(
  () => adjustNewBalance.value === "" || adjustReason.value.trim() === "",
);

async function openAdjust(): Promise<void> {
  adjustNewBalance.value = String(stats.stats?.public.balance ?? "");
  adjustReason.value = "";
  stats.adjustError = "";
  adjustOpen.value = true;
}

async function submitAdjust(): Promise<void> {
  if (adjustDisabled.value) return;
  try {
    await stats.adjustBalance(adjustNewBalance.value, adjustReason.value.trim());
    adjustOpen.value = false;
  } catch {
    // 422 → stats.adjustError 红字；409 → 全局 toast + refresh
  }
}

let unregisterRefresh: (() => void) | null = null;

onMounted(() => {
  ensureStatsResetRegistered();
  stats.refresh();
  unregisterRefresh = registerRefreshHook(() => void stats.refresh());
});
onBeforeUnmount(() => {
  unregisterRefresh?.();
  unregisterRefresh = null;
});

const balance = computed(() => stats.stats?.public.balance ?? "0");
const overBalance = computed(() => {
  const v = Number(dividendAmount.value);
  return dividendAmount.value !== "" && Number.isFinite(v) && v > Number(balance.value);
});
const dividendDisabled = computed(
  () => dividendAmount.value === "" || overBalance.value || !Number.isFinite(Number(dividendAmount.value)),
);

async function confirmDividend(): Promise<void> {
  if (dividendDisabled.value) return;
  try {
    await stats.confirmDividend(dividendAmount.value, dividendMemo.value.trim());
    dividendAmount.value = "";
    dividendMemo.value = "";
  } catch {
    // 422 → stats.dividendError 红字；409 → 全局 toast + refresh
  }
}

function fmtTxn(t: RecentTxn): string {
  const sign = t.direction === "in" ? "+" : "-";
  return `${sign}${t.amount}`;
}
</script>

<template>
  <div class="page">
    <h1 class="title">{{ COPY.navStats }}</h1>

    <div class="kpi-row">
      <div class="card kpi">
        <span class="kpi-label">{{ COPY.income }}</span>
        <span class="kpi-value tabular">{{ stats.stats?.income ?? "—" }}</span>
      </div>
      <div class="card kpi">
        <span class="kpi-label">{{ COPY.expense }}</span>
        <span class="kpi-value tabular">{{ stats.stats?.expense ?? "—" }}</span>
      </div>
      <div class="card kpi">
        <span class="kpi-label">{{ COPY.profitRate }}</span>
        <span class="kpi-value tabular">{{
          stats.stats?.profit_rate != null ? stats.stats.profit_rate : "—"
        }}</span>
      </div>
    </div>

    <div class="card public-card">
      <div class="public-head">
        <span class="kpi-label">{{ COPY.publicAccount }}</span>
        <span class="head-right">
          <span class="kpi-value tabular">{{ balance }}</span>
          <ConfirmButton v-if="isManager" :action="openAdjust">
            {{ COPY.adjustBalance }}
          </ConfirmButton>
        </span>
      </div>
      <div class="recent">
        <div class="recent-title">{{ COPY.recentTxns }}</div>
        <div v-for="t in stats.stats?.public.recent_txns ?? []" :key="t.id" class="txn">
          <span class="txn-memo">
            {{ t.memo || SOURCE_TYPE_LABELS[t.source_type as keyof typeof SOURCE_TYPE_LABELS] }}
            <span class="txn-kind">{{ TXN_DIRECTION_LABELS[t.direction] }}</span>
          </span>
          <span class="tabular" :class="{ 'txn-in': t.direction === 'in' }">{{ fmtTxn(t) }}</span>
        </div>
        <p v-if="(stats.stats?.public.recent_txns.length ?? 0) === 0" class="muted">
          暂无变动
        </p>
      </div>

      <!-- 调整记录公示：最近 3 条（两角色可见）；查看更多 → 流水页调整筛选 -->
      <div v-if="stats.adjustments.items.length" class="recent">
        <div class="recent-title">
          {{ COPY.adjustLog }}（{{ stats.adjustments.total }}）
          <RouterLink
            v-if="stats.adjustments.total > stats.adjustments.items.length"
            class="link"
            to="/ledger/entries?filter=adjustment"
          >
            {{ COPY.viewMore }}
          </RouterLink>
        </div>
        <div v-for="a in stats.adjustments.items" :key="a.id" class="txn">
          <span class="txn-memo">
            {{ a.date }} · {{ a.reason }}
          </span>
          <span class="tabular" :class="{ 'txn-in': a.direction === 'income' }">
            {{ a.direction === "income" ? "调增" : "调减" }} {{ a.amount }} · 余额 {{ a.balance_after }}
          </span>
        </div>
      </div>
    </div>

    <AppModal :open="adjustOpen" :title="COPY.adjustBalance" @close="adjustOpen = false">
      <p class="adjust-hint">{{ COPY.adjustHint }}</p>
      <div class="adjust-form">
        <label class="field">
          <span>{{ COPY.currentBalance }}</span>
          <input class="tabular" :value="balance" readonly />
        </label>
        <label class="field">
          <span>{{ COPY.newBalance }}</span>
          <input
            v-model="adjustNewBalance"
            class="tabular"
            type="number"
            step="0.01"
            @input="stats.adjustError = ''"
          />
        </label>
        <label class="field">
          <span>{{ COPY.adjustReason }}</span>
          <input
            v-model="adjustReason"
            maxlength="500"
            placeholder="如：盘点差异、期初补录"
            @input="stats.adjustError = ''"
          />
        </label>
      </div>
      <p v-if="stats.adjustError" class="error">{{ stats.adjustError }}</p>
      <div class="actions">
        <ConfirmButton :action="submitAdjust" :disabled="adjustDisabled">
          {{ COPY.adjustBalance }}
        </ConfirmButton>
      </div>
    </AppModal>

    <div class="card dividend-card">
      <div class="kpi-label">{{ COPY.dividendConfirm }}</div>
      <div class="dividend-form">
        <label class="field">
          <span>{{ COPY.dividendAmount }}</span>
          <input
            v-model="dividendAmount"
            class="tabular"
            type="number"
            min="0"
            step="0.01"
            :readonly="!isManager"
            :disabled="!isManager || overBalance"
          />
        </label>
        <label v-if="isManager" class="field">
          <span>{{ COPY.memo }}</span>
          <input v-model="dividendMemo" maxlength="500" />
        </label>
        <ConfirmButton
          v-if="isManager"
          :action="confirmDividend"
          :disabled="dividendDisabled"
        >
          {{ COPY.dividendConfirm }}
        </ConfirmButton>
      </div>
      <p v-if="overBalance" class="error">{{ COPY.overBalance }}</p>
      <p v-else-if="stats.dividendError" class="error">{{ stats.dividendError }}</p>
    </div>
  </div>
</template>

<style scoped>
.page {
  display: grid;
  gap: var(--space-md);
  max-width: var(--size-content-max);
}
.title {
  margin: 0;
  font-size: var(--text-xl);
}
.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  display: grid;
  gap: var(--space-md);
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
}
.kpi {
  padding: var(--space-md) var(--space-lg);
}
.kpi-label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.kpi-value {
  font-size: var(--text-2xl);
  font-weight: 600;
}
.tabular {
  font-variant-numeric: tabular-nums;
}
.public-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.head-right {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}
.adjust-hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.adjust-form {
  display: grid;
  gap: var(--space-md);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
.recent {
  display: grid;
  gap: var(--space-sm);
}
.recent-title {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.link {
  color: var(--color-primary);
  text-decoration: none;
  margin-left: var(--space-sm);
}
.link:hover {
  text-decoration: underline;
}
.txn {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-md);
}
.txn-in {
  color: var(--color-success);
}
.txn-memo {
  display: flex;
  gap: var(--space-sm);
}
.txn-kind {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}
.muted {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
.dividend-form {
  display: flex;
  align-items: end;
  gap: var(--space-md);
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
.error {
  margin: 0;
  color: var(--color-error);
  font-size: var(--text-sm);
}
</style>
