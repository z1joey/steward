<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { api } from "@/app/http";
import { homePath } from "@/app/router";
import { useSessionStore } from "@/app/stores/session";
import { useStoreContextStore } from "@/app/stores/storeContext";
import { COPY } from "@/shared/copy";
import type { LoginResponse } from "@/shared/types";

/**
 * TA-09 · /login：邮箱 + 密码；401 显「邮箱或密码错误」。
 */
const router = useRouter();
const route = useRoute();
const session = useSessionStore();
const ctx = useStoreContextStore();

const email = ref("");
const password = ref("");
const error = ref("");
const submitting = ref(false);

async function submit(): Promise<void> {
  if (submitting.value) return;
  error.value = "";
  submitting.value = true;
  try {
    const { data } = await api.post<LoginResponse>("/auth/login", {
      email: email.value.trim(),
      password: password.value,
    });
    session.setSession(data.access_token, data.user);
    await ctx.refresh();
    const redirect = route.query.redirect;
    await router.push(typeof redirect === "string" ? redirect : await homePath());
  } catch (e) {
    const status = (e as { response?: { status?: number } }).response?.status;
    if (status === 401) {
      error.value = COPY.loginFailed;
    } else {
      error.value = "登录失败，请稍后再试";
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <div class="auth-wrap">
    <form class="card" @submit.prevent="submit">
      <h1 class="title">{{ COPY.appName }}</h1>
      <label class="field">
        <span>{{ COPY.email }}</span>
        <input
          v-model="email"
          name="email"
          type="email"
          autocomplete="username"
          required
          maxlength="255"
        />
      </label>
      <label class="field">
        <span>{{ COPY.password }}</span>
        <input
          v-model="password"
          name="password"
          type="password"
          autocomplete="current-password"
          required
        />
      </label>
      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button class="primary" type="submit" :disabled="submitting">
        {{ COPY.login }}
      </button>
      <RouterLink class="link" to="/register">没有账号？{{ COPY.register }}</RouterLink>
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
