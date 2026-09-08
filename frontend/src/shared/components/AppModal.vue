<script setup lang="ts">
import { onBeforeUnmount, onMounted } from "vue";

import { registerModalCloser } from "@/app/reset";

/**
 * T0-11 · 独立弹窗容器：size.modal-sm 440px · shadow.md · overlay rgba(15,23,42,.45)
 * （design-system §6/§7，AC-LED-01 弹窗基座）。
 */
const props = defineProps<{
  open: boolean;
  title?: string;
  width?: string;
}>();

const emit = defineEmits<{ close: [] }>();

let unregister: (() => void) | null = null;

onMounted(() => {
  unregister = registerModalCloser(() => emit("close"));
});
onBeforeUnmount(() => unregister?.());
</script>

<template>
  <Teleport to="body">
    <div v-if="props.open" class="overlay" @click.self="emit('close')">
      <div
        class="modal"
        :style="{ width: props.width ?? 'var(--size-modal-sm)' }"
        role="dialog"
        :aria-label="props.title"
      >
        <header v-if="props.title" class="modal-head">
          <h2 class="modal-title">{{ props.title }}</h2>
          <button type="button" class="close" aria-label="关闭" @click="emit('close')">×</button>
        </header>
        <div class="modal-body">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-lg);
  max-width: calc(100vw - 32px);
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-md);
}
.modal-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
}
.close {
  border: none;
  background: transparent;
  color: var(--color-text-muted);
  font-size: var(--text-xl);
  line-height: 1;
  padding: var(--space-xs);
}
.modal-body {
  display: grid;
  gap: var(--space-md);
}
</style>
