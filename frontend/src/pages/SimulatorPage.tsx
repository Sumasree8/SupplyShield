import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Zap, AlertTriangle } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/services/api';
import type { Supplier, DisruptionImpact } from '@/types';

export function SimulatorPage() {
  const [selectedId, setSelectedId] = useState('');
  const [result, setResult] = useState<DisruptionImpact | null>(null);

  const { data: suppliers } = useQuery({
    queryKey: ['suppliers-all'],
    queryFn: () => api.listSuppliers({ page_size: 100 }),
  });

  const simulate = useMutation({
    mutationFn: (id: string) => api.simulateDisruption(id),
    onSuccess: data => setResult(data),
    onError: () => toast.error('Simulation failed'),
  });

  const selectedSupplier = suppliers?.items.find((s: Supplier) => s.id === selectedId);

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Impact Simulator</h1>
          <p className="page__subtitle">Model the cascading effects of a supplier disruption across your supply chain</p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 'var(--space-4)' }}>
        <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Configure Simulation</p>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)', marginBottom: 'var(--space-4)' }}>
          Select a supplier to simulate what happens if they go offline. The simulator traverses the supply chain graph 
          to identify all downstream impacts based on your actual stored relationships.
        </p>
        <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <label className="form-label">Select supplier to disrupt</label>
            <select className="form-input" value={selectedId} onChange={e => { setSelectedId(e.target.value); setResult(null); }}>
              <option value="">Choose a supplier...</option>
              {suppliers?.items.map((s: Supplier) => (
                <option key={s.id} value={s.id}>
                  {s.name} (Tier {s.tier}, {s.country})
                </option>
              ))}
            </select>
          </div>
          <button
            className="btn btn--primary"
            onClick={() => simulate.mutate(selectedId)}
            disabled={!selectedId || simulate.isPending}
          >
            <Zap size={15} />
            {simulate.isPending ? 'Simulating...' : 'Run Simulation'}
          </button>
        </div>

        {selectedSupplier && (
          <div style={{
            marginTop: 'var(--space-4)', padding: 'var(--space-3)', background: 'var(--color-bg)',
            borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)'
          }}>
            <p style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{selectedSupplier.name}</p>
            <p className="text-muted">
              Tier {selectedSupplier.tier} · {selectedSupplier.country}
              {selectedSupplier.industry ? ` · ${selectedSupplier.industry}` : ''}
            </p>
          </div>
        )}
      </div>

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {/* Summary KPIs */}
          <div className="stats-grid">
            <div className="stat-card">
              <p className="stat-card__label">Total Affected</p>
              <p className="stat-card__value" style={{ color: result.total_affected > 0 ? 'var(--color-risk-high)' : 'inherit' }}>
                {result.total_affected}
              </p>
              <p className="stat-card__sub">downstream suppliers</p>
            </div>
            <div className="stat-card">
              <p className="stat-card__label">Disruption Radius</p>
              <p className="stat-card__value">{result.disruption_radius}</p>
              <p className="stat-card__sub">supply chain hops</p>
            </div>
            <div className="stat-card">
              <p className="stat-card__label">Critical Vulnerabilities</p>
              <p className="stat-card__value" style={{ color: result.sole_source_vulnerabilities.length > 0 ? 'var(--color-risk-critical)' : 'inherit' }}>
                {result.sole_source_vulnerabilities.length}
              </p>
              <p className="stat-card__sub">sole-source dependencies</p>
            </div>
          </div>

          {/* Critical vulnerabilities */}
          {result.sole_source_vulnerabilities.length > 0 && (
            <div className="card" style={{ borderLeft: '3px solid var(--color-risk-critical)' }}>
              <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', marginBottom: 'var(--space-3)' }}>
                <AlertTriangle size={16} color="var(--color-risk-critical)" />
                <p className="card__title" style={{ color: 'var(--color-risk-critical)' }}>
                  Critical: Sole-Source Vulnerabilities
                </p>
              </div>
              <p className="text-sm text-muted" style={{ marginBottom: 'var(--space-3)' }}>
                These suppliers have no alternative upstream source. Their operations will halt immediately.
              </p>
              {result.sole_source_vulnerabilities.map(v => (
                <div key={v.supplier_id} style={{ padding: 'var(--space-2) 0', borderBottom: '1px solid var(--color-border)' }}>
                  <p style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{v.name}</p>
                  <p className="text-muted">{v.reason}</p>
                </div>
              ))}
            </div>
          )}

          {/* Impact by tier */}
          {Object.keys(result.impact_by_tier).length > 0 ? (
            Object.entries(result.impact_by_tier)
              .sort(([a], [b]) => Number(a) - Number(b))
              .map(([tier, affected]) => (
                <div key={tier} className="card">
                  <div className="card__header">
                    <span className="card__title">
                      <span className={`badge badge--tier-${tier}`}>Tier {tier}</span>
                      {' '}— {(affected as unknown[]).length} supplier(s) affected
                    </span>
                  </div>
                  <div className="table-container" style={{ border: 'none' }}>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Supplier</th>
                          <th>Country</th>
                          <th>Distance from Disruption</th>
                          <th>Propagation Path</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(affected as Array<{ supplier_id: string; name: string; country: string; distance_from_disruption: number; propagation_path: string[] }>).map(s => (
                          <tr key={s.supplier_id}>
                            <td style={{ fontWeight: 500 }}>{s.name}</td>
                            <td>{s.country}</td>
                            <td>{s.distance_from_disruption} hop(s)</td>
                            <td>
                              <span className="font-mono text-sm text-muted">
                                {s.propagation_path.length} nodes in path
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))
          ) : (
            <div className="card">
              <p className="text-muted" style={{ textAlign: 'center', padding: 'var(--space-8)' }}>
                No downstream suppliers affected. This supplier may be a leaf node in the graph.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
