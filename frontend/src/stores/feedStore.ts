import { create } from 'zustand';

interface FeedCacheState {
  items: any[];
  cursor: string | null;
  hasMore: boolean;
  lastUpdated: string | null;
  setFeedCache: (items: any[], cursor: string | null, hasMore: boolean) => void;
  clearFeedCache: () => void;
}

export const useFeedStore = create<FeedCacheState>((set) => ({
  items: [],
  cursor: null,
  hasMore: true,
  lastUpdated: null,
  setFeedCache: (items, cursor, hasMore) =>
    set({ items, cursor, hasMore, lastUpdated: new Date().toISOString() }),
  clearFeedCache: () => set({ items: [], cursor: null, hasMore: true, lastUpdated: null }),
}));
