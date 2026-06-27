import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api } from '@/services/api';
import type { SupplierRiskScore } from '@/types';
import { RiskLevelBadge } from '@/components/risk/RiskLevelBadge';

export function RiskPage() {
  const { data: scoreData, isLoading: scoresLoading } = useQuery({
    queryKey: ['risk-scores'],
    queryFn: () => api.listLatestRiskScores(),
  });

  const { data: eventData, isLoading: eventsLoading } = useQuery({
    queryKey: ['risk-events'],
    queryFn: () => api.listRiskEvents({ limit: 100 }),
  });

  const scores = scoreData?.scores ?? [];

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Risk Intelligence</h1>
          <p className="page__subtitle">
            Explainable composite risk scores per supplier, plus external risk events as they are ingested.
          </p>
        </div>
      </div>

      {/* ── Computed supplier risk scores ───────────────────────────────── */}
      <div className="card" style={{ marginBottom: 'var(--space-5)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
          <p className="card__title">Supplier Risk Scores</p>
          <span className="text-muted text-sm">{scores.length} scored suppliers</span>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Supplier</th>
                <th>Tier</th>
                <th>Country</th>
                <th>Overall</th>
                <th>Level</th>
                <th>Climate</th>
                <th>Geopolitical</th>
                <th>Operational</th>
                <th>Logistics</th>
                <th>Dependency</th>
              </tr>
            </thead>
            <tbody>
              {scoresLoading ? (
                <tr><td colSpan={10} style={{ textAlign: 'center', padding: 40 }}><span className="loading-spinner" /></td></tr>
              ) : scores.length === 0 ? (
                <tr><td colSpan={10}>
                  <div className="empty-state">
                    <p className="empty-state__title">No risk scores yet</p>
                    <p className="text-muted">
                      Open a supplier and run “Calculate Risk Score”, or seed the demo data
                      (<span className="font-mono">scripts/seed_demo.py</span>) to populate scores.
                    </p>
                  </div>
                </td></tr>
              ) : scores.map((s: SupplierRiskScore) => (
                <tr key={s.supplier_id}>
                  <td>
                    <Link to={`/suppliers/${s.supplier_id}`} style={{ fontWeight: 500, color: 'var(--color-accent)' }}>
                      {s.supplier_name}
                    </Link>
                  </td>
                  <td><span className={`badge badge--tier-${Math.min(s.tier, 4)}`}>Tier {s.tier}</span></td>
                  <td className="text-sm text-muted">{s.country}</td>
                  <td style={{ fontWeight: 700 }}>{s.overall_score.toFixed(1)}</td>
                  <td><RiskLevelBadge level={s.risk_level} /></td>
                  <td className="text-sm text-muted">{fmt(s.climate_score)}</td>
                  <td className="text-sm text-muted">{fmt(s.geopolitical_score)}</td>
                  <td className="text-sm text-muted">{fmt(s.operational_score)}</td>
                  <td className="text-sm text-muted">{fmt(s.logistics_score)}</td>
                  <td className="text-sm text-muted">{fmt(s.dependency_score)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── External ingested risk events ───────────────────────────────── */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
          <p className="card__title">External Risk Events</p>
          <span className="text-muted text-sm">{eventData?.total ?? '—'} events</span>
        </div>

        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Category</th>
                <th>Title</th>
                <th>Severity</th>
                <th>Affected Countries</th>
                <th>Ingested</th>
              </tr>
            </thead>
            <tbody>
              {eventsLoading ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40 }}><span className="loading-spinner" /></td></tr>
              ) : (eventData?.events?.length ?? 0) === 0 ? (
                <tr><td colSpan={6}>
                  <div className="empty-state">
                    <p className="empty-state__title">No external events ingested yet</p>
                    <p className="text-muted">
                      Events are populated by scheduled jobs — configure NOAA / GDELT / OpenWeather
                      API keys and run the Celery workers to enable live ingestion.
                    </p>
                  </div>
                </td></tr>
              ) : eventData.events.map((e: {
                id: string; source: string; category: string; title: string;
                severity: string; affected_countries?: string[]; ingested_at: string;
              }) => (
                <tr key={e.id}>
                  <td><span className="font-mono text-sm">{e.source}</span></td>
                  <td style={{ textTransform: 'capitalize' }}>{e.category}</td>
                  <td style={{ fontWeight: 500, fontSize: 'var(--text-sm)' }}>{e.title}</td>
                  <td><RiskLevelBadge level={e.severity} /></td>
                  <td className="text-sm text-muted">{e.affected_countries?.join(', ') || '—'}</td>
                  <td className="text-sm text-muted">{new Date(e.ingested_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function fmt(v: number | null): string {
  return v === null || v === undefined ? '—' : v.toFixed(0);
}
