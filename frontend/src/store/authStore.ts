/**
 * Authentication state store.
 * Token persistence via localStorage.
 */
import { create } from 'zustand';
import type { User } from '@/types';
import { api } from '@/services/api';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  isLoading: false,

  login: async (email, password) => {
    set({ isLoading: true });
    try {
      const tokens = await api.login(email, password);
      // Only the short-lived access token lives in JS; the refresh token is an
      // httpOnly cookie set by the server and never touched here.
      localStorage.setItem('access_token', tokens.access_token);
      const user = await api.getMe();
      set({ user, isAuthenticated: true, isLoading: false });
    } catch (e) {
      set({ isLoading: false });
      throw e;
    }
  },

  logout: () => {
    void api.logout(); // clear the httpOnly refresh cookie server-side
    localStorage.removeItem('access_token');
    set({ user: null, isAuthenticated: false });
  },

  loadUser: async () => {
    if (!localStorage.getItem('access_token')) return;
    try {
      const user = await api.getMe();
      set({ user, isAuthenticated: true });
    } catch {
      localStorage.clear();
      set({ user: null, isAuthenticated: false });
    }
  },
}));
