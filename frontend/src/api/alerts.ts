import { get, post } from "./client";
import type { AlertRule, AlertEvent } from "../types";

export const fetchAlertRules = () => get<AlertRule[]>("/api/v1/alerts/rules");
export const fetchAlertEvents = (limit = 20) => get<AlertEvent[]>(`/api/v1/alerts/events?limit=${limit}`);

export const createAlertRule = (rule: Omit<AlertRule, "id" | "created_at">) =>
  post<AlertRule>("/api/v1/alerts/rules", rule);

export const toggleAlertRule = (rule: AlertRule) =>
  fetch(`/api/v1/alerts/rules/${rule.id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...rule, enabled: !rule.enabled }),
  }).then((r) => r.json() as Promise<AlertRule>);

export const deleteAlertRule = (id: number) =>
  fetch(`/api/v1/alerts/rules/${id}`, { method: "DELETE" });

export const triggerManualCheck = () =>
  post<AlertEvent[]>("/api/v1/alerts/check", {});
