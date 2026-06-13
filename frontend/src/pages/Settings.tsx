import { useState, useEffect } from 'react';
import { useTheme } from '../ui/theme';
import {
  createEncryptedUserBackup,
  restoreEncryptedUserBackup,
  getScheduledBackupPolicy,
  saveScheduledBackupPolicy,
  getLocalFirstMetricsExport,
  type ScheduledBackupPolicy,
  type LocalFirstMetricsExport,
} from '../lib/encryptedBackup';
import { clearLocalStore } from '../lib/localDb';
import { flushQueuedRequests } from '../lib/offlineQueue';
import { apiRequest } from '../lib/api';
import { useToasts } from '../ui/ToastProvider';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

export default function Settings() {
  const { theme, preference, setTheme, accentColor, setAccentColor } = useTheme();
  const { push } = useToasts();

  const [passphrase, setPassphrase] = useState('');
  const [backupFile, setBackupFile] = useState<File | null>(null);
  const [restorePassphrase, setRestorePassphrase] = useState('');
  
  const [scheduledPolicy, setScheduledPolicy] = useState<ScheduledBackupPolicy>({
    enabled: false,
    intervalHours: 24,
    retentionCount: 7,
  });

  const [metrics, setMetrics] = useState<LocalFirstMetricsExport>({
    queue_depth: 0,
    failed_sync_count: 0,
    restore_count: 0,
    cache_size_bytes: 0,
    generated_at: new Date().toISOString(),
  });

  const [isLoadingMetrics, setIsLoadingMetrics] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [isSavingPolicy, setIsSavingPolicy] = useState(false);
  const [isFlushing, setIsFlushing] = useState(false);

  const loadMetrics = async () => {
    setIsLoadingMetrics(true);
    try {
      const data = await getLocalFirstMetricsExport();
      setMetrics(data);
    } catch (error) {
      console.error('Failed to load metrics:', error);
    } finally {
      setIsLoadingMetrics(false);
    }
  };

  const loadPolicy = async () => {
    try {
      const data = await getScheduledBackupPolicy();
      setScheduledPolicy(data);
    } catch (error) {
      console.error('Failed to load backup policy:', error);
    }
  };

  useEffect(() => {
    void loadMetrics();
    void loadPolicy();
  }, []);

  const handleExportBackup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passphrase.trim()) {
      push({ type: 'error', message: 'Passphrase is required to encrypt backup.' });
      return;
    }
    setIsExporting(true);
    try {
      const backup = await createEncryptedUserBackup(passphrase);
      const blob = new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `chattingapp-backup-${Date.now()}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setPassphrase('');
      push({ type: 'success', message: 'Backup created and downloaded successfully.' });
      void loadMetrics();
    } catch (error) {
      push({ type: 'error', message: error instanceof Error ? error.message : 'Export failed.' });
    } finally {
      setIsExporting(false);
    }
  };

  const handleRestoreBackup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!backupFile) {
      push({ type: 'error', message: 'Please select a backup file first.' });
      return;
    }
    if (!restorePassphrase.trim()) {
      push({ type: 'error', message: 'Passphrase is required to decrypt backup.' });
      return;
    }

    setIsRestoring(true);
    try {
      const text = await backupFile.text();
      const backup = JSON.parse(text);
      const manifest = await restoreEncryptedUserBackup(backup, restorePassphrase);
      push({
        type: 'success',
        message: `Backup restored successfully! Restored items: ${JSON.stringify(manifest.restoredItemCounts)}`,
      });
      setRestorePassphrase('');
      setBackupFile(null);
      // Reload in a short moment to apply changes
      setTimeout(() => window.location.reload(), 2000);
    } catch (error) {
      push({ type: 'error', message: error instanceof Error ? error.message : 'Restore failed.' });
    } finally {
      setIsRestoring(false);
    }
  };

  const handleSavePolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSavingPolicy(true);
    try {
      const updated = await saveScheduledBackupPolicy(scheduledPolicy);
      setScheduledPolicy(updated);
      push({ type: 'success', message: 'Scheduled backup policy updated.' });
    } catch (error) {
      push({ type: 'error', message: 'Failed to save policy.' });
    } finally {
      setIsSavingPolicy(false);
    }
  };

  const handleClearCache = async () => {
    try {
      await clearLocalStore('feedCache');
      await clearLocalStore('drafts');
      push({ type: 'success', message: 'Feed cache and message drafts cleared.' });
      void loadMetrics();
    } catch (error) {
      push({ type: 'error', message: 'Failed to clear cache.' });
    }
  };

  const handleForceSync = async () => {
    setIsFlushing(true);
    try {
      const result = await flushQueuedRequests((request) =>
        apiRequest(request.path, {
          method: request.method,
          body: request.body,
          headers: { 'Idempotency-Key': request.idempotencyKey },
          skipOfflineQueue: true,
        }),
      );
      if (result.flushed > 0) {
        push({ type: 'success', message: `${result.flushed} offline requests synced.` });
      } else {
        push({ type: 'info', message: 'No pending requests to sync.' });
      }
      void loadMetrics();
    } catch (error) {
      push({ type: 'error', message: 'Sync failed: ' + (error instanceof Error ? error.message : 'Unknown error') });
    } finally {
      setIsFlushing(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="settings-page" style={{ padding: '20px', maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <header>
        <h1 style={{ margin: '0 0 8px 0', fontSize: 'var(--text-xl)', fontWeight: 'bold' }}>Application Settings</h1>
        <p style={{ color: 'var(--muted)', margin: 0 }}>Configure client behavior, local database backups, and visualization options.</p>
      </header>

      {/* Theme and Accent Color Options */}
      <section className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div>
          <h2 style={{ fontSize: 'var(--text-lg)', margin: '0 0 4px 0', fontWeight: '600' }}>Theme Preference</h2>
          <p style={{ color: 'var(--muted)', margin: 0, fontSize: 'var(--text-sm)' }}>Choose a theme or adapt to your operating system preference.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          {(['light', 'dark', 'system'] as const).map((pref) => (
            <button
              key={pref}
              className={`btn ${preference === pref ? '' : 'btn-ghost'}`}
              onClick={() => setTheme(pref)}
              style={{
                padding: '10px 20px',
                borderRadius: 'var(--radius-pill)',
                textTransform: 'capitalize',
                border: '1px solid var(--border)',
                background: preference === pref ? 'linear-gradient(135deg, var(--color-primary), var(--color-accent))' : 'transparent',
                color: preference === pref ? '#fff' : 'var(--text)',
                cursor: 'pointer',
                fontWeight: preference === pref ? '600' : 'normal',
                boxShadow: preference === pref ? '0 4px 12px var(--focus-ring)' : 'none',
                transition: 'all 0.2s ease',
              }}
            >
              {pref}
            </button>
          ))}
        </div>

        <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px', marginTop: '4px' }}>
          <h2 style={{ fontSize: 'var(--text-lg)', margin: '0 0 4px 0', fontWeight: '600' }}>Brand Accent Color</h2>
          <p style={{ color: 'var(--muted)', margin: 0, fontSize: 'var(--text-sm)' }}>Customize the application's primary accent color scheme.</p>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
          {([
            { id: 'blue', name: 'Cosmic Blue', color: '#2563eb' },
            { id: 'green', name: 'Emerald Green', color: '#10b981' },
            { id: 'orange', name: 'Sunset Orange', color: '#f97316' },
            { id: 'red', name: 'Passion Red', color: '#ef4444' },
            { id: 'purple', name: 'Royal Purple', color: '#8b5cf6' },
            { id: 'pink', name: 'Sweet Pink', color: '#ec4899' },
          ] as const).map((item) => {
            const isSelected = accentColor === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setAccentColor(item.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '8px 16px',
                  borderRadius: 'var(--radius-pill)',
                  border: isSelected ? `2px solid ${item.color}` : '1px solid var(--border)',
                  background: 'var(--surface-soft)',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  fontWeight: isSelected ? '600' : 'normal',
                  transition: 'all 0.2s ease',
                  boxShadow: isSelected ? `0 4px 14px ${item.color}33` : 'none',
                  transform: isSelected ? 'scale(1.03)' : 'scale(1)',
                }}
              >
                <span style={{
                  width: '12px',
                  height: '12px',
                  borderRadius: '50%',
                  backgroundColor: item.color,
                  display: 'inline-block',
                  boxShadow: `0 0 6px ${item.color}`,
                }} />
                {item.name}
              </button>
            );
          })}
        </div>
      </section>

      {/* Sync Status / Offline metrics */}
      <section className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', margin: 0 }}>Offline Storage & Sync Metrics</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '16px' }}>
          <div style={{ padding: '16px', background: 'var(--surface-soft)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--muted)' }}>Pending Sync requests</span>
            <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'bold', marginTop: '4px' }}>
              {isLoadingMetrics ? '...' : metrics.queue_depth}
            </div>
          </div>
          <div style={{ padding: '16px', background: 'var(--surface-soft)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--muted)' }}>Failed Sync Attempts</span>
            <div style={{ fontSize: 'var(--text-xl)', fontWeight: 'bold', marginTop: '4px' }}>
              {isLoadingMetrics ? '...' : metrics.failed_sync_count}
            </div>
          </div>
          <div style={{ padding: '16px', background: 'var(--surface-soft)', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--muted)' }}>Local Cache Size</span>
            <div style={{ fontSize: 'var(--text-lg)', fontWeight: 'bold', marginTop: '4px' }}>
              {isLoadingMetrics ? '...' : formatBytes(metrics.cache_size_bytes)}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
          <Button onClick={handleForceSync} disabled={isFlushing || metrics.queue_depth === 0}>
            {isFlushing ? 'Syncing...' : 'Sync Pending Requests'}
          </Button>
          <Button variant="ghost" onClick={handleClearCache} style={{ borderColor: 'var(--danger)', color: 'var(--danger)' }}>
            Clear Local Cache
          </Button>
          <Button variant="ghost" onClick={loadMetrics}>
            Refresh Metrics
          </Button>
        </div>
      </section>

      {/* Local Encrypted Backup / Restore */}
      <section className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', margin: 0 }}>Local Database Encrypted Backup</h2>
        
        {/* Create Backup */}
        <form onSubmit={handleExportBackup} style={{ display: 'flex', flexDirection: 'column', gap: '12px', paddingBottom: '16px', borderBottom: '1px solid var(--border)' }}>
          <h3 style={{ fontSize: 'var(--text-md)', margin: 0 }}>Create Encrypted Backup</h3>
          <p style={{ color: 'var(--muted)', margin: 0, fontSize: 'var(--text-sm)' }}>
            Saves your offline messages, settings, drafts, and media index into a passphrase-protected file.
          </p>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <Input
              type="password"
              placeholder="Enter passphrase to encrypt"
              value={passphrase}
              onChange={(e) => setPassphrase(e.target.value)}
              style={{ flex: 1, padding: '10px 16px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', background: 'var(--surface-soft)', color: 'var(--text)' }}
            />
            <Button type="submit" disabled={isExporting}>
              {isExporting ? 'Exporting...' : 'Export Backup'}
            </Button>
          </div>
        </form>

        {/* Restore Backup */}
        <form onSubmit={handleRestoreBackup} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h3 style={{ fontSize: 'var(--text-md)', margin: 0 }}>Restore from Encrypted Backup</h3>
          <p style={{ color: 'var(--muted)', margin: 0, fontSize: 'var(--text-sm)' }}>
            Select a backup file and enter the passphrase used during export to restore your data.
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
            <input
              type="file"
              accept=".json"
              onChange={(e) => setBackupFile(e.target.files?.[0] || null)}
              style={{ flex: 1, minWidth: '200px' }}
            />
            <Input
              type="password"
              placeholder="Enter decryption passphrase"
              value={restorePassphrase}
              onChange={(e) => setRestorePassphrase(e.target.value)}
              style={{ flex: 1, minWidth: '200px', padding: '10px 16px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', background: 'var(--surface-soft)', color: 'var(--text)' }}
            />
            <Button type="submit" disabled={isRestoring || !backupFile}>
              {isRestoring ? 'Restoring...' : 'Restore Backup'}
            </Button>
          </div>
        </form>
      </section>

      {/* Auto Backup Policy */}
      <section className="glass-panel" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', margin: 0 }}>Scheduled Backup Policy</h2>
        <p style={{ color: 'var(--muted)', margin: 0, fontSize: 'var(--text-sm)' }}>Enable automated background backups to keep your data safe.</p>
        <form onSubmit={handleSavePolicy} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={scheduledPolicy.enabled}
                onChange={(e) => setScheduledPolicy({ ...scheduledPolicy, enabled: e.target.checked })}
              />
              Enable scheduled backups
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--muted)' }}>Interval (Hours)</span>
              <Input
                type="number"
                min="1"
                value={scheduledPolicy.intervalHours}
                onChange={(e) => setScheduledPolicy({ ...scheduledPolicy, intervalHours: parseInt(e.target.value) || 24 })}
                style={{ width: '80px', padding: '6px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', background: 'var(--surface-soft)', color: 'var(--text)' }}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--muted)' }}>Retention Count (Files)</span>
              <Input
                type="number"
                min="1"
                value={scheduledPolicy.retentionCount}
                onChange={(e) => setScheduledPolicy({ ...scheduledPolicy, retentionCount: parseInt(e.target.value) || 7 })}
                style={{ width: '80px', padding: '6px 12px', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', background: 'var(--surface-soft)', color: 'var(--text)' }}
              />
            </label>
          </div>
          <div>
            <Button type="submit" disabled={isSavingPolicy}>
              {isSavingPolicy ? 'Saving...' : 'Save Policy'}
            </Button>
          </div>
        </form>
      </section>
    </div>
  );
}
