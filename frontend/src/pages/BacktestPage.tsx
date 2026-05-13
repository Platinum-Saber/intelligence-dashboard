import { useState } from "react"
import { useMutation, useQuery } from "@tanstack/react-query"
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, ResponsiveContainer
} from "recharts"
import {
  runBacktest, listUATScenarios, runScenario,
  type BacktestResult, type UATScenario, type ScenarioRunResult,
} from "@/api/backtest"
import { fetchAlertRules } from "@/api/alerts"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import { FlaskConical, Play, TrendingUp, AlertTriangle, CheckCircle2, Calendar } from "lucide-react"

// ── Helpers ───────────────────────────────────────────────────────────────────

function nDaysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().split("T")[0]
}

function today(): string {
  return new Date().toISOString().split("T")[0]
}

function ruleTypeBadge(type: string) {
  const map: Record<string, string> = {
    FX_THRESHOLD: "bg-blue-500/15 text-blue-500",
    COMMODITY_DIP: "bg-orange-500/15 text-orange-500",
    WEATHER_RISK: "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400",
    SENTIMENT_NEGATIVE: "bg-red-500/15 text-red-500",
  }
  return map[type] ?? "bg-muted text-muted-foreground"
}

function ruleTypeLabel(type: string) {
  const map: Record<string, string> = {
    FX_THRESHOLD: "FX",
    COMMODITY_DIP: "Commodity",
    WEATHER_RISK: "Weather",
    SENTIMENT_NEGATIVE: "Sentiment",
  }
  return map[type] ?? type
}

// ── Backtesting Tab ───────────────────────────────────────────────────────────

function BacktestTab() {
  const [startDate, setStartDate] = useState(nDaysAgo(90))
  const [endDate, setEndDate] = useState(today())
  const [result, setResult] = useState<BacktestResult | null>(null)

  const rules = useQuery({ queryKey: ["alert-rules"], queryFn: fetchAlertRules })

  const mutation = useMutation({
    mutationFn: () => runBacktest({ start_date: startDate, end_date: endDate, rule_ids: null }),
    onSuccess: (data) => setResult(data),
  })

  const chartData = result?.daily_results.map((d) => ({
    date: d.date.slice(5),    // MM-DD
    alerts: d.alerts_fired,
    fx: d.fx_rate,
  })) ?? []

  const topRule = result?.rule_summaries[0]

  return (
    <div className="flex flex-col gap-6">
      {/* Config card */}
      <Card>
        <CardHeader>
          <CardTitle>Alert Rule Backtest</CardTitle>
          <CardDescription>
            Simulate how your current alert rules would have performed against historical data. No data is modified.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-4">
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                max={endDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="h-10 rounded-md border border-[var(--c-border)] bg-background px-3 text-sm text-foreground"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                min={startDate}
                max={today()}
                onChange={(e) => setEndDate(e.target.value)}
                className="h-10 rounded-md border border-[var(--c-border)] bg-background px-3 text-sm text-foreground"
              />
            </div>
            <div className="flex gap-2">
              {[30, 60, 90].map((d) => (
                <button
                  key={d}
                  onClick={() => { setStartDate(nDaysAgo(d)); setEndDate(today()) }}
                  className="px-3 h-10 rounded-md border border-[var(--c-border)] text-sm text-muted-foreground hover:bg-muted transition-colors"
                >
                  {d}d
                </button>
              ))}
            </div>
            <Button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending}
              className="h-10"
            >
              <Play size={14} className="mr-1.5" />
              {mutation.isPending ? "Running…" : "Run Backtest"}
            </Button>
          </div>

          {rules.data && (
            <p className="mt-3 text-xs text-muted-foreground">
              Will evaluate {rules.data.length} alert rule{rules.data.length !== 1 ? "s" : ""} against historical data.
            </p>
          )}

          {mutation.isError && (
            <p className="mt-3 text-sm text-red-500">
              Backtest failed. Make sure the backend is running and has historical data.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Loading */}
      {mutation.isPending && (
        <div className="grid grid-cols-3 gap-4">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-24 rounded-lg" />)}
        </div>
      )}

      {/* Results */}
      {result && !mutation.isPending && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              {
                icon: <Calendar size={16} className="text-[var(--c-primary)]" />,
                label: "Days analysed",
                value: result.total_days,
              },
              {
                icon: <AlertTriangle size={16} className="text-orange-500" />,
                label: "Total alert fires",
                value: result.total_alerts_fired,
              },
              {
                icon: <TrendingUp size={16} className="text-[var(--c-primary)]" />,
                label: "Avg fires / day",
                value: result.total_days > 0
                  ? (result.total_alerts_fired / result.total_days).toFixed(2)
                  : "—",
              },
              {
                icon: <FlaskConical size={16} className="text-[var(--c-gold)]" />,
                label: "Most triggered",
                value: topRule ? topRule.total_fires : "—",
                sub: topRule?.rule_name,
              },
            ].map(({ icon, label, value, sub }) => (
              <Card key={label}>
                <CardContent className="pt-5 pb-4">
                  <div className="flex items-center gap-2 mb-1">
                    {icon}
                    <span className="text-xs text-muted-foreground uppercase tracking-wide">{label}</span>
                  </div>
                  <p className="text-2xl font-bold text-foreground">{value}</p>
                  {sub && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{sub}</p>}
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Timeline chart */}
          <Card>
            <CardHeader>
              <CardTitle>Alert Frequency Over Time</CardTitle>
              <CardDescription>Number of alert rule fires per day during the backtest period</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={chartData} barSize={chartData.length > 60 ? 2 : 6}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--c-border)" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: "var(--c-text-muted)" }}
                    interval={Math.floor(chartData.length / 8)}
                  />
                  <YAxis tick={{ fontSize: 11, fill: "var(--c-text-muted)" }} allowDecimals={false} />
                  <ChartTooltip
                    contentStyle={{
                      background: "var(--c-surface)",
                      border: "1px solid var(--c-border)",
                      borderRadius: 8,
                      fontSize: 12,
                    }}
                    labelStyle={{ color: "var(--c-text)" }}
                  />
                  <Bar dataKey="alerts" name="Alerts fired" fill="var(--c-primary)" radius={[2, 2, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Rule summary table */}
          <Card>
            <CardHeader>
              <CardTitle>Per-Rule Summary</CardTitle>
              <CardDescription>How often each rule would have triggered during the period</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--c-border)]">
                      {["Rule", "Type", "Fires", "Fire rate", "First fire", "Last fire"].map((h) => (
                        <th key={h} className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rule_summaries.map((r) => (
                      <tr key={r.rule_id} className="border-b border-[var(--c-border)] hover:bg-muted/20 transition-colors">
                        <td className="py-3 px-3 font-medium text-foreground">{r.rule_name}</td>
                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${ruleTypeBadge(r.rule_type)}`}>
                            {ruleTypeLabel(r.rule_type)}
                          </span>
                        </td>
                        <td className="py-3 px-3 font-bold text-foreground">{r.total_fires}</td>
                        <td className="py-3 px-3 text-muted-foreground">{r.fire_rate_pct}%</td>
                        <td className="py-3 px-3 text-muted-foreground">{r.first_fire_date ?? "—"}</td>
                        <td className="py-3 px-3 text-muted-foreground">{r.last_fire_date ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

// ── UAT Scenarios Tab ─────────────────────────────────────────────────────────

function ScenarioCard({
  scenario,
  onRun,
  isRunning,
  result,
}: {
  scenario: UATScenario
  onRun: () => void
  isRunning: boolean
  result: ScenarioRunResult | null
}) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            <p className="font-semibold text-foreground">{scenario.name}</p>
            <p className="text-sm text-muted-foreground mt-0.5">{scenario.description}</p>
          </div>
          <Button size="sm" variant="outline" onClick={onRun} disabled={isRunning} className="shrink-0">
            <Play size={12} className="mr-1" />
            {isRunning ? "Running…" : "Run"}
          </Button>
        </div>

        {/* Conditions summary */}
        <div className="flex flex-wrap gap-2 mb-4">
          <span className="text-xs bg-muted rounded px-2 py-1 text-muted-foreground">
            USD/LKR {scenario.conditions.usd_lkr.toFixed(1)}
          </span>
          <span className="text-xs bg-muted rounded px-2 py-1 text-muted-foreground">
            Cu {scenario.conditions.copper_change_pct > 0 ? "+" : ""}{scenario.conditions.copper_change_pct.toFixed(1)}%
          </span>
          <span className="text-xs bg-muted rounded px-2 py-1 text-muted-foreground">
            Al {scenario.conditions.aluminium_change_pct > 0 ? "+" : ""}{scenario.conditions.aluminium_change_pct.toFixed(1)}%
          </span>
          {scenario.conditions.high_risk_locations.length > 0 && (
            <span className="text-xs bg-yellow-500/15 text-yellow-600 dark:text-yellow-400 rounded px-2 py-1">
              Flood: {scenario.conditions.high_risk_locations.join(", ")}
            </span>
          )}
        </div>

        {/* Results */}
        {result && (
          <div className="border-t border-[var(--c-border)] pt-3">
            {result.total_fired === 0 ? (
              <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                <CheckCircle2 size={14} />
                No alert rules would fire under these conditions.
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                  {result.total_fired} rule{result.total_fired !== 1 ? "s" : ""} would fire
                </p>
                {result.fired_rules.map((r) => (
                  <div key={r.rule_id} className="flex items-start gap-2 text-sm">
                    <span className={`mt-0.5 inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold shrink-0 ${ruleTypeBadge(r.rule_type)}`}>
                      {ruleTypeLabel(r.rule_type)}
                    </span>
                    <div>
                      <p className="font-medium text-foreground">{r.rule_name}</p>
                      <p className="text-muted-foreground text-xs">{r.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function UATTab() {
  const scenarios = useQuery({
    queryKey: ["uat-scenarios"],
    queryFn: listUATScenarios,
  })

  const [results, setResults] = useState<Record<string, ScenarioRunResult>>({})
  const [running, setRunning] = useState<string | null>(null)

  async function handleRun(scenario: UATScenario) {
    setRunning(scenario.id)
    try {
      const res = await runScenario(scenario.conditions)
      setResults((prev) => ({ ...prev, [scenario.id]: res }))
    } finally {
      setRunning(null)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="pt-5 pb-4">
          <p className="text-sm text-muted-foreground">
            Each scenario simulates a specific market condition and evaluates which of your current alert rules would fire.
            Use these to validate that your rules are configured correctly before live deployment.
          </p>
        </CardContent>
      </Card>

      {scenarios.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-40 rounded-lg" />)}
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {scenarios.data?.map((s) => (
          <ScenarioCard
            key={s.id}
            scenario={s}
            onRun={() => handleRun(s)}
            isRunning={running === s.id}
            result={results[s.id] ?? null}
          />
        ))}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export function BacktestPage() {
  return (
    <div className="flex flex-col gap-6">
      <Tabs defaultValue="backtest">
        <TabsList className="mb-2">
          <TabsTrigger value="backtest">
            <TrendingUp size={14} className="mr-1.5" />
            Alert Backtesting
          </TabsTrigger>
          <TabsTrigger value="uat">
            <FlaskConical size={14} className="mr-1.5" />
            UAT Scenarios
          </TabsTrigger>
        </TabsList>

        <TabsContent value="backtest">
          <BacktestTab />
        </TabsContent>

        <TabsContent value="uat">
          <UATTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
