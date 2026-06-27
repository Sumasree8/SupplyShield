import { useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/authStore';

export function RegisterPage() {
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', organization_name: '', industry: ''
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (form.password.length < 12) {
      toast.error('Password must be at least 12 characters');
      return;
    }
    setLoading(true);
    try {
      await api.register(form);
      await login(form.email, form.password);
      toast.success('Organization created successfully');
      navigate('/');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card" style={{ maxWidth: 460 }}>
        <div className="auth-brand">
          <ShieldAlert size={22} color="var(--color-accent)" />
          <span style={{ fontWeight: 600, fontSize: 'var(--text-md)' }}>SupplyShield AI</span>
        </div>
        <p className="auth-title">Create your organization</p>
        <p className="auth-subtitle">Set up supply chain risk intelligence for your company</p>

        <form onSubmit={handleSubmit}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Full name</label>
              <input className="form-input" value={form.full_name} onChange={set('full_name')} required placeholder="Jane Smith" />
            </div>
            <div className="form-group">
              <label className="form-label">Work email</label>
              <input className="form-input" type="email" value={form.email} onChange={set('email')} required placeholder="jane@company.com" />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Organization name</label>
            <input className="form-input" value={form.organization_name} onChange={set('organization_name')} required placeholder="Acme Manufacturing Corp." />
          </div>

          <div className="form-group">
            <label className="form-label">Industry</label>
            <select className="form-input filter-select" value={form.industry} onChange={set('industry')} style={{ width: '100%' }}>
              <option value="">Select industry</option>
              <option>Automotive</option>
              <option>Electronics</option>
              <option>Aerospace & Defense</option>
              <option>Pharmaceuticals</option>
              <option>Consumer Goods</option>
              <option>Industrial Equipment</option>
              <option>Logistics & Transportation</option>
              <option>Energy</option>
              <option>Other</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Password <span className="text-muted">(min. 12 characters)</span></label>
            <input className="form-input" type="password" value={form.password} onChange={set('password')} required minLength={12} />
          </div>

          <button type="submit" className="btn btn--primary w-full" disabled={loading} style={{ justifyContent: 'center' }}>
            {loading ? <span className="loading-spinner" /> : 'Create account'}
          </button>
        </form>

        <p style={{ marginTop: 'var(--space-5)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', textAlign: 'center' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--color-accent)', fontWeight: 500 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
