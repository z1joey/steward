<script setup lang="ts">
import { ref } from "vue";

import { api } from "@/app/http";
import { useStoreContextStore } from "@/app/stores/storeContext";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";

/**
 * TA-10 · 创建门店弹窗：成功后刷新门店上下文并进入账本流水（AC-AUTH-04）。
 */
const emit = defineEmits<{ created: [] }>();

const ctx = useStoreContextStore();
const open = defineModel<boolean>({ default: false });
const name = ref("");

async function submit(): Promise<void> {
  const trimmed = name.value.trim();
  if (!trimmed) return;
  await api.post("/stores", { name: trimmed });
  await ctx.refresh();
  open.value = false;
  name.value = "";
  emit("created");
}

function close(): void {
  open.value = false;
}
</script>

<template>
  <AppModal :open="open" :title="COPY.createStore" @close="close">
    <label class="field">
      <span>{{ COPY.storeName }}</span>
      <input v-model="name" maxlength="100" required @keyup.enter="submit" />
    </label>
    <div class="actions">
      <ConfirmButton :action="submit">{{ COPY.createStore }}</ConfirmButton>
    </div>
  </AppModal>
</template>

<style scoped>
.field {
  display: grid;
  gap: var(--space-xs);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
