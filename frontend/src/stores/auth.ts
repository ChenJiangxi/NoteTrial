import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  accessToken: string | null;
  refreshToken: string | null;
  
  // Actions
  setUser: (user: User | null) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
  updateCredits: (credits: number) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      accessToken: null,
      refreshToken: null,
      
      setUser: (user) => 
        set({ 
          user, 
          isAuthenticated: !!user,
        }),
      
      setTokens: (accessToken, refreshToken) => 
        set({ 
          accessToken, 
          refreshToken,
          isAuthenticated: true,
        }),
      
      logout: () => 
        set({ 
          user: null,
          isAuthenticated: false,
          accessToken: null,
          refreshToken: null,
        }),
      
      updateCredits: (credits) => 
        set((state) => ({
          user: state.user ? { ...state.user, credits } : null,
        })),
    }),
    {
      name: 'notetrial-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
);

// 选择器 Hooks
export const useUser = () => useAuthStore((state) => state.user);
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated);
export const useAccessToken = () => useAuthStore((state) => state.accessToken);
