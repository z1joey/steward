<script setup lang="ts">
/**
 * Phase B–E 页面占位（T0-10 路由表要求全部 path 可达）。
 * 各模块页面按 C-tasks 对应任务交付，不在此实现任何业务功能。
 */
const props = defineProps<{ pageTitle?: string }>();
</script>

<template>
  <div class="placeholder">
    <div class="card">
      <h1 class="title">{{ props.pageTitle }}</h1>
      <p class="hint">该模块按交付计划在后续阶段实现。</p>
    </div>
  </div>
</template>

<style scoped>
.placeholder {
  display: flex;
  justify-content: center;
  padding-top: var(--space-2xl);
}
.card {
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-xl);
  text-align: center;
}
.title {
  margin: 0 0 var(--space-sm);
  font-size: var(--text-xl);
}
.hint {
  margin: 0;
  color: var(--color-text-muted);
  font-size: var(--text-sm);
}
</style>
