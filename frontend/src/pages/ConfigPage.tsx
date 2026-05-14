import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  fetchAlertRules,
  createAlertRule,
  toggleAlertRule,
  deleteAlertRule,
  triggerManualCheck,
} from "@/api/alerts"
import { post as apiPost } from "@/api/client"
import type { AlertRule } from "@/types"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Separator } from "@/components/ui/separator"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Plus, Trash2, Zap, Brain, Activity, CheckCircle2, AlertTriangle, XCircle } from "lucide-react"
import { getDataSourceAudit, type DataSourceStatus } from "@/api/backtest"
import { fetchAppSettings } from "@/api/settings"

const RULE_TYPES = ["FX_THRESHOLD", "COMMODITY_DIP", "WEATHER_RISK", "SENTIMENT_NEGATIVE"] as const
const METRICS: Record<string, string[]> = {
  FX_THRESHOLD:       ["usd_lkr", "usd_lkr_change_pct"],
  COMMODITY_DIP:      ["copper_price", "aluminium_price"],
  WEATHER_RISK:       ["flood_risk", "drought_risk", "heatwave"],
  SENTIMENT_NEGATIVE: ["news_sentiment"],
}
const METRIC_LABELS: Record<string, string> = {
  usd_lkr:            "USD/LKR Rate",
  usd_lkr_change_pct: "USD/LKR Daily Change %",
  copper_price:       "Copper Landed Cost Δ%",
  aluminium_price:    "Aluminium Landed Cost Δ%",
  flood_risk:         "Flood Risk",
  drought_risk:       "Drought Risk",
  heatwave:           "Heatwave (°C)",
  news_sentiment:     "News Sentiment",
}
const TREND_WINDOW_METRICS = new Set(["usd_lkr", "flood_risk"])
const RULE_TYPE_COLORS: Record<string, string> = {
  FX_THRESHOLD:       "bg-[var(--c-primary)]/15 text-[var(--c-primary)]",
  COMMODITY_DIP:      "bg-[var(--c-orange)]/15 text-[var(--c-orange)]",
  WEATHER_RISK:       "bg-[var(--c-red)]/15 text-[var(--c-red)]",
  SENTIMENT_NEGATIVE: "bg-[var(--c-purple)]/15 text-[var(--c-purple)]",
}

const EMPTY_RULE: Omit<AlertRule, "id" | "created_at"> = {
  name: "",
  rule_type: "FX_THRESHOLD",
  metric: "usd_lkr",
  comparison: "lt",
  threshold_value: null,
  threshold_text: null,
  enabled: true,
  email_recipients: "",
  trend_window_hours: null,
}

function RuleTypeChip({ type }: { type: string }) {
  return (
    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${RULE_TYPE_COLORS[type] ?? "bg-muted text-muted-foreground"}`}>
      {type.replace("_", " ")}
    </span>
  )
}

export function ConfigPage() {
  return (
    <Tabs defaultValue="rules" className="flex flex-col gap-5">
      <TabsList className="w-fit">
        <TabsTrigger value="rules">Alert Rules</TabsTrigger>
        <TabsTrigger value="app">App Settings</TabsTrigger>
        <TabsTrigger value="model">Model Tuning</TabsTrigger>
        <TabsTrigger value="datasources">
          <Activity size={13} className="mr-1" />
          Data Sources
        </TabsTrigger>
      </TabsList>
      <TabsContent value="rules"><AlertRulesTab /></TabsContent>
      <TabsContent value="app"><AppSettingsTab /></TabsContent>
      <TabsContent value="model"><ModelTuningTab /></TabsContent>
      <TabsContent value="datasources"><DataSourceAuditTab /></TabsContent>
    </Tabs>
  )
}

function AlertRulesTab() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ ...EMPTY_RULE })

  const rules = useQuery({ queryKey: ["alert-rules"], queryFn: fetchAlertRules })

  const createMutation = useMutation({
    mutationFn: createAlertRule,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert-rules"] })
      setOpen(false)
      setForm({ ...EMPTY_RULE })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: toggleAlertRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteAlertRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  })

  const checkMutation = useMutation({
    mutationFn: triggerManualCheck,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alert-events"] })
      qc.invalidateQueries({ queryKey: ["alert-events-full"] })
    },
  })

  function setField(field: string, value: string | number | boolean | null) {
    setForm((prev) => {
      const next = { ...prev, [field]: value }
      if (field === "rule_type") next.metric = METRICS[value as string]?.[0] ?? ""
      return next
    })
  }

  const isTextMetric = form.metric === "flood_risk" || form.metric === "drought_risk" || form.metric === "news_sentiment"
  const showTrendWindow = TREND_WINDOW_METRICS.has(form.metric)

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <CardTitle>Alert Rules</CardTitle>
              <CardDescription>Rules are evaluated every 15 minutes by the scheduler</CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => checkMutation.mutate()}
                disabled={checkMutation.isPending}
              >
                <Zap size={14} />
                {checkMutation.isPending ? "Checking…" : "Check Now"}
              </Button>
              <Button size="sm" onClick={() => setOpen(true)}>
                <Plus size={14} />
                New Rule
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {rules.isLoading && <p className="text-sm text-muted-foreground">Loading rules…</p>}
          {rules.data?.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">No rules configured.</p>
          )}
          <div className="space-y-2">
            {rules.data?.map((rule) => (
              <div
                key={rule.id}
                className={`flex items-center gap-3 p-3 rounded-lg border transition-colors ${
                  rule.enabled ? "border-border bg-card" : "border-dashed border-border bg-muted/30"
                }`}
              >
                <Switch
                  checked={rule.enabled}
                  onCheckedChange={() => toggleMutation.mutate(rule)}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`text-sm font-medium ${rule.enabled ? "text-foreground" : "text-muted-foreground"}`}>
                      {rule.name}
                    </span>
                    <RuleTypeChip type={rule.rule_type} />
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {rule.metric} {rule.comparison}{" "}
                    {rule.threshold_text ?? rule.threshold_value}
                    {rule.email_recipients && ` · ${rule.email_recipients}`}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="icon"
                  className="text-muted-foreground hover:text-destructive shrink-0"
                  onClick={() => deleteMutation.mutate(rule.id)}
                >
                  <Trash2 size={15} />
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* New rule dialog */}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>New Alert Rule</DialogTitle>
          </DialogHeader>
          <form
            onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form) }}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label>Rule name</Label>
              <Input
                value={form.name}
                onChange={(e) => setField("name", e.target.value)}
                placeholder="e.g. FX rate below 285"
                required
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label>Type</Label>
                <Select value={form.rule_type} onValueChange={(v) => setField("rule_type", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {RULE_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Metric</Label>
                <Select value={form.metric} onValueChange={(v) => setField("metric", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {(METRICS[form.rule_type] ?? []).map((m) => (
                      <SelectItem key={m} value={m}>{METRIC_LABELS[m] ?? m}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Comparison</Label>
                <Select value={form.comparison} onValueChange={(v) => setField("comparison", v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="lt">less than (&lt;)</SelectItem>
                    <SelectItem value="gt">greater than (&gt;)</SelectItem>
                    <SelectItem value="eq">equals</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {isTextMetric ? (
                <div className="space-y-2">
                  <Label>Threshold (text)</Label>
                  <Input
                    value={form.threshold_text ?? ""}
                    onChange={(e) => setField("threshold_text", e.target.value)}
                    placeholder={
                      form.metric === "news_sentiment" ? "e.g. COPPER:0.60"
                      : form.metric === "drought_risk"  ? "e.g. HIGH"
                      : "e.g. HIGH"
                    }
                  />
                </div>
              ) : (
                <div className="space-y-2">
                  <Label>Threshold value{form.metric === "heatwave" ? " (°C)" : form.metric === "usd_lkr_change_pct" ? " (%)" : ""}</Label>
                  <Input
                    type="number"
                    step="any"
                    value={form.threshold_value ?? ""}
                    onChange={(e) => setField("threshold_value", parseFloat(e.target.value))}
                  />
                </div>
              )}
              <div className="space-y-2">
                <Label>Email recipients</Label>
                <Input
                  value={form.email_recipients ?? ""}
                  onChange={(e) => setField("email_recipients", e.target.value)}
                  placeholder="comma-separated (optional)"
                />
              </div>
            </div>
            {showTrendWindow && (
              <div className="space-y-2">
                <Label>Sustained for (hours) <span className="text-muted-foreground font-normal">— optional, enables trend alert</span></Label>
                <Input
                  type="number"
                  min="1"
                  step="1"
                  value={form.trend_window_hours ?? ""}
                  onChange={(e) => setField("trend_window_hours", e.target.value ? parseInt(e.target.value) : null)}
                  placeholder="e.g. 48 — leave blank for snapshot check"
                  className="max-w-xs"
                />
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? "Saving…" : "Save Rule"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function AppSettingsTab() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["app-settings"],
    queryFn: fetchAppSettings,
    staleTime: 30_000,
  })

  const envRows = data
    ? [
        { key: "DEBUG",             value: String(data.debug),             desc: "Debug mode — uses generated data, skips live API calls" },
        { key: "FX_API_KEY",        value: data.fx_api_key_configured ? "••••••••" : "not set", desc: "exchangerate-api.com key for live USD/LKR rates" },
        { key: "NEWSAPI_KEY",       value: data.newsapi_key_configured ? "••••••••" : "not set", desc: "newsapi.org key for live news feed" },
        { key: "SENTIMENT_ENABLED", value: String(data.sentiment_enabled),  desc: "Enable/disable FinBERT sentiment scoring" },
        { key: "DATABASE_URL",      value: data.database_url,               desc: "Active database connection (credentials stripped)" },
      ]
    : []

  return (
    <Card>
      <CardHeader>
        <CardTitle>Application Settings</CardTitle>
        <CardDescription>Runtime configuration — edit .env on the server to persist changes</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        {isLoading && <p className="text-sm text-muted-foreground">Loading settings…</p>}
        {isError  && <p className="text-sm text-destructive">Could not load settings from backend.</p>}

        {data && (
          <>
            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Data Collection</h3>
              <Separator />
              {envRows.map(({ key, value, desc }) => (
                <div key={key} className="flex items-start justify-between gap-4 py-1.5">
                  <div>
                    <p className="text-sm font-medium font-mono">{key}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
                  </div>
                  <Badge
                    variant="secondary"
                    className={`font-mono shrink-0 ${
                      value === "false" || value === "not set"
                        ? "text-destructive"
                        : value === "true"
                        ? "text-[var(--c-green)]"
                        : ""
                    }`}
                  >
                    {value}
                  </Badge>
                </div>
              ))}
            </div>

            <div className="space-y-3">
              <h3 className="text-sm font-semibold">Scheduler</h3>
              <Separator />
              {data.scheduler_jobs.map((job) => (
                <div key={job.id} className="flex items-center justify-between py-1">
                  <span className="text-sm text-muted-foreground">{job.name}</span>
                  <span className="text-sm font-medium">{job.interval}</span>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="rounded-lg border border-dashed border-border p-4 text-sm text-muted-foreground">
          Settings are read from <code className="text-xs bg-muted px-1 py-0.5 rounded">backend/.env</code> at startup.
          Restart the backend after editing environment variables.
        </div>
      </CardContent>
    </Card>
  )
}

function DataSourceAuditTab() {
  const audit = useQuery({
    queryKey: ["datasource-audit"],
    queryFn: getDataSourceAudit,
    staleTime: 60_000,
  })

  function statusIcon(status: string) {
    if (status === "ok") return <CheckCircle2 size={16} className="text-green-500 shrink-0" />
    if (status === "degraded") return <AlertTriangle size={16} className="text-yellow-500 shrink-0" />
    return <XCircle size={16} className="text-red-500 shrink-0" />
  }

  function fragilityBadge(rating: DataSourceStatus["fragility_rating"]) {
    const map = {
      LOW: "bg-green-500/15 text-green-600 dark:text-green-400",
      MEDIUM: "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400",
      HIGH: "bg-red-500/15 text-red-500",
    }
    return (
      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${map[rating]}`}>
        {rating}
      </span>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity size={18} />
            Data Source Reliability Audit
          </CardTitle>
          <CardDescription>
            Review which external APIs are in use, their fragility, and recommended paid fallbacks for production.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {audit.isLoading && <p className="text-sm text-muted-foreground">Loading audit…</p>}
          {audit.isError && <p className="text-sm text-red-500">Could not load audit data.</p>}

          {audit.data && (
            <div className="space-y-4">
              {audit.data.sources.map((src) => (
                <div key={src.source_name} className="rounded-lg border border-[var(--c-border)] p-4 space-y-2">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2">
                      {statusIcon(src.status)}
                      <span className="font-medium text-sm text-foreground">{src.source_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {fragilityBadge(src.fragility_rating)}
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        src.status === "ok"
                          ? "bg-green-500/15 text-green-600 dark:text-green-400"
                          : src.status === "degraded"
                          ? "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400"
                          : "bg-red-500/15 text-red-500"
                      }`}>
                        {src.status.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
                    <div>
                      <p className="text-muted-foreground uppercase tracking-wide font-semibold mb-0.5">Data points (24h)</p>
                      <p className="font-medium">{src.data_points_24h}</p>
                    </div>
                    <div>
                      <p className="text-muted-foreground uppercase tracking-wide font-semibold mb-0.5">Last reading</p>
                      <p className="font-medium">
                        {src.last_data_timestamp
                          ? new Date(src.last_data_timestamp).toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
                          : "No data"}
                      </p>
                    </div>
                    <div>
                      <p className="text-muted-foreground uppercase tracking-wide font-semibold mb-0.5">Paid fallback</p>
                      <p className="font-medium">{src.paid_fallback ?? "None needed"}</p>
                    </div>
                  </div>

                  <p className="text-xs text-muted-foreground border-t border-[var(--c-border)] pt-2">
                    <span className="font-semibold text-foreground">Risk: </span>{src.fragility_reason}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    <span className="font-semibold text-foreground">Note: </span>{src.notes}
                  </p>
                </div>
              ))}

              <p className="text-xs text-muted-foreground text-right">
                Audited at {new Date(audit.data.audit_timestamp).toLocaleString("en-GB")}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function ModelTuningTab() {
  const [batchSize, setBatchSize] = useState("50")
  const [scored, setScored] = useState<number | null>(null)
  const [scoring, setScoring] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function scoreNow() {
    setScoring(true)
    setError(null)
    try {
      const data = await apiPost<{ scored: number }>("/api/v1/news/score-now", {})
      setScored(data.scored)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setScoring(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Brain size={18} />
            FinBERT Sentiment Model
          </CardTitle>
          <CardDescription>
            ProsusAI/finbert — pre-trained financial sentiment model, CPU inference
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-2 gap-4 text-sm">
            {[
              ["Model", "ProsusAI/finbert"],
              ["Device", "CPU (no GPU required)"],
              ["Labels", "POSITIVE · NEGATIVE · NEUTRAL"],
              ["Max token length", "512"],
              ["Auto-scoring", "Every 2 hours (scheduler)"],
              ["Toggle", "SENTIMENT_ENABLED in .env"],
            ].map(([k, v]) => (
              <div key={k} className="flex flex-col gap-0.5">
                <span className="text-xs text-muted-foreground uppercase tracking-wide font-semibold">{k}</span>
                <span className="font-medium">{v}</span>
              </div>
            ))}
          </div>

          <Separator />

          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Manual Scoring</h3>
            <div className="flex items-end gap-3">
              <div className="space-y-2 w-40">
                <Label>Batch size</Label>
                <Input
                  type="number"
                  min="1"
                  max="500"
                  value={batchSize}
                  onChange={(e) => setBatchSize(e.target.value)}
                />
              </div>
              <Button onClick={scoreNow} disabled={scoring} variant="outline">
                <Zap size={14} />
                {scoring ? "Scoring…" : "Score unscored news"}
              </Button>
            </div>
            {scored !== null && (
              <p className="text-sm text-[var(--c-green)]">
                Scored {scored} article{scored !== 1 ? "s" : ""} successfully.
              </p>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <Separator />

          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Sentiment-based alert format</h3>
            <div className="rounded-md bg-muted p-3 font-mono text-xs space-y-1">
              <p>Rule type: SENTIMENT_NEGATIVE</p>
              <p>Metric: news_sentiment</p>
              <p>Comparison: gt</p>
              <p>Threshold (text): COPPER:0.60</p>
            </div>
            <p className="text-xs text-muted-foreground">
              Triggers when &gt;60% of COPPER news in the last 24h is negative.
              Format: <code className="bg-muted px-1 rounded">TOPIC:fraction</code> (0–1).
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
