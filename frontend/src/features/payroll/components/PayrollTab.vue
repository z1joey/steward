<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { registerRefreshHook } from "@/app/http";
import { useRole } from "@/app/composables/useRole";
import {
  ensurePayrollResetRegistered,
  usePayrollStore,
} from "@/features/payroll/stores/payroll";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";

/**
 * TD-09 · 薪资 Tab（AC-PAY-01/02 / US-E7/E8 · [O-07 拍板 2026-09-09]）：
 * 月选择器；表 姓名/工时/出勤/应发（null →「未设置计薪」）/段数；无「计算」按钮；
 * 排班保存后自动 refresh；管理者「结算工资」ConfirmButton；已结算月只读 + 链接
 * filter=payroll；店长不渲染按钮。
 */
const payroll = usePayrollStore();
const { isManager } = useRole();

const settleError = ref("");

let unregisterRefresh: (() => void) | null = null;

onMounted(() => {
  ensurePayrollResetRegistered();
  payroll.refresh();
  unregisterRefresh = registerRefreshHook(() => void payroll.refresh());
});
onBeforeUnmount(() => {
  unregisterRefresh?.();
  unregisterRefresh = null;
});

function onShiftsChanged(): void {
  void payroll.refresh();
}

defineExpose({ onShiftsChanged });

const isSettled = computed(() => payroll.data?.settled != null);

async function settle(): Promise<void> {
  settleError.value = "";
  try {
    await payroll.settle();
  } catch (e) {
    const status = (e as { response?: { status?: number; data?: { detail?: string } } })
      .response?.status;
    if (status === 422) {
      settleError.value = COPY.settleBlocked;
    }
    // 409 → 全局 toast + refresh 兜底
  }
}
</script>

<template>
  <div class="payroll">
    <div class="toolbar">
      <input
        class="month"
        type="month"
        :value="payroll.month"
        @change="payroll.setMonth(($event.target as HTMLInputElement).value)"
      />
      <span class="spacer"></span>
      <ConfirmButton
        v-if="isManager && !isSettled"
        :action="settle"
      >
        {{ COPY.payrollSettle }}
      </ConfirmButton>
    </div>

    <p v-if="settleError" class="error">{{ settleError }}</p>

    <!-- 已结算月：只读明细 + 流水链接（AC-PAY-02） -->
    <template v-if="isSettled">
      <p class="settled-tag">{{ COPY.settledMonth }} · 合计 {{ payroll.data?.settled?.total_amount }}</p>
      <table class="table">
        <thead>
          <tr>
            <th>{{ COPY.employeeName }}</th>
            <th class="right">工时</th>
            <th class="right">应发</th>
            <th class="right">流水</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in payroll.data?.settled?.lines ?? []" :key="l.employee_id">
            <td>{{ payroll.data?.preview.find((p) => p.employee_id === l.employee_id)?.name ?? l.employee_id }}</td>
            <td class="right tabular">{{ l.hours }}</td>
            <td class="right tabular">{{ l.amount }}</td>
            <td class="right">
              <RouterLink class="link" to="/ledger/entries?filter=payroll">
                {{ COPY.navEntries }}
              </RouterLink>
            </td>
          </tr>
        </tbody>
      </table>
    </template>

    <!-- 未结算：自动汇总预览 -->
    <template v-else>
      <table class="table">
        <thead>
          <tr>
            <th>{{ COPY.employeeName }}</th>
            <th>工时</th>
            <th class="right">{{ COPY.attendance }}</th>
            <th class="right">应发</th>
            <th class="right">段数</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in payroll.data?.preview ?? []" :key="p.employee_id">
            <td>{{ p.name }}</td>
            <td class="tabular">{{ p.hours }}</td>
            <td class="right tabular">{{ p.worked_days }} 天</td>
            <td class="right tabular">
              {{ p.amount ?? COPY.ratePending }}
            </td>
            <td class="right tabular">{{ p.segments_count }}</td>
          </tr>
          <tr v-if="(payroll.data?.preview.length ?? 0) === 0 && !payroll.loading">
            <td class="empty" colspan="5">本月暂无排班</td>
          </tr>
        </tbody>
      </table>
      <div v-if="payroll.data?.preview.length" class="totals tabular">
        合计工时 {{ payroll.data?.total_hours }} · 合计应发
        {{ payroll.data?.total_amount ?? COPY.ratePending }}
      </div>
    </template>
  </div>
</template>

<style scoped>
.payroll {
  display: grid;
  gap: var(--space-md);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}
.month {
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
}
.spacer {
  flex: 1;
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
.tabular {
  font-variant-numeric: tabular-nums;
}
.settled-tag {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-success);
}
.link {
  color: var(--color-primary);
  text-decoration: none;
}
.link:hover {
  text-decoration: underline;
}
.totals {
  text-align: right;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-xl);
}
.error {
  margin: 0;
  color: var(--color-error);
  font-size: var(--text-sm);
}
</style>
