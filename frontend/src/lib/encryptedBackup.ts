import { getAllLocalRecords, LOCAL_DB_STORES, localDbPut, putLocalRecord, type LocalDbValue, type LocalStoreName } from './localDb';
import { getSyncQueueMetrics } from './offlineQueue';
import { apiPost } from './api';

export const BACKUP_STORES: LocalStoreName[] = [
  'settings',
  'drafts',
  'feedCache',
  'messages',
  'mediaIndex',
  'syncQueue',
  'backupManifests',
];

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

export type BackupManifest = {
  id: string;
  createdAt: number;
  version: 1;
  stores: Record<string, number>;
  syncQueueDepth: number;
  failedSyncAttempts: number;
  restoredItemCounts?: Record<string, number>;
};

export type EncryptedUserBackup = {
  manifest: BackupManifest;
  kdf: 'PBKDF2-SHA256';
  cipher: 'AES-GCM';
  salt: string;
  iv: string;
  ciphertext: string;
};

export type LocalFirstMetricsExport = {
  queue_depth: number;
  failed_sync_count: number;
  restore_count: number;
  cache_size_bytes: number;
  generated_at: string;
};

export type ScheduledBackupPolicy = {
  enabled: boolean;
  intervalHours: number;
  retentionCount: number;
  cloudHookUrl?: string;
  lastRunAt?: number;
  nextRunAt?: number;
};

const SCHEDULED_BACKUP_POLICY_ID = 'scheduled-backup-policy';

function bytesToBase64(bytes: Uint8Array) {
  return btoa(String.fromCharCode(...bytes));
}

function base64ToBytes(value: string): Uint8Array<ArrayBuffer> {
  const bytes = Uint8Array.from(atob(value), (char) => char.charCodeAt(0));
  return new Uint8Array(bytes);
}

function cryptoBytes(length: number): Uint8Array<ArrayBuffer> {
  return crypto.getRandomValues(new Uint8Array(length));
}

function assertBackupEnvelope(backup: EncryptedUserBackup) {
  if (backup.kdf !== 'PBKDF2-SHA256' || backup.cipher !== 'AES-GCM') {
    throw new Error('Unsupported encrypted backup format.');
  }
  if (!backup.manifest?.id || backup.manifest.version !== 1 || !backup.salt || !backup.iv || !backup.ciphertext) {
    throw new Error('Encrypted backup is missing required metadata.');
  }
}

function assertPayloadMatchesManifest(
  manifest: BackupManifest,
  payload: Record<LocalStoreName, unknown[]>,
) {
  BACKUP_STORES.forEach((storeName) => {
    const records = payload[storeName];
    if (!Array.isArray(records)) {
      throw new Error(`Backup payload is missing ${storeName}.`);
    }
    if (records.length !== manifest.stores[storeName]) {
      throw new Error(`Backup manifest count mismatch for ${storeName}.`);
    }
  });
}

async function deriveKey(passphrase: string, salt: Uint8Array<ArrayBuffer>) {
  const baseKey = await crypto.subtle.importKey('raw', textEncoder.encode(passphrase), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 210000, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['encrypt', 'decrypt'],
  );
}

async function collectBackupPayload() {
  const entries = await Promise.all(
    BACKUP_STORES.map(async (storeName) => [storeName, await getAllLocalRecords(storeName)] as const),
  );
  return Object.fromEntries(entries) as Record<LocalStoreName, unknown[]>;
}

function estimatePayloadSizeBytes(payload: unknown) {
  return textEncoder.encode(JSON.stringify(payload)).byteLength;
}

export async function getLocalFirstMetricsExport(): Promise<LocalFirstMetricsExport> {
  const [payload, syncMetrics, manifests] = await Promise.all([
    collectBackupPayload(),
    getSyncQueueMetrics(),
    getAllLocalRecords<BackupManifest>('backupManifests'),
  ]);
  const restoreCount = manifests.filter((record) => Boolean(record.value?.restoredItemCounts)).length;

  return {
    queue_depth: syncMetrics.depth,
    failed_sync_count: syncMetrics.failedItems,
    restore_count: restoreCount,
    cache_size_bytes: estimatePayloadSizeBytes(payload),
    generated_at: new Date().toISOString(),
  };
}

export async function exportLocalFirstMetrics() {
  const metrics = await getLocalFirstMetricsExport();
  await apiPost('/api/v1/analytics/sync-metrics', metrics);
  return metrics;
}

export async function getScheduledBackupPolicy(): Promise<ScheduledBackupPolicy> {
  const record = await getAllLocalRecords<ScheduledBackupPolicy>('settings').then((records) =>
    records.find((item) => item.id === SCHEDULED_BACKUP_POLICY_ID),
  );
  return record?.value ?? {
    enabled: false,
    intervalHours: 24,
    retentionCount: 7,
  };
}

export async function saveScheduledBackupPolicy(policy: ScheduledBackupPolicy) {
  const now = Date.now();
  const normalized: ScheduledBackupPolicy = {
    ...policy,
    intervalHours: Math.max(1, policy.intervalHours),
    retentionCount: Math.max(1, policy.retentionCount),
    nextRunAt: policy.enabled ? policy.nextRunAt ?? now + Math.max(1, policy.intervalHours) * 60 * 60 * 1000 : undefined,
  };
  await putLocalRecord<ScheduledBackupPolicy>('settings', {
    id: SCHEDULED_BACKUP_POLICY_ID,
    value: normalized,
  });
  return normalized;
}

export async function runScheduledBackupIfDue(passphrase: string, now = Date.now()) {
  const policy = await getScheduledBackupPolicy();
  if (!policy.enabled || !policy.nextRunAt || policy.nextRunAt > now) {
    return { ran: false as const, policy };
  }

  const backup = await createEncryptedUserBackup(passphrase);
  const updatedPolicy = await saveScheduledBackupPolicy({
    ...policy,
    lastRunAt: now,
    nextRunAt: now + policy.intervalHours * 60 * 60 * 1000,
  });

  if (policy.cloudHookUrl) {
    await fetch(policy.cloudHookUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(backup),
    });
  }

  return { ran: true as const, backup, policy: updatedPolicy };
}

export async function createEncryptedUserBackup(passphrase: string): Promise<EncryptedUserBackup> {
  if (!passphrase.trim()) throw new Error('A passphrase is required to encrypt backups.');

  const payload = await collectBackupPayload();
  const metrics = await getSyncQueueMetrics();
  const manifest: BackupManifest = {
    id: `backup-${Date.now()}`,
    createdAt: Date.now(),
    version: 1,
    stores: Object.fromEntries(Object.entries(payload).map(([store, records]) => [store, records.length])),
    syncQueueDepth: metrics.depth,
    failedSyncAttempts: metrics.failedAttempts,
  };

  const salt = cryptoBytes(16);
  const iv = cryptoBytes(12);
  const key = await deriveKey(passphrase, salt);
  const plaintext = textEncoder.encode(JSON.stringify({ manifest, payload }));
  const ciphertext = new Uint8Array(await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, plaintext));
  const archive = {
    manifest,
    kdf: 'PBKDF2-SHA256' as const,
    cipher: 'AES-GCM' as const,
    salt: bytesToBase64(salt),
    iv: bytesToBase64(iv),
    ciphertext: bytesToBase64(ciphertext),
  };

  await putLocalRecord<BackupManifest>('backupManifests', { id: manifest.id, value: manifest });
  return archive;
}

export async function previewEncryptedUserBackup(backup: EncryptedUserBackup, passphrase: string) {
  assertBackupEnvelope(backup);
  const key = await deriveKey(passphrase, base64ToBytes(backup.salt));
  const plaintext = await crypto.subtle.decrypt(
    { name: 'AES-GCM', iv: base64ToBytes(backup.iv) },
    key,
    base64ToBytes(backup.ciphertext),
  );
  const decoded = JSON.parse(textDecoder.decode(plaintext)) as {
    manifest: BackupManifest;
    payload: Record<LocalStoreName, Array<{ id: string; value: unknown; updatedAt?: number }>>;
  };

  if (decoded.manifest.id !== backup.manifest.id || decoded.manifest.createdAt !== backup.manifest.createdAt) {
    throw new Error('Backup manifest verification failed.');
  }
  assertPayloadMatchesManifest(backup.manifest, decoded.payload);
  assertPayloadMatchesManifest(decoded.manifest, decoded.payload);

  return decoded;
}

export async function restoreEncryptedUserBackup(backup: EncryptedUserBackup, passphrase: string) {
  const decoded = await previewEncryptedUserBackup(backup, passphrase);
  const restoredItemCounts: Record<string, number> = {};

  await Promise.all(
    BACKUP_STORES.map(async (storeName) => {
      const records = decoded.payload[storeName] ?? [];
      restoredItemCounts[storeName] = records.length;
      if (storeName === 'syncQueue') {
        await Promise.all(records.map((record) => localDbPut(LOCAL_DB_STORES.syncQueue, record as LocalDbValue)));
        return;
      }

      await Promise.all(
        records.map((record) =>
          putLocalRecord(storeName, {
            id: record.id,
            updatedAt: record.updatedAt,
            value: record.value,
          }),
        ),
      );
    }),
  );

  const manifest = { ...decoded.manifest, restoredItemCounts };
  await putLocalRecord<BackupManifest>('backupManifests', { id: manifest.id, value: manifest });
  return manifest;
}
