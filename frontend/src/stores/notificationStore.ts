import { create } from 'zustand';

interface NotificationState {
  toasts: { id: string; message: string; type?: 'info' | 'error' | 'success' }[];
  push: (msg: string, type?: 'info' | 'error' | 'success') => void;
  remove: (id: string) => void;
}

export const useNotificationStore = create<NotificationState>((set) => ({
  toasts: [],
  push: (message, type = 'info') =>
    set((state) => ({
      toasts: [...state.toasts, { id: Date.now().toString(), message, type }],
    })),
  remove: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
