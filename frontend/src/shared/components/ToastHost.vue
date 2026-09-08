<script setup lang="ts">
import { useToastStore } from "@/app/stores/toasts";

/** T0-11 · 全局 toast 宿主（挂载于根组件；AC-CON-02 提示载体）。 */
const toasts = useToastStore();
</script>

<template>
  <Teleport to="body">
    <div class="toast-host" aria-live="polite">
      <div
        v-for="t in toasts.toasts"
        :key="t.id"
        class="toast"
        :class="t.kind"
        @click="toasts.dismiss(t.id)"
      >
        {{ t.text }}
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-host {
  position: fixed;
  top: calc(var(--size-topbar) + var(--space-md));
  left: 50%;
  transform: translateX(-50%);
  display: grid;
  gap: var(--space-sm);
  z-index: 100;
}
.toast {
  background: var(--color-surface);
  color: var(--color-text);
  border: 1px solid var(--color-line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-sm) var(--space-md);
  font-size: var(--text-md);
}
.toast.error {
  border-color: var(--color-error);
  color: var(--color-error);
}
.toast.success {
  border-color: var(--color-success);
  color: var(--color-success);
}
</style>
