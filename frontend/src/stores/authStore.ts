import { create } from 'zustand';

interface AuthState {
  userId: string | null;
  token: string | null;
  setUser: (id: string | null, token: string | null) => void;
  clear: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  userId: null,
  token: null,
  setUser: (id, token) => set({ userId: id, token }),
  clear: () => set({ userId: null, token: null }),
}));
