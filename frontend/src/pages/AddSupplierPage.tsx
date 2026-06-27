import { useState, FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Building2 } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/services/api';

interface SupplierFormData {
  name: string;
  legal_name: string;
  country: string;
  region: string;
  city: string;
  tier: string;
  status: string;
  industry: string;
  annual_revenue_usd: string;
  employee_count: string;
  website: string;
  contact_email: string;
  external_id: string;
  latitude: string;
  longitude: string;
  notes: string;
}

const EMPTY: SupplierFormData = {
  name: '', legal_name: '', country: '', region: '', city: '',
  tier: '1', status: 'active', industry: '', annual_revenue_usd: '',
  employee_count: '', website: '', contact_email: '', external_id: '',
  latitude: '', longitude: '', notes: '',
};

const COUNTRIES = [
  'Australia', 'Brazil', 'Canada', 'China', 'France', 'Germany', 'India',
  'Indonesia', 'Italy', 'Japan', 'Malaysia', 'Mexico', 'Netherlands',
  'Philippines', 'Poland', 'Singapore', 'South Korea', 'Spain', 'Sweden',
  'Taiwan', 'Thailand', 'Turkey', 'United Kingdom', 'United States', 'Vietnam',
  'Other',
];

const INDUSTRIES = [
  'Aerospace & Defense', 'Automotive', 'Chemicals', 'Consumer Electronics',
  'Consumer Goods', 'Energy', 'Food & Beverage', 'Industrial Equipment',
  'Logistics & Transportation', 'Medical Devices', 'Metals & Mining',
  'Pharmaceuticals', 'Plastics & Rubber', 'Semiconductors',
  'Textiles & Apparel', 'Other',
];

export function AddSupplierPage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [form, setForm] = useState<SupplierFormData>(EMPTY);
  const [errors, setErrors] = useState<Partial<SupplierFormData>>({});

  const set = (field: keyof SupplierFormData) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      setForm(f => ({ ...f, [field]: e.target.value }));
      setErrors(err => ({ ...err, [field]: undefined }));
    };

  const validate = (): boolean => {
    const errs: Partial<SupplierFormData> = {};
    if (!form.name.trim()) errs.name = 'Supplier name is required';
    if (!form.country) errs.country = 'Country is required';
    if (!form.tier) errs.tier = 'Tier is required';
    if (form.contact_email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.contact_email)) {
      errs.contact_email = 'Invalid email address';
    }
    if (form.website && !/^https?:\/\/.+/.test(form.website)) {
      errs.website = 'Website must start with http:// or https://';
    }
    if (form.latitude && (isNaN(Number(form.latitude)) || Math.abs(Number(form.latitude)) > 90)) {
      errs.latitude = 'Latitude must be between -90 and 90';
    }
    if (form.longitude && (isNaN(Number(form.longitude)) || Math.abs(Number(form.longitude)) > 180)) {
      errs.longitude = 'Longitude must be between -180 and 180';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const createMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api.createSupplier(data),
    onSuccess: (supplier) => {
      qc.invalidateQueries({ queryKey: ['suppliers'] });
      qc.invalidateQueries({ queryKey: ['tier-summary'] });
      qc.invalidateQueries({ queryKey: ['graph-visualization'] });
      toast.success(`${supplier.name} added to your supply chain`);
      navigate(`/suppliers/${supplier.id}`);
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || 'Failed to create supplier');
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    const payload: Record<string, unknown> = {
      name: form.name.trim(),
      country: form.country,
      tier: Number(form.tier),
      status: form.status,
    };

    // Only include optional fields when provided
    if (form.legal_name.trim()) payload.legal_name = form.legal_name.trim();
    if (form.region.trim()) payload.region = form.region.trim();
    if (form.city.trim()) payload.city = form.city.trim();
    if (form.industry) payload.industry = form.industry;
    if (form.external_id.trim()) payload.external_id = form.external_id.trim();
    if (form.contact_email.trim()) payload.contact_email = form.contact_email.trim();
    if (form.website.trim()) payload.website = form.website.trim();
    if (form.notes.trim()) payload.notes = form.notes.trim();
    if (form.annual_revenue_usd) payload.annual_revenue_usd = Number(form.annual_revenue_usd) * 1_000_000;
    if (form.employee_count) payload.employee_count = Number(form.employee_count);
    if (form.latitude) payload.latitude = Number(form.latitude);
    if (form.longitude) payload.longitude = Number(form.longitude);

    createMutation.mutate(payload);
  };

  return (
    <div className="page" style={{ maxWidth: 860 }}>
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <Link to="/suppliers" className="btn btn--secondary btn--sm">
          <ArrowLeft size={14} /> Back to Suppliers
        </Link>
      </div>

      <div className="page__header">
        <div>
          <h1 className="page__title">Add Supplier</h1>
          <p className="page__subtitle">
            Register a new supply chain participant. Accurate tier and geography data improves risk scoring quality.
          </p>
        </div>
        <Building2 size={32} style={{ color: 'var(--color-border-strong)', flexShrink: 0 }} />
      </div>

      <form onSubmit={handleSubmit}>
        {/* ── Identity ── */}
        <section className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Identity</p>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="name">
                Supplier Name <span style={{ color: 'var(--color-risk-critical)' }}>*</span>
              </label>
              <input
                id="name" className={`form-input${errors.name ? ' form-input--error' : ''}`}
                value={form.name} onChange={set('name')}
                placeholder="e.g. Foxconn Technology Group"
              />
              {errors.name && <p className="form-error">{errors.name}</p>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="legal_name">Legal / Registered Name</label>
              <input id="legal_name" className="form-input" value={form.legal_name} onChange={set('legal_name')}
                placeholder="Full legal entity name" />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="external_id">External / ERP ID</label>
              <input id="external_id" className="form-input" value={form.external_id} onChange={set('external_id')}
                placeholder="SAP vendor code, ERP reference..." />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="industry">Industry</label>
              <select id="industry" className="form-input" value={form.industry} onChange={set('industry')}>
                <option value="">Select industry</option>
                {INDUSTRIES.map(i => <option key={i}>{i}</option>)}
              </select>
            </div>
          </div>
        </section>

        {/* ── Supply Chain Position ── */}
        <section className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Supply Chain Position</p>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="tier">
                Tier <span style={{ color: 'var(--color-risk-critical)' }}>*</span>
              </label>
              <select id="tier" className="form-input" value={form.tier} onChange={set('tier')}>
                <option value="1">Tier 1 — Direct supplier (you buy directly from them)</option>
                <option value="2">Tier 2 — Supplier's supplier</option>
                <option value="3">Tier 3 — Sub-tier component supplier</option>
                <option value="4">Tier 4+ — Raw material / commodity</option>
              </select>
              {errors.tier && <p className="form-error">{errors.tier}</p>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="status">Status</label>
              <select id="status" className="form-input" value={form.status} onChange={set('status')}>
                <option value="active">Active</option>
                <option value="under_review">Under Review</option>
                <option value="inactive">Inactive</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>
          </div>

          <div
            style={{
              padding: 'var(--space-3)',
              background: 'var(--color-accent-light)',
              borderRadius: 'var(--radius-md)',
              fontSize: 'var(--text-sm)',
              color: 'var(--color-accent)',
              marginTop: 'var(--space-2)',
            }}
          >
            After adding this supplier, go to <strong>Supply Graph → Add Relationship</strong> to
            connect them to other suppliers in your network.
          </div>
        </section>

        {/* ── Geography ── */}
        <section className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <p className="card__title" style={{ marginBottom: 'var(--space-1)' }}>Geography</p>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-4)' }}>
            Accurate location data enables climate and geopolitical risk matching against external event feeds.
          </p>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="country">
                Country <span style={{ color: 'var(--color-risk-critical)' }}>*</span>
              </label>
              <select id="country" className="form-input" value={form.country} onChange={set('country')}>
                <option value="">Select country</option>
                {COUNTRIES.map(c => <option key={c}>{c}</option>)}
              </select>
              {errors.country && <p className="form-error">{errors.country}</p>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="region">Region / State / Province</label>
              <input id="region" className="form-input" value={form.region} onChange={set('region')}
                placeholder="e.g. Guangdong, Bavaria, Texas" />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="city">City</label>
              <input id="city" className="form-input" value={form.city} onChange={set('city')}
                placeholder="e.g. Shenzhen" />
            </div>

            <div className="form-group" style={{ display: 'none' /* revealed below */ }} />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="latitude">Latitude</label>
              <input id="latitude" className="form-input" type="number" step="any"
                value={form.latitude} onChange={set('latitude')} placeholder="e.g. 22.5431" />
              {errors.latitude && <p className="form-error">{errors.latitude}</p>}
            </div>
            <div className="form-group">
              <label className="form-label" htmlFor="longitude">Longitude</label>
              <input id="longitude" className="form-input" type="number" step="any"
                value={form.longitude} onChange={set('longitude')} placeholder="e.g. 114.0579" />
              {errors.longitude && <p className="form-error">{errors.longitude}</p>}
            </div>
          </div>
        </section>

        {/* ── Business Details ── */}
        <section className="card" style={{ marginBottom: 'var(--space-4)' }}>
          <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>Business Details</p>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label" htmlFor="annual_revenue_usd">Annual Revenue (USD millions)</label>
              <input id="annual_revenue_usd" className="form-input" type="number" min="0" step="0.1"
                value={form.annual_revenue_usd} onChange={set('annual_revenue_usd')}
                placeholder="e.g. 450 (= $450M)" />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="employee_count">Employee Count</label>
              <input id="employee_count" className="form-input" type="number" min="0"
                value={form.employee_count} onChange={set('employee_count')}
                placeholder="e.g. 12000" />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="contact_email">Contact Email</label>
              <input id="contact_email" className="form-input" type="email"
                value={form.contact_email} onChange={set('contact_email')}
                placeholder="procurement@supplier.com" />
              {errors.contact_email && <p className="form-error">{errors.contact_email}</p>}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="website">Website</label>
              <input id="website" className="form-input" type="url"
                value={form.website} onChange={set('website')}
                placeholder="https://www.supplier.com" />
              {errors.website && <p className="form-error">{errors.website}</p>}
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="notes">Notes</label>
            <textarea id="notes" className="form-input" value={form.notes} onChange={set('notes')}
              rows={3} placeholder="Relationship history, special terms, quality notes..."
              style={{ resize: 'vertical' }} />
          </div>
        </section>

        {/* ── Actions ── */}
        <div style={{ display: 'flex', gap: 'var(--space-3)', justifyContent: 'flex-end' }}>
          <Link to="/suppliers" className="btn btn--secondary">Cancel</Link>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={createMutation.isPending}
          >
            {createMutation.isPending ? (
              <><span className="loading-spinner" /> Creating...</>
            ) : (
              <><Building2 size={15} /> Add Supplier</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
