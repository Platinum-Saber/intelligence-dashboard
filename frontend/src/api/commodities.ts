import { get } from "./client";
import type { CommodityPrice, CommoditySummary } from "../types";

export const fetchLatest = (symbol: string) =>
  get<CommodityPrice>(`/api/v1/commodities/${symbol}/latest`);

export const fetchHistory = (symbol: string, days = 30) =>
  get<CommodityPrice[]>(`/api/v1/commodities/${symbol}/history?days=${days}`);

export const fetchSummary = (symbol: string) =>
  get<CommoditySummary>(`/api/v1/commodities/${symbol}/summary`);
