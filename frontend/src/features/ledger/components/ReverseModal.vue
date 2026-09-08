<script setup lang="ts">
import { ref, watch } from "vue";

import { api } from "@/app/http";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";

/**
 * TB-08 · 冲正确认弹窗（AC-LED-08 / US-B6 / [Open O-09]）：
 * 可选原因；ConfirmButton 防连点；成功后由父组件刷新（原行「已冲正」+ 新反向行）。
 */
const target = defineModel<{ id: number; version: number; memo: string } | null>({
  default: null,
});
const emit = defineEmits<{ reversed: [] }>();

const reason = ref("");

watch(target, (t) => {
  if (t != null) reason.value = "";
});

async function submit(): Promise<void> {
  const t = target.value;
  if (t == null) return;
  await api.post(`/ledger/entries/${t.id}/reverse`, {
    version: t.version,
    reason: reason.value.trim(),
  });
  target.value = null;
  emit("reversed");
}

function close(): void {
  target.value = null;
}
</script>

<template>
  <AppModal :open="target != null" :title="COPY.confirmReverse" @close="close">
    <p v-if="target" class="hint">{{ target.memo || COPY.memo }}</p>
    <label class="field">
      <span>{{ COPY.reverseReason }}</span>
      <input v-model="reason" maxlength="500" @keyup.enter="submit" />
    </label>
    <div class="actions">
      <ConfirmButton :action="submit">{{ COPY.reverse }}</ConfirmButton>
    </div>
  </AppModal>
</template>

<style scoped>
.hint {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
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
}
</style>
