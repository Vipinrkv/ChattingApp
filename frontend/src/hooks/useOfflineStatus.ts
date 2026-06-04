import { useEffect, useState } from 'react';
import { getQueuedRequestCount } from '../lib/offlineQueue';

export function useOfflineStatus() {
  const [isOnline, setIsOnline] = useState(() => navigator.onLine);
  const [queuedCount, setQueuedCount] = useState(0);

  useEffect(() => {
    const updateOnline = () => setIsOnline(navigator.onLine);
    const updateQueue = (event?: Event) => {
      const detail = (event as CustomEvent<{ count?: number }> | undefined)?.detail;
      setQueuedCount(typeof detail?.count === 'number' ? detail.count : getQueuedRequestCount());
    };
    updateQueue();
    window.addEventListener('online', updateOnline);
    window.addEventListener('offline', updateOnline);
    window.addEventListener('offline-queue:changed', updateQueue);
    return () => {
      window.removeEventListener('online', updateOnline);
      window.removeEventListener('offline', updateOnline);
      window.removeEventListener('offline-queue:changed', updateQueue);
    };
  }, []);

  return { isOnline, queuedCount };
}
