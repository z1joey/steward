<script setup lang="ts">
import { ref } from "vue";

import { api } from "@/app/http";
import AppModal from "@/shared/components/AppModal.vue";
import ConfirmButton from "@/shared/components/ConfirmButton.vue";
import { COPY } from "@/shared/copy";

/**
 * TB-06 · 记一笔弹窗（AC-LED-01 独立弹窗 / US-B1/B2）：
 * 日期（默认今日）/ 金额 / 摘要 / ☐ 需要报销（默认不勾）；
 * 提交 loading，成功关闭由父组件刷新；无收支切换控件（[Open O-23]）。
 */
const open = defineModel<boolean>({ default: false });
const emit = defineEmits<{ created: [] }>();

function today(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

const date = ref(today());
const amount = ref("");
const memo = ref("");
const needsReimbursement = ref(false);

async function submit(): Promise<void> {
  // v-model 在 number 输入上返回 number；统一转字符串再校验
  const value = String(amount.value ?? "").trim();
  if (!value || Number(value) <= 0) return;
  await api.post("/ledger/entries", {
    date: date.value,
    amount: value,
    memo: memo.value.trim(),
    needs_reimbursement: needsReimbursement.value,
  });
  open.value = false;
  amount.value = "";
  memo.value = "";
  needsReimbursement.value = false;
  date.value = today();
  emit("created");
}

function close(): void {
  open.value = false;
}
</script>

<template>
  <AppModal :open="open" :title="COPY.recordEntry" @close="close">
    <label class="field">
      <span>{{ COPY.date }}</span>
      <input v-model="date" type="date" required />
    </label>
    <label class="field">
      <span>{{ COPY.amount }}</span>
      <input
        v-model="amount"
        class="tabular"
        type="number"
        min="0.01"
        step="0.01"
        placeholder="0.00"
        required
      />
    </label>
    <label class="field">
      <span>{{ COPY.memo }}</span>
      <input v-model="memo" maxlength="500" @keyup.enter="submit" />
    </label>
    <label class="check">
      <input v-model="needsReimbursement" type="checkbox" />
      <span>{{ COPY.needsReimbursement }}</span>
    </label>
    <div class="actions">
      <ConfirmButton :action="submit">{{ COPY.recordEntry }}</ConfirmButton>
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
.field input {
  padding: var(--space-sm);
  border: 1px solid var(--color-line-strong);
  border-radius: var(--radius-md);
  font-size: var(--text-md);
}
.tabular {
  font-variant-numeric: tabular-nums;
  text-align: right;
}
.check {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  font-size: var(--text-md);
}
.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
