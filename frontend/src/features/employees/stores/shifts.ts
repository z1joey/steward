import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";
import type { ShiftList } from "@/shared/types";

/** 切店重置注册（Pinia 激活后调用一次）。 */
let resetRegistered = false;

export function ensureShiftsResetRegistered(): void {
  if (resetRegistered) return;
  resetRegistered = true;
  registerStoreReset(() => useShiftsStore().$reset());
}

function mondayOf(d: Date): string {
  const day = d.getDate() - ((d.getDay() + 6) % 7);
  const monday = new Date(d.getFullYear(), d.getMonth(), day);
  return `${monday.getFullYear()}-${String(monday.getMonth() + 1).padStart(2, "0")}-${String(
    monday.getDate(),
  ).padStart(2, "0")}`;
}

/** TD-08 · shiftsStore：周视图数据 + 段 CRUD（AC-EMP-04/05）。 */
export const useShiftsStore = defineStore("shifts", {
  state: () => ({
    weekStart: mondayOf(new Date()),   // YYYY-MM-DD（周一）
    items: [] as ShiftList["items"],
    employees: [] as ShiftList["employees"],
    loading: false,
  }),
  getters: {
    weekDays(state): Date[] {
      const [y, m, d] = state.weekStart.split("-").map(Number);
      const monday = new Date(y, m - 1, d);
      return Array.from({ length: 7 }, (_, i) => {
        const day = new Date(monday);
        day.setDate(monday.getDate() + i);
        return day;
      });
    },
  },
  actions: {
    async refresh(): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<ShiftList>("/shift_segments", {
          params: { from: this.weekStart, to: this.weekStart },
        });
        this.items = data.items;
        this.employees = data.employees;
      } finally {
        this.loading = false;
      }
    },
    async setWeek(weekStart: string): Promise<void> {
      this.weekStart = weekStart;
      await this.refresh();
    },
    segmentsOf(employeeId: number, day: Date): ShiftList["items"] {
      const key = `${day.getFullYear()}-${String(day.getMonth() + 1).padStart(2, "0")}-${String(
        day.getDate(),
      ).padStart(2, "0")}`;
      return this.items.filter(
        (s) => s.employee_id === employeeId && s.start_at.slice(0, 10) === key,
      );
    },
    async createSegment(payload: {
      employee_id: number;
      start_at: string;
      end_at: string;
    }): Promise<void> {
      await api.post("/shift_segments", payload);
      await this.refresh();
    },
    async updateSegment(
      id: number,
      version: number,
      payload: { start_at: string; end_at: string },
    ): Promise<void> {
      await api.put(`/shift_segments/${id}`, { version, ...payload });
      await this.refresh();
    },
    async deleteSegment(id: number, version: number): Promise<void> {
      await api.request({ method: "DELETE", url: `/shift_segments/${id}`, data: { version } });
      await this.refresh();
    },
    $reset() {
      this.weekStart = mondayOf(new Date());
      this.items = [];
      this.employees = [];
      this.loading = false;
    },
  },
});
