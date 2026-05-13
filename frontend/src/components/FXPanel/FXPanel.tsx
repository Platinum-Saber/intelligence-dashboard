import { useState } from "react";
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
} from "recharts";
import { fetchFXHistory, fetchFXSummary } from "../../api/fx";
import styles from "./FXPanel.module.css";

const DAY_OPTIONS = [30, 60, 90] as const;

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
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

  const chartData = (history.data ?? []).map((r) => ({
    date: fmt(r.timestamp),
    rate: r.usd_lkr,
  }));

  const avg = summary.data?.avg_30d;

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
            stroke="var(--c-primary)"
            dot={false}
            strokeWidth={2}
          />
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
