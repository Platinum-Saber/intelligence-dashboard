import { get, post, put, del } from "./client";
import type { AlertRule, AlertEvent } from "../types";

export const fetchAlertRules = () => get<AlertRule[]>("/api/v1/alerts/rules");
export const fetchAlertEvents = (limit = 20) => get<AlertEvent[]>(`/api/v1/alerts/events?limit=${limit}`);

export const createAlertRule = (rule: Omit<AlertRule, "id" | "created_at">) =>
  post<AlertRule>("/api/v1/alerts/rules", rule);

export const toggleAlertRule = (rule: AlertRule) =>
  put<AlertRule>(`/api/v1/alerts/rules/${rule.id}`, { ...rule, enabled: !rule.enabled });

export const deleteAlertRule = (id: number) =>
  del(`/api/v1/alerts/rules/${id}`);

export const triggerManualCheck = () =>
  post<AlertEvent[]>("/api/v1/alerts/check", {});
