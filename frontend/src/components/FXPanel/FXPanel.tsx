import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Legend,
} from "recharts";
import { fetchFXHistory, fetchFXSummary } from "../../api/fx";
import { fetchCBSLHistory } from "../../api/cbsl";
import type { CBSLRateOut } from "../../api/cbsl";
import styles from "./FXPanel.module.css";

const DAY_OPTIONS = [30, 60, 90] as const;

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

/** Build step-function CBSL rate keyed by formatted date string, spanning to the next entry date. */
function buildCBSLSteps(
  cbslRates: CBSLRateOut[],
  marketDates: string[],
): Record<string, number> {
  if (!cbslRates.length || !marketDates.length) return {};
  // Sort ascending
  const sorted = [...cbslRates].sort(
    (a, b) => new Date(a.effective_date).getTime() - new Date(b.effective_date).getTime(),
  );
  const steps: Record<string, number> = {};
  for (const date of marketDates) {
    const d = new Date(date);
    // Find the most recent CBSL rate that took effect on or before this date
    let rate: number | null = null;
    for (const entry of sorted) {
      if (new Date(entry.effective_date) <= d) rate = entry.rate;
      else break;
    }
    if (rate !== null) steps[date] = rate;
  }
  return steps;
}

export function FXPanel() {
  const [days, setDays] = useState<30 | 60 | 90>(30);

  const history = useQuery({
    queryKey: ["fx-history", days],
    queryFn: () => fetchFXHistory(days),
    refetchInterval: 60_000,
  });

  const summary = useQuery({
    queryKey: ["fx-summary"],
    queryFn: fetchFXSummary,
    refetchInterval: 60_000,
  });

  const cbslHistory = useQuery({
    queryKey: ["cbsl-history", days],
    queryFn: () => fetchCBSLHistory(days),
    staleTime: 300_000,
  });

  const rawDates = useMemo(
    () => (history.data ?? []).map((r) => r.timestamp),
    [history.data],
  );

  const cbslSteps = useMemo(
    () => buildCBSLSteps(cbslHistory.data ?? [], rawDates),
    [cbslHistory.data, rawDates],
  );

  const chartData = (history.data ?? []).map((r) => ({
    date: fmt(r.timestamp),
    rate: r.usd_lkr,
    cbsl: cbslSteps[r.timestamp] ?? null,
  }));

  const avg = summary.data?.avg_30d;
  const hasCBSL = Object.keys(cbslSteps).length > 0;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>USD / LKR Exchange Rate</h2>
        <div className={styles.tabs}>
          {DAY_OPTIONS.map((d) => (
            <button
              key={d}
              className={days === d ? styles.activeTab : styles.tab}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {summary.data && (
        <div className={styles.stats}>
          <Stat label="Current" value={summary.data.current.toFixed(2)} />
          <Stat
            label="24h Change"
            value={`${summary.data.change_24h > 0 ? "+" : ""}${summary.data.change_24h.toFixed(2)} (${summary.data.change_24h_pct.toFixed(2)}%)`}
            color={summary.data.change_24h > 0 ? "var(--red)" : "var(--green)"}
          />
          <Stat label="30d High" value={summary.data.high_30d.toFixed(2)} />
          <Stat label="30d Low" value={summary.data.low_30d.toFixed(2)} />
          <Stat label="30d Avg" value={summary.data.avg_30d.toFixed(2)} />
        </div>
      )}

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--c-border)" />
          <XAxis
            dataKey="date"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            width={52}
          />
          <Tooltip
            contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--c-border)", borderRadius: 8 }}
            labelStyle={{ color: "var(--text-muted)" }}
          />
          {hasCBSL && (
            <Legend
              verticalAlign="top"
              align="right"
              wrapperStyle={{ fontSize: 11, color: "var(--text-muted)" }}
            />
          )}
          {avg && (
            <ReferenceLine
              y={avg}
              stroke="var(--c-primary)"
              strokeDasharray="4 4"
              label={{ value: `Avg ${avg.toFixed(1)}`, fill: "var(--c-primary)", fontSize: 11 }}
            />
          )}
          <Line
            type="monotone"
            dataKey="rate"
            name="Market Rate"
            stroke="var(--c-primary)"
            dot={false}
            strokeWidth={2}
          />
          {hasCBSL && (
            <Line
              type="stepAfter"
              dataKey="cbsl"
              name="CBSL Ref Rate"
              stroke="var(--c-gold)"
              strokeDasharray="6 3"
              dot={false}
              strokeWidth={2}
              connectNulls
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className={styles.stat}>
      <span className={styles.statLabel}>{label}</span>
      <span className={styles.statValue} style={color ? { color } : undefined}>{value}</span>
    </div>
  );
}
