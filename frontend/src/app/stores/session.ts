import { defineStore } from "pinia";

const TOKEN_KEY = "steward.token";
const USER_KEY = "steward.user";

export interface SessionUser {
  id: number;
  phone: string;
}

/** useSession（B-specs §0.5）：token · user，持久化 localStorage。 */
export const useSessionStore = defineStore("session", {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) ?? "",
    user: JSON.parse(localStorage.getItem(USER_KEY) ?? "null") as SessionUser | null,
  }),
  actions: {
    setSession(token: string, user: SessionUser) {
      this.token = token;
      this.user = user;
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    },
    logout() {
      this.token = "";
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    },
  },
});
