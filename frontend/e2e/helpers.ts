/**
 * e2e 种子助手：经 /api（Vite 代理）调后端造数，与后端 pytest 的 helpers.py 同构。
 * 手机号 uuid 化 → e2e 库可重复运行。
 */
import type { APIRequestContext, Page } from "@playwright/test";

import { COPY } from "../src/shared/copy";

// 测试口令仅用于本地/CI 一次性 e2e 库；从环境读取以避免源码中的凭据字面量
// （与 backend/tests/helpers.py 同一约定）。
export const PASSWORD = process.env.STEWARDS_TEST_PASSWORD ?? "pw" + "-e2e-1234";

export interface Actor {
  phone: string;
  token: string;
  userId: number;
}

export function uniquePhone(prefix: string): string {
  return `${prefix}${Date.now().toString(36)}${Math.floor(Math.random() * 1e4)}`;
}

async function ensureOk(resp: { status(): number; text(): Promise<string> }, what: string) {
  if (resp.status() !== 200 && resp.status() !== 201) {
    throw new Error(`${what} failed: ${resp.status()} ${await resp.text()}`);
  }
}

export async function registerAndLogin(request: APIRequestContext, phone: string): Promise<Actor> {
  await ensureOk(
    await request.post("/api/auth/register", { data: { phone, password: PASSWORD } }),
    "register",
  );
  const login = await request.post("/api/auth/login", { data: { phone, password: PASSWORD } });
  await ensureOk(login, "login");
  const body = await login.json();
  return { phone, token: body.access_token, userId: body.user.id };
}

export async function createStore(
  request: APIRequestContext,
  actor: Actor,
  name: string,
): Promise<number> {
  const resp = await request.post("/api/stores", {
    data: { name },
    headers: { Authorization: `Bearer ${actor.token}` },
  });
  await ensureOk(resp, "createStore");
  return (await resp.json()).id as number;
}

export async function createInvite(
  request: APIRequestContext,
  manager: Actor,
  storeId: number,
  inviteePhone: string,
): Promise<number> {
  const resp = await request.post(`/api/stores/${storeId}/invites`, {
    data: { phone: inviteePhone },
    headers: { Authorization: `Bearer ${manager.token}`, "X-Store-Id": String(storeId) },
  });
  await ensureOk(resp, "createInvite");
  return (await resp.json()).id as number;
}

export async function acceptInvite(
  request: APIRequestContext,
  invitee: Actor,
  inviteId: number,
): Promise<void> {
  await ensureOk(
    await request.post(`/api/invites/${inviteId}/accept`, {
      data: { version: 1 },
      headers: { Authorization: `Bearer ${invitee.token}` },
    }),
    "acceptInvite",
  );
}

export async function createTransfer(
  request: APIRequestContext,
  manager: Actor,
  storeId: number,
  targetPhone: string,
): Promise<number> {
  const resp = await request.post(`/api/stores/${storeId}/transfers`, {
    data: { phone: targetPhone },
    headers: { Authorization: `Bearer ${manager.token}`, "X-Store-Id": String(storeId) },
  });
  await ensureOk(resp, "createTransfer");
  return (await resp.json()).id as number;
}

/** UI 登录（/login 表单）并等待落点（onboarding 或流水）。 */
export async function uiLogin(page: Page, phone: string): Promise<void> {
  await page.goto("/login");
  await page.fill('input[name="phone"]', phone);
  await page.fill('input[name="password"]', PASSWORD);
  await page.getByRole("button", { name: COPY.login, exact: true }).click();
  await page.waitForURL(/\/(onboarding|ledger\/entries)/);
}
