import { create } from 'zustand';

interface UIState {
  darkMode: boolean;
  toggleDark: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  darkMode: false,
  toggleDark: () => set((s) => ({ darkMode: !s.darkMode })),
}));
