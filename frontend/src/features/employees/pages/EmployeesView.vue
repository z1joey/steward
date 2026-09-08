<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { registerRefreshHook } from "@/app/http";
import {
  ensureEmployeesResetRegistered,
  useEmployeesStore,
} from "@/features/employees/stores/employees";
import { ensureShiftsResetRegistered } from "@/features/employees/stores/shifts";
import { ensurePayrollResetRegistered, usePayrollStore } from "@/features/payroll/stores/payroll";
import RosterTab from "@/features/employees/components/RosterTab.vue";
import ShiftsTab from "@/features/employees/components/ShiftsTab.vue";
import PayrollTab from "@/features/payroll/components/PayrollTab.vue";
import { COPY } from "@/shared/copy";

/**
 * TD-06/08/09 · /employees 顶部 Tab [C · O-11]：花名册 · 排班 · 薪资（?tab= 查询参数）。
 */
const route = useRoute();
const router = useRouter();
const employees = useEmployeesStore();
const payroll = usePayrollStore();

type Tab = "roster" | "shifts" | "payroll";
const TABS: { key: Tab; label: string }[] = [
  { key: "roster", label: COPY.tabRoster },
  { key: "shifts", label: COPY.tabShifts },
  { key: "payroll", label: COPY.tabPayroll },
];

function currentTab(): Tab {
  const t = route.query.tab;
  return t === "shifts" || t === "payroll" ? t : "roster";
}

const tab = ref<Tab>(currentTab());

watch(tab, (t) => {
  if (route.query.tab !== t) router.replace({ query: { tab: t } });
});

let unregisterRefresh: (() => void) | null = null;

onMounted(() => {
  ensureEmployeesResetRegistered();
  ensureShiftsResetRegistered();
  ensurePayrollResetRegistered();
  employees.refresh();
  unregisterRefresh = registerRefreshHook(() => {
    void employees.refresh();
    void payroll.refresh();
  });
});
onBeforeUnmount(() => {
  unregisterRefresh?.();
  unregisterRefresh = null;
});

function onShiftsChanged(): void {
  // AC-PAY-01：排班保存后薪资汇总自动刷新
  void payroll.refresh();
}
</script>

<template>
  <div class="page">
    <h1 class="title">{{ COPY.navEmployees }}</h1>
    <nav class="tabs">
      <button
        v-for="t in TABS"
        :key="t.key"
        type="button"
        class="tab"
        :class="{ active: tab === t.key }"
        @click="tab = t.key"
      >
        {{ t.label }}
      </button>
    </nav>

    <RosterTab v-if="tab === 'roster'" />
    <ShiftsTab v-else-if="tab === 'shifts'" @changed="onShiftsChanged" />
    <PayrollTab v-else />
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
.tabs {
  display: flex;
  gap: var(--space-sm);
  border-bottom: 1px solid var(--color-line);
}
.tab {
  border: none;
  background: transparent;
  padding: var(--space-sm) var(--space-md);
  font-size: var(--text-md);
  color: var(--color-text-muted);
  border-bottom: 2px solid transparent;
}
.tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 500;
}
</style>
