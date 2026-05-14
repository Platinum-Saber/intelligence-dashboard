import { get, post, put, del } from "./client";

export interface CBSLRateOut {
  id: number;
  effective_date: string;
  rate: number;
  note: string | null;
}

export interface CBSLRateIn {
  effective_date: string;
  rate: number;
  note?: string | null;
}

export const fetchCBSLHistory = (days = 90) =>
  get<CBSLRateOut[]>(`/api/v1/fx/cbsl/history?days=${days}`);

export const listCBSLRates = () =>
  get<CBSLRateOut[]>("/api/v1/fx/cbsl/");

export const createCBSLRate = (body: CBSLRateIn) =>
  post<CBSLRateOut>("/api/v1/fx/cbsl/", body);

export const updateCBSLRate = (id: number, body: CBSLRateIn) =>
  put<CBSLRateOut>(`/api/v1/fx/cbsl/${id}`, body);

export const deleteCBSLRate = (id: number) =>
  del(`/api/v1/fx/cbsl/${id}`);
