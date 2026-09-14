<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useDebouncedSave } from "@/shared/components/useDebouncedSave";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";
import { EMPLOYEE_STATUS_LABELS, JOB_TYPE_LABELS } from "@/shared/enums";
import type { EmployeeDetail, JobType, PayType } from "@/shared/types";
import { fetchEmployeeDetail, useEmployeesStore } from "@/features/employees/stores/employees";

/**
 * TD-07 · 员工详情（AC-EMP-02 / US-E2/E3/E4）：
 * 资料表单防抖自动保存（500ms，PUT 带 version）；
 * 计薪区（[O-07] 计薪方式 + 单价，同表单自动保存）；
 * 请假区（起止日 + 登记 + 列表）；离职区（生效日 + ConfirmButton；已离职只读）。
 */
const route = useRoute();
const router = useRouter();
const employees = useEmployeesStore();

const employeeId = Number(route.params.id);
const detail = ref<EmployeeDetail | null>(null);
const notFound = ref(false);
const version = ref(1);
const saveState = ref<"idle" | "saving" | "saved" | "error">("idle");

const name = ref("");
const contact = ref("");
const jobType = ref<JobType>("long_term");
const notes = ref("");
// [O-07] 计薪："" = 未设置（pay_type/unit_price 双 null）
const payType = ref<PayType | "">("");
const unitPrice = ref<string>("");

const leaveStart = ref("");
const leaveEnd = ref("");
const leaveNote = ref("");

const resignOn = ref("");
const resignError = ref("");

const JOB_OPTIONS: JobType[] = ["long_term", "summer", "winter", "weekend", "temporary"];
const PAY_OPTIONS: { value: PayType | ""; label: string }[] = [
  { value: "", label: COPY.payTypeNone },
  { value: "hourly", label: COPY.payTypeHourly },
  { value: "daily", label: COPY.payTypeDaily },
];

const unitPriceSuffix = (): string =>
  payType.value === "daily" ? COPY.unitPerDay : COPY.unitPerHour;

async function load(): Promise<void> {
  try {
    const d = await fetchEmployeeDetail(employeeId);
    detail.value = d;
    name.value = d.name;
    contact.value = d.contact;
    jobType.value = d.job_type;
    notes.value = d.notes;
    payType.value = d.pay_type ?? "";
    unitPrice.value = d.unit_price ?? "";
    version.value = d.version;
  } catch {
    notFound.value = true;
  }
}

onMounted(load);

async function save(): Promise<void> {
  if (detail.value == null) return;
  saveState.value = "saving";
  try {
    version.value = await employees.saveProfile(employeeId, version.value, {
      name: name.value.trim(),
      contact: contact.value.trim(),
      job_type: jobType.value,
      notes: notes.value.trim(),
      // [O-07] 成对下发：未设置 → 双 null（后端视为「不变更」）；设置 → 双值
      pay_type: payType.value === "" ? null : payType.value,
      unit_price:
        payType.value === "" || unitPrice.value === "" ? null : unitPrice.value,
    });
    saveState.value = "saved";
  } catch {
    saveState.value = "error";
  }
}

const scheduleSave = useDebouncedSave(save, 500);

async function registerLeave(): Promise<void> {
  if (!leaveStart.value || !leaveEnd.value) return;
  await employees.registerLeave(employeeId, {
    start_date: leaveStart.value,
    end_date: leaveEnd.value,
    note: leaveNote.value.trim(),
  });
  leaveStart.value = "";
  leaveEnd.value = "";
  leaveNote.value = "";
  await load();
}

async function deleteLeave(leaveId: number, v: number): Promise<void> {
  await employees.deleteLeave(employeeId, leaveId, v);
  await load();
}

async function resign(): Promise<void> {
  if (!resignOn.value) return;
  resignError.value = "";
  try {
    await employees.resign(employeeId, resignOn.value, version.value);
    await load();
  } catch {
    resignError.value = "办理失败，请刷新后重试";
  }
}

function goBack(): void {
  router.push("/employees");
}
</script>

<template>
  <div v-if="notFound" class="page">
    <p class="muted">员工不存在</p>
  </div>
  <div v-else-if="detail" class="page">
    <header class="head">
      <button type="button" class="text-btn" @click="goBack">← {{ COPY.tabRoster }}</button>
      <h1 class="title">
        {{ detail.name }}
        <span class="pill" :class="detail.display_status">{{
          detail.display_status === "resigned"
            ? `${COPY.resignedOn} ${detail.resigned_on}`
            : EMPLOYEE_STATUS_LABELS[detail.display_status]
        }}</span>
      </h1>
      <span class="save-state">
        {{ saveState === "saving" ? "保存中…" : saveState === "saved" ? "已保存" : saveState === "error" ? "保存失败" : COPY.saveHint }}
      </span>
    </header>

    <section class="card">
      <h2 class="section-title">资料</h2>
      <div class="grid2">
        <label class="field">
          <span>{{ COPY.employeeName }}</span>
          <input v-model="name" maxlength="50" :disabled="detail.status === 'resigned'" @input="scheduleSave" />
        </label>
        <label class="field">
          <span>{{ COPY.contact }}</span>
          <input v-model="contact" maxlength="100" :disabled="detail.status === 'resigned'" @input="scheduleSave" />
        </label>
        <label class="field">
          <span>{{ COPY.jobType }}</span>
          <select v-model="jobType" :disabled="detail.status === 'resigned'" @change="scheduleSave">
            <option v-for="j in JOB_OPTIONS" :key="j" :value="j">{{ JOB_TYPE_LABELS[j] }}</option>
          </select>
        </label>
        <label class="field">
          <span>{{ COPY.notesLabel }}</span>
          <input v-model="notes" maxlength="500" :disabled="detail.status === 'resigned'" @input="scheduleSave" />
        </label>
      </div>
    </section>

    <section class="card">
      <h2 class="section-title">{{ COPY.paySection }}</h2>
      <div class="grid2">
        <label class="field">
          <span>{{ COPY.payTypeLabel }}</span>
          <select v-model="payType" :disabled="detail.status === 'resigned'" @change="scheduleSave">
            <!-- [O-07] 已设置后不支持清除（后端无清除语义） -->
            <option
              v-for="o in PAY_OPTIONS"
              :key="o.value"
              :value="o.value"
              :disabled="o.value === '' && detail.pay_type != null"
            >
              {{ o.label }}
            </option>
          </select>
        </label>
        <label class="field">
          <span>{{ COPY.unitPrice }}（{{ unitPriceSuffix() }}）</span>
          <input
            v-model="unitPrice"
            type="number"
            min="0.01"
            step="0.01"
            :disabled="detail.status === 'resigned' || payType === ''"
            @input="scheduleSave"
          />
        </label>
      </div>
    </section>

    <section class="card">
      <h2 class="section-title">请假</h2>
      <div class="grid3">
        <label class="field">
          <span>{{ COPY.leaveStart }}</span>
          <input v-model="leaveStart" type="date" />
        </label>
        <label class="field">
          <span>{{ COPY.leaveEnd }}</span>
          <input v-model="leaveEnd" type="date" />
        </label>
        <label class="field">
          <span>{{ COPY.notesLabel }}</span>
          <input v-model="leaveNote" maxlength="200" />
        </label>
      </div>
      <div class="actions">
        <ConfirmButton :action="registerLeave">{{ COPY.registerLeave }}</ConfirmButton>
      </div>
      <table class="mini-table">
        <tbody>
          <tr v-for="l in detail.leaves" :key="l.id">
            <td>{{ l.start_date }} ~ {{ l.end_date }}</td>
            <td>{{ l.note || "—" }}</td>
            <td class="right">
              <ConfirmButton danger class="mini" :action="() => deleteLeave(l.id, l.version)">
                {{ COPY.reject }}
              </ConfirmButton>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <section class="card">
      <h2 class="section-title">离职</h2>
      <template v-if="detail.status !== 'resigned'">
        <div class="grid3">
          <label class="field">
            <span>{{ COPY.resignEffective }}</span>
            <input v-model="resignOn" type="date" />
          </label>
        </div>
        <p v-if="resignError" class="error">{{ resignError }}</p>
        <div class="actions">
          <ConfirmButton danger :action="resign" :disabled="!resignOn">
            {{ COPY.resign }}
          </ConfirmButton>
        </div>
      </template>
      <p v-else class="muted">{{ COPY.resignedOn }}：{{ detail.resigned_on }}</p>
    </section>
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
  gap: var(--space-md);
}
.title {
  margin: 0;
  font-size: var(--text-xl);
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex: 1;
}
.save-state {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
.text-btn {
  border: none;
  background: transparent;
  color: var(--color-primary);
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
.grid2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}
.grid3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
  align-items: end;
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
.actions {
  display: flex;
  justify-content: flex-end;
}
.mini-table {
  width: 100%;
  border-collapse: collapse;
}
.mini-table td {
  padding: var(--space-sm) 0;
  border-bottom: 1px solid var(--color-line);
  font-size: var(--text-sm);
}
.right {
  text-align: right;
}
.pill {
  display: inline-block;
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  padding: 2px var(--space-sm);
  background: var(--color-surface-sunken);
  color: var(--color-text-muted);
}
.pill.on_leave {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
.mini {
  padding: 2px var(--space-sm);
  font-size: var(--text-xs);
}
.muted {
  margin: 0;
  color: var(--color-text-muted);
}
.error {
  margin: 0;
  color: var(--color-error);
  font-size: var(--text-sm);
}
</style>
