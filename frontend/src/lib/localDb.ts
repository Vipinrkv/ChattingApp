const DB_NAME = 'chattingapp-local';
const DB_VERSION = 2;

export const LOCAL_DB_STORES = {
  offlineQueue: 'offlineQueue',
  localRecords: 'localRecords',
  encryptedBackups: 'encryptedBackups',
  settings: 'settings',
  drafts: 'drafts',
  feedCache: 'feedCache',
  messages: 'messages',
  mediaIndex: 'mediaIndex',
  syncQueue: 'syncQueue',
  backupManifests: 'backupManifests',
} as const;

type StoreName = (typeof LOCAL_DB_STORES)[keyof typeof LOCAL_DB_STORES];
export type LocalStoreName =
  | 'settings'
  | 'drafts'
  | 'feedCache'
  | 'messages'
  | 'mediaIndex'
  | 'syncQueue'
  | 'backupManifests';

export type LocalDbValue = {
  id: string;
  [key: string]: unknown;
};

export type LocalRecord<T = unknown> = LocalDbValue & {
  value: T;
  updatedAt: number;
  deletedAt?: number | null;
  deviceId?: string;
};

let dbPromise: Promise<IDBDatabase> | null = null;
const memoryStores = new Map<StoreName, Map<string, LocalDbValue>>();

function hasIndexedDb() {
  return typeof indexedDB !== 'undefined';
}

function memoryStore(storeName: StoreName) {
  let store = memoryStores.get(storeName);
  if (!store) {
    store = new Map<string, LocalDbValue>();
    memoryStores.set(storeName, store);
  }
  return store;
}

function openLocalDb(): Promise<IDBDatabase> {
  if (!hasIndexedDb()) {
    return Promise.reject(new Error('IndexedDB is unavailable'));
  }

  if (dbPromise) return dbPromise;

  dbPromise = new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = () => {
      const db = request.result;

      if (!db.objectStoreNames.contains(LOCAL_DB_STORES.offlineQueue)) {
        const queueStore = db.createObjectStore(LOCAL_DB_STORES.offlineQueue, { keyPath: 'id' });
        queueStore.createIndex('status', 'status', { unique: false });
        queueStore.createIndex('idempotencyKey', 'idempotencyKey', { unique: false });
        queueStore.createIndex('nextAttemptAt', 'nextAttemptAt', { unique: false });
      }

      if (!db.objectStoreNames.contains(LOCAL_DB_STORES.localRecords)) {
        const recordStore = db.createObjectStore(LOCAL_DB_STORES.localRecords, { keyPath: 'id' });
        recordStore.createIndex('collection', 'collection', { unique: false });
        recordStore.createIndex('dirty', 'dirty', { unique: false });
        recordStore.createIndex('updatedAt', 'updatedAt', { unique: false });
      }

      if (!db.objectStoreNames.contains(LOCAL_DB_STORES.encryptedBackups)) {
        const backupStore = db.createObjectStore(LOCAL_DB_STORES.encryptedBackups, { keyPath: 'id' });
        backupStore.createIndex('createdAt', 'createdAt', { unique: false });
      }

      ([
        LOCAL_DB_STORES.settings,
        LOCAL_DB_STORES.drafts,
        LOCAL_DB_STORES.feedCache,
        LOCAL_DB_STORES.messages,
        LOCAL_DB_STORES.mediaIndex,
        LOCAL_DB_STORES.syncQueue,
        LOCAL_DB_STORES.backupManifests,
      ] as StoreName[]).forEach((storeName) => {
        if (!db.objectStoreNames.contains(storeName)) {
          const localStore = db.createObjectStore(storeName, { keyPath: 'id' });
          localStore.createIndex('updatedAt', 'updatedAt', { unique: false });
          localStore.createIndex('deletedAt', 'deletedAt', { unique: false });
          localStore.createIndex('deviceId', 'deviceId', { unique: false });
        }
      });
    };

    request.onsuccess = () => {
      const db = request.result;
      db.onversionchange = () => {
        db.close();
        dbPromise = null;
      };
      resolve(db);
    };
    request.onerror = () => reject(request.error ?? new Error('Could not open local database'));
  });

  return dbPromise;
}

async function withStore<T>(
  storeName: StoreName,
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T> | Promise<T>,
): Promise<T> {
  const db = await openLocalDb();

  return new Promise<T>((resolve, reject) => {
    const transaction = db.transaction(storeName, mode);
    const store = transaction.objectStore(storeName);
    let operationResult: IDBRequest<T> | Promise<T>;

    transaction.onerror = () => reject(transaction.error ?? new Error('IndexedDB transaction failed'));
    transaction.onabort = () => reject(transaction.error ?? new Error('IndexedDB transaction aborted'));

    try {
      operationResult = operation(store);
    } catch (error) {
      reject(error);
      return;
    }

    if ('onsuccess' in operationResult) {
      operationResult.onsuccess = () => resolve(operationResult.result);
      operationResult.onerror = () => reject(operationResult.error ?? new Error('IndexedDB request failed'));
      return;
    }

    void operationResult.then(resolve, reject);
  });
}

export async function localDbGetAll<T extends LocalDbValue>(storeName: StoreName): Promise<T[]> {
  if (!hasIndexedDb()) return Array.from(memoryStore(storeName).values()) as T[];
  return withStore<T[]>(storeName, 'readonly', (store) => store.getAll() as IDBRequest<T[]>);
}

export async function localDbGet<T extends LocalDbValue>(storeName: StoreName, id: string): Promise<T | undefined> {
  if (!hasIndexedDb()) return memoryStore(storeName).get(id) as T | undefined;
  return withStore<T | undefined>(storeName, 'readonly', (store) => store.get(id) as IDBRequest<T | undefined>);
}

export async function localDbPut<T extends LocalDbValue>(storeName: StoreName, value: T): Promise<T> {
  if (!hasIndexedDb()) {
    memoryStore(storeName).set(value.id, value);
    return value;
  }
  await withStore<IDBValidKey>(storeName, 'readwrite', (store) => store.put(value));
  return value;
}

export async function localDbDelete(storeName: StoreName, id: string): Promise<void> {
  if (!hasIndexedDb()) {
    memoryStore(storeName).delete(id);
    return;
  }
  await withStore<undefined>(storeName, 'readwrite', (store) => store.delete(id) as IDBRequest<undefined>);
}

export async function localDbClear(storeName: StoreName): Promise<void> {
  if (!hasIndexedDb()) {
    memoryStore(storeName).clear();
    return;
  }
  await withStore<undefined>(storeName, 'readwrite', (store) => store.clear() as IDBRequest<undefined>);
}

export async function localDbReplaceAll<T extends LocalDbValue>(storeName: StoreName, values: T[]): Promise<void> {
  if (!hasIndexedDb()) {
    const store = memoryStore(storeName);
    store.clear();
    values.forEach((value) => store.set(value.id, value));
    return;
  }

  const db = await openLocalDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(storeName, 'readwrite');
    const store = transaction.objectStore(storeName);
    store.clear();
    values.forEach((value) => store.put(value));
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error ?? new Error('IndexedDB replace failed'));
    transaction.onabort = () => reject(transaction.error ?? new Error('IndexedDB replace aborted'));
  });
}

function normalizeLocalRecord<T>(record: { id: string; value: T; updatedAt?: number; deletedAt?: number | null; deviceId?: string }): LocalRecord<T> {
  return {
    ...record,
    updatedAt: record.updatedAt ?? Date.now(),
    deletedAt: record.deletedAt ?? null,
  };
}

export async function putLocalRecord<T>(
  storeName: LocalStoreName,
  record: { id: string; value: T; updatedAt?: number; deletedAt?: number | null; deviceId?: string },
): Promise<LocalRecord<T>> {
  return localDbPut(LOCAL_DB_STORES[storeName], normalizeLocalRecord(record));
}

export async function getLocalRecord<T>(storeName: LocalStoreName, id: string): Promise<LocalRecord<T> | undefined> {
  return localDbGet<LocalRecord<T>>(LOCAL_DB_STORES[storeName], id);
}

export async function getAllLocalRecords<T>(storeName: LocalStoreName): Promise<Array<LocalRecord<T>>> {
  return localDbGetAll<LocalRecord<T>>(LOCAL_DB_STORES[storeName]);
}

export async function deleteLocalRecord(storeName: LocalStoreName, id: string): Promise<void> {
  await localDbDelete(LOCAL_DB_STORES[storeName], id);
}

export async function clearLocalStore(storeName: LocalStoreName): Promise<void> {
  await localDbClear(LOCAL_DB_STORES[storeName]);
}

export function resetLocalDbForTests() {
  memoryStores.clear();
  dbPromise = null;
}
