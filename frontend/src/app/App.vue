<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import AppShell from "@/app/AppShell.vue";
import ToastHost from "@/shared/components/ToastHost.vue";
import { COPY } from "@/shared/copy";

const route = useRoute();
const bare = computed(() => route.meta.bare === true);
const title = computed(() => (route.meta.title as string | undefined) ?? COPY.appName);
</script>

<template>
  <component :is="bare ? 'div' : AppShell">
    <RouterView v-slot="{ Component }">
      <component :is="Component" :key="route.fullPath" :page-title="title" />
    </RouterView>
  </component>
  <ToastHost />
</template>
