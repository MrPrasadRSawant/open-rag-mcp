import { defineStore, acceptHMRUpdate } from 'pinia';

import { getProfile, login, register, type TokenResponse, type User } from '@/services/api';

const TOKEN_KEY = 'open-rag-mcp-token';

type AuthPayload = {
  email: string;
  password: string;
  full_name?: string | null;
};

export const useSessionStore = defineStore('session', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY),
    user: null as User | null,
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
  },

  actions: {
    async restore() {
      if (!this.token || this.user) {
        return;
      }
      this.loading = true;
      try {
        this.user = await getProfile(this.token);
      } catch {
        this.logout();
      } finally {
        this.loading = false;
      }
    },

    async login(payload: AuthPayload) {
      const response = await login({ email: payload.email, password: payload.password });
      this.setTokenResponse(response);
    },

    async register(payload: AuthPayload) {
      const response = await register(payload);
      this.setTokenResponse(response);
    },

    logout() {
      this.token = null;
      this.user = null;
      localStorage.removeItem(TOKEN_KEY);
    },

    setTokenResponse(response: TokenResponse) {
      this.token = response.access_token;
      this.user = response.user;
      localStorage.setItem(TOKEN_KEY, response.access_token);
    },
  },
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useSessionStore, import.meta.hot));
}
