import { get } from "./client";
import type { NewsItem } from "../types";

export const fetchNews = (days = 7, topic?: string) => {
  const params = new URLSearchParams({ days: String(days) });
  if (topic) params.set("topic", topic);
  return get<NewsItem[]>(`/api/v1/news/?${params}`);
};
