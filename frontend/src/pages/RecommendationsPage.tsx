import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Lightbulb, ChevronDown, ChevronUp, ExternalLink, AlertTriangle } from 'lucide-react';
import { api } from '@/services/api';
import type { Supplier } from '@/types';
import { RiskLevelBadge } from '@/components/risk/RiskLevelBadge';

export function RecommendationsPage() {
  const [selectedSupplierId, setSelectedSupplierId] = useState('');
  const [maxResults, setMaxResults] = useState(10);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: suppliers } = useQuery({
    queryKey: ['suppliers-all-for-rec'],
    queryFn: () => api.listSuppliers({ page_size: 100 }),
  });

  // Auto-select the first supplier so recommendations are shown immediately
  // rather than presenting a blank page on first load.
  useEffect(() => {
    if (!selectedSupplierId && suppliers?.items?.length) {
      setSelectedSupplierId(suppliers.items[0].id);
    }
  }, [suppliers, selectedSupplierId]);

  const { data: recommendations, isLoading, isFetching } = useQuery({
    queryKey: ['recommendations', selectedSupplierId, maxResults],
    queryFn: () => api.getAlternativeSuppliers(selectedSupplierId, maxResults),
    enabled: !!selectedSupplierId,
  });

  const selectedSupplier = suppliers?.items.find((s: Supplier) => s.id === selectedSupplierId);

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Alternative Supplier Recommendations</h1>
          <p className="page__subtitle">
            Identify qualified replacement candidates based on geography, industry, tier, and risk profile.
            All recommendations are explainable — no black-box suggestions.
          </p>
        </div>
        <Lightbulb size={32} style={{ color: 'var(--color-border-strong)', flexShrink: 0 }} />
      </div>

      {/* Configuration */}
      <div className="card" style={{ marginBottom: 'var(--space-5)' }}>
        <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Find Alternatives For</p>
        <div style={{ display: 'flex', gap: 'var(--space-4)', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 280 }}>
            <label className="form-label">Target supplier (the one to replace or backup)</label>
            <select
              className="form-input"
              value={selectedSupplierId}
              onChange={e => setSelectedSupplierId(e.target.value)}
            >
              <option value="">Choose a supplier…</option>
              {suppliers?.items.map((s: Supplier) => (
                <option key={s.id} value={s.id}>
                  {s.name} — Tier {s.tier}, {s.country}
                </option>
              ))}
            </select>
          </div>
          <div style={{ minWidth: 160 }}>
            <label className="form-label">Max results</label>
            <select
              className="form-input"
              value={maxResults}
              onChange={e => setMaxResults(Number(e.target.value))}
            >
              {[5, 10, 20, 50].map(n => <option key={n} value={n}>{n} results</option>)}
            </select>
          </div>
        </div>

        {selectedSupplier && (
          <div style={{
            marginTop: 'var(--space-4)', padding: 'var(--space-3)',
            background: 'var(--color-bg)', borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-border)',
            display: 'flex', gap: 'var(--space-4)', alignItems: 'center', flexWrap: 'wrap',
          }}>
            <div>
              <p style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{selectedSupplier.name}</p>
              <p className="text-muted">{selectedSupplier.country}{selectedSupplier.city ? `, ${selectedSupplier.city}` : ''}</p>
            </div>
            <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
              <span className={`badge badge--tier-${Math.min(selectedSupplier.tier, 4)}`}>
                Tier {selectedSupplier.tier}
              </span>
              <span className={`badge badge--${selectedSupplier.status}`}>
                {selectedSupplier.status}
              </span>
            </div>
            {selectedSupplier.industry && (
              <span className="text-sm text-muted">{selectedSupplier.industry}</span>
            )}
          </div>
        )}
      </div>

      {/* Methodology note */}
      {selectedSupplierId && (
        <div style={{
          padding: 'var(--space-3) var(--space-4)',
          background: 'var(--color-accent-light)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid #c3d4f8',
          marginBottom: 'var(--space-4)',
          fontSize: 'var(--text-sm)',
          color: 'var(--color-accent)',
        }}>
          <strong>Methodology:</strong> Candidates ranked by geographic proximity (30pts), industry match (25pts),
          tier compatibility (20pts), operational status (15pts), and risk profile (10pts).
          Suppliers already in a direct dependency relationship are excluded.
          Only real stored data is used — no assumptions or estimates.
        </div>
      )}

      {/* Results */}
      {isLoading || isFetching ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-12)' }}>
          <span className="loading-spinner" />
        </div>
      ) : recommendations ? (
        <div>
          <div style={{
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            marginBottom: 'var(--space-4)',
          }}>
            <p className="text-sm text-muted">
              {recommendations.total_matches} candidate(s) found from{' '}
              {recommendations.total_candidates_evaluated} evaluated
            </p>
          </div>

          {recommendations.recommendations.length === 0 ? (
            <div className="card">
              <div className="empty-state">
                <Lightbulb size={36} style={{ color: 'var(--color-border-strong)' }} />
                <p className="empty-state__title">No alternatives found</p>
                <p className="text-muted">
                  Add more suppliers to your network to enable alternative sourcing analysis.
                  Candidates require active status and at least some attribute overlap with the target.
                </p>
                <Link to="/suppliers/new" className="btn btn--primary" style={{ marginTop: 'var(--space-4)', display: 'inline-flex' }}>
                  Add Suppliers
                </Link>
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
              {recommendations.recommendations.map((rec: RecommendationResult, index: number) => (
                <RecommendationCard
                  key={rec.supplier_id}
                  rec={rec}
                  rank={index + 1}
                  expanded={expandedId === rec.supplier_id}
                  onToggle={() => setExpandedId(expandedId === rec.supplier_id ? null : rec.supplier_id)}
                />
              ))}
            </div>
          )}
        </div>
      ) : selectedSupplierId ? null : (
        <div className="card">
          <div className="empty-state">
            <Lightbulb size={36} style={{ color: 'var(--color-border-strong)' }} />
            <p className="empty-state__title">Select a supplier to find alternatives</p>
            <p className="text-muted">
              Choose a target supplier above to see ranked alternative candidates with full reasoning.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

interface RecommendationResult {
  supplier_id: string;
  name: string;
  country: string;
  region?: string;
  city?: string;
  tier: number;
  industry?: string;
  status: string;
  employee_count?: number;
  annual_revenue_usd?: number;
  certifications?: Record<string, string>;
  contact_email?: string;
  website?: string;
  ranking_score: number;
  latest_risk_score?: number;
  risk_level?: string;
  reasons: Array<{ factor: string; weight: number; detail: string }>;
  caveats: string[];
}

function RecommendationCard({
  rec, rank, expanded, onToggle,
}: {
  rec: RecommendationResult;
  rank: number;
  expanded: boolean;
  onToggle: () => void;
}) {
  const maxScore = 100;
  const scorePercent = Math.min(100, (rec.ranking_score / maxScore) * 100);

  return (
    <div
      className="card"
      style={{
        borderLeft: rank <= 3 ? '3px solid var(--color-accent)' : '1px solid var(--color-border)',
        transition: 'box-shadow 0.15s',
      }}
    >
      {/* Header row */}
      <div
        style={{ display: 'flex', alignItems: 'flex-start', gap: 'var(--space-4)', cursor: 'pointer' }}
        onClick={onToggle}
      >
        {/* Rank badge */}
        <div style={{
          width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
          background: rank === 1 ? '#fef3c7' : rank === 2 ? '#f1f5f9' : 'var(--color-bg)',
          border: '1px solid var(--color-border)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)',
        }}>
          #{rank}
        </div>

        {/* Supplier info */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <p style={{ fontWeight: 600, fontSize: 'var(--text-md)' }}>{rec.name}</p>
            <span className={`badge badge--tier-${Math.min(rec.tier, 4)}`}>Tier {rec.tier}</span>
            <span className={`badge badge--${rec.status}`}>{rec.status}</span>
            {rec.risk_level && <RiskLevelBadge level={rec.risk_level} />}
          </div>
          <p className="text-muted" style={{ marginTop: 2 }}>
            {rec.country}{rec.city ? `, ${rec.city}` : ''}{rec.industry ? ` · ${rec.industry}` : ''}
          </p>

          {/* Score bar */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginTop: 'var(--space-2)' }}>
            <div className="risk-score-bar" style={{ flex: 1, height: 6 }}>
              <div
                className="risk-score-bar__fill"
                style={{
                  width: `${scorePercent}%`,
                  background: rank === 1 ? 'var(--color-accent)' : rank <= 3 ? '#7c3aed' : 'var(--color-tier-3)',
                }}
              />
            </div>
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-secondary)', flexShrink: 0 }}>
              {rec.ranking_score.toFixed(0)} pts
            </span>
          </div>
        </div>

        {/* Top reasons preview */}
        <div style={{ minWidth: 200, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {rec.reasons.slice(0, 2).map((r, i) => (
            <div key={i} style={{
              fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)',
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              <span style={{ color: '#16a34a', fontWeight: 700 }}>✓</span> {r.factor}
            </div>
          ))}
          {rec.caveats.length > 0 && (
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-risk-medium)', display: 'flex', alignItems: 'center', gap: 4 }}>
              <AlertTriangle size={11} /> {rec.caveats.length} caveat{rec.caveats.length > 1 ? 's' : ''}
            </div>
          )}
        </div>

        <button style={{ flexShrink: 0, color: 'var(--color-text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}>
          {expanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ marginTop: 'var(--space-4)', paddingTop: 'var(--space-4)', borderTop: '1px solid var(--color-border)' }}>
          <div className="grid-2" style={{ gap: 'var(--space-5)' }}>
            {/* Reasons */}
            <div>
              <p className="card__title" style={{ marginBottom: 'var(--space-3)' }}>Why This Candidate</p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)' }}>
                {rec.reasons.map((r, i) => (
                  <div key={i} style={{
                    padding: 'var(--space-2) var(--space-3)',
                    background: 'var(--color-bg)',
                    borderRadius: 'var(--radius-md)',
                    borderLeft: '3px solid #16a34a',
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <p style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{r.factor}</p>
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                        +{Math.round(r.weight * 100)}pts
                      </span>
                    </div>
                    <p className="text-muted">{r.detail}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Caveats + Supplier details */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {rec.caveats.length > 0 && (
                <div>
                  <p className="card__title" style={{ marginBottom: 'var(--space-3)' }}>Caveats</p>
                  {rec.caveats.map((c, i) => (
                    <div key={i} style={{
                      padding: 'var(--space-2) var(--space-3)',
                      background: 'var(--color-risk-medium-bg)',
                      borderRadius: 'var(--radius-md)',
                      borderLeft: '3px solid var(--color-risk-medium)',
                      marginBottom: 'var(--space-2)',
                      fontSize: 'var(--text-sm)',
                      color: 'var(--color-text-secondary)',
                      display: 'flex', gap: 'var(--space-2)',
                    }}>
                      <AlertTriangle size={14} style={{ color: 'var(--color-risk-medium)', flexShrink: 0, marginTop: 1 }} />
                      {c}
                    </div>
                  ))}
                </div>
              )}

              <div>
                <p className="card__title" style={{ marginBottom: 'var(--space-3)' }}>Supplier Details</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {rec.employee_count && (
                    <DetailItem label="Employees" value={rec.employee_count.toLocaleString()} />
                  )}
                  {rec.annual_revenue_usd && (
                    <DetailItem label="Revenue" value={`$${(rec.annual_revenue_usd / 1_000_000).toFixed(1)}M`} />
                  )}
                  {rec.latest_risk_score !== undefined && rec.latest_risk_score !== null && (
                    <DetailItem label="Risk Score" value={`${rec.latest_risk_score}/100`} />
                  )}
                  {rec.certifications && Object.keys(rec.certifications).length > 0 && (
                    <DetailItem label="Certifications" value={Object.keys(rec.certifications).join(', ')} />
                  )}
                  {rec.contact_email && (
                    <DetailItem label="Contact" value={rec.contact_email} />
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 'var(--space-2)', marginTop: 'var(--space-4)', paddingTop: 'var(--space-3)', borderTop: '1px solid var(--color-border)' }}>
            <Link to={`/suppliers/${rec.supplier_id}`} className="btn btn--secondary btn--sm">
              View Full Profile
            </Link>
            <Link to={`/suppliers/${rec.supplier_id}`} state={{ startRiskCalc: true }} className="btn btn--secondary btn--sm">
              <ExternalLink size={13} /> Calculate Risk Score
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

function DetailItem({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-sm)' }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
      <span style={{ fontWeight: 500 }}>{value}</span>
    </div>
  );
}
