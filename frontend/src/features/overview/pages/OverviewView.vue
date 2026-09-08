<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";

import { registerRefreshHook } from "@/app/http";
import { ensureOverviewResetRegistered, useOverviewStore } from "@/features/overview/stores/overview";
import { COPY } from "@/shared/copy";

/**
 * TE-02 · /overview（AC-OV-01/02 / US-D1 / ui-spec §3.4）：
 * 四张 KPI 卡（收入 · 支出 · 公账 · 待审报销 件数+金额）+ 月选择器；
 * 卡片点击跳对应账本子页 [C]；无多店切换/合计/分店构成。
 */
const overview = useOverviewStore();
const router = useRouter();

let unregisterRefresh: (() => void) | null = null;

onMounted(() => {
  ensureOverviewResetRegistered();
  overview.refresh();
  unregisterRefresh = registerRefreshHook(() => void overview.refresh());
});
onBeforeUnmount(() => {
  unregisterRefresh?.();
  unregisterRefresh = null;
});

const monthValue = computed(() => overview.month || "");

function setMonth(e: Event): void {
  const v = (e.target as HTMLInputElement).value;
  if (v) void overview.refresh(v);
}

function go(path: string): void {
  void router.push(path);
}
</script>

<template>
  <div class="page">
    <header class="head">
      <h1 class="title">{{ COPY.navOverview }}</h1>
      <input
        class="month"
        type="month"
        :value="monthValue"
        @change="setMonth"
      />
    </header>

    <div class="kpi-grid">
      <button type="button" class="card kpi" @click="go('/ledger/stats')">
        <span class="kpi-label">{{ COPY.income }}</span>
        <span class="kpi-value tabular">{{ overview.data?.income ?? "—" }}</span>
      </button>
      <button type="button" class="card kpi" @click="go('/ledger/stats')">
        <span class="kpi-label">{{ COPY.expense }}</span>
        <span class="kpi-value tabular">{{ overview.data?.expense ?? "—" }}</span>
      </button>
      <button type="button" class="card kpi" @click="go('/ledger/stats')">
        <span class="kpi-label">{{ COPY.publicAccount }}</span>
        <span class="kpi-value tabular">{{ overview.data?.public_balance ?? "—" }}</span>
      </button>
      <button type="button" class="card kpi" @click="go('/ledger/entries?filter=claim')">
        <span class="kpi-label">待审报销</span>
        <span class="kpi-value tabular">
          {{ overview.data?.pending_claims.count ?? 0 }}
          <span class="kpi-sub">· {{ overview.data?.pending_claims.amount ?? "0.00" }}</span>
        </span>
      </button>
    </div>
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
.month {
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-md);
}
.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  display: grid;
  gap: var(--space-sm);
  border: none;
  text-align: left;
}
.card:hover {
  box-shadow: var(--shadow-md);
}
.kpi-label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.kpi-value {
  font-size: var(--text-2xl);
  font-weight: 600;
}
.kpi-sub {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  font-weight: 400;
}
.tabular {
  font-variant-numeric: tabular-nums;
}
</style>
