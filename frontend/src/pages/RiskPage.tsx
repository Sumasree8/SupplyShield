import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '@/services/api';
import { RiskLevelBadge } from '@/components/risk/RiskLevelBadge';

const CATEGORIES = ['', 'climate', 'geopolitical', 'operational', 'logistics', 'dependency'];

export function RiskPage() {
  const [category, setCategory] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['risk-events', category],
    queryFn: () => api.listRiskEvents({ category: category || undefined, limit: 100 }),
  });

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Risk Intelligence</h1>
          <p className="page__subtitle">External risk events ingested from NOAA, GDELT, OpenWeather, and logistics feeds</p>
        </div>
      </div>

      <div className="filters-bar mb-4" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)' }}>
        <select className="filter-select" value={category} onChange={e => setCategory(e.target.value)}>
          {CATEGORIES.map(c => (
            <option key={c} value={c}>{c ? c.charAt(0).toUpperCase() + c.slice(1) : 'All categories'}</option>
          ))}
        </select>
        <span className="text-muted text-sm" style={{ marginLeft: 'auto' }}>
          {data?.total ?? '—'} events
        </span>
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
              <th>Event Date</th>
              <th>Ingested</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={7} style={{ textAlign: 'center', padding: 40 }}><span className="loading-spinner" /></td></tr>
            ) : data?.events.length === 0 ? (
              <tr><td colSpan={7}>
                <div className="empty-state">
                  <p className="empty-state__title">No risk events ingested yet</p>
                  <p className="text-muted">
                    Risk events are populated by scheduled background jobs.<br />
                    Configure API keys for NOAA, GDELT, and OpenWeather to enable live ingestion.
                  </p>
                </div>
              </td></tr>
            ) : data?.events.map((e: {
              id: string; source: string; category: string; title: string;
              description?: string; severity: string; affected_countries?: string[];
              event_date?: string; ingested_at: string;
            }) => (
              <tr key={e.id}>
                <td><span className="font-mono text-sm">{e.source}</span></td>
                <td>
                  <span style={{
                    textTransform: 'capitalize', fontSize: 'var(--text-xs)', fontWeight: 600,
                    padding: '2px 8px', borderRadius: 100,
                    background: catBg(e.category), color: catColor(e.category),
                  }}>
                    {e.category}
                  </span>
                </td>
                <td>
                  <p style={{ fontWeight: 500, fontSize: 'var(--text-sm)' }}>{e.title}</p>
                  {e.description && (
                    <p className="text-muted" style={{ maxWidth: 380, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {e.description}
                    </p>
                  )}
                </td>
                <td><RiskLevelBadge level={e.severity} /></td>
                <td className="text-sm text-muted">{e.affected_countries?.join(', ') || '—'}</td>
                <td className="text-sm text-muted">
                  {e.event_date ? new Date(e.event_date).toLocaleDateString() : '—'}
                </td>
                <td className="text-sm text-muted">
                  {new Date(e.ingested_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function catColor(cat: string) {
  const map: Record<string, string> = {
    climate: '#0891b2', geopolitical: '#dc2626', operational: '#ea580c',
    logistics: '#7c3aed', dependency: '#ca8a04', financial: '#16a34a',
  };
  return map[cat] || '#6b7280';
}

function catBg(cat: string) {
  const map: Record<string, string> = {
    climate: '#ecfeff', geopolitical: '#fef2f2', operational: '#fff7ed',
    logistics: '#f5f3ff', dependency: '#fefce8', financial: '#f0fdf4',
  };
  return map[cat] || '#f9fafb';
}
