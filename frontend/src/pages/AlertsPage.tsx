import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import { RiskLevelBadge } from '@/components/risk/RiskLevelBadge';
import toast from 'react-hot-toast';

const STATUSES = ['', 'created', 'assigned', 'investigating', 'resolved', 'closed'];
const SEVERITIES = ['', 'critical', 'high', 'medium', 'low'];

export function AlertsPage() {
  const qc = useQueryClient();
  const [severity, setSeverity] = useState('');
  const [status, setStatus] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['alerts', severity, status],
    queryFn: () => api.listAlerts({
      severity: severity || undefined,
      status: status || undefined,
      limit: 100,
    }),
  });

  const { data: detail } = useQuery({
    queryKey: ['alert-detail', selectedId],
    queryFn: () => api.getAlert(selectedId!),
    enabled: !!selectedId,
  });

  const statusMutation = useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: string; notes?: string }) =>
      api.updateAlertStatus(id, status, notes),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alerts'] });
      qc.invalidateQueries({ queryKey: ['alert-detail', selectedId] });
      toast.success('Alert status updated');
    },
    onError: () => toast.error('Failed to update alert status'),
  });

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Early Warning Alerts</h1>
          <p className="page__subtitle">Monitor and manage supply chain risk escalations</p>
        </div>
      </div>

      <div className="filters-bar mb-4" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)' }}>
        <select className="filter-select" value={severity} onChange={e => setSeverity(e.target.value)}>
          {SEVERITIES.map(s => <option key={s} value={s}>{s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All severities'}</option>)}
        </select>
        <select className="filter-select" value={status} onChange={e => setStatus(e.target.value)}>
          {STATUSES.map(s => <option key={s} value={s}>{s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All statuses'}</option>)}
        </select>
        <span className="text-muted text-sm" style={{ marginLeft: 'auto' }}>{data?.total ?? '—'} alerts</span>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-start' }}>
        {/* Alert list */}
        <div className="table-container" style={{ flex: 1 }}>
          <table className="table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', padding: 40 }}><span className="loading-spinner" /></td></tr>
              ) : data?.alerts.length === 0 ? (
                <tr><td colSpan={5}>
                  <div className="empty-state">
                    <p className="empty-state__title">No alerts</p>
                    <p className="text-muted">Alerts are created automatically when risk thresholds are breached</p>
                  </div>
                </td></tr>
              ) : data?.alerts.map(a => (
                <tr
                  key={a.id}
                  className="clickable"
                  onClick={() => setSelectedId(selectedId === a.id ? null : a.id)}
                  style={{ background: selectedId === a.id ? 'var(--color-accent-light)' : undefined }}
                >
                  <td>
                    <p style={{ fontWeight: 500 }}>{a.title}</p>
                    <p className="text-muted">{a.trigger_type}</p>
                  </td>
                  <td style={{ textTransform: 'capitalize' }}>{a.category}</td>
                  <td><RiskLevelBadge level={a.severity} /></td>
                  <td><span className={`status-badge status-badge--${a.status}`}>{a.status}</span></td>
                  <td className="text-muted">{new Date(a.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Alert detail */}
        {selectedId && detail && (
          <div className="card" style={{ width: 320, flexShrink: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-3)' }}>
              <p className="card__title">Alert Detail</p>
              <button className="btn btn--secondary btn--sm" onClick={() => setSelectedId(null)}>✕</button>
            </div>

            <p style={{ fontWeight: 600, marginBottom: 'var(--space-2)' }}>{detail.title}</p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-3)' }}>{detail.description}</p>

            <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', marginBottom: 'var(--space-4)' }}>
              <RiskLevelBadge level={detail.severity} />
              <span className={`status-badge status-badge--${detail.status}`}>{detail.status}</span>
            </div>

            {/* Status transitions */}
            <p className="card__title" style={{ marginBottom: 'var(--space-3)' }}>Update Status</p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)', marginBottom: 'var(--space-4)' }}>
              {NEXT_STATUSES[detail.status]?.map(next => (
                <button
                  key={next}
                  className="btn btn--secondary btn--sm"
                  onClick={() => statusMutation.mutate({ id: detail.id, status: next })}
                  disabled={statusMutation.isPending}
                >
                  → {next}
                </button>
              ))}
            </div>

            {/* Status history */}
            <p className="card__title" style={{ marginBottom: 'var(--space-2)' }}>Status History</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {detail.status_history?.map((h: { from_status?: string; to_status: string; notes?: string; changed_at: string }, i: number) => (
                <div key={i} style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>
                  <span style={{ fontWeight: 500 }}>
                    {h.from_status ? `${h.from_status} → ` : ''}{h.to_status}
                  </span>
                  <span style={{ float: 'right', color: 'var(--color-text-muted)' }}>
                    {new Date(h.changed_at).toLocaleDateString()}
                  </span>
                  {h.notes && <p>{h.notes}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const NEXT_STATUSES: Record<string, string[]> = {
  created: ['assigned', 'closed'],
  assigned: ['investigating', 'resolved', 'closed'],
  investigating: ['resolved', 'closed'],
  resolved: ['closed'],
  closed: [],
};
