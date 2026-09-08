<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";

import { api } from "@/app/http";
import { homePath } from "@/app/router";
import { useSessionStore } from "@/app/stores/session";
import { useStoreContextStore } from "@/app/stores/storeContext";
import { COPY } from "@/shared/copy";

/**
 * TA-09 · /register：注册成功自动登录 → 路由决策（AC-AUTH-01/02）。
 */
const router = useRouter();
const session = useSessionStore();
const ctx = useStoreContextStore();

const phone = ref("");
const password = ref("");
const error = ref("");
const submitting = ref(false);

async function submit(): Promise<void> {
  if (submitting.value) return;
  error.value = "";
  submitting.value = true;
  try {
    await api.post("/auth/register", { phone: phone.value.trim(), password: password.value });
    // 注册成功自动登录
    const { data } = await api.post("/auth/login", {
      phone: phone.value.trim(),
      password: password.value,
    });
    session.setSession(data.access_token, data.user);
    await ctx.refresh();
    await router.push(await homePath());
  } catch (e) {
    const status = (e as { response?: { status?: number } }).response?.status;
    if (status === 409) {
      error.value = "该手机号已注册";
    } else if (status === 422) {
      error.value = "请检查手机号与密码（均不能为空）";
    } else {
      error.value = "注册失败，请稍后再试";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="auth-wrap">
    <form class="card" @submit.prevent="submit">
      <h1 class="title">{{ COPY.appName }} · {{ COPY.register }}</h1>
      <label class="field">
        <span>{{ COPY.phone }}</span>
        <input v-model="phone" name="phone" required maxlength="32" />
      </label>
      <label class="field">
        <span>{{ COPY.password }}</span>
        <input v-model="password" name="password" type="password" required />
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="primary" type="submit" :disabled="submitting">
        {{ COPY.register }}
      </button>
      <RouterLink class="link" to="/login">已有账号？{{ COPY.login }}</RouterLink>
    </form>
  </div>
</template>

<style scoped>
.auth-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.card {
  width: var(--size-modal-sm);
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: var(--space-xl);
  display: grid;
  gap: var(--space-md);
}
.title {
  margin: 0;
  text-align: center;
  font-size: var(--text-xl);
}
.field {
  display: grid;
  gap: var(--space-xs);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}
.error {
  margin: 0;
  color: var(--color-error);
  font-size: var(--text-sm);
}
.primary {
  background: var(--color-primary);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
}
.primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
.primary:disabled {
  opacity: 0.6;
}
.link {
  text-align: center;
  color: var(--color-primary);
  text-decoration: none;
  font-size: var(--text-sm);
}
</style>
