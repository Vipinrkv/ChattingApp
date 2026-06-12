import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 60 * 24,
      retry: (failureCount) => (navigator.onLine ? failureCount < 2 : false),
      refetchOnWindowFocus: () => navigator.onLine,
      refetchOnReconnect: true,
      networkMode: 'offlineFirst',
    },
    mutations: {
      networkMode: 'offlineFirst',
      retry: (failureCount) => (navigator.onLine ? failureCount < 1 : false),
    },
  },
});
