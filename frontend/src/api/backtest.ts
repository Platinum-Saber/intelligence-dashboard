import { get, post } from "./client"

export interface BacktestRequest {
  rule_ids?: number[] | null
  start_date: string   // YYYY-MM-DD
  end_date: string
}

export interface BacktestDayResult {
  date: string
  triggered_rules: string[]
  alerts_fired: number
  fx_rate: number | null
  copper_price: number | null
  aluminium_price: number | null
}

export interface BacktestRuleSummary {
  rule_id: number
  rule_name: string
  rule_type: string
  total_fires: number
  fire_rate_pct: number
  first_fire_date: string | null
  last_fire_date: string | null
}

export interface BacktestResult {
  rule_summaries: BacktestRuleSummary[]
  daily_results: BacktestDayResult[]
  total_days: number
  total_alerts_fired: number
  start_date: string
  end_date: string
}

export interface SentimentTopic {
  positive: number
  negative: number
  neutral: number
}

export interface ScenarioConditions {
  usd_lkr: number
  copper_change_pct: number
  aluminium_change_pct: number
  high_risk_locations: string[]
  sentiment_by_topic: Record<string, SentimentTopic>
}

export interface UATScenario {
  id: string
  name: string
  description: string
  conditions: ScenarioConditions
}

export interface ScenarioFiredRule {
  rule_id: number
  rule_name: string
  rule_type: string
  message: string
}

export interface ScenarioRunResult {
  fired_rules: ScenarioFiredRule[]
  total_fired: number
  conditions: ScenarioConditions
}

export interface DataSourceStatus {
  source_name: string
  status: "ok" | "degraded" | "down"
  data_points_24h: number
  last_data_timestamp: string | null
  fragility_rating: "LOW" | "MEDIUM" | "HIGH"
  fragility_reason: string
  paid_fallback: string | null
  notes: string
}

export interface DataSourceAuditResult {
  sources: DataSourceStatus[]
  audit_timestamp: string
  overall_health: string
}

export const runBacktest = (body: BacktestRequest) =>
  post<BacktestResult>("/api/v1/backtest/run", body)

export const listUATScenarios = () =>
  get<UATScenario[]>("/api/v1/backtest/scenarios")

export const runScenario = (conditions: ScenarioConditions) =>
  post<ScenarioRunResult>("/api/v1/backtest/scenario/run", { conditions })

export const getDataSourceAudit = () =>
  get<DataSourceAuditResult>("/api/v1/datasources/audit")
