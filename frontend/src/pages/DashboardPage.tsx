import { useQuery } from '@tanstack/react-query';
import { ShieldAlert, Building2, AlertTriangle, Network, TrendingUp, Bell } from 'lucide-react';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/authStore';
import { RiskLevelBadge } from '@/components/risk/RiskLevelBadge';
import { Link } from 'react-router-dom';

export function DashboardPage() {
  const user = useAuthStore(s => s.user);

  const { data: tierSummary } = useQuery({
    queryKey: ['tier-summary'],
    queryFn: () => api.getTierSummary(),
  });

  const { data: alertsData } = useQuery({
    queryKey: ['alerts-dashboard'],
    queryFn: () => api.listAlerts({ limit: 5 }),
  });

  const { data: riskEvents } = useQuery({
    queryKey: ['risk-events-dashboard'],
    queryFn: () => api.listRiskEvents({ limit: 5 }),
  });

  const { data: suppliersData } = useQuery({
    queryKey: ['suppliers-dashboard'],
    queryFn: () => api.listSuppliers({ page_size: 1 }),
  });

  const openAlerts = alertsData?.alerts.filter(
    a => a.status !== 'closed' && a.status !== 'resolved'
  ).length ?? 0;

  const criticalAlerts = alertsData?.alerts.filter(a => a.severity === 'critical').length ?? 0;

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">
            Good {getGreeting()}, {user?.full_name.split(' ')[0]}
          </h1>
          <p className="page__subtitle">
            {user?.organization_name} · Supply Chain Risk Overview
          </p>
        </div>
        <Link to="/suppliers/new" className="btn btn--primary">
          <Building2 size={16} /> Add Supplier
        </Link>
      </div>

      {/* KPI Stats — all from real API data */}
      <div className="stats-grid">
        <div className="stat-card">
          <p className="stat-card__label">Total Suppliers</p>
          <p className="stat-card__value">{suppliersData?.total ?? '—'}</p>
          <p className="stat-card__sub">Across all tiers</p>
        </div>
        <div className="stat-card">
          <p className="stat-card__label">Supply Relationships</p>
          <p className="stat-card__value">{tierSummary?.total_relationships ?? '—'}</p>
          <p className="stat-card__sub">Dependency edges in graph</p>
        </div>
        <div className="stat-card">
          <p className="stat-card__label">Open Alerts</p>
          <p className="stat-card__value" style={{ color: openAlerts > 0 ? 'var(--color-risk-high)' : 'inherit' }}>
            {openAlerts}
          </p>
          <p className="stat-card__sub">{criticalAlerts} critical</p>
        </div>
        <div className="stat-card">
          <p className="stat-card__label">Risk Events</p>
          <p className="stat-card__value">{riskEvents?.total ?? '—'}</p>
          <p className="stat-card__sub">Ingested from external sources</p>
        </div>
      </div>

      <div className="grid-2" style={{ alignItems: 'start' }}>
        {/* Tier Breakdown */}
        <div className="card">
          <div className="card__header">
            <span className="card__title">Supplier Tier Breakdown</span>
            <Link to="/graph" className="btn btn--secondary btn--sm">
              <Network size={13} /> View Graph
            </Link>
          </div>
          {tierSummary ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {[1, 2, 3, 4].map(tier => {
                const count = tierSummary.tier_breakdown?.[tier] ?? 0;
                const total = tierSummary.total_suppliers || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={tier}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span className="text-sm">
                        <span className={`badge badge--tier-${tier}`}>Tier {tier}</span>
                      </span>
                      <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                        {count} suppliers ({pct}%)
                      </span>
                    </div>
                    <div className="risk-score-bar">
                      <div
                        className="risk-score-bar__fill"
                        style={{
                          width: `${pct}%`,
                          background: tier === 1 ? 'var(--color-tier-1)' :
                            tier === 2 ? 'var(--color-tier-2)' :
                            tier === 3 ? 'var(--color-tier-3)' : 'var(--color-tier-4)',
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={<Network size={28} />}
              title="No suppliers yet"
              action={{ label: 'Add your first supplier', to: '/suppliers' }}
            />
          )}
        </div>

        {/* Active Alerts */}
        <div className="card">
          <div className="card__header">
            <span className="card__title">Recent Alerts</span>
            <Link to="/alerts" className="btn btn--secondary btn--sm">
              <Bell size={13} /> All alerts
            </Link>
          </div>
          {alertsData && alertsData.alerts.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
              {alertsData.alerts.slice(0, 5).map(alert => (
                <Link
                  key={alert.id}
                  to={`/alerts`}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)',
                    padding: 'var(--space-3) 0',
                    borderBottom: '1px solid var(--color-border)',
                    textDecoration: 'none',
                  }}
                >
                  <AlertTriangle
                    size={16}
                    style={{ marginTop: 2, flexShrink: 0 }}
                    color={alert.severity === 'critical' ? 'var(--color-risk-critical)' :
                      alert.severity === 'high' ? 'var(--color-risk-high)' :
                      alert.severity === 'medium' ? 'var(--color-risk-medium)' : 'var(--color-risk-low)'}
                  />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <p style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--color-text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {alert.title}
                    </p>
                    <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: 2 }}>
                      {alert.category} · {new Date(alert.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <RiskLevelBadge level={alert.severity as 'low' | 'medium' | 'high' | 'critical'} />
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState icon={<Bell size={28} />} title="No active alerts" />
          )}
        </div>
      </div>

      {/* Recent Risk Events */}
      <div className="card mt-4">
        <div className="card__header">
          <span className="card__title">External Risk Events</span>
          <Link to="/risk" className="btn btn--secondary btn--sm">
            <ShieldAlert size={13} /> Risk Intelligence
          </Link>
        </div>
        {riskEvents && riskEvents.events.length > 0 ? (
          <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Source</th>
                  <th>Category</th>
                  <th>Title</th>
                  <th>Severity</th>
                  <th>Countries</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {riskEvents.events.map((e: { id: string; source: string; category: string; title: string; severity: string; affected_countries?: string[]; event_date?: string }) => (
                  <tr key={e.id}>
                    <td><span className="font-mono text-sm">{e.source}</span></td>
                    <td><span style={{ textTransform: 'capitalize' }}>{e.category}</span></td>
                    <td style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.title}</td>
                    <td><RiskLevelBadge level={e.severity as 'low' | 'medium' | 'high' | 'critical'} /></td>
                    <td className="text-sm text-muted">{e.affected_countries?.join(', ') || '—'}</td>
                    <td className="text-sm text-muted">
                      {e.event_date ? new Date(e.event_date).toLocaleDateString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={<TrendingUp size={28} />}
            title="No risk events ingested yet"
            description="Risk events are populated by scheduled ingestion jobs (NOAA, GDELT, OpenWeather)"
          />
        )}
      </div>
    </div>
  );
}

function EmptyState({ icon, title, description, action }: {
  icon: React.ReactNode; title: string; description?: string;
  action?: { label: string; to: string };
}) {
  return (
    <div className="empty-state">
      <div style={{ color: 'var(--color-border-strong)', marginBottom: 'var(--space-3)' }}>{icon}</div>
      <p className="empty-state__title">{title}</p>
      {description && <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', marginTop: 4 }}>{description}</p>}
      {action && (
        <Link to={action.to} className="btn btn--secondary btn--sm" style={{ marginTop: 'var(--space-3)', display: 'inline-flex' }}>
          {action.label}
        </Link>
      )}
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}
