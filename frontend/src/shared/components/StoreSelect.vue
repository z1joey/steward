<script setup lang="ts">
import { computed } from "vue";

import { useStoreContextStore } from "@/app/stores/storeContext";
import { COPY } from "@/shared/copy";

/**
 * TA-11 · 侧栏门店选择器：仅已接受 membership；单店隐藏（AC-AUTH-05）；
 * 切换由父级接 watch → resetStoreScopedStores() + 重拉（AC-ISO-03 / US-A8）。
 */
const emit = defineEmits<{ changed: [] }>();

const ctx = useStoreContextStore();

const visible = computed(() => ctx.stores.length > 1);

function onChange(event: Event): void {
  const value = Number((event.target as HTMLSelectElement).value);
  if (value !== ctx.selectedStoreId) {
    ctx.select(value);
    ctx.persistSelection();
    emit("changed");
  }
}
</script>

<template>
  <select
    v-if="visible"
    class="store-select"
    :value="ctx.selectedStoreId ?? undefined"
    :aria-label="COPY.storeName"
    @change="onChange"
  >
    <option v-for="s in ctx.stores" :key="s.id" :value="s.id">{{ s.name }}</option>
  </select>
</template>

<style scoped>
.store-select {
  width: 100%;
}
</style>
