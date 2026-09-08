<script setup lang="ts">
import { useStoreContextStore } from "@/app/stores/storeContext";
import PendingList from "@/features/onboarding/components/PendingList.vue";

/**
 * TA-10 · /invites：与 onboarding 复用同一列表组件（B-specs §1.3）。
 */
const ctx = useStoreContextStore();

async function afterChanged(): Promise<void> {
  await ctx.refresh();
}
</script>

<template>
  <div class="page">
    <PendingList @changed="afterChanged" />
  </div>
</template>

<style scoped>
.page {
  max-width: var(--size-content-max);
}
</style>
