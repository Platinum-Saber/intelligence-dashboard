import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { fetchCostHistory } from "../../api/calculator";
import styles from "./CostHistory.module.css";

const LKR_M = new Intl.NumberFormat("en-LK", { maximumFractionDigits: 1 });

const COLORS: Record<string, string> = {
  COPPER:    "#f97316",
  ALUMINIUM: "#a78bfa",
};

export function CostHistory() {
  const [material, setMaterial] = useState<"COPPER" | "ALUMINIUM">("COPPER");
  const [qty, setQty] = useState(50);
  const [days, setDays] = useState(90);

  const { data, isLoading } = useQuery({
    queryKey: ["cost-history", material, qty, days],
    queryFn: () => fetchCostHistory(material, qty, days),
    refetchInterval: 300_000,
  });

  const chartData = (data ?? []).map((p) => ({
    date: p.date.slice(5),           // "MM-DD"
    cost_m: p.landed_cost_lkr / 1_000_000,
    lme: p.lme_price_usd,
    fx: p.usd_lkr,
  }));

  const latest = data?.[data.length - 1];
  const earliest = data?.[0];
  const costChange = latest && earliest
    ? ((latest.landed_cost_lkr - earliest.landed_cost_lkr) / earliest.landed_cost_lkr) * 100
    : null;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>Historical Landed Cost</h2>
        <div className={styles.controls}>
          <select
            value={material}
            onChange={(e) => setMaterial(e.target.value as "COPPER" | "ALUMINIUM")}
            className={styles.select}
          >
            <option value="COPPER">Copper</option>
            <option value="ALUMINIUM">Aluminium</option>
          </select>
          <input
            type="number"
            min={1}
            max={5000}
            step={1}
            value={qty}
            onChange={(e) => setQty(parseInt(e.target.value) || 50)}
            className={styles.qtyInput}
            title="Order size (tonnes)"
          />
          <span className={styles.unit}>t</span>
          <select
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value))}
            className={styles.select}
          >
            <option value={30}>30d</option>
            <option value={60}>60d</option>
            <option value={90}>90d</option>
          </select>
        </div>
      </div>

      {latest && (
        <div className={styles.stats}>
          <div className={styles.stat}>
            <span className={styles.statLabel}>Latest (LKR mn)</span>
            <span className={styles.statValue}>
              {LKR_M.format(latest.landed_cost_lkr / 1_000_000)}
            </span>
          </div>
          {costChange !== null && (
            <div className={styles.stat}>
              <span className={styles.statLabel}>Change over period</span>
              <span
                className={styles.statValue}
                style={{ color: costChange > 0 ? "var(--red)" : "var(--green)" }}
              >
                {costChange > 0 ? "+" : ""}{costChange.toFixed(1)}%
              </span>
            </div>
          )}
          <div className={styles.stat}>
            <span className={styles.statLabel}>LME (USD/t)</span>
            <span className={styles.statValue}>${latest.lme_price_usd.toLocaleString()}</span>
          </div>
          <div className={styles.stat}>
            <span className={styles.statLabel}>USD/LKR</span>
            <span className={styles.statValue}>{latest.usd_lkr.toFixed(2)}</span>
          </div>
        </div>
      )}

      {isLoading && <p className={styles.muted}>Loading…</p>}

      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={COLORS[material]} stopOpacity={0.25} />
              <stop offset="95%" stopColor={COLORS[material]} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--c-border)" />
          <XAxis
            dataKey="date"
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "var(--text-muted)", fontSize: 11 }}
            width={56}
            tickFormatter={(v) => `${(v as number).toFixed(0)}M`}
          />
          <Tooltip
            formatter={(v) => [`LKR ${(v as number).toFixed(1)} Mn`, "Landed Cost"]}
            contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--c-border)", borderRadius: 8 }}
            labelStyle={{ color: "var(--text-muted)" }}
          />
          <Area
            type="monotone"
            dataKey="cost_m"
            stroke={COLORS[material]}
            fill="url(#costGrad)"
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>

      <p className={styles.hint}>
        Showing cost to import {qty} t of {material} — using daily LME close and end-of-day USD/LKR.
      </p>
    </div>
  );
}
