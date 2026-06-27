import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Building2, Network, ShieldAlert,
  Bell, Zap, Users, LogOut, Menu, X, ChevronRight, Lightbulb
} from 'lucide-react';
import { useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import clsx from 'clsx';

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { to: '/suppliers', label: 'Suppliers', icon: Building2 },
  { to: '/graph', label: 'Supply Graph', icon: Network },
  { to: '/risk', label: 'Risk Intelligence', icon: ShieldAlert },
  { to: '/alerts', label: 'Alerts', icon: Bell },
  { to: '/simulator', label: 'Impact Simulator', icon: Zap },
  { to: '/recommendations', label: 'Recommendations', icon: Lightbulb },
  { to: '/users', label: 'Users', icon: Users },
];

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="app-layout">
      <aside className={clsx('sidebar', { 'sidebar--collapsed': !sidebarOpen })}>
        <div className="sidebar__header">
          <div className="sidebar__brand">
            <ShieldAlert size={20} className="brand-icon" />
            {sidebarOpen && <span className="brand-name">SupplyShield AI</span>}
          </div>
          <button
            className="sidebar__toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
          </button>
        </div>

        <nav className="sidebar__nav" role="navigation" aria-label="Main navigation">
          {NAV_ITEMS.map(({ to, label, icon: Icon, exact }) => (
            <NavLink
              key={to}
              to={to}
              end={exact}
              className={({ isActive }) =>
                clsx('nav-item', { 'nav-item--active': isActive })
              }
            >
              <Icon size={18} className="nav-item__icon" />
              {sidebarOpen && <span className="nav-item__label">{label}</span>}
              {sidebarOpen && <ChevronRight size={14} className="nav-item__arrow" />}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar__footer">
          {sidebarOpen && user && (
            <div className="user-info">
              <p className="user-info__name">{user.full_name}</p>
              <p className="user-info__role">{user.role.replace(/_/g, ' ')}</p>
              <p className="user-info__org">{user.organization_name}</p>
            </div>
          )}
          <button className="logout-btn" onClick={handleLogout} aria-label="Log out">
            <LogOut size={16} />
            {sidebarOpen && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
}
