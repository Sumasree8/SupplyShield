import { useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ShieldAlert } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuthStore } from '@/store/authStore';

const DEMO_EMAIL = 'demo@gmail.com';
const DEMO_PASSWORD = 'demo@1234';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await login(email, password);
      navigate('/');
    } catch {
      toast.error('Invalid credentials. Please try again.');
    }
  };

  const handleDemoLogin = async () => {
    setEmail(DEMO_EMAIL);
    setPassword(DEMO_PASSWORD);
    try {
      await login(DEMO_EMAIL, DEMO_PASSWORD);
      navigate('/');
    } catch {
      toast.error('Demo account unavailable. Run the seed script first (scripts/seed_demo.py).');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <ShieldAlert size={22} color="var(--color-accent)" />
          <span style={{ fontWeight: 600, fontSize: 'var(--text-md)', letterSpacing: '-0.01em' }}>
            SupplyShield AI
          </span>
        </div>
        <p className="auth-title">Sign in to your account</p>
        <p className="auth-subtitle">Supply chain risk intelligence platform</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="email">Work email</label>
            <input
              id="email"
              type="email"
              className="form-input"
              value={email}
              onChange={e => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              autoComplete="email"
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              className="form-input"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder="••••••••••••"
              required
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn--primary w-full"
            disabled={isLoading}
            style={{ justifyContent: 'center', marginTop: 'var(--space-2)' }}
          >
            {isLoading ? <span className="loading-spinner" /> : 'Sign in'}
          </button>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', margin: 'var(--space-4) 0' }}>
          <span style={{ flex: 1, height: 1, background: 'var(--color-border)' }} />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)' }}>or</span>
          <span style={{ flex: 1, height: 1, background: 'var(--color-border)' }} />
        </div>

        <button
          type="button"
          className="btn w-full"
          onClick={handleDemoLogin}
          disabled={isLoading}
          style={{ justifyContent: 'center' }}
        >
          Explore with a demo account
        </button>
        <p style={{ marginTop: 'var(--space-2)', fontSize: 'var(--text-xs)', color: 'var(--color-text-secondary)', textAlign: 'center' }}>
          Signs in as an admin with sample supply-chain data — no setup needed.
        </p>

        <p style={{ marginTop: 'var(--space-5)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', textAlign: 'center' }}>
          New organization?{' '}
          <Link to="/register" style={{ color: 'var(--color-accent)', fontWeight: 500 }}>
            Create account
          </Link>
        </p>
      </div>
    </div>
  );
}
