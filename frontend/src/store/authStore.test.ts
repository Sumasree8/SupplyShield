import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the API client the store depends on.
vi.mock('@/services/api', () => ({
  api: {
    login: vi.fn(async () => ({ access_token: 'a.b.c' })),
    logout: vi.fn(async () => undefined),
    getMe: vi.fn(async () => ({
      id: '1', email: 'u@example.com', full_name: 'U', role: 'admin',
      organization_id: 'o1', organization_name: 'Org',
    })),
  },
}));

import { useAuthStore } from './authStore';
import { api } from '@/services/api';

beforeEach(() => {
  localStorage.clear();
  useAuthStore.setState({ user: null, isAuthenticated: false, isLoading: false });
  vi.clearAllMocks();
});

describe('authStore', () => {
  it('login stores only the access token (refresh is an httpOnly cookie)', async () => {
    await useAuthStore.getState().login('u@example.com', 'pw');
    expect(localStorage.getItem('access_token')).toBe('a.b.c');
    // Refresh token must never be written to JS-accessible storage.
    expect(localStorage.getItem('refresh_token')).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().user?.email).toBe('u@example.com');
  });

  it('logout clears tokens and state', async () => {
    await useAuthStore.getState().login('u@example.com', 'pw');
    useAuthStore.getState().logout();
    expect(localStorage.getItem('access_token')).toBeNull();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().user).toBeNull();
  });

  it('login surfaces API errors and stops loading', async () => {
    (api.login as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('bad creds'));
    await expect(useAuthStore.getState().login('u@example.com', 'wrong')).rejects.toThrow('bad creds');
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().isLoading).toBe(false);
  });
});
