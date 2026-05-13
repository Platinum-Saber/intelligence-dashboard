import { useQuery } from "@tanstack/react-query";
import { fetchFXSummary } from "../../api/fx";
import { fetchSummary as fetchCommoditySummary } from "../../api/commodities";
import { fetchHighRisk } from "../../api/weather";
import { fetchNews } from "../../api/news";
import styles from "./Overview.module.css";

function StatCard({
  label,
  value,
  sub,
  trend,
}: {
  label: string;
  value: string;
  sub?: string;
  trend?: "up" | "down" | "neutral";
}) {
  const trendColor =
    trend === "up" ? "var(--green)" : trend === "down" ? "var(--red)" : "var(--text-muted)";
  return (
    <div className={styles.card}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{value}</span>
      {sub && (
        <span className={styles.sub} style={{ color: trendColor }}>
          {sub}
        </span>
      )}
    </div>
  );
}

export function Overview() {
  const fx = useQuery({ queryKey: ["fx-summary"], queryFn: fetchFXSummary, refetchInterval: 60_000 });
  const copper = useQuery({ queryKey: ["copper-summary"], queryFn: () => fetchCommoditySummary("COPPER"), refetchInterval: 60_000 });
  const aluminium = useQuery({ queryKey: ["aluminium-summary"], queryFn: () => fetchCommoditySummary("ALUMINIUM"), refetchInterval: 60_000 });
  const highRisk = useQuery({ queryKey: ["weather-high-risk"], queryFn: fetchHighRisk, refetchInterval: 300_000 });
  const news = useQuery({ queryKey: ["news-latest"], queryFn: () => fetchNews(1), refetchInterval: 300_000 });

  const fxTrend = (fx.data?.change_24h ?? 0) > 0 ? "up" : (fx.data?.change_24h ?? 0) < 0 ? "down" : "neutral";

  return (
    <div className={styles.grid}>
      <StatCard
        label="USD / LKR"
        value={fx.data ? fx.data.current.toFixed(2) : "—"}
        sub={fx.data ? `${fx.data.change_24h_pct > 0 ? "+" : ""}${fx.data.change_24h_pct.toFixed(2)}% 24h` : undefined}
        trend={fxTrend}
      />
      <StatCard
        label="LME Copper (USD/t)"
        value={copper.data ? copper.data.current_price_usd.toLocaleString() : "—"}
        sub={copper.data ? `${copper.data.change_24h_pct > 0 ? "+" : ""}${copper.data.change_24h_pct.toFixed(2)}% 24h` : undefined}
        trend={copper.data ? (copper.data.change_24h_pct >= 0 ? "up" : "down") : "neutral"}
      />
      <StatCard
        label="LME Aluminium (USD/t)"
        value={aluminium.data ? aluminium.data.current_price_usd.toLocaleString() : "—"}
        sub={aluminium.data ? `${aluminium.data.change_24h_pct > 0 ? "+" : ""}${aluminium.data.change_24h_pct.toFixed(2)}% 24h` : undefined}
        trend={aluminium.data ? (aluminium.data.change_24h_pct >= 0 ? "up" : "down") : "neutral"}
      />
      <StatCard
        label="High-Risk Locations"
        value={highRisk.data ? String(highRisk.data.length) : "—"}
        sub={highRisk.data && highRisk.data.length > 0 ? highRisk.data.map((l) => l.location_name).slice(0, 2).join(", ") : "No active warnings"}
        trend={highRisk.data && highRisk.data.length > 0 ? "down" : "neutral"}
      />
      <StatCard
        label="News Today"
        value={news.data ? String(news.data.length) : "—"}
        sub="supply-chain relevant articles"
        trend="neutral"
      />
    </div>
  );
}
