import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { ArrowLeft, Zap, ShieldAlert, Network, ExternalLink, Lightbulb } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/services/api';
import { RiskScorePanel } from '@/components/risk/RiskScorePanel';
import type { RiskScore, DisruptionImpact } from '@/types';

export function SupplierDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'overview' | 'risk' | 'impact' | 'dependencies' | 'alternatives'>('overview');

  const { data: supplier, isLoading } = useQuery({
    queryKey: ['supplier', id],
    queryFn: () => api.getSupplier(id!),
    enabled: !!id,
  });

  const scoreMutation = useMutation({
    mutationFn: () => api.calculateRiskScore(id!),
    onError: () => toast.error('Risk score calculation failed'),
  });

  const simulateMutation = useMutation({
    mutationFn: () => api.simulateDisruption(id!),
    onError: () => toast.error('Simulation failed'),
  });

  const { data: scoreHistory } = useQuery({
    queryKey: ['risk-history', id],
    queryFn: () => api.getRiskScoreHistory(id!, 5),
    enabled: !!id,
  });

  const { data: upstream } = useQuery({
    queryKey: ['upstream', id],
    queryFn: () => api.getUpstreamDependencies(id!),
    enabled: !!id && activeTab === 'dependencies',
  });

  const { data: alternatives, isLoading: altLoading } = useQuery({
    queryKey: ['alternatives', id],
    queryFn: () => api.getAlternativeSuppliers(id!, 5),
    enabled: !!id && activeTab === 'alternatives',
  });

  if (isLoading) {
    return <div className="page" style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}><span className="loading-spinner" /></div>;
  }
  if (!supplier) {
    return <div className="page"><p>Supplier not found. <Link to="/suppliers">Back to suppliers</Link></p></div>;
  }

  const latestScore: RiskScore | undefined = scoreMutation.data ?? scoreHistory?.history?.[0];

  return (
    <div className="page">
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <button className="btn btn--secondary btn--sm" onClick={() => navigate('/suppliers')}>
          <ArrowLeft size={14} /> Back to suppliers
        </button>
      </div>

      {/* Header */}
      <div className="page__header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
            <h1 className="page__title">{supplier.name}</h1>
            <span className={`badge badge--${supplier.status}`}>{supplier.status.replace('_', ' ')}</span>
            <span className={`badge badge--tier-${Math.min(supplier.tier, 4)}`}>Tier {supplier.tier}</span>
          </div>
          <p className="page__subtitle">
            {supplier.country}{supplier.city ? `, ${supplier.city}` : ''}
            {supplier.industry ? ` · ${supplier.industry}` : ''}
            {supplier.external_id ? ` · ID: ${supplier.external_id}` : ''}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
          <button
            className="btn btn--secondary"
            onClick={() => { scoreMutation.mutate(); setActiveTab('risk'); }}
            disabled={scoreMutation.isPending}
          >
            <ShieldAlert size={15} />
            {scoreMutation.isPending ? 'Calculating...' : 'Calculate Risk Score'}
          </button>
          <button
            className="btn btn--primary"
            onClick={() => { simulateMutation.mutate(); setActiveTab('impact'); }}
            disabled={simulateMutation.isPending}
          >
            <Zap size={15} />
            {simulateMutation.isPending ? 'Simulating...' : 'Simulate Disruption'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 0, borderBottom: '1px solid var(--color-border)', marginBottom: 'var(--space-5)' }}>
        {(['overview', 'risk', 'impact', 'dependencies'] as const).map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              padding: 'var(--space-3) var(--space-5)',
              fontSize: 'var(--text-sm)',
              fontWeight: activeTab === tab ? 600 : 400,
              color: activeTab === tab ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              borderBottom: activeTab === tab ? '2px solid var(--color-accent)' : '2px solid transparent',
              background: 'none',
              textTransform: 'capitalize',
              transition: 'color 0.1s',
            }}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="grid-2">
          <div className="card">
            <div className="card__header"><span className="card__title">Supplier Details</span></div>
            <DetailRow label="Legal Name" value={supplier.legal_name} />
            <DetailRow label="Country" value={supplier.country} />
            <DetailRow label="Region" value={supplier.region} />
            <DetailRow label="City" value={supplier.city} />
            <DetailRow label="Industry" value={supplier.industry} />
            <DetailRow label="Status" value={<span className={`badge badge--${supplier.status}`}>{supplier.status}</span>} />
            <DetailRow label="Annual Revenue" value={supplier.annual_revenue_usd ? `$${(supplier.annual_revenue_usd / 1_000_000).toFixed(1)}M` : null} />
            <DetailRow label="Employees" value={supplier.employee_count?.toLocaleString()} />
            <DetailRow label="Contact" value={supplier.contact_email} />
            {supplier.website && (
              <DetailRow label="Website" value={
                <a href={supplier.website} target="_blank" rel="noreferrer" style={{ color: 'var(--color-accent)', display: 'flex', alignItems: 'center', gap: 4 }}>
                  {supplier.website} <ExternalLink size={12} />
                </a>
              } />
            )}
          </div>
          <div className="card">
            <div className="card__header"><span className="card__title">Certifications</span></div>
            {supplier.certifications && Object.keys(supplier.certifications).length > 0 ? (
              Object.entries(supplier.certifications).map(([k, v]) => (
                <DetailRow key={k} label={k} value={String(v)} />
              ))
            ) : (
              <p className="text-muted">No certifications recorded</p>
            )}
            {supplier.notes && (
              <>
                <p className="card__title" style={{ marginTop: 'var(--space-4)' }}>Notes</p>
                <p className="text-sm" style={{ color: 'var(--color-text-secondary)', marginTop: 'var(--space-2)' }}>{supplier.notes}</p>
              </>
            )}
          </div>
        </div>
      )}

      {activeTab === 'risk' && (
        <div>
          {latestScore ? (
            <RiskScorePanel score={latestScore} history={scoreHistory?.history} />
          ) : (
            <div className="card">
              <div className="empty-state">
                <ShieldAlert size={32} style={{ color: 'var(--color-border-strong)' }} />
                <p className="empty-state__title">No risk score calculated yet</p>
                <p className="text-muted">Click "Calculate Risk Score" to generate an explainable risk assessment</p>
                <button className="btn btn--primary" style={{ marginTop: 'var(--space-4)', display: 'inline-flex' }} onClick={() => scoreMutation.mutate()}>
                  Calculate now
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'impact' && (
        <div>
          {simulateMutation.data ? (
            <DisruptionImpactPanel impact={simulateMutation.data} />
          ) : (
            <div className="card">
              <div className="empty-state">
                <Zap size={32} style={{ color: 'var(--color-border-strong)' }} />
                <p className="empty-state__title">No simulation run yet</p>
                <p className="text-muted">Click "Simulate Disruption" to model cascading supply chain impacts</p>
                <button className="btn btn--primary" style={{ marginTop: 'var(--space-4)', display: 'inline-flex' }} onClick={() => simulateMutation.mutate()}>
                  Run simulation
                </button>
              </div>
            </div>
          )}
        </div>
      )}


      {activeTab === 'alternatives' && (
        <div>
          <div className="card" style={{ marginBottom: 'var(--space-4)', borderLeft: '3px solid var(--color-accent)' }}>
            <p className="card__title" style={{ marginBottom: 'var(--space-1)' }}>Alternative Supplier Candidates</p>
            <p className="text-muted">
              Ranked alternatives based on geographic proximity, industry match, tier compatibility, and risk profile.
              All reasoning is explicit — no black-box suggestions.
            </p>
          </div>
          {altLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}><span className="loading-spinner" /></div>
          ) : alternatives && alternatives.recommendations.length > 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {alternatives.recommendations.map((rec: {
                supplier_id: string; name: string; country: string; tier: number;
                industry?: string; status: string; ranking_score: number;
                risk_level?: string; reasons: Array<{ factor: string; detail: string }>;
                caveats: string[];
              }, i: number) => (
                <div key={rec.supplier_id} className="card">
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-3)' }}>
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
                      background: 'var(--color-accent-light)', border: '1px solid #c3d4f8',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontWeight: 700, fontSize: 'var(--text-xs)', color: 'var(--color-accent)',
                    }}>#{i + 1}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', flexWrap: 'wrap' }}>
                        <Link to={`/suppliers/${rec.supplier_id}`} style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
                          {rec.name}
                        </Link>
                        <span className={`badge badge--tier-${Math.min(rec.tier, 4)}`}>Tier {rec.tier}</span>
                        <span className={`badge badge--${rec.status}`}>{rec.status}</span>
                        {rec.risk_level && <span className={`badge badge--${rec.risk_level}`}>{rec.risk_level} risk</span>}
                      </div>
                      <p className="text-muted" style={{ marginTop: 2 }}>
                        {rec.country}{rec.industry ? ` · ${rec.industry}` : ''}
                      </p>
                      <div style={{ marginTop: 'var(--space-2)', display: 'flex', flexWrap: 'wrap', gap: 'var(--space-2)' }}>
                        {rec.reasons.slice(0, 3).map((r, j) => (
                          <span key={j} style={{
                            fontSize: 'var(--text-xs)', padding: '2px 8px', borderRadius: 100,
                            background: '#f0fdf4', color: '#16a34a', fontWeight: 500,
                          }}>✓ {r.factor}</span>
                        ))}
                      </div>
                    </div>
                    <span style={{ fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--color-accent)', flexShrink: 0 }}>
                      {rec.ranking_score.toFixed(0)}pts
                    </span>
                  </div>
                </div>
              ))}
              <Link to="/recommendations" className="btn btn--secondary btn--sm" style={{ alignSelf: 'flex-start' }}>
                <Lightbulb size={13} /> Full Recommendations View
              </Link>
            </div>
          ) : (
            <div className="card">
              <div className="empty-state">
                <Lightbulb size={32} style={{ color: 'var(--color-border-strong)' }} />
                <p className="empty-state__title">No alternatives found</p>
                <p className="text-muted">Add more suppliers to your network to enable alternative sourcing analysis.</p>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'dependencies' && (
        <div className="card">
          <div className="card__header">
            <span className="card__title">Upstream Dependencies</span>
            <Link to="/graph" className="btn btn--secondary btn--sm"><Network size={13} /> View Full Graph</Link>
          </div>
          {upstream ? (
            upstream.dependencies.length > 0 ? (
              <div>
                <p className="text-sm text-muted" style={{ marginBottom: 'var(--space-4)' }}>
                  {upstream.total_dependencies} upstream supplier(s) found
                </p>
                <div className="table-container" style={{ border: 'none' }}>
                  <table className="table">
                    <thead>
                      <tr><th>Supplier</th><th>Tier</th><th>Country</th><th>Depth</th></tr>
                    </thead>
                    <tbody>
                      {upstream.dependencies.map((d: { supplier_id: string; name: string; tier: number; country: string; depth: number }) => (
                        <tr key={d.supplier_id}>
                          <td><Link to={`/suppliers/${d.supplier_id}`} style={{ color: 'var(--color-accent)' }}>{d.name}</Link></td>
                          <td><span className={`badge badge--tier-${Math.min(d.tier, 4)}`}>Tier {d.tier}</span></td>
                          <td>{d.country}</td>
                          <td className="text-muted">{d.depth} hop{d.depth !== 1 ? 's' : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <p className="text-muted">No upstream dependencies found. This may be a root supplier.</p>
            )
          ) : <span className="loading-spinner" />}
        </div>
      )}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  if (!value) return null;
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--space-2) 0', borderBottom: '1px solid var(--color-border)' }}>
      <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--color-text-primary)', textAlign: 'right' }}>{value}</span>
    </div>
  );
}

function DisruptionImpactPanel({ impact }: { impact: DisruptionImpact }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      <div className="stats-grid">
        <div className="stat-card">
          <p className="stat-card__label">Affected Suppliers</p>
          <p className="stat-card__value" style={{ color: impact.total_affected > 0 ? 'var(--color-risk-high)' : 'inherit' }}>
            {impact.total_affected}
          </p>
        </div>
        <div className="stat-card">
          <p className="stat-card__label">Disruption Radius</p>
          <p className="stat-card__value">{impact.disruption_radius}</p>
          <p className="stat-card__sub">max hops downstream</p>
        </div>
        <div className="stat-card">
          <p className="stat-card__label">Sole-Source Risks</p>
          <p className="stat-card__value" style={{ color: impact.sole_source_vulnerabilities.length > 0 ? 'var(--color-risk-critical)' : 'inherit' }}>
            {impact.sole_source_vulnerabilities.length}
          </p>
          <p className="stat-card__sub">no alternative source</p>
        </div>
      </div>

      {impact.sole_source_vulnerabilities.length > 0 && (
        <div className="card" style={{ borderColor: 'var(--color-risk-critical-bg)', borderLeftWidth: 3, borderLeftColor: 'var(--color-risk-critical)' }}>
          <p className="card__title" style={{ color: 'var(--color-risk-critical)', marginBottom: 'var(--space-3)' }}>
            ⚠ Sole-Source Vulnerabilities
          </p>
          {impact.sole_source_vulnerabilities.map(v => (
            <div key={v.supplier_id} style={{ padding: 'var(--space-2) 0', borderBottom: '1px solid var(--color-border)' }}>
              <p style={{ fontWeight: 500, fontSize: 'var(--text-sm)' }}>{v.name}</p>
              <p className="text-muted">{v.reason}</p>
            </div>
          ))}
        </div>
      )}

      {Object.entries(impact.impact_by_tier).map(([tier, suppliers]) => (
        <div key={tier} className="card">
          <div className="card__header">
            <span className="card__title">
              <span className={`badge badge--tier-${tier}`}>Tier {tier}</span> Impact — {(suppliers as unknown[]).length} supplier(s)
            </span>
          </div>
          <div className="table-container" style={{ border: 'none' }}>
            <table className="table">
              <thead>
                <tr><th>Supplier</th><th>Country</th><th>Distance</th></tr>
              </thead>
              <tbody>
                {(suppliers as Array<{ supplier_id: string; name: string; country: string; distance_from_disruption: number }>).map(s => (
                  <tr key={s.supplier_id}>
                    <td><Link to={`/suppliers/${s.supplier_id}`} style={{ color: 'var(--color-accent)' }}>{s.name}</Link></td>
                    <td>{s.country}</td>
                    <td className="text-muted">{s.distance_from_disruption} hop(s)</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
