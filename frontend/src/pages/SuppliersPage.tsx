import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { Plus, Search, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/services/api';
import { RiskLevelBadge } from '@/components/risk/RiskLevelBadge';
import type { Supplier } from '@/types';

export function SuppliersPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [tier, setTier] = useState('');
  const [status, setStatus] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['suppliers', page, search, tier, status],
    queryFn: () => api.listSuppliers({
      page, page_size: 20,
      search: search || undefined,
      tier: tier ? Number(tier) : undefined,
      status: status || undefined,
    }),
    placeholderData: prev => prev,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteSupplier(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['suppliers'] });
      toast.success('Supplier removed');
    },
    onError: () => toast.error('Could not remove supplier'),
  });

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">Suppliers</h1>
          <p className="page__subtitle">Manage your supply chain participants across all tiers</p>
        </div>
        <Link to="/suppliers/new" className="btn btn--primary">
          <Plus size={16} /> Add Supplier
        </Link>
      </div>

      {/* Filters */}
      <div className="filters-bar mb-4" style={{ borderRadius: 'var(--radius-lg)', border: '1px solid var(--color-border)' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 200 }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--color-text-muted)' }} />
          <input
            className="form-input"
            style={{ paddingLeft: 32 }}
            placeholder="Search suppliers..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
        <select className="filter-select" value={tier} onChange={e => { setTier(e.target.value); setPage(1); }}>
          <option value="">All tiers</option>
          <option value="1">Tier 1</option>
          <option value="2">Tier 2</option>
          <option value="3">Tier 3</option>
          <option value="4">Tier 4+</option>
        </select>
        <select className="filter-select" value={status} onChange={e => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="under_review">Under Review</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Tier</th>
              <th>Country</th>
              <th>Industry</th>
              <th>Status</th>
              <th>Risk</th>
              <th>Annual Revenue</th>
              <th style={{ width: 60 }}></th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40 }}><span className="loading-spinner" /></td></tr>
            ) : data?.items.length === 0 ? (
              <tr><td colSpan={8} style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-muted)' }}>
                No suppliers found. <Link to="/suppliers/new" style={{ color: 'var(--color-accent)' }}>Add one</Link>
              </td></tr>
            ) : data?.items.map((s: Supplier) => (
              <tr
                key={s.id}
                className="clickable"
                onClick={() => navigate(`/suppliers/${s.id}`)}
              >
                <td>
                  <p style={{ fontWeight: 500 }}>{s.name}</p>
                  {s.external_id && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>ID: {s.external_id}</p>}
                </td>
                <td><span className={`badge badge--tier-${Math.min(s.tier, 4)}`}>Tier {s.tier}</span></td>
                <td>{s.country}{s.city ? `, ${s.city}` : ''}</td>
                <td className="text-muted">{s.industry || '—'}</td>
                <td><span className={`badge badge--${s.status}`}>{s.status.replace('_', ' ')}</span></td>
                <td><SupplierRiskCell supplierId={s.id} /></td>
                <td className="text-sm">
                  {s.annual_revenue_usd ? `$${(s.annual_revenue_usd / 1_000_000).toFixed(1)}M` : '—'}
                </td>
                <td onClick={e => e.stopPropagation()}>
                  <button
                    className="btn btn--secondary btn--sm"
                    onClick={() => {
                      if (confirm(`Remove ${s.name}?`)) deleteMutation.mutate(s.id);
                    }}
                    aria-label={`Remove ${s.name}`}
                  >
                    <Trash2 size={13} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {data && data.total_pages > 1 && (
          <div className="pagination">
            <span className="pagination__info">
              Showing {((page - 1) * 20) + 1}–{Math.min(page * 20, data.total)} of {data.total}
            </span>
            <div className="pagination__controls">
              <button className="btn btn--secondary btn--sm" onClick={() => setPage(p => p - 1)} disabled={page === 1}>
                <ChevronLeft size={14} />
              </button>
              <button className="btn btn--secondary btn--sm" onClick={() => setPage(p => p + 1)} disabled={page >= data.total_pages}>
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SupplierRiskCell({ supplierId }: { supplierId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['risk-history', supplierId, 'compact'],
    queryFn: () => api.getRiskScoreHistory(supplierId, 1),
    staleTime: 60_000,
  });

  if (isLoading) {
    return <span className="text-muted text-sm">…</span>;
  }

  const latest = data?.history?.[0];
  if (!latest) {
    return <span className="text-muted text-sm">Not assessed</span>;
  }

  return <RiskLevelBadge level={latest.risk_level} />;
}
