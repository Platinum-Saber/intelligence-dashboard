import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchAlertRules,
  fetchAlertEvents,
  createAlertRule,
  toggleAlertRule,
  deleteAlertRule,
  triggerManualCheck,
} from "../../api/alerts";
import type { AlertRule } from "../../types";
import styles from "./AlertsPanel.module.css";

const RULE_TYPES = ["FX_THRESHOLD", "COMMODITY_DIP", "WEATHER_RISK", "SENTIMENT_NEGATIVE"] as const;
const METRICS: Record<string, string[]> = {
  FX_THRESHOLD:      ["usd_lkr"],
  COMMODITY_DIP:     ["copper_price", "aluminium_price"],
  WEATHER_RISK:      ["flood_risk"],
  SENTIMENT_NEGATIVE: ["news_sentiment"],
};

const EMPTY_RULE: Omit<AlertRule, "id" | "created_at"> = {
  name: "",
  rule_type: "FX_THRESHOLD",
  metric: "usd_lkr",
  comparison: "lt",
  threshold_value: null,
  threshold_text: null,
  enabled: true,
  email_recipients: "",
};

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3_600_000);
  if (h < 1) return "< 1h ago";
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function AlertsPanel() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ ...EMPTY_RULE });

  const rules = useQuery({ queryKey: ["alert-rules"], queryFn: fetchAlertRules });
  const events = useQuery({ queryKey: ["alert-events"], queryFn: () => fetchAlertEvents(15), refetchInterval: 60_000 });

  const createMutation = useMutation({
    mutationFn: createAlertRule,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["alert-rules"] }); setShowForm(false); setForm({ ...EMPTY_RULE }); },
  });

  const toggleMutation = useMutation({
    mutationFn: toggleAlertRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteAlertRule,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-rules"] }),
  });

  const checkMutation = useMutation({
    mutationFn: triggerManualCheck,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alert-events"] }),
  });

  function handleFieldChange(field: string, value: string | number | boolean | null) {
    setForm((prev) => {
      const next = { ...prev, [field]: value };
      if (field === "rule_type") {
        next.metric = METRICS[value as string]?.[0] ?? "";
      }
      return next;
    });
  }

  const isTextMetric = form.metric === "flood_risk" || form.metric === "news_sentiment";

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>Alert Rules</h2>
        <div className={styles.headerActions}>
          <button className={styles.checkBtn} onClick={() => checkMutation.mutate()} disabled={checkMutation.isPending}>
            {checkMutation.isPending ? "Checking…" : "Check Now"}
          </button>
          <button className={styles.addBtn} onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "+ New Rule"}
          </button>
        </div>
      </div>

      {showForm && (
        <form
          className={styles.form}
          onSubmit={(e) => { e.preventDefault(); createMutation.mutate(form); }}
        >
          <label className={styles.field}>
            Name
            <input value={form.name} onChange={(e) => handleFieldChange("name", e.target.value)} required placeholder="e.g. FX below 285" />
          </label>
          <div className={styles.row}>
            <label className={styles.field}>
              Type
              <select value={form.rule_type} onChange={(e) => handleFieldChange("rule_type", e.target.value)}>
                {RULE_TYPES.map((t) => <option key={t}>{t}</option>)}
              </select>
            </label>
            <label className={styles.field}>
              Metric
              <select value={form.metric} onChange={(e) => handleFieldChange("metric", e.target.value)}>
                {(METRICS[form.rule_type] ?? []).map((m) => <option key={m}>{m}</option>)}
              </select>
            </label>
            <label className={styles.field}>
              Comparison
              <select value={form.comparison} onChange={(e) => handleFieldChange("comparison", e.target.value)}>
                <option value="lt">less than (&lt;)</option>
                <option value="gt">greater than (&gt;)</option>
                <option value="eq">equals</option>
              </select>
            </label>
          </div>
          <div className={styles.row}>
            {isTextMetric ? (
              <label className={styles.field}>
                Threshold (text)
                <input
                  value={form.threshold_text ?? ""}
                  onChange={(e) => handleFieldChange("threshold_text", e.target.value)}
                  placeholder={form.metric === "news_sentiment" ? "e.g. COPPER:0.60" : "e.g. HIGH"}
                />
              </label>
            ) : (
              <label className={styles.field}>
                Threshold value
                <input
                  type="number"
                  step="any"
                  value={form.threshold_value ?? ""}
                  onChange={(e) => handleFieldChange("threshold_value", parseFloat(e.target.value))}
                />
              </label>
            )}
            <label className={styles.field}>
              Email recipients
              <input
                value={form.email_recipients ?? ""}
                onChange={(e) => handleFieldChange("email_recipients", e.target.value)}
                placeholder="comma-separated (optional)"
              />
            </label>
          </div>
          <button className={styles.saveBtn} type="submit" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Saving…" : "Save Rule"}
          </button>
        </form>
      )}

      <div className={styles.ruleList}>
        {rules.data?.map((rule) => (
          <div key={rule.id} className={`${styles.ruleRow} ${!rule.enabled ? styles.disabled : ""}`}>
            <div className={styles.ruleInfo}>
              <span className={styles.ruleName}>{rule.name}</span>
              <span className={styles.ruleType}>{rule.rule_type}</span>
            </div>
            <div className={styles.ruleActions}>
              <button
                className={rule.enabled ? styles.toggleOn : styles.toggleOff}
                onClick={() => toggleMutation.mutate(rule)}
                title={rule.enabled ? "Disable" : "Enable"}
              >
                {rule.enabled ? "ON" : "OFF"}
              </button>
              <button className={styles.deleteBtn} onClick={() => deleteMutation.mutate(rule.id)} title="Delete">✕</button>
            </div>
          </div>
        ))}
      </div>

      <section>
        <h3 className={styles.sectionTitle}>Recent Events</h3>
        {events.data?.length === 0 && <p className={styles.muted}>No alerts triggered yet.</p>}
        {events.data?.map((ev) => (
          <div key={ev.id} className={styles.eventRow}>
            <span className={styles.eventTime}>{timeAgo(ev.triggered_at)}</span>
            <div>
              <span className={styles.eventName}>{ev.rule_name}</span>
              <p className={styles.eventMsg}>{ev.message}</p>
            </div>
          </div>
        ))}
      </section>
    </div>
  );
}
