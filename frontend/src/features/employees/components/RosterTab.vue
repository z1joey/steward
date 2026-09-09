<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { useEmployeesStore } from "@/features/employees/stores/employees";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";
import { EMPLOYEE_STATUS_LABELS, JOB_TYPE_LABELS } from "@/shared/enums";
import type { JobType, PayType } from "@/shared/types";

/**
 * TD-06 · 花名册 Tab（AC-EMP-01/02 / US-E1）：
 * 列 姓名/状态 pill/联系方式/工种/备注；「新增员工」抽屉（[O-07] 可选计薪方式+单价）；
 * 行上无请假/离职控件（Locked）；「显示已离职」开关 [C]。
 */
const employees = useEmployeesStore();
const router = useRouter();

const drawerOpen = ref(false);
const formName = ref("");
const formContact = ref("");
const formJobType = ref<JobType>("long_term");
const formNotes = ref("");
const formPayType = ref<PayType | "">("");
const formUnitPrice = ref("");

const JOB_OPTIONS: JobType[] = ["long_term", "summer", "winter", "weekend", "temporary"];

async function submitCreate(): Promise<void> {
  if (!formName.value.trim()) return;
  await employees.createEmployee({
    name: formName.value.trim(),
    contact: formContact.value.trim(),
    job_type: formJobType.value,
    notes: formNotes.value.trim(),
    // [O-07] 可选：成对下发，未设置则不带（后端默认双 null）
    ...(formPayType.value !== "" && formUnitPrice.value !== ""
      ? { pay_type: formPayType.value, unit_price: formUnitPrice.value }
      : {}),
  });
  drawerOpen.value = false;
  formName.value = "";
  formContact.value = "";
  formNotes.value = "";
  formPayType.value = "";
  formUnitPrice.value = "";
}
</script>

<template>
  <div class="roster">
    <div class="toolbar">
      <label class="switch">
        <input
          type="checkbox"
          :checked="employees.includeResigned"
          @change="employees.setIncludeResigned(!employees.includeResigned)"
        />
        <span>{{ COPY.showResigned }}</span>
      </label>
      <button type="button" class="primary-btn" @click="drawerOpen = true">
        {{ COPY.addEmployee }}
      </button>
    </div>

    <table class="table">
      <thead>
        <tr>
          <th>{{ COPY.employeeName }}</th>
          <th>状态</th>
          <th>{{ COPY.contact }}</th>
          <th>{{ COPY.jobType }}</th>
          <th>{{ COPY.notesLabel }}</th>
        </tr>
      </thead>
      <tbody>
        <!-- 行点击进详情；行上无请假/离职控件（Locked） -->
        <tr
          v-for="e in employees.items"
          :key="e.id"
          class="row"
          @click="router.push(`/employees/${e.id}`)"
        >
          <td>{{ e.name }}</td>
          <td>
            <span class="pill" :class="e.display_status">
              {{ EMPLOYEE_STATUS_LABELS[e.display_status as keyof typeof EMPLOYEE_STATUS_LABELS] ?? e.display_status }}
            </span>
          </td>
          <td>{{ e.contact || "—" }}</td>
          <td>{{ JOB_TYPE_LABELS[e.job_type] }}</td>
          <td class="notes">{{ e.notes || "—" }}</td>
        </tr>
        <tr v-if="employees.items.length === 0 && !employees.loading">
          <td class="empty" colspan="5">暂无员工</td>
        </tr>
      </tbody>
    </table>

    <AppModal :open="drawerOpen" :title="COPY.addEmployee" @close="drawerOpen = false">
      <label class="field">
        <span>{{ COPY.employeeName }}</span>
        <input v-model="formName" maxlength="50" />
      </label>
      <label class="field">
        <span>{{ COPY.contact }}</span>
        <input v-model="formContact" maxlength="100" />
      </label>
      <label class="field">
        <span>{{ COPY.jobType }}</span>
        <select v-model="formJobType">
          <option v-for="j in JOB_OPTIONS" :key="j" :value="j">{{ JOB_TYPE_LABELS[j] }}</option>
        </select>
      </label>
      <label class="field">
        <span>{{ COPY.notesLabel }}</span>
        <input v-model="formNotes" maxlength="500" />
      </label>
      <div class="grid2">
        <label class="field">
          <span>{{ COPY.payTypeLabel }}</span>
          <select v-model="formPayType">
            <option value="">{{ COPY.payTypeNone }}</option>
            <option value="hourly">{{ COPY.payTypeHourly }}</option>
            <option value="daily">{{ COPY.payTypeDaily }}</option>
          </select>
        </label>
        <label class="field">
          <span>{{ COPY.unitPrice }}</span>
          <input
            v-model="formUnitPrice"
            type="number"
            min="0.01"
            step="0.01"
            :disabled="formPayType === ''"
          />
        </label>
      </div>
      <div class="actions">
        <ConfirmButton :action="submitCreate">{{ COPY.addEmployee }}</ConfirmButton>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.roster {
  display: grid;
  gap: var(--space-md);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.switch {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
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
.row {
  cursor: pointer;
}
.row:hover {
  background: var(--color-primary-soft);
}
.notes {
  color: var(--color-text-muted);
}
.pill {
  display: inline-block;
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  padding: 2px var(--space-sm);
}
.pill.active {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.pill.resigned {
  background: var(--color-surface-sunken);
  color: var(--color-text-muted);
}
.pill.on_leave {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.empty {
  text-align: center;
  color: var(--color-text-muted);
  padding: var(--space-xl);
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
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
