<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import { registerRefreshHook } from "@/app/http";
import {
  ensureShiftsResetRegistered,
  useShiftsStore,
} from "@/features/employees/stores/shifts";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";

/**
 * TD-08 · 排班 Tab（AC-EMP-04/05 / US-E5/E6 / ui-spec §3.7）：
 * 周视图 7 列 × 员工行；日格多段卡片（时段 + text.xs 时长）；多段格「当日合计」；
 * 段新增/编辑/删除（分钟精度，version）；可见员工由服务端 employees 决定。
 */
const shifts = useShiftsStore();

const emit = defineEmits<{ changed: [] }>();

let unregisterRefresh: (() => void) | null = null;

onMounted(() => {
  ensureShiftsResetRegistered();
  shifts.refresh();
  unregisterRefresh = registerRefreshHook(() => void shifts.refresh());
});
onBeforeUnmount(() => {
  unregisterRefresh?.();
  unregisterRefresh = null;
});

function keyOf(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
}

function shiftWeek(deltaDays: number): void {
  const [y, m, d] = shifts.weekStart.split("-").map(Number);
  const monday = new Date(y, m - 1, d + deltaDays);
  void shifts.setWeek(keyOf(monday));
}

function fmtDay(d: Date): string {
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function fmtMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}${COPY.hoursUnit}` : `${h}${COPY.hoursUnit}${m}m`;
}

const totalMinutes = computed(() =>
  fmtMinutes(shifts.items.reduce((acc, i) => acc + i.minutes, 0)),
);

// —— 段编辑弹窗（新增 / 编辑共用）——
const open = ref(false);
const editingId = ref<number | null>(null);
const editingVersion = ref(1);
const segEmployeeId = ref<number | null>(null);
const segDate = ref<string>("");
const segStart = ref("09:00");
const segEnd = ref("17:00");

function openCreate(employeeId: number, day: Date): void {
  editingId.value = null;
  segEmployeeId.value = employeeId;
  segDate.value = keyOf(day);
  segStart.value = "09:00";
  segEnd.value = "17:00";
  open.value = true;
}

function openEdit(
  employeeId: number,
  segId: number,
  version: number,
  startAt: string,
  endAt: string,
): void {
  editingId.value = segId;
  editingVersion.value = version;
  segEmployeeId.value = employeeId;
  segDate.value = startAt.slice(0, 10);
  segStart.value = startAt.slice(11, 16);
  segEnd.value = endAt.slice(11, 16);
  open.value = true;
}

async function submitSegment(): Promise<void> {
  if (segEmployeeId.value == null || !segDate.value) return;
  const body = {
    start_at: `${segDate.value}T${segStart.value}`,
    end_at: `${segDate.value}T${segEnd.value}`,
  };
  if (editingId.value == null) {
    await shifts.createSegment({ employee_id: segEmployeeId.value, ...body });
  } else {
    await shifts.updateSegment(editingId.value, editingVersion.value, body);
  }
  open.value = false;
  emit("changed");
}

async function removeSegment(): Promise<void> {
  if (editingId.value == null) return;
  await shifts.deleteSegment(editingId.value, editingVersion.value);
  open.value = false;
  emit("changed");
}
</script>

<template>
  <div class="shifts">
    <div class="toolbar">
      <button type="button" class="week-btn" @click="shiftWeek(-7)">←</button>
      <span class="week-label">{{ shifts.weekStart }} 起 · 本周合计 {{ totalMinutes }}</span>
      <button type="button" class="week-btn" @click="shiftWeek(7)">→</button>
    </div>

    <div class="grid-head">
      <div class="emp-col"></div>
      <div v-for="d in shifts.weekDays" :key="keyOf(d)" class="day-head">
        {{ fmtDay(d) }}
      </div>
    </div>

    <div v-for="e in shifts.employees" :key="e.id" class="row">
      <div class="emp-col">
        <span class="emp-name">{{ e.name }}</span>
        <span v-if="e.status === 'resigned'" class="resigned-tag">离职</span>
      </div>
      <div
        v-for="d in shifts.weekDays"
        :key="keyOf(d)"
        class="day-cell"
        @click="openCreate(e.id, d)"
      >
        <div
          v-for="seg in shifts.segmentsOf(e.id, d)"
          :key="seg.id"
          class="seg"
          @click.stop="openEdit(e.id, seg.id, seg.version, seg.start_at, seg.end_at)"
        >
          <span class="seg-time">{{ seg.start_at.slice(11, 16) }}–{{ seg.end_at.slice(11, 16) }}</span>
          <span class="seg-mins">{{ fmtMinutes(seg.minutes) }}</span>
        </div>
        <div v-if="shifts.segmentsOf(e.id, d).length > 1" class="day-total">
          {{ COPY.dayTotal }}
          {{ fmtMinutes(shifts.segmentsOf(e.id, d).reduce((a, s) => a + s.minutes, 0)) }}
        </div>
      </div>
    </div>

    <AppModal :open="open" :title="COPY.addSegment" @close="open = false">
      <div class="seg-form">
        <label class="field">
          <span>日期</span>
          <input v-model="segDate" type="date" />
        </label>
        <label class="field">
          <span>开始</span>
          <input v-model="segStart" type="time" />
        </label>
        <label class="field">
          <span>结束</span>
          <input v-model="segEnd" type="time" />
        </label>
      </div>
      <div class="actions">
        <ConfirmButton v-if="editingId != null" danger :action="removeSegment">
          删除
        </ConfirmButton>
        <ConfirmButton :action="submitSegment">
          {{ editingId == null ? "新增" : "保存" }}
        </ConfirmButton>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.shifts {
  display: grid;
  gap: var(--space-md);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}
.week-btn {
  border: 1px solid var(--color-line-strong);
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: var(--space-xs) var(--space-sm);
}
.week-label {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.grid-head,
.row {
  display: grid;
  grid-template-columns: 120px repeat(7, 1fr);
  gap: 4px;
}
.day-head {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  padding: var(--space-xs);
}
.emp-col {
  font-size: var(--text-sm);
  padding: var(--space-xs);
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}
.emp-name {
  font-weight: 500;
}
.resigned-tag {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  background: var(--color-surface-sunken);
  border-radius: var(--radius-pill);
  padding: 0 var(--space-sm);
}
.day-cell {
  min-height: 64px;
  background: var(--color-surface);
  border-radius: var(--radius-md);
  padding: 4px;
  display: grid;
  gap: 4px;
  align-content: start;
  cursor: pointer;
  border: 1px solid var(--color-line);
}
.seg {
  background: var(--color-primary-soft);
  border-radius: var(--radius-sm);
  padding: 2px var(--space-xs);
  display: grid;
}
.seg-time {
  font-size: var(--text-xs);
}
.seg-mins {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
.day-total {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
.seg-form {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
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
.actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-md);
}
</style>
