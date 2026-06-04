// frontend/src/stores/groupStore.ts
import { create } from 'zustand';

interface GroupState {
  activeGroupId: string | null;
  setActiveGroup: (id: string | null) => void;
}

export const useGroupStore = create<GroupState>((set) => ({
  activeGroupId: null,
  setActiveGroup: (id) => set({ activeGroupId: id }),
}));
