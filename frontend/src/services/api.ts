/**
 * SupplyShield AI API client.
 * Handles auth token injection, refresh, and error normalization.
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  AuthTokens, User, Supplier, GraphData, RiskScore,
  Alert, DisruptionImpact, PaginatedResponse
} from '@/types';

const BASE_URL = import.meta.env.VITE_API_URL || '';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${BASE_URL}/api/v1`,
      headers: { 'Content-Type': 'application/json' },
    });

    // Inject auth token
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle 401 — attempt a single token refresh, de-duplicated across
    // concurrent requests. The `_retry` flag prevents an infinite refresh loop
    // when the refreshed token is itself rejected.
    this.client.interceptors.response.use(
      (r) => r,
      async (error: AxiosError) => {
        const original = error.config as (typeof error.config & { _retry?: boolean }) | undefined;
        if (error.response?.status !== 401 || !original || original._retry) {
          return Promise.reject(error);
        }

        const refresh = localStorage.getItem('refresh_token');
        if (!refresh) {
          this.forceLogout();
          return Promise.reject(error);
        }

        original._retry = true;
        try {
          // Share a single in-flight refresh across concurrent 401s.
          this.refreshPromise ??= axios
            .post(`${BASE_URL}/api/v1/auth/refresh`, null, { params: { refresh_token: refresh } })
            .then((res) => {
              const { access_token, refresh_token } = res.data as AuthTokens;
              localStorage.setItem('access_token', access_token);
              localStorage.setItem('refresh_token', refresh_token);
              return access_token;
            })
            .finally(() => { this.refreshPromise = null; });

          const access_token = await this.refreshPromise;
          original.headers.Authorization = `Bearer ${access_token}`;
          return this.client.request(original);
        } catch {
          this.forceLogout();
          return Promise.reject(error);
        }
      }
    );
  }

  private refreshPromise: Promise<string> | null = null;

  private forceLogout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }

  // --- Auth ---
  async login(email: string, password: string): Promise<AuthTokens> {
    const res = await this.client.post('/auth/login', { email, password });
    return res.data;
  }

  async register(data: {
    email: string; password: string; full_name: string;
    organization_name: string; industry?: string;
  }): Promise<User> {
    const res = await this.client.post('/auth/register', data);
    return res.data;
  }

  async getMe(): Promise<User> {
    const res = await this.client.get('/auth/me');
    return res.data;
  }

  // --- Suppliers ---
  async listSuppliers(params?: {
    page?: number; page_size?: number; tier?: number;
    country?: string; status?: string; search?: string;
  }): Promise<PaginatedResponse<Supplier>> {
    const res = await this.client.get('/suppliers', { params });
    return res.data;
  }

  async getSupplier(id: string): Promise<Supplier> {
    const res = await this.client.get(`/suppliers/${id}`);
    return res.data;
  }

  async createSupplier(data: Partial<Supplier>): Promise<Supplier> {
    const res = await this.client.post('/suppliers', data);
    return res.data;
  }

  async updateSupplier(id: string, data: Partial<Supplier>): Promise<Supplier> {
    const res = await this.client.patch(`/suppliers/${id}`, data);
    return res.data;
  }

  async deleteSupplier(id: string): Promise<void> {
    await this.client.delete(`/suppliers/${id}`);
  }

  async createRelationship(data: {
    from_supplier_id: string; to_supplier_id: string;
    relationship_type?: string; annual_volume_usd?: number; lead_time_days?: number;
  }) {
    const res = await this.client.post('/suppliers/relationships', data);
    return res.data;
  }

  // --- Graph ---
  async getGraphVisualization(): Promise<GraphData> {
    const res = await this.client.get('/graph/visualization');
    return res.data;
  }

  async getUpstreamDependencies(supplierId: string, maxDepth = 5) {
    const res = await this.client.get(`/graph/suppliers/${supplierId}/upstream`, {
      params: { max_depth: maxDepth },
    });
    return res.data;
  }

  async getTierSummary() {
    const res = await this.client.get('/graph/tier-summary');
    return res.data;
  }

  // --- Risk ---
  async calculateRiskScore(supplierId: string): Promise<RiskScore> {
    const res = await this.client.post(`/risk/suppliers/${supplierId}/score`);
    return res.data;
  }

  async getRiskScoreHistory(supplierId: string, limit = 10) {
    const res = await this.client.get(`/risk/suppliers/${supplierId}/scores`, { params: { limit } });
    return res.data;
  }

  async listRiskEvents(params?: { category?: string; limit?: number }) {
    const res = await this.client.get('/risk/events', { params });
    return res.data;
  }

  // --- Alerts ---
  async listAlerts(params?: {
    severity?: string; status?: string; supplier_id?: string; limit?: number;
  }): Promise<{ alerts: Alert[]; total: number }> {
    const res = await this.client.get('/alerts', { params });
    return res.data;
  }

  async getAlert(id: string) {
    const res = await this.client.get(`/alerts/${id}`);
    return res.data;
  }

  async updateAlertStatus(id: string, status: string, notes?: string) {
    const res = await this.client.patch(`/alerts/${id}/status`, { status, notes });
    return res.data;
  }

  // --- Simulator ---
  async simulateDisruption(supplierId: string): Promise<DisruptionImpact> {
    const res = await this.client.post(`/simulator/suppliers/${supplierId}/disruption`);
    return res.data;
  }


  // --- Users ---
  async listUsers(): Promise<{ users: Array<{
    id: string; email: string; full_name: string; role: string;
    is_active: boolean; last_login?: string; created_at: string;
  }> }> {
    const res = await this.client.get('/users');
    return res.data;
  }

  async createUser(data: { email: string; full_name: string; password: string; role: string }) {
    const res = await this.client.post('/users', data);
    return res.data;
  }

  // --- Recommendations ---
  async getAlternativeSuppliers(supplierId: string, maxResults = 10) {
    const res = await this.client.get(`/recommendations/suppliers/${supplierId}/alternatives`, {
      params: { max_results: maxResults },
    });
    return res.data;
  }

  async listRecommendationCandidates(params?: {
    country?: string; industry?: string; tier?: number; max_results?: number;
  }) {
    const res = await this.client.get('/recommendations/candidates', { params });
    return res.data;
  }
  // --- Health ---
  async health() {
    const res = await this.client.get('/health');
    return res.data;
  }
}

export const api = new ApiClient();
