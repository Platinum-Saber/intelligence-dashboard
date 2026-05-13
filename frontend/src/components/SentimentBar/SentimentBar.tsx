import { useQuery } from "@tanstack/react-query";
import { fetchSentimentSummary } from "../../api/news";
import type { SentimentSummary } from "../../types";
import styles from "./SentimentBar.module.css";

const TOPIC_ORDER = ["FX", "COPPER", "ALUMINIUM", "TRADE", "LOGISTICS"];
const TOPIC_COLOR: Record<string, string> = {
  FX:        "var(--accent)",
  COPPER:    "var(--orange)",
  ALUMINIUM: "#a78bfa",
  TRADE:     "var(--yellow)",
  LOGISTICS: "var(--green)",
};

function Bar({ s }: { s: SentimentSummary }) {
  const total = s.positive + s.negative + s.neutral + s.unscored;
  if (total === 0) return null;
  const pctPos  = (s.positive / total) * 100;
  const pctNeg  = (s.negative / total) * 100;
  const pctNeut = (s.neutral  / total) * 100;

  return (
    <div className={styles.row}>
      <span className={styles.topic} style={{ color: TOPIC_COLOR[s.topic] }}>{s.topic}</span>
      <div className={styles.barTrack}>
        <div className={styles.barPos}  style={{ width: `${pctPos}%` }}  title={`Positive: ${s.positive}`} />
        <div className={styles.barNeut} style={{ width: `${pctNeut}%` }} title={`Neutral: ${s.neutral}`} />
        <div className={styles.barNeg}  style={{ width: `${pctNeg}%` }}  title={`Negative: ${s.negative}`} />
      </div>
      <span className={styles.counts}>{s.positive}↑ {s.neutral}– {s.negative}↓</span>
    </div>
  );
}

export function SentimentBar() {
  const { data, isLoading } = useQuery({
    queryKey: ["sentiment-summary"],
    queryFn: () => fetchSentimentSummary(7),
    refetchInterval: 300_000,
  });

  const sorted = (data ?? []).sort(
    (a, b) => TOPIC_ORDER.indexOf(a.topic) - TOPIC_ORDER.indexOf(b.topic)
  );

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>News Sentiment (7d)</h2>
        <div className={styles.legend}>
          <span className={styles.legendPos}>Positive</span>
          <span className={styles.legendNeut}>Neutral</span>
          <span className={styles.legendNeg}>Negative</span>
        </div>
      </div>

      {isLoading && <p className={styles.muted}>Loading…</p>}

      <div className={styles.bars}>
        {sorted.map((s) => <Bar key={s.topic} s={s} />)}
      </div>

      <p className={styles.hint}>
        Sentiment scored by FinBERT on headline text. Treat as a directional signal, not a forecast.
      </p>
    </div>
  );
}
