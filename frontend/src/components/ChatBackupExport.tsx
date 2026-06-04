import React, { useState, useEffect, useRef } from 'react';
import { apiPost, apiGet } from '../lib/api';
import {
  createEncryptedUserBackup,
  exportLocalFirstMetrics,
  getLocalFirstMetricsExport,
  getScheduledBackupPolicy,
  previewEncryptedUserBackup,
  restoreEncryptedUserBackup,
  runScheduledBackupIfDue,
  saveScheduledBackupPolicy,
  type EncryptedUserBackup,
  type LocalFirstMetricsExport,
  type ScheduledBackupPolicy,
} from '../lib/encryptedBackup';

export function ChatBackupExport() {
  const [backups, setBackups] = useState<any[]>([]);
  const [backupName, setBackupName] = useState('');
  const [format, setFormat] = useState('json');
  const [loading, setLoading] = useState(false);
  const [passphrase, setPassphrase] = useState('');
  const [restoreText, setRestoreText] = useState('');
  const [localStatus, setLocalStatus] = useState<string | null>(null);
  const [restorePreview, setRestorePreview] = useState<Awaited<ReturnType<typeof previewEncryptedUserBackup>> | null>(null);
  const [metrics, setMetrics] = useState<LocalFirstMetricsExport | null>(null);
  const [scheduledPolicy, setScheduledPolicy] = useState<ScheduledBackupPolicy>({
    enabled: false,
    intervalHours: 24,
    retentionCount: 7,
  });
  const loadedRef = useRef(false);
  const creatingRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    loadBackups();
  }, []);

  async function loadBackups() {
    try {
      const [response, localMetrics, policy] = await Promise.all([
        apiGet('/api/v1/chats/backups'),
        getLocalFirstMetricsExport(),
        getScheduledBackupPolicy(),
      ]);
      setBackups(response.backups || []);
      setMetrics(localMetrics);
      setScheduledPolicy(policy);
    } catch (err) {
      console.error('Failed to load backups:', err);
    }
  }

  async function handleCreateBackup() {
    if (!backupName.trim()) return;
    if (creatingRef.current) return;
    try {
      creatingRef.current = true;
      setLoading(true);
      const response = await apiPost('/api/v1/chats/backups', {
        backup_name: backupName,
        format,
      });
      setBackups((prev) => [response, ...prev]);
      setBackupName('');
    } catch (err) {
      console.error('Backup creation error:', err);
    } finally {
      creatingRef.current = false;
      setLoading(false);
    }
  }

  async function handleEncryptedExport() {
    if (!passphrase.trim()) return;
    try {
      setLoading(true);
      setLocalStatus(null);
      const backup = await createEncryptedUserBackup(passphrase);
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${backup.manifest.id}.encrypted.json`;
      link.click();
      URL.revokeObjectURL(url);
      setLocalStatus(`Encrypted local backup created with ${Object.values(backup.manifest.stores).reduce((a, b) => a + b, 0)} records.`);
    } catch (err) {
      setLocalStatus(err instanceof Error ? err.message : 'Encrypted backup failed.');
    } finally {
      setLoading(false);
    }
  }

  async function handleRestorePreview() {
    try {
      const backup = JSON.parse(restoreText) as EncryptedUserBackup;
      const preview = await previewEncryptedUserBackup(backup, passphrase);
      setRestorePreview(preview);
      setLocalStatus(`Backup verified: ${Object.entries(preview.manifest.stores).map(([store, count]) => `${store} ${count}`).join(', ')}`);
    } catch (err) {
      setRestorePreview(null);
      setLocalStatus(err instanceof Error ? err.message : 'Backup verification failed.');
    }
  }

  async function handleRestore() {
    if (!restorePreview) {
      setLocalStatus('Preview the backup before staged import.');
      return;
    }
    try {
      const backup = JSON.parse(restoreText) as EncryptedUserBackup;
      const manifest = await restoreEncryptedUserBackup(backup, passphrase);
      setLocalStatus(`Restore staged locally: ${Object.entries(manifest.restoredItemCounts ?? {}).map(([store, count]) => `${store} ${count}`).join(', ')}`);
      setMetrics(await getLocalFirstMetricsExport());
    } catch (err) {
      setLocalStatus(err instanceof Error ? err.message : 'Restore failed.');
    }
  }

  async function handleExportMetrics() {
    try {
      setLoading(true);
      const exported = await exportLocalFirstMetrics();
      setMetrics(exported);
      setLocalStatus(`Sync metrics exported: queue ${exported.queue_depth}, failed ${exported.failed_sync_count}, restores ${exported.restore_count}.`);
    } catch (err) {
      setLocalStatus(err instanceof Error ? err.message : 'Could not export sync metrics.');
    } finally {
      setLoading(false);
    }
  }

  async function handleSaveScheduledPolicy() {
    try {
      const policy = await saveScheduledBackupPolicy(scheduledPolicy);
      setScheduledPolicy(policy);
      setLocalStatus(policy.enabled ? 'Scheduled encrypted backups enabled locally.' : 'Scheduled encrypted backups disabled.');
    } catch (err) {
      setLocalStatus(err instanceof Error ? err.message : 'Could not save scheduled backup policy.');
    }
  }

  async function handleRunScheduledBackup() {
    try {
      if (!passphrase.trim()) {
        setLocalStatus('Enter your passphrase or recovery key before running a scheduled backup.');
        return;
      }
      const result = await runScheduledBackupIfDue(passphrase, Date.now() + 1);
      setScheduledPolicy(result.policy);
      setLocalStatus(result.ran ? 'Scheduled encrypted backup completed.' : 'No scheduled backup is due yet.');
    } catch (err) {
      setLocalStatus(err instanceof Error ? err.message : 'Scheduled backup failed.');
    }
  }

  return (
    <div className="chat-backup-export">
      <div className="backup-header">
        <h3>💾 Chat Backup & Export</h3>
      </div>

      <div className="backup-form">
        <input
          type="text"
          placeholder="Backup name (e.g., 'May 2026 Backup')"
          value={backupName}
          onChange={(e) => setBackupName(e.target.value)}
          className="backup-name-input"
        />
        <select
          value={format}
          onChange={(e) => setFormat(e.target.value)}
          className="backup-format-select"
          aria-label="Backup format"
        >
          <option value="json">JSON</option>
          <option value="csv">CSV</option>
          <option value="pdf">PDF</option>
        </select>
        <button
          onClick={handleCreateBackup}
          disabled={loading || !backupName.trim()}
          className="backup-btn"
        >
          {loading ? 'Creating...' : 'Create Backup'}
        </button>
      </div>

      <div className="backup-form encrypted-backup-form">
        <input
          type="password"
          placeholder="Passphrase or recovery key"
          value={passphrase}
          onChange={(e) => setPassphrase(e.target.value)}
          className="backup-name-input"
        />
        <button
          onClick={handleEncryptedExport}
          disabled={loading || !passphrase.trim()}
          className="backup-btn"
        >
          Export Encrypted Local Backup
        </button>
      </div>

      <div className="backup-form encrypted-backup-form">
        <textarea
          placeholder="Paste encrypted backup JSON to verify or restore"
          value={restoreText}
          onChange={(e) => setRestoreText(e.target.value)}
          className="backup-name-input"
          rows={4}
        />
        <button onClick={handleRestorePreview} disabled={!passphrase.trim() || !restoreText.trim()} className="backup-btn">
          1. Preview & Detect Tampering
        </button>
        <button onClick={handleRestore} disabled={!passphrase.trim() || !restoreText.trim() || !restorePreview} className="backup-btn">
          2. Stage Local Import
        </button>
      </div>

      {restorePreview ? (
        <div className="backup-preview" role="region" aria-label="Restore preview">
          <h4>Restore Preview</h4>
          <p>Manifest {restorePreview.manifest.id} verified. Review counts before import.</p>
          <ul>
            {Object.entries(restorePreview.manifest.stores).map(([store, count]) => (
              <li key={store}>{store}: {count}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="backup-form encrypted-backup-form">
        <label>
          <input
            type="checkbox"
            checked={scheduledPolicy.enabled}
            onChange={(event) => setScheduledPolicy((prev) => ({ ...prev, enabled: event.target.checked }))}
          />
          Enable local scheduled encrypted backups
        </label>
        <input
          type="number"
          min={1}
          value={scheduledPolicy.intervalHours}
          onChange={(event) => setScheduledPolicy((prev) => ({ ...prev, intervalHours: Number(event.target.value) }))}
          className="backup-name-input"
          aria-label="Scheduled backup interval hours"
        />
        <input
          type="number"
          min={1}
          value={scheduledPolicy.retentionCount}
          onChange={(event) => setScheduledPolicy((prev) => ({ ...prev, retentionCount: Number(event.target.value) }))}
          className="backup-name-input"
          aria-label="Scheduled backup retention count"
        />
        <input
          type="url"
          value={scheduledPolicy.cloudHookUrl ?? ''}
          onChange={(event) => setScheduledPolicy((prev) => ({ ...prev, cloudHookUrl: event.target.value || undefined }))}
          className="backup-name-input"
          placeholder="Optional encrypted cloud backup hook URL"
        />
        <button type="button" onClick={handleSaveScheduledPolicy} className="backup-btn">Save Schedule</button>
        <button type="button" onClick={handleRunScheduledBackup} className="backup-btn">Run Due Backup</button>
      </div>

      <div className="backup-form encrypted-backup-form">
        <p className="small-note">
          Sync metrics: queue {metrics?.queue_depth ?? 0}, failed {metrics?.failed_sync_count ?? 0}, restores {metrics?.restore_count ?? 0}, cache {metrics ? (metrics.cache_size_bytes / 1024).toFixed(1) : '0.0'} KB
        </p>
        <button type="button" onClick={handleExportMetrics} disabled={loading} className="backup-btn">
          Export Sync Metrics
        </button>
      </div>

      {localStatus ? <p className="backup-status" role="status">{localStatus}</p> : null}

      <div className="backup-list">
        <h4>Recent Backups:</h4>
        {backups.length === 0 ? (
          <p className="empty-state">No backups yet</p>
        ) : (
          backups.map((backup) => (
            <div key={backup.backup_id} className="backup-item">
              <div className="backup-info">
                <p className="backup-name">{backup.backup_name}</p>
                <p className="backup-meta">
                  {backup.message_count} messages • {(backup.file_size_bytes / 1024 / 1024).toFixed(2)} MB
                </p>
                <p className="backup-status">
                  Status: <span className={`status-${backup.status}`}>{backup.status}</span>
                </p>
              </div>
              {backup.download_url && (
                <a href={backup.download_url} download className="backup-download">
                  ⬇️ Download
                </a>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
