import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import toast from 'react-hot-toast';
import { api } from '@/services/api';
import { useAuthStore } from '@/store/authStore';

export function UsersPage() {
  const qc = useQueryClient();
  const { user: me } = useAuthStore();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'risk_analyst' });

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['users-list'],
    queryFn: () => api.listUsers(),
  });

  const createMutation = useMutation({
    mutationFn: (data: typeof form) => api.createUser(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users-list'] });
      setShowForm(false);
      setForm({ email: '', full_name: '', password: '', role: 'risk_analyst' });
      toast.success('User created');
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(detail || 'Failed to create user');
    },
  });

  const ROLE_LABELS: Record<string, string> = {
    admin: 'Admin',
    risk_analyst: 'Risk Analyst',
    procurement_manager: 'Procurement Manager',
    executive_viewer: 'Executive Viewer',
  };

  const users = usersData?.users ?? [];

  return (
    <div className="page">
      <div className="page__header">
        <div>
          <h1 className="page__title">User Management</h1>
          <p className="page__subtitle">Manage access and roles for {me?.organization_name}</p>
        </div>
        {me?.role === 'admin' && (
          <button className="btn btn--primary" onClick={() => setShowForm(!showForm)}>
            <Plus size={16} /> Add User
          </button>
        )}
      </div>

      {showForm && (
        <div className="card mb-4">
          <p className="card__title" style={{ marginBottom: 'var(--space-4)' }}>New User</p>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Full Name</label>
              <input className="form-input" value={form.full_name} onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Email</label>
              <input className="form-input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Password <span className="text-muted">(min. 12 chars)</span></label>
              <input className="form-input" type="password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
            </div>
            <div className="form-group">
              <label className="form-label">Role</label>
              <select className="form-input" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                <option value="executive_viewer">Executive Viewer</option>
                <option value="procurement_manager">Procurement Manager</option>
                <option value="risk_analyst">Risk Analyst</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            <button className="btn btn--primary" onClick={() => createMutation.mutate(form)} disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Creating...' : 'Create User'}
            </button>
            <button className="btn btn--secondary" onClick={() => setShowForm(false)}>Cancel</button>
          </div>
        </div>
      )}

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Last Login</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            {usersLoading ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40 }}><span className="loading-spinner" /></td></tr>
            ) : users.length === 0 ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 40, color: 'var(--color-text-muted)' }}>No users found</td></tr>
            ) : users.map((u: { id: string; full_name: string; email: string; role: string; is_active: boolean; last_login?: string; created_at: string }) => (
              <tr key={u.id}>
                <td>
                  <p style={{ fontWeight: 500 }}>{u.full_name}</p>
                  {u.id === me?.id && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-accent)' }}>You</span>}
                </td>
                <td className="text-sm">{u.email}</td>
                <td><span className="badge badge--active">{ROLE_LABELS[u.role] || u.role}</span></td>
                <td>
                  <span className={`badge badge--${u.is_active ? 'active' : 'inactive'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="text-muted">{u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}</td>
                <td className="text-muted">{new Date(u.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
