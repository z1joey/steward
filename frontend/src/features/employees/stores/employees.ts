import { defineStore } from "pinia";

import { api } from "@/app/http";
import { registerStoreReset } from "@/app/reset";
import type { EmployeeDetail, EmployeeItem, LeaveItem } from "@/shared/types";

/** 切店重置注册（Pinia 激活后调用一次）。 */
let resetRegistered = false;

export function ensureEmployeesResetRegistered(): void {
  if (resetRegistered) return;
  resetRegistered = true;
  registerStoreReset(() => useEmployeesStore().$reset());
}

/** TD-06 · employeesStore：花名册（AC-EMP-01/02）。 */
export const useEmployeesStore = defineStore("employees", {
  state: () => ({
    items: [] as EmployeeItem[],
    includeResigned: false,
    loading: false,
  }),
  actions: {
    async refresh(): Promise<void> {
      this.loading = true;
      try {
        const { data } = await api.get<{ items: EmployeeItem[] }>("/employees", {
          params: this.includeResigned ? { include_resigned: true } : {},
        });
        this.items = data.items;
      } finally {
        this.loading = false;
      }
    },
    async setIncludeResigned(v: boolean): Promise<void> {
      this.includeResigned = v;
      await this.refresh();
    },
    async createEmployee(payload: {
      name: string;
      contact: string;
      job_type: string;
      notes: string;
      pay_type?: string | null;
      unit_price?: string | null;
    }): Promise<void> {
      await api.post("/employees", payload);
      await this.refresh();
    },
    async saveProfile(
      id: number,
      version: number,
      fields: {
        name?: string;
        contact?: string;
        job_type?: string;
        notes?: string;
        pay_type?: string | null;
        unit_price?: string | null;
      },
    ): Promise<number> {
      const { data } = await api.put<EmployeeItem>(`/employees/${id}`, {
        version,
        ...fields,
      });
      return data.version;
    },
    async registerLeave(
      id: number,
      payload: { start_date: string; end_date: string; note: string },
    ): Promise<LeaveItem> {
      const { data } = await api.post<LeaveItem>(`/employees/${id}/leaves`, payload);
      return data;
    },
    async deleteLeave(employeeId: number, leaveId: number, version: number): Promise<void> {
      await api.request({ method: "DELETE", url: `/employees/${employeeId}/leaves/${leaveId}`, data: { version } });
    },
    async resign(id: number, effectiveOn: string, version: number): Promise<void> {
      await api.post(`/employees/${id}/resign`, {
        effective_on: effectiveOn,
        version,
      });
    },
    $reset() {
      this.items = [];
      this.includeResigned = false;
      this.loading = false;
    },
  },
});

export async function fetchEmployeeDetail(id: number): Promise<EmployeeDetail> {
  const { data } = await api.get<EmployeeDetail>(`/employees/${id}`);
  return data;
}
