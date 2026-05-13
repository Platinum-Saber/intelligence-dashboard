import { get } from "./client";
import type { FXRate, FXSummary } from "../types";

export const fetchFXLatest = () => get<FXRate>("/api/v1/fx/latest");
export const fetchFXHistory = (days = 30) => get<FXRate[]>(`/api/v1/fx/history?days=${days}`);
export const fetchFXSummary = () => get<FXSummary>("/api/v1/fx/summary");
