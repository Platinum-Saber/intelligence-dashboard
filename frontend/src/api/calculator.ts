import { get, post } from "./client";
import type { LandedCostRequest, LandedCostResponse, CostHistoryPoint } from "../types";

export const calcLandedCost = (req: LandedCostRequest) =>
  post<LandedCostResponse>("/api/v1/calculator/landed-cost", req);

export const fetchCostHistory = (material: string, quantityTonnes: number, days: number) =>
  get<CostHistoryPoint[]>(
    `/api/v1/calculator/history?material=${material}&quantity_tonnes=${quantityTonnes}&days=${days}`
  );
