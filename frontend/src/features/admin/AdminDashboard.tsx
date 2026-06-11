import { useCallback, useEffect, useState } from 'react';
import { apiGet, apiPost } from '../../lib/api';
import { normalizeError } from '../../lib/errors';
import RetryPanel from '../../components/RetryPanel';

type Report = {
  id: string;
  reporter_id?: string;
  target_type: string;
  target_id: string;
  reason: string;
  status: string;
  created_at?: string;
  details?: string | null;
};

type HealthDetails = {
  status?: string;
  database?: string;
  redis?: string;
  [key: string]: unknown;
};

type AnalyticsSummary = {
  active_users?: number;
  total_events?: number;
  engagement_events?: number;
  creator_events?: number;
  revenue_events?: number;
  moderation_events?: number;
  retained_users?: number;
  heatmap?: Array<{ hour?: number; count?: number }>;
};

type ScalingStatus = {
  task_queue_backend?: string;
  event_bus_backend?: string;
  redis_enabled?: boolean;
  kafka_configured?: boolean;
  read_replica_configured?: boolean;
};

type PlatformSummary = {
  live_streams?: number;
  active_calls?: number;
  screen_shares?: number;
  monetized_creators?: number;
  marketplace_listings?: number;
  subscription_plans?: number;
  platform_events?: number;
  community_channels?: number;
};

type EnterpriseSummary = {
  roles?: number;
  open_audit_reviews?: number;
  open_support_tickets?: number;
  booked_revenue?: number;
  reporting_snapshots?: number;
  moderation_queue?: number;
};

type GlobalizationSummary = {
  locales?: number;
  localized_strings?: number;
  regional_policies?: number;
  international_moderation_items?: number;
  scheduled_items?: number;
  regional_recommendations?: number;
};

function AdminDashboard() {
  const [reports, setReports] = useState<Report[]>([]);
  const [health, setHealth] = useState<HealthDetails | null>(null);
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [scaling, setScaling] = useState<ScalingStatus | null>(null);
  const [platform, setPlatform] = useState<PlatformSummary | null>(null);
  const [enterprise, setEnterprise] = useState<EnterpriseSummary | null>(null);
  const [globalization, setGlobalization] = useState<GlobalizationSummary | null>(null);
  const [pendingGroups, setPendingGroups] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadAdminData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [reportData, healthData, analyticsData, scalingData, platformData, enterpriseData, globalizationData, pendingGroupsData] = await Promise.all([
        apiGet('/api/v1/admin/reports?limit=25'),
        apiGet('/health/details'),
        apiGet('/api/v1/analytics/admin/summary?days=30'),
        apiGet('/api/v1/analytics/admin/scaling'),
        apiGet('/api/v1/platform/summary'),
        apiGet('/api/v1/enterprise/summary'),
        apiGet('/api/v1/globalization/summary'),
        apiGet('/api/v1/admin/groups/pending'),
      ]);
      setReports(Array.isArray(reportData) ? reportData : reportData?.data ?? []);
      setHealth(healthData?.data ?? healthData);
      setAnalytics(analyticsData?.data ?? analyticsData);
      setScaling(scalingData?.data ?? scalingData);
      setPlatform(platformData?.data ?? platformData);
      setEnterprise(enterpriseData?.data ?? enterpriseData);
      setGlobalization(globalizationData?.data ?? globalizationData);
      setPendingGroups(Array.isArray(pendingGroupsData) ? pendingGroupsData : pendingGroupsData?.data ?? []);
    } catch (err) {
      setError(normalizeError(err, 'Could not load admin console.').message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadAdminData();
  }, [loadAdminData]);

  const resolveReport = async (reportId: string) => {
    setActionId(reportId);
    setError(null);
    try {
      await apiPost(`/api/v1/admin/reports/${reportId}/resolve`, {
        comment: 'Resolved from admin console.',
      });
      await loadAdminData();
    } catch (err) {
      setError(normalizeError(err, 'Could not resolve report.').message);
    } finally {
      setActionId(null);
    }
  };

  const handleApproveVerification = async (groupId: string) => {
    setActionId(groupId);
    setError(null);
    try {
      await apiPost(`/api/v1/admin/groups/${groupId}/verify/approve`, {});
      await loadAdminData();
    } catch (err) {
      setError(normalizeError(err, 'Could not approve verification.').message);
    } finally {
      setActionId(null);
    }
  };

  const handleRejectVerification = async (groupId: string) => {
    setActionId(groupId);
    setError(null);
    try {
      await apiPost(`/api/v1/admin/groups/${groupId}/verify/reject`, {});
      await loadAdminData();
    } catch (err) {
      setError(normalizeError(err, 'Could not reject verification.').message);
    } finally {
      setActionId(null);
    }
  };

  if (loading) {
    return <div className="page-loading">Loading admin console...</div>;
  }

  if (error && !reports.length && !health) {
    return (
      <RetryPanel
        title="Admin console unavailable"
        message={error}
        onRetry={() => void loadAdminData()}
      />
    );
  }

  const healthStatus = health?.status ?? 'unknown';

  return (
    <div className="page-panel admin-page">
      <section className="glass-panel admin-hero">
        <div>
          <p className="hero-label">Admin console</p>
          <h1>Moderation and system health</h1>
          <p>
            Review reports, track platform health, and keep operational signals visible from one guarded surface.
          </p>
        </div>
        <button className="secondary-button" type="button" onClick={() => void loadAdminData()}>
          Refresh
        </button>
      </section>

      {error ? <div className="error-message admin-error" role="alert">{error}</div> : null}

      <section className="admin-grid">
        <article className="card admin-card analytics-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">Analytics</p>
              <h2>Business signals</h2>
            </div>
            <span className="status-pill">{analytics?.total_events ?? 0} events</span>
          </div>
          <div className="admin-metric-grid">
            <span><strong>{analytics?.active_users ?? 0}</strong> Active users</span>
            <span><strong>{analytics?.engagement_events ?? 0}</strong> Engagement</span>
            <span><strong>{analytics?.creator_events ?? 0}</strong> Creator</span>
            <span><strong>{analytics?.revenue_events ?? 0}</strong> Revenue</span>
            <span><strong>{analytics?.moderation_events ?? 0}</strong> Moderation</span>
            <span><strong>{analytics?.retained_users ?? 0}</strong> Retention</span>
          </div>
          <div className="heatmap-strip" aria-label="Realtime engagement heatmap">
            {Array.from({ length: 24 }, (_, hour) => {
              const slot = analytics?.heatmap?.find((item) => item.hour === hour);
              return (
                <span
                  key={hour}
                  title={`${hour}:00 - ${slot?.count ?? 0}`}
                  style={{ opacity: Math.min(1, 0.2 + Number(slot?.count ?? 0) / 20) }}
                />
              );
            })}
          </div>
        </article>

        <article className="card admin-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">Scale</p>
              <h2>Runtime strategy</h2>
            </div>
            <span className="status-pill">{scaling?.event_bus_backend ?? 'unknown'}</span>
          </div>
          <div className="admin-health-list">
            <span>Queue: {scaling?.task_queue_backend ?? 'unknown'}</span>
            <span>Redis fanout: {scaling?.redis_enabled ? 'ready' : 'not active'}</span>
            <span>Kafka: {scaling?.kafka_configured ? 'configured' : 'not configured'}</span>
            <span>Read replica: {scaling?.read_replica_configured ? 'configured' : 'not configured'}</span>
          </div>
        </article>

        <article className="card admin-card expansion-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">Platform</p>
              <h2>Expansion systems</h2>
            </div>
            <span className="status-pill">{platform?.live_streams ?? 0} streams</span>
          </div>
          <div className="admin-metric-grid">
            <span><strong>{platform?.active_calls ?? 0}</strong> Active calls</span>
            <span><strong>{platform?.screen_shares ?? 0}</strong> Screen shares</span>
            <span><strong>{platform?.monetized_creators ?? 0}</strong> Creators</span>
            <span><strong>{platform?.marketplace_listings ?? 0}</strong> Listings</span>
            <span><strong>{platform?.subscription_plans ?? 0}</strong> Plans</span>
            <span><strong>{platform?.community_channels ?? 0}</strong> Channels</span>
          </div>
        </article>

        <article className="card admin-card expansion-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">Enterprise</p>
              <h2>Operations suite</h2>
            </div>
            <span className="status-pill">{enterprise?.roles ?? 0} roles</span>
          </div>
          <div className="admin-metric-grid">
            <span><strong>{enterprise?.open_audit_reviews ?? 0}</strong> Audit reviews</span>
            <span><strong>{enterprise?.open_support_tickets ?? 0}</strong> Tickets</span>
            <span><strong>{enterprise?.moderation_queue ?? 0}</strong> Moderation</span>
            <span><strong>{enterprise?.reporting_snapshots ?? 0}</strong> Reports</span>
            <span><strong>${(enterprise?.booked_revenue ?? 0).toLocaleString()}</strong> Revenue</span>
          </div>
        </article>

        <article className="card admin-card expansion-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">Global</p>
              <h2>Localization readiness</h2>
            </div>
            <span className="status-pill">{globalization?.locales ?? 0} locales</span>
          </div>
          <div className="admin-metric-grid">
            <span><strong>{globalization?.localized_strings ?? 0}</strong> Strings</span>
            <span><strong>{globalization?.regional_policies ?? 0}</strong> Policies</span>
            <span><strong>{globalization?.international_moderation_items ?? 0}</strong> Intl queue</span>
            <span><strong>{globalization?.scheduled_items ?? 0}</strong> Scheduled</span>
            <span><strong>{globalization?.regional_recommendations ?? 0}</strong> Recommendations</span>
          </div>
        </article>

        <article className="card admin-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">System</p>
              <h2>Health</h2>
            </div>
            <span className={`status-pill ${healthStatus === 'ok' ? 'success' : ''}`}>{healthStatus}</span>
          </div>
          <div className="admin-health-list">
            <span>Database: {String(health?.database ?? 'unknown')}</span>
            <span>Redis: {String(health?.redis ?? 'unknown')}</span>
          </div>
        </article>

        <article className="card admin-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">Queue</p>
              <h2>Reports</h2>
            </div>
            <span className="status-pill">{reports.length}</span>
          </div>

          {reports.length ? (
            <div className="admin-report-list">
              {reports.map((report) => (
                <div className="admin-report-row" key={report.id}>
                  <div>
                    <strong>{report.reason}</strong>
                    <p>{report.target_type} - {report.target_id}</p>
                    {report.details ? <small>{report.details}</small> : null}
                  </div>
                  <div className="admin-report-actions">
                    <span className="pill soft">{report.status}</span>
                    <button
                      className="secondary-button"
                      type="button"
                      disabled={actionId === report.id || report.status === 'resolved'}
                      onClick={() => void resolveReport(report.id)}
                    >
                      {actionId === report.id ? 'Resolving...' : 'Resolve'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state-card">No reports are waiting for review.</div>
          )}
        </article>

        <article className="card admin-card">
          <div className="panel-header">
            <div>
              <p className="hero-label">Queue</p>
              <h2>Group Verifications</h2>
            </div>
            <span className="status-pill">{pendingGroups.length}</span>
          </div>

          {pendingGroups.length ? (
            <div className="admin-report-list">
              {pendingGroups.map((group) => (
                <div className="admin-report-row" key={group.id}>
                  <div>
                    <strong>{group.name}</strong>
                    <p>{group.type} - {group.category ?? 'Uncategorized'}</p>
                    <small>Created by: {group.created_by}</small>
                  </div>
                  <div className="admin-report-actions">
                    <button
                      className="secondary-button success"
                      type="button"
                      disabled={actionId === group.id}
                      onClick={() => void handleApproveVerification(group.id)}
                      style={{ background: 'rgba(34, 197, 94, 0.16)', color: 'var(--success)' }}
                    >
                      {actionId === group.id ? 'Processing...' : 'Approve'}
                    </button>
                    <button
                      className="secondary-button danger"
                      type="button"
                      disabled={actionId === group.id}
                      onClick={() => void handleRejectVerification(group.id)}
                      style={{ background: 'rgba(239, 68, 68, 0.16)', color: 'var(--danger)' }}
                    >
                      {actionId === group.id ? 'Processing...' : 'Reject'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state-card">No group verification requests pending.</div>
          )}
        </article>
      </section>
    </div>
  );
}

export default AdminDashboard;
