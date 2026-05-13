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
} from "recharts";
import { fetchHistory, fetchSummary } from "../../api/commodities";
import styles from "./CommodityPanel.module.css";

const SYMBOLS = ["COPPER", "ALUMINIUM"] as const;
const DAY_OPTIONS = [30, 60, 90] as const;
const COLORS: Record<string, string> = {
  COPPER: "#f97316",
  ALUMINIUM: "#a78bfa",
};

function fmt(iso: string) {
  return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

export function CommodityPanel() {
  const [symbol, setSymbol] = useState<"COPPER" | "ALUMINIUM">("COPPER");
  const [days, setDays] = useState<30 | 60 | 90>(30);

  const history = useQuery({
    queryKey: ["commodity-history", symbol, days],
    queryFn: () => fetchHistory(symbol, days),
    refetchInterval: 300_000,
  });

  const summary = useQuery({
    queryKey: ["commodity-summary", symbol],
    queryFn: () => fetchSummary(symbol),
    refetchInterval: 300_000,
  });

  const chartData = (history.data ?? []).map((r) => ({
    date: fmt(r.timestamp),
    price: r.price_usd,
  }));

  const color = COLORS[symbol];

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <div className={styles.symbolTabs}>
          {SYMBOLS.map((s) => (
            <button
              key={s}
              className={symbol === s ? styles.activeSymbol : styles.symbolTab}
              style={symbol === s ? { background: COLORS[s], borderColor: COLORS[s] } : undefined}
              onClick={() => setSymbol(s)}
            >
              {s}
            </button>
          ))}
        </div>
        <div className={styles.dayTabs}>
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
          <Stat label="Current (USD/t)" value={summary.data.current_price_usd.toLocaleString()} />
          <Stat
            label="24h Change"
            value={`${summary.data.change_24h > 0 ? "+" : ""}${summary.data.change_24h.toFixed(0)} (${summary.data.change_24h_pct.toFixed(2)}%)`}
            color={summary.data.change_24h >= 0 ? "var(--green)" : "var(--red)"}
          />
          <Stat label="30d High" value={summary.data.high_30d.toLocaleString()} />
          <Stat label="30d Low" value={summary.data.low_30d.toLocaleString()} />
        </div>
      )}

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            dataKey="date"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            width={64}
            tickFormatter={(v) => `$${(v as number).toLocaleString()}`}
          />
          <Tooltip
            formatter={(v) => [`$${(v as number).toLocaleString()}`, "Price USD/t"]}
            contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8 }}
            labelStyle={{ color: "var(--text-muted)" }}
          />
          <Line type="monotone" dataKey="price" stroke={color} dot={false} strokeWidth={2} />
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
