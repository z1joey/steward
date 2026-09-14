<script setup lang="ts">
import { ref } from "vue";

/**
 * 密码输入框（带显示/隐藏切换按钮）：登录密码、注册密码、确认密码共用。
 * 保留 name/required/maxlength/autocomplete 语义，v-model 与原生 input 一致。
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
      {{ visible ? "🙈" : "👁" }}
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
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  padding: 0;
  line-height: 1;
}
</style>
