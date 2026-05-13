import { post } from "./client";
import type { LandedCostRequest, LandedCostResponse } from "../types";

export const calcLandedCost = (req: LandedCostRequest) =>
  post<LandedCostResponse>("/api/v1/calculator/landed-cost", req);
