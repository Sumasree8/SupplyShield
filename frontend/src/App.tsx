import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';

import { useAuthStore } from '@/store/authStore';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { AppLayout } from '@/components/layout/AppLayout';
import { LoginPage } from '@/pages/LoginPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { DashboardPage } from '@/pages/DashboardPage';
import { SuppliersPage } from '@/pages/SuppliersPage';
import { AddSupplierPage } from '@/pages/AddSupplierPage';
import { SupplierDetailPage } from '@/pages/SupplierDetailPage';
import { GraphPage } from '@/pages/GraphPage';
import { RiskPage } from '@/pages/RiskPage';
import { AlertsPage } from '@/pages/AlertsPage';
import { SimulatorPage } from '@/pages/SimulatorPage';
import { UsersPage } from '@/pages/UsersPage';
import { RecommendationsPage } from '@/pages/RecommendationsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const loadUser = useAuthStore((s) => s.loadUser);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <AppLayout />
              </PrivateRoute>
            }
          >
            <Route index element={<DashboardPage />} />
            <Route path="suppliers" element={<SuppliersPage />} />
            <Route path="suppliers/new" element={<AddSupplierPage />} />
            <Route path="suppliers/:id" element={<SupplierDetailPage />} />
            <Route path="graph" element={<GraphPage />} />
            <Route path="risk" element={<RiskPage />} />
            <Route path="alerts" element={<AlertsPage />} />
            <Route path="simulator" element={<SimulatorPage />} />
            <Route path="recommendations" element={<RecommendationsPage />} />
            <Route path="users" element={<UsersPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </ErrorBoundary>
      <Toaster
        position="top-right"
        toastOptions={{
          className: 'ss-toast',
          duration: 4000,
        }}
      />
    </QueryClientProvider>
  );
}
