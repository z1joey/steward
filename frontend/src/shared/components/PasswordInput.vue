<script setup lang="ts">
import { ref } from "vue";

/**
 * 密码输入框（带显示/隐藏切换按钮）：登录密码、注册密码、确认密码共用。
 * 保留 name/required/maxlength/autocomplete 语义，v-model 与原生 input 一致。
 * 图标为线性 SVG（eye / eye-off，描边取 currentColor）。
 */
const props = defineProps<{
  modelValue: string;
  name: string;
  autocomplete?: string;
  maxlength?: number;
  required?: boolean;
}>();

const emit = defineEmits<{ "update:modelValue": [string] }>();

const visible = ref(false);

function onInput(e: Event): void {
  emit("update:modelValue", (e.target as HTMLInputElement).value);
}
</script>

<template>
  <div class="pwd-wrap">
    <input
      :value="modelValue"
      :name="name"
      :type="visible ? 'text' : 'password'"
      :autocomplete="autocomplete"
      :maxlength="maxlength"
      :required="required"
      @input="onInput"
    />
    <button
      type="button"
      class="toggle"
      :aria-label="visible ? '隐藏密码' : '显示密码'"
      :title="visible ? '隐藏密码' : '显示密码'"
      tabindex="-1"
      @click="visible = !visible"
    >
      <!-- eye-off（密文态，点击显示） -->
      <svg
        v-if="!visible"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
        <line x1="1" y1="1" x2="23" y2="23" />
      </svg>
      <!-- eye（明文态，点击隐藏） -->
      <svg
        v-else
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
        aria-hidden="true"
      >
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    </button>
  </div>
</template>

<style scoped>
.pwd-wrap {
  position: relative;
  display: block;
}
.pwd-wrap input {
  width: 100%;
  box-sizing: border-box;
  padding-right: 2.4rem;
}
.toggle {
  position: absolute;
  right: var(--space-xs);
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 0 var(--space-xs);
  line-height: 1;
}
.toggle:hover {
  color: var(--color-text);
}
.toggle svg {
  width: 16px;
  height: 16px;
}
</style>
