import { useQuery } from "@tanstack/react-query";
import { fetchWeatherLatest } from "../../api/weather";
import type { WeatherLatest } from "../../types";
import styles from "./WeatherPanel.module.css";

const RISK_COLOR: Record<string, string> = {
  LOW: "var(--green)",
  MEDIUM: "var(--yellow)",
  HIGH: "var(--orange)",
  CRITICAL: "var(--red)",
};

function LocationRow({ loc }: { loc: WeatherLatest }) {
  return (
    <div className={styles.row}>
      <span className={styles.name}>{loc.location_name}</span>
      <span className={styles.rain}>{loc.rainfall_mm != null ? `${loc.rainfall_mm} mm` : "—"}</span>
      <span className={styles.badge} style={{ color: RISK_COLOR[loc.flood_risk] ?? "var(--text-muted)" }}>
        {loc.flood_risk}
      </span>
    </div>
  );
}

export function WeatherPanel() {
  const { data, isLoading } = useQuery({
    queryKey: ["weather-latest"],
    queryFn: fetchWeatherLatest,
    refetchInterval: 300_000,
  });

  const slDistricts = data?.filter((l) => l.location_type === "sri_lanka_district") ?? [];
  const ports = data?.filter((l) => l.location_type === "supplier_port") ?? [];

  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>Weather & Logistics Risk</h2>

      {isLoading && <p className={styles.muted}>Loading…</p>}

      <section>
        <h3 className={styles.sectionTitle}>Sri Lanka Districts</h3>
        <div className={styles.tableHeader}>
          <span>District</span><span>Rainfall</span><span>Risk</span>
        </div>
        {slDistricts.map((loc) => (
          <LocationRow key={loc.location_name} loc={loc} />
        ))}
      </section>

      <section style={{ marginTop: 16 }}>
        <h3 className={styles.sectionTitle}>Supplier Ports</h3>
        <div className={styles.tableHeader}>
          <span>Port</span><span>Rainfall</span><span>Risk</span>
        </div>
        {ports.map((loc) => (
          <LocationRow key={loc.location_name} loc={loc} />
        ))}
      </section>
    </div>
  );
}
