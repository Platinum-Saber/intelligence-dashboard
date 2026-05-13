import { useQuery } from "@tanstack/react-query";
import { MapContainer, TileLayer, CircleMarker, Tooltip } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { fetchWeatherLatest } from "../../api/weather";
import type { WeatherLatest } from "../../types";
import styles from "./WeatherMap.module.css";

// Static coordinates for Sri Lanka districts
const SL_COORDS: Record<string, [number, number]> = {
  "Western":       [6.9271, 79.8612],
  "Southern":      [6.0535, 80.2210],
  "Northern":      [9.6615, 80.0255],
  "Eastern":       [8.5874, 81.2152],
  "North Western": [7.9403, 80.3500],
  "North Central": [8.3347, 80.4000],
  "Uva":           [6.9934, 81.0550],
  "Sabaragamuwa":  [6.6828, 80.3992],
  "Central":       [7.2906, 80.6337],
};

const RISK_COLOR: Record<string, string> = {
  LOW:      "#22c55e",
  MEDIUM:   "#eab308",
  HIGH:     "#f97316",
  CRITICAL: "#ef4444",
};

function PortRow({ loc }: { loc: WeatherLatest }) {
  const color = RISK_COLOR[loc.flood_risk] ?? "#8892a4";
  return (
    <div className={styles.portRow}>
      <span className={styles.portDot} style={{ background: color }} />
      <span className={styles.portName}>{loc.location_name}</span>
      <span className={styles.portRain}>{loc.rainfall_mm != null ? `${loc.rainfall_mm} mm` : "—"}</span>
      <span style={{ color, fontWeight: 600, fontSize: 11 }}>{loc.flood_risk}</span>
    </div>
  );
}

export function WeatherMap() {
  const { data, isLoading } = useQuery({
    queryKey: ["weather-latest"],
    queryFn: fetchWeatherLatest,
    refetchInterval: 300_000,
  });

  const districts = data?.filter((l) => l.location_type === "sri_lanka_district") ?? [];
  const ports = data?.filter((l) => l.location_type === "supplier_port") ?? [];

  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>Weather & Logistics Risk</h2>

      {isLoading && <p className={styles.muted}>Loading…</p>}

      <div className={styles.mapWrap}>
        <MapContainer
          center={[7.87, 80.77]}
          zoom={7}
          style={{ height: "100%", width: "100%", borderRadius: 8 }}
          scrollWheelZoom={false}
          attributionControl={false}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='© OpenStreetMap'
          />
          {districts.map((loc) => {
            const coords = SL_COORDS[loc.location_name];
            if (!coords) return null;
            return (
              <CircleMarker
                key={loc.location_name}
                center={coords}
                radius={12}
                pathOptions={{
                  fillColor: RISK_COLOR[loc.flood_risk] ?? "#8892a4",
                  fillOpacity: 0.85,
                  color: "#fff",
                  weight: 1.5,
                }}
              >
                <Tooltip permanent={false} direction="top">
                  <strong>{loc.location_name}</strong>
                  <br />
                  Rainfall: {loc.rainfall_mm != null ? `${loc.rainfall_mm} mm` : "—"}
                  <br />
                  Risk: <strong>{loc.flood_risk}</strong>
                  {loc.temperature_c != null && <><br />Temp: {loc.temperature_c}°C</>}
                </Tooltip>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      <section>
        <h3 className={styles.sectionTitle}>Supplier Ports</h3>
        {ports.map((p) => <PortRow key={p.location_name} loc={p} />)}
      </section>

      <div className={styles.legend}>
        {Object.entries(RISK_COLOR).map(([level, color]) => (
          <span key={level} className={styles.legendItem}>
            <span className={styles.legendDot} style={{ background: color }} />
            {level}
          </span>
        ))}
      </div>
    </div>
  );
}
