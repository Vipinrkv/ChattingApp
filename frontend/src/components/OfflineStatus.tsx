import { useEffect } from 'react';
import { useToasts } from '../ui/ToastProvider';
import { useOfflineStatus } from '../hooks/useOfflineStatus';
import { flushQueuedRequests, type QueuedRequest } from '../lib/offlineQueue';
import { apiRequest } from '../lib/api';

export default function OfflineStatus() {
  const { isOnline, queuedCount } = useOfflineStatus();
  const { push } = useToasts();

  useEffect(() => {
    if (!isOnline) {
      push({ type: 'warn', message: 'Offline mode active. Recent pages and queued actions remain available.' });
    }
  }, [isOnline, push]);

  useEffect(() => {
    if (!isOnline || queuedCount === 0) return;
    void flushQueuedRequests((request: QueuedRequest) =>
      apiRequest(request.path, {
        method: request.method,
        body: request.body,
        headers: { 'Idempotency-Key': request.idempotencyKey },
        skipOfflineQueue: true,
      }),
    ).then(({ flushed }) => {
      if (flushed > 0) {
        push({ type: 'success', message: `${flushed} offline action${flushed === 1 ? '' : 's'} synced.` });
      }
    });
  }, [isOnline, queuedCount, push]);

  useEffect(() => {
    const handleServiceWorkerMessage = (event: MessageEvent) => {
      if (event.data?.type !== 'BACKGROUND_SYNC_READY') return;
      if (!navigator.onLine || queuedCount === 0) return;

      void flushQueuedRequests((request: QueuedRequest) =>
        apiRequest(request.path, {
          method: request.method,
          body: request.body,
          headers: { 'Idempotency-Key': request.idempotencyKey },
          skipOfflineQueue: true,
        }),
      ).then(({ flushed }) => {
        if (flushed > 0) {
          push({ type: 'success', message: `${flushed} offline action${flushed === 1 ? '' : 's'} synced via background sync.` });
        }
      });
    };

    navigator.serviceWorker?.addEventListener('message', handleServiceWorkerMessage);
    return () => {
      navigator.serviceWorker?.removeEventListener('message', handleServiceWorkerMessage);
    };
  }, [queuedCount, push]);

  return (
    <div className={`offline-status ${isOnline ? 'online' : 'offline'}`} role="status" aria-live="polite">
      {isOnline ? (queuedCount ? `${queuedCount} action${queuedCount === 1 ? '' : 's'} waiting to sync` : 'Online') : 'Offline mode'}
    </div>
  );
}
