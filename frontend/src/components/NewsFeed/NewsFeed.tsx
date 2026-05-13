import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchNews } from "../../api/news";
import styles from "./NewsFeed.module.css";

const TOPICS = ["ALL", "FX", "COPPER", "ALUMINIUM", "TRADE", "LOGISTICS"] as const;

const TOPIC_COLOR: Record<string, string> = {
  FX: "var(--c-primary)",
  COPPER: "var(--orange)",
  ALUMINIUM: "#a78bfa",
  TRADE: "var(--yellow)",
  LOGISTICS: "var(--green)",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return "< 1h ago";
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function NewsFeed() {
  const [topic, setTopic] = useState<string>("ALL");

  const news = useQuery({
    queryKey: ["news", topic],
    queryFn: () => fetchNews(7, topic === "ALL" ? undefined : topic),
    refetchInterval: 300_000,
  });

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>News Feed</h2>
        <div className={styles.topicBar}>
          {TOPICS.map((t) => (
            <button
              key={t}
              className={topic === t ? styles.activeChip : styles.chip}
              style={topic === t && t !== "ALL" ? { background: TOPIC_COLOR[t], borderColor: TOPIC_COLOR[t] } : undefined}
              onClick={() => setTopic(t)}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      <div className={styles.list}>
        {news.isLoading && <p className={styles.muted}>Loading…</p>}
        {news.data?.map((item) => (
          <div key={item.id} className={styles.item}>
            <div className={styles.itemMeta}>
              {item.topic && (
                <span className={styles.topicTag} style={{ color: TOPIC_COLOR[item.topic] ?? "var(--text-muted)" }}>
                  {item.topic}
                </span>
              )}
              {item.sentiment && (
                <span
                  className={styles.sentimentBadge}
                  style={{
                    color: item.sentiment === "POSITIVE" ? "var(--green)"
                         : item.sentiment === "NEGATIVE" ? "var(--red)"
                         : "var(--text-muted)",
                  }}
                >
                  {item.sentiment === "POSITIVE" ? "↑" : item.sentiment === "NEGATIVE" ? "↓" : "–"}
                  {" "}{item.sentiment}
                </span>
              )}
              <span className={styles.time}>{timeAgo(item.published_at)}</span>
            </div>
            <p className={styles.headline}>{item.headline}</p>
            {item.summary && <p className={styles.summary}>{item.summary}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
