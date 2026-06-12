import { LOCAL_DB_STORES, localDbDelete, localDbGetAll, localDbPut, type LocalDbValue } from './localDb';

export type ConflictStrategy = 'local-wins' | 'remote-wins' | 'latest-wins';

export type LocalFirstRecord<T extends Record<string, unknown> = Record<string, unknown>> = LocalDbValue & {
  collection: string;
  remoteId?: string;
  data: T;
  revision: number;
  updatedAt: number;
  dirty: boolean;
  deleted?: boolean;
};

export type ConflictResult<T extends Record<string, unknown>> = {
  record: LocalFirstRecord<T>;
  conflict: boolean;
  resolution: ConflictStrategy | 'none';
};

export function createLocalRecord<T extends Record<string, unknown>>(
  collection: string,
  data: T,
  options: Partial<Pick<LocalFirstRecord<T>, 'id' | 'remoteId' | 'revision' | 'updatedAt' | 'dirty' | 'deleted'>> = {},
): LocalFirstRecord<T> {
  const now = Date.now();
  return {
    id: options.id ?? `${collection}:${now}:${Math.random().toString(36).slice(2, 10)}`,
    collection,
    data,
    revision: options.revision ?? 0,
    updatedAt: options.updatedAt ?? now,
    dirty: options.dirty ?? true,
    ...(options.remoteId ? { remoteId: options.remoteId } : {}),
    ...(options.deleted ? { deleted: true } : {}),
  };
}

export function resolveLocalConflict<T extends Record<string, unknown>>(
  localRecord: LocalFirstRecord<T>,
  remoteRecord: LocalFirstRecord<T>,
  strategy: ConflictStrategy = 'latest-wins',
): ConflictResult<T> {
  const conflict = localRecord.dirty && remoteRecord.revision > localRecord.revision;
  if (!conflict) {
    const record = remoteRecord.revision >= localRecord.revision ? remoteRecord : localRecord;
    return { record, conflict: false, resolution: 'none' };
  }

  if (strategy === 'local-wins') {
    return {
      record: { ...localRecord, revision: remoteRecord.revision + 1, dirty: true },
      conflict: true,
      resolution: strategy,
    };
  }

  if (strategy === 'remote-wins') {
    return {
      record: { ...remoteRecord, dirty: false },
      conflict: true,
      resolution: strategy,
    };
  }

  const record = localRecord.updatedAt >= remoteRecord.updatedAt
    ? { ...localRecord, revision: remoteRecord.revision + 1, dirty: true }
    : { ...remoteRecord, dirty: false };
  return { record, conflict: true, resolution: strategy };
}

export async function saveLocalRecord<T extends Record<string, unknown>>(record: LocalFirstRecord<T>) {
  return localDbPut(LOCAL_DB_STORES.localRecords, record);
}

export async function listLocalRecords<T extends Record<string, unknown>>(collection?: string) {
  const records = await localDbGetAll<LocalFirstRecord<T>>(LOCAL_DB_STORES.localRecords);
  return collection ? records.filter((record) => record.collection === collection) : records;
}

export async function deleteLocalRecord(id: string) {
  await localDbDelete(LOCAL_DB_STORES.localRecords, id);
}
