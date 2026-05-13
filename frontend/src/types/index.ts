export interface FXRate {
  id: number;
  timestamp: string;
  usd_lkr: number;
  source: string | null;
}

export interface FXSummary {
  current: number;
  change_24h: number;
  change_24h_pct: number;
  high_30d: number;
  low_30d: number;
  avg_30d: number;
}

export interface CommodityPrice {
  id: number;
  timestamp: string;
  symbol: string;
  price_usd: number;
  unit: string;
  source: string | null;
}

export interface CommoditySummary {
  symbol: string;
  current_price_usd: number;
  change_24h: number;
  change_24h_pct: number;
  high_30d: number;
  low_30d: number;
  avg_30d: number;
}

export interface WeatherLatest {
  location_name: string;
  location_type: string;
  timestamp: string;
  rainfall_mm: number | null;
  flood_risk: string;
  temperature_c: number | null;
}

export interface NewsItem {
  id: number;
  published_at: string;
  headline: string;
  summary: string | null;
  url: string | null;
  source: string | null;
  topic: string | null;
  relevance_score: number | null;
  sentiment: string | null;
}

export interface AlertRule {
  id: number;
  created_at: string;
  name: string;
  rule_type: string;
  metric: string;
  comparison: string;
  threshold_value: number | null;
  threshold_text: string | null;
  enabled: boolean;
  email_recipients: string | null;
}

export interface AlertEvent {
  id: number;
  triggered_at: string;
  rule_id: number;
  rule_name: string;
  message: string;
  notified: boolean;
}

export interface LandedCostRequest {
  material: string;
  quantity_tonnes: number;
  custom_lme_price_usd?: number | null;
  custom_fx_rate?: number | null;
}

export interface LandedCostResponse {
  material: string;
  quantity_tonnes: number;
  lme_price_usd_per_tonne: number;
  usd_lkr_rate: number;
  total_usd: number;
  total_lkr: number;
  calculated_at: string;
}
