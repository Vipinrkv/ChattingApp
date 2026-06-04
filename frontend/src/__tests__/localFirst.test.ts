import { beforeEach, describe, expect, it, vi } from 'vitest';
import { clearLocalStore, getAllLocalRecords, putLocalRecord, resetLocalDbForTests } from '../lib/localDb';
import { resolveLocalConflict } from '../lib/localConflicts';
import {
  createEncryptedUserBackup,
  getLocalFirstMetricsExport,
  getScheduledBackupPolicy,
  previewEncryptedUserBackup,
  restoreEncryptedUserBackup,
  runScheduledBackupIfDue,
  saveScheduledBackupPolicy,
} from '../lib/encryptedBackup';
import { flushQueuedRequests, getQueuedRequestCount, getSyncQueueMetrics, queueRequest, resetOfflineQueueForTests } from '../lib/offlineQueue';

describe('local-first persistence', () => {
  beforeEach(async () => {
    resetLocalDbForTests();
    resetOfflineQueueForTests();
    await clearLocalStore('syncQueue');
    await clearLocalStore('settings');
    await clearLocalStore('backupManifests');
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
  });

  it('stores offline requests with idempotency and retry metadata', async () => {
    const queued = await queueRequest({ path: '/api/v1/posts', method: 'POST', body: '{"body":"hello"}' });
    const duplicate = await queueRequest({ path: '/api/v1/posts', method: 'POST', body: '{"body":"hello"}' });

    expect(duplicate.id).toBe(queued.id);
    expect(await getQueuedRequestCount()).toBe(1);
    expect(queued.attempts).toBe(0);
    expect(queued.idempotencyKey).toContain('/api/v1/posts');
  });

  it('increments retry attempts and keeps failed queued writes', async () => {
    await queueRequest({ path: '/api/v1/posts', method: 'POST', body: '{"body":"hello"}' });
    const send = vi.fn().mockRejectedValue(new Error('still offline'));

    const result = await flushQueuedRequests(send);

    expect(result).toEqual({ flushed: 0, remaining: 1, failed: 0 });
    expect(send.mock.calls[0][0].attempts).toBe(0);
    await expect(getSyncQueueMetrics()).resolves.toMatchObject({ depth: 1, failedAttempts: 1, failedItems: 0 });
  });

  it('exposes local conflict policies for settings and append-only records', () => {
    const settings = resolveLocalConflict(
      'settings',
      { value: { theme: 'dark' }, updatedAt: 20 },
      { value: { locale: 'en', theme: 'light' }, updatedAt: 10 },
    );
    const message = resolveLocalConflict('messages', { value: 'local', updatedAt: 1 }, { value: 'remote', updatedAt: 2 });

    expect(settings.strategy).toBe('merge-settings');
    expect(settings.winner.value).toEqual({ locale: 'en', theme: 'dark' });
    expect(message.strategy).toBe('append-only');
    expect(message.winner.value).toBe('remote');
  });

  it('writes canonical stores through the IndexedDB wrapper fallback', async () => {
    const record = await putLocalRecord('settings', { id: 'user-1:settings', value: { theme: 'system' } });

    expect(record.id).toBe('user-1:settings');
    expect(record.updatedAt).toBeGreaterThan(0);
  });

  it('recovers a fresh browser profile from an encrypted backup', async () => {
    await putLocalRecord('settings', { id: 'user-1:settings', value: { theme: 'system' } });
    await queueRequest({ path: '/api/v1/posts', method: 'POST', body: '{"body":"draft"}' });

    const backup = await createEncryptedUserBackup('correct horse battery staple');
    const preview = await previewEncryptedUserBackup(backup, 'correct horse battery staple');

    expect(preview.manifest.stores.settings).toBe(1);
    expect(preview.manifest.syncQueueDepth).toBe(1);

    await clearLocalStore('settings');
    await clearLocalStore('syncQueue');
    resetOfflineQueueForTests();
    const manifest = await restoreEncryptedUserBackup(backup, 'correct horse battery staple');

    expect(manifest.restoredItemCounts).toMatchObject({ settings: 1, syncQueue: 1 });
    await expect(getAllLocalRecords('settings')).resolves.toHaveLength(1);
    await expect(getSyncQueueMetrics()).resolves.toMatchObject({ depth: 1 });
  });

  it('rejects corrupted encrypted backup archives', async () => {
    await putLocalRecord('settings', { id: 'user-1:settings', value: { theme: 'dark' } });
    const backup = await createEncryptedUserBackup('correct horse battery staple');

    await expect(
      previewEncryptedUserBackup({ ...backup, ciphertext: backup.ciphertext.slice(0, -4) + 'AAAA' }, 'correct horse battery staple'),
    ).rejects.toThrow();
  });

  it('rejects encrypted backups whose manifest no longer matches the payload', async () => {
    await putLocalRecord('settings', { id: 'user-1:settings', value: { theme: 'dark' } });
    const backup = await createEncryptedUserBackup('correct horse battery staple');
    const tampered = {
      ...backup,
      manifest: {
        ...backup.manifest,
        stores: { ...backup.manifest.stores, settings: backup.manifest.stores.settings + 1 },
      },
    };

    await expect(previewEncryptedUserBackup(tampered, 'correct horse battery staple')).rejects.toThrow(
      'Backup manifest count mismatch',
    );
  });

  it('exports local-first sync metrics from IndexedDB stores', async () => {
    await putLocalRecord('settings', { id: 'user-1:settings', value: { theme: 'dark' } });
    await queueRequest({ path: '/api/v1/posts', method: 'POST', body: '{"body":"draft"}' });
    const backup = await createEncryptedUserBackup('correct horse battery staple');
    await restoreEncryptedUserBackup(backup, 'correct horse battery staple');

    const metrics = await getLocalFirstMetricsExport();

    expect(metrics.queue_depth).toBeGreaterThanOrEqual(1);
    expect(metrics.restore_count).toBeGreaterThanOrEqual(1);
    expect(metrics.cache_size_bytes).toBeGreaterThan(0);
    expect(metrics.generated_at).toContain('T');
  });

  it('saves scheduled backup policy and runs due encrypted backups', async () => {
    await putLocalRecord('settings', { id: 'user-1:settings', value: { theme: 'dark' } });
    const policy = await saveScheduledBackupPolicy({
      enabled: true,
      intervalHours: 1,
      retentionCount: 3,
      nextRunAt: 1,
    });

    expect(policy.enabled).toBe(true);
    await expect(getScheduledBackupPolicy()).resolves.toMatchObject({ enabled: true, retentionCount: 3 });

    const result = await runScheduledBackupIfDue('correct horse battery staple', 2);

    expect(result.ran).toBe(true);
    expect(result.policy.lastRunAt).toBe(2);
    expect(result.policy.nextRunAt).toBe(60 * 60 * 1000 + 2);
  });
});
