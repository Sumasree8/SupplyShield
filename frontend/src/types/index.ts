// SupplyShield AI - Core TypeScript types

export type UserRole = 'admin' | 'risk_analyst' | 'procurement_manager' | 'executive_viewer';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  organization_id: string;
  organization_name: string;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface SupplierRiskScore {
  supplier_id: string;
  supplier_name: string;
  country: string;
  tier: number;
  overall_score: number;
  risk_level: 'critical' | 'high' | 'medium' | 'low';
  climate_score: number | null;
  geopolitical_score: number | null;
  operational_score: number | null;
  logistics_score: number | null;
  dependency_score: number | null;
  calculated_at: string;
}

export type SupplierStatus = 'active' | 'inactive' | 'under_review' | 'suspended';

export interface Supplier {
  id: string;
  organization_id: string;
  external_id?: string;
  name: string;
  legal_name?: string;
  country: string;
  region?: string;
  city?: string;
  latitude?: number;
  longitude?: number;
  tier: 1 | 2 | 3 | 4;
  status: SupplierStatus;
  industry?: string;
  annual_revenue_usd?: number;
  employee_count?: number;
  website?: string;
  contact_email?: string;
  certifications?: Record<string, string>;
  notes?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface SupplyRelationship {
  id: string;
  from_supplier_id: string;
  to_supplier_id: string;
  material_id?: string;
  relationship_type: string;
  annual_volume_usd?: number;
  lead_time_days?: number;
  is_active: boolean;
  created_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  tier: number;
  country: string;
  status: SupplierStatus;
  industry?: string;
  latitude?: number;
  longitude?: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  annual_volume_usd?: number;
  lead_time_days?: number;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
  stats: {
    total_nodes: number;
    total_edges: number;
    tier_breakdown: Record<number, number>;
    country_breakdown: Record<string, number>;
  };
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type RiskCategory = 'climate' | 'geopolitical' | 'operational' | 'logistics' | 'dependency' | 'financial';

export interface RiskFactor {
  description: string;
  category: RiskCategory;
  score_contribution: number;
  source: string;
  evidence?: string;
}

export interface RiskScore {
  supplier_id: string;
  supplier_name: string;
  overall_score: number;
  risk_level: RiskLevel;
  category_scores: Record<RiskCategory, number>;
  weights: Record<RiskCategory, number>;
  contributing_factors: RiskFactor[];
  data_sources: string[];
  calculated_at: string;
  scoring_version: string;
  score_id: string;
}

export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'created' | 'assigned' | 'investigating' | 'resolved' | 'closed';

export interface Alert {
  id: string;
  title: string;
  description: string;
  category: RiskCategory;
  severity: AlertSeverity;
  status: AlertStatus;
  supplier_id?: string;
  trigger_type: string;
  created_at: string;
  resolved_at?: string;
}

export interface DisruptionImpact {
  disrupted_supplier_id: string;
  total_affected: number;
  impact_by_tier: Record<number, Array<{
    supplier_id: string;
    name: string;
    country: string;
    distance_from_disruption: number;
    propagation_path: string[];
  }>>;
  sole_source_vulnerabilities: Array<{
    supplier_id: string;
    name: string;
    reason: string;
  }>;
  disruption_radius: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
