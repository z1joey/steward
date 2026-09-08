<script setup lang="ts">
import { ref } from "vue";

/**
 * T0-11 · 确认类按钮（AC-CON-03）：点击后 loading 直至响应完成，防连点。
 */
const props = defineProps<{
  action: () => Promise<unknown>;
  danger?: boolean;
  disabled?: boolean;
}>();

const loading = ref(false);

async function onClick(): Promise<void> {
  if (loading.value || props.disabled) return;
  loading.value = true;
  try {
    await props.action();
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <button
    type="button"
    class="confirm-btn"
    :class="{ danger: props.danger, loading }"
    :disabled="loading || props.disabled"
    @click="onClick"
  >
    <span v-if="loading" class="spinner" aria-label="loading" />
    <slot />
  </button>
</template>

<style scoped>
.confirm-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-sm);
  padding: var(--space-sm) var(--space-md);
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
}
.confirm-btn:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
.confirm-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.confirm-btn.danger {
  background: transparent;
  color: var(--color-error);
  border: 1px solid var(--color-error);
}
.confirm-btn.danger:hover:not(:disabled) {
  background: var(--color-error-soft);
}
.spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.danger .spinner {
  border-color: var(--color-error-soft);
  border-top-color: var(--color-error);
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
