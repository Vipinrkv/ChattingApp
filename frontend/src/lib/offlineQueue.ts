import { LOCAL_DB_STORES, localDbDelete, localDbGetAll, localDbPut } from './localDb';

const LEGACY_QUEUE_KEY = 'chattingapp:offline-request-queue';
const QUEUE_STORE = LOCAL_DB_STORES.syncQueue;
const LEGACY_INDEXED_DB_QUEUE_STORE = LOCAL_DB_STORES.offlineQueue;
const MAX_QUEUE_SIZE = 100;
export const MAX_OFFLINE_RETRY_ATTEMPTS = 5;

export type QueuedRequest = {
  id: string;
  path: string;
  method: string;
  body?: string;
  createdAt: number;
  updatedAt: number;
  attempts: number;
  maxAttempts: number;
  idempotencyKey: string;
  status: 'pending' | 'retrying' | 'failed';
  nextAttemptAt: number;
  lastError?: string;
};

type LegacyQueuedRequest = Omit<QueuedRequest, 'updatedAt' | 'attempts' | 'maxAttempts' | 'idempotencyKey' | 'status' | 'nextAttemptAt'>;

let queueSnapshot: QueuedRequest[] = [];
let hydratePromise: Promise<QueuedRequest[]> | null = null;

function now() {
  return Date.now();
}

function fingerprint(request: Pick<QueuedRequest, 'path' | 'method'> & { body?: string }) {
  return `${request.method.toUpperCase()}:${request.path}:${request.body ?? ''}`;
}

function createIdempotencyKey(request: Pick<QueuedRequest, 'path' | 'method'> & { body?: string }) {
  let hash = 0;
  const input = fingerprint(request);
  for (let index = 0; index < input.length; index += 1) {
    hash = Math.imul(31, hash) + input.charCodeAt(index) | 0;
  }
  return `offline:${request.method.toUpperCase()}:${request.path}:${Math.abs(hash).toString(36)}`;
}

function normalizeQueuedRequest(request: LegacyQueuedRequest | QueuedRequest): QueuedRequest {
  const createdAt = request.createdAt ?? now();
  const normalized = request as Partial<QueuedRequest> & LegacyQueuedRequest;
  return {
    id: normalized.id,
    path: normalized.path,
    method: normalized.method.toUpperCase(),
    body: normalized.body,
    createdAt,
    updatedAt: normalized.updatedAt ?? createdAt,
    attempts: normalized.attempts ?? 0,
    maxAttempts: normalized.maxAttempts ?? MAX_OFFLINE_RETRY_ATTEMPTS,
    idempotencyKey: normalized.idempotencyKey ?? createIdempotencyKey(normalized),
    status: normalized.status ?? 'pending',
    nextAttemptAt: normalized.nextAttemptAt ?? createdAt,
    lastError: normalized.lastError,
  };
}

function dispatchQueueChanged() {
  window.dispatchEvent(new CustomEvent('offline-queue:changed', { detail: { count: queueSnapshot.length } }));
}

function setSnapshot(queue: QueuedRequest[]) {
  queueSnapshot = queue
    .filter((request) => request.status !== 'failed' || request.attempts < request.maxAttempts)
    .sort((a, b) => a.createdAt - b.createdAt)
    .slice(-MAX_QUEUE_SIZE);
  dispatchQueueChanged();
}

function readLegacyQueue(): QueuedRequest[] {
  try {
    const raw = localStorage.getItem(LEGACY_QUEUE_KEY);
    const parsed = raw ? JSON.parse(raw) as LegacyQueuedRequest[] : [];
    return parsed.map(normalizeQueuedRequest);
  } catch {
    return [];
  }
}

async function persistQueue(queue: QueuedRequest[]) {
  setSnapshot(queue);
  await Promise.all(queueSnapshot.map((request) => localDbPut(QUEUE_STORE, request)));
}

async function hydrateQueue() {
  if (hydratePromise) return hydratePromise;

  hydratePromise = (async () => {
    const storedQueue = (await localDbGetAll<QueuedRequest>(QUEUE_STORE)).map(normalizeQueuedRequest);
    const legacyIndexedDbQueue = (await localDbGetAll<QueuedRequest>(LEGACY_INDEXED_DB_QUEUE_STORE)).map(normalizeQueuedRequest);
    const legacyQueue = readLegacyQueue();
    const byIdempotencyKey = new Map<string, QueuedRequest>();

    [...storedQueue, ...legacyIndexedDbQueue, ...legacyQueue].forEach((request) => {
      const existing = byIdempotencyKey.get(request.idempotencyKey);
      if (!existing || request.updatedAt > existing.updatedAt) {
        byIdempotencyKey.set(request.idempotencyKey, request);
      }
    });

    const queue = Array.from(byIdempotencyKey.values()).slice(-MAX_QUEUE_SIZE);
    setSnapshot(queue);
    await Promise.all(queue.map((request) => localDbPut(QUEUE_STORE, request)));
    localStorage.removeItem(LEGACY_QUEUE_KEY);
    return queueSnapshot;
  })();

  return hydratePromise;
}

void hydrateQueue().catch(() => {
  const legacyQueue = readLegacyQueue();
  if (legacyQueue.length) setSnapshot(legacyQueue);
});

export function getQueuedRequestCount() {
  return queueSnapshot.length;
}

export function resetOfflineQueueForTests() {
  queueSnapshot = [];
  hydratePromise = null;
}

export async function getSyncQueueMetrics() {
  const queue = await hydrateQueue();
  const persistedQueue = (await localDbGetAll<QueuedRequest>(QUEUE_STORE)).map(normalizeQueuedRequest);
  return {
    depth: queue.filter((request) => request.status !== 'failed').length,
    failedAttempts: persistedQueue.reduce((total, request) => total + request.attempts, 0),
    failedItems: persistedQueue.filter((request) => request.status === 'failed' || request.attempts >= request.maxAttempts).length,
  };
}

export function queueRequest(request: Omit<QueuedRequest, 'id' | 'createdAt' | 'updatedAt' | 'attempts' | 'maxAttempts' | 'idempotencyKey' | 'status' | 'nextAttemptAt'>) {
  const normalizedMethod = request.method.toUpperCase();
  const idempotencyKey = createIdempotencyKey({ ...request, method: normalizedMethod });
  const existing = queueSnapshot.find((item) => item.idempotencyKey === idempotencyKey && item.attempts < item.maxAttempts);
  if (existing) return existing;

  const createdAt = now();
  const queued: QueuedRequest = {
    ...request,
    method: normalizedMethod,
    id: `${createdAt}-${Math.random().toString(36).slice(2, 9)}`,
    createdAt,
    updatedAt: createdAt,
    attempts: 0,
    maxAttempts: MAX_OFFLINE_RETRY_ATTEMPTS,
    idempotencyKey,
    status: 'pending',
    nextAttemptAt: createdAt,
  };

  setSnapshot([...queueSnapshot, queued]);
  void localDbPut(QUEUE_STORE, queued);
  registerBackgroundSync();
  return queued;
}

export async function flushQueuedRequests(send: (request: QueuedRequest) => Promise<unknown>) {
  const queue = await hydrateQueue();
  if (!queue.length || !navigator.onLine) return { flushed: 0, remaining: queue.length, failed: 0 };

  const remaining: QueuedRequest[] = [];
  let flushed = 0;
  let failed = 0;
  const currentTime = now();

  for (const request of queue) {
    if (request.nextAttemptAt > currentTime) {
      remaining.push(request);
      continue;
    }

    try {
      await send(request);
      await Promise.all([
        localDbDelete(QUEUE_STORE, request.id),
        localDbDelete(LEGACY_INDEXED_DB_QUEUE_STORE, request.id),
      ]);
      flushed += 1;
    } catch (error) {
      const attempts = request.attempts + 1;
      const capped = attempts >= request.maxAttempts;
      const nextRequest: QueuedRequest = {
        ...request,
        attempts,
        updatedAt: currentTime,
        status: capped ? 'failed' : 'retrying',
        nextAttemptAt: capped ? Number.MAX_SAFE_INTEGER : currentTime + Math.min(30000, 1000 * 2 ** attempts),
        lastError: error instanceof Error ? error.message : 'Request failed',
      };

      if (capped) {
        failed += 1;
      } else {
        remaining.push(nextRequest);
      }
      await localDbPut(QUEUE_STORE, nextRequest);
    }
  }

  setSnapshot(remaining);
  return { flushed, remaining: remaining.length, failed };
}

async function registerBackgroundSync() {
  if (!('serviceWorker' in navigator)) return;
  try {
    const registration = await navigator.serviceWorker.ready;
    const syncManager = (registration as ServiceWorkerRegistration & { sync?: { register: (tag: string) => Promise<void> } }).sync;
    await syncManager?.register('chattingapp-background-sync');
  } catch {
    // Background Sync is optional; online flush still handles queued writes.
  }
}
