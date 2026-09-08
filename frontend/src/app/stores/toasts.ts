import { defineStore } from "pinia";

export interface Toast {
  id: number;
  text: string;
  kind: "info" | "error" | "success";
}

let nextId = 1;

/** 全局 toast 队列（AC-CON-02：409 → 「已被别人更新，已刷新」）。 */
export const useToastStore = defineStore("toasts", {
  state: () => ({ toasts: [] as Toast[] }),
  actions: {
    show(text: string, kind: Toast["kind"] = "info", ttlMs = 3000) {
      const id = nextId++;
      this.toasts.push({ id, text, kind });
      window.setTimeout(() => this.dismiss(id), ttlMs);
    },
    dismiss(id: number) {
      this.toasts = this.toasts.filter((t) => t.id !== id);
    },
  },
});
