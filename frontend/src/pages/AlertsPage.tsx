import { useState, useMemo } from "react"
import { useQuery } from "@tanstack/react-query"
import { fetchAlertEvents, fetchAlertRules } from "@/api/alerts"
import type { AlertEvent, AlertRule } from "@/types"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Bell, Search } from "lucide-react"

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60_000)
  const h = Math.floor(diff / 3_600_000)
  const d = Math.floor(diff / 86_400_000)
  if (m < 1) return "just now"
  if (m < 60) return `${m}m ago`
  if (h < 24) return `${h}h ago`
  return `${d}d ago`
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  })
}

/** Returns Tailwind classes for row bg, dot, and badge based on alert type + message content */
function getSeverity(ruleType: string | undefined, message: string): {
  rowBg: string
  dot: string
  badgeClass: string
  label: string
} {
  const msg = message.toLowerCase()

  if (ruleType === "WEATHER_RISK" || msg.includes("flood")) {
    if (msg.includes("critical"))
      return { rowBg: "bg-red-500/8 dark:bg-red-500/10",      dot: "bg-red-500",    badgeClass: "bg-red-500/15 text-red-500",    label: "Critical" }
    if (msg.includes("high"))
      return { rowBg: "bg-orange-500/8 dark:bg-orange-500/10", dot: "bg-orange-500", badgeClass: "bg-orange-500/15 text-orange-500", label: "High Risk" }
    if (msg.includes("medium"))
      return { rowBg: "bg-yellow-500/8 dark:bg-yellow-500/10", dot: "bg-yellow-500", badgeClass: "bg-yellow-500/15 text-yellow-600 dark:text-yellow-400", label: "Medium" }
    return   { rowBg: "bg-yellow-500/5",                        dot: "bg-yellow-400", badgeClass: "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400", label: "Low" }
  }

  if (ruleType === "SENTIMENT_NEGATIVE" || msg.includes("sentiment") || msg.includes("negative"))
    return { rowBg: "bg-red-500/8 dark:bg-red-500/10",      dot: "bg-red-500",    badgeClass: "bg-red-500/15 text-red-500",    label: "Negative" }

  if (ruleType === "COMMODITY_DIP") {
    if (msg.includes("fell") || msg.includes("below") || msg.includes("dip") || msg.includes("dropped"))
      return { rowBg: "bg-green-500/6 dark:bg-green-500/8",  dot: "bg-green-500",  badgeClass: "bg-green-500/15 text-green-600 dark:text-green-400", label: "Favourable" }
    return { rowBg: "bg-orange-500/8 dark:bg-orange-500/10", dot: "bg-orange-500", badgeClass: "bg-orange-500/15 text-orange-500", label: "Price Alert" }
  }

  if (ruleType === "FX_THRESHOLD" || msg.includes("usd") || msg.includes("lkr") || msg.includes("fx") || msg.includes("exchange"))
    return { rowBg: "",                                        dot: "bg-blue-500",   badgeClass: "bg-blue-500/15 text-blue-500",  label: "FX" }

  return { rowBg: "",                                          dot: "bg-blue-400",   badgeClass: "bg-blue-500/10 text-blue-400",  label: "Info" }
}

const LIMIT_OPTIONS = [25, 50, 100, 200]

export function AlertsPage() {
  const [limit, setLimit] = useState(50)
  const [search, setSearch] = useState("")

  const events = useQuery({
    queryKey: ["alert-events-full", limit],
    queryFn: () => fetchAlertEvents(limit),
    refetchInterval: 60_000,
  })

  const rules = useQuery({
    queryKey: ["alert-rules"],
    queryFn: fetchAlertRules,
  })

  const ruleMap = useMemo(() => {
    const m: Record<number, AlertRule> = {}
    rules.data?.forEach((r) => { m[r.id] = r })
    return m
  }, [rules.data])

  const filtered = (events.data ?? []).filter((ev: AlertEvent) =>
    search === "" ||
    ev.rule_name.toLowerCase().includes(search.toLowerCase()) ||
    ev.message.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <CardTitle>Alert Event Log</CardTitle>
              <CardDescription>Historical record of all triggered alert rules</CardDescription>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search events…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 w-56"
                />
              </div>
              <select
                className="h-10 rounded-md border border-[var(--c-border)] bg-background px-3 text-sm text-foreground"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
              >
                {LIMIT_OPTIONS.map((n) => (
                  <option key={n} value={n}>Last {n}</option>
                ))}
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Legend */}
          <div className="flex flex-wrap gap-3 mb-4 text-xs">
            {[
              { dot: "bg-red-500",    label: "Critical / Negative sentiment" },
              { dot: "bg-orange-500", label: "High risk / Price rise" },
              { dot: "bg-yellow-400", label: "Medium / Low risk" },
              { dot: "bg-green-500",  label: "Favourable (price drop)" },
              { dot: "bg-blue-500",   label: "FX / Informational" },
            ].map(({ dot, label }) => (
              <span key={label} className="flex items-center gap-1.5 text-muted-foreground">
                <span className={`w-2 h-2 rounded-full shrink-0 ${dot}`} />
                {label}
              </span>
            ))}
          </div>

          {events.isLoading && (
            <div className="flex items-center justify-center py-16 text-muted-foreground text-sm">
              Loading events…
            </div>
          )}

          {!events.isLoading && filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
              <Bell size={32} strokeWidth={1.5} />
              <p className="text-sm">
                {search ? "No events match your search." : "No alert events recorded yet."}
              </p>
              <p className="text-xs">Alert rules are evaluated every 15 minutes.</p>
            </div>
          )}

          {filtered.length > 0 && (
            <div className="overflow-x-auto -mx-1">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--c-border)]">
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-6" />
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-40">Time</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-36">Type</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-44">Rule</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide">Message</th>
                    <th className="text-left py-2.5 px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wide w-24">Notified</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((ev: AlertEvent) => {
                    const rule = ruleMap[ev.rule_id]
                    const { rowBg, dot, badgeClass, label } = getSeverity(rule?.rule_type, ev.message)
                    return (
                      <tr
                        key={ev.id}
                        className={`border-b border-[var(--c-border)] transition-colors hover:bg-muted/30 ${rowBg}`}
                      >
                        {/* Severity dot */}
                        <td className="py-3 px-3">
                          <span className={`block w-2 h-2 rounded-full mx-auto ${dot}`} />
                        </td>
                        {/* Time */}
                        <td className="py-3 px-3">
                          <div className="font-medium text-foreground">{timeAgo(ev.triggered_at)}</div>
                          <div className="text-xs text-muted-foreground mt-0.5">{formatDate(ev.triggered_at)}</div>
                        </td>
                        {/* Type badge */}
                        <td className="py-3 px-3">
                          <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold ${badgeClass}`}>
                            {label}
                          </span>
                        </td>
                        {/* Rule name */}
                        <td className="py-3 px-3">
                          <span className="font-medium text-foreground line-clamp-2">{ev.rule_name}</span>
                          {rule && (
                            <span className="text-[10px] text-muted-foreground uppercase tracking-wide">{rule.rule_type}</span>
                          )}
                        </td>
                        {/* Message */}
                        <td className="py-3 px-3">
                          <p className="text-muted-foreground">{ev.message}</p>
                        </td>
                        {/* Notified */}
                        <td className="py-3 px-3">
                          <Badge variant={ev.notified ? "success" : "neutral"}>
                            {ev.notified ? "Sent" : "Pending"}
                          </Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {filtered.length > 0 && (
            <div className="mt-3 text-xs text-muted-foreground text-right">
              Showing {filtered.length} event{filtered.length !== 1 ? "s" : ""}
              {search && ` (filtered from ${events.data?.length ?? 0})`}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
